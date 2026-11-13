"""
Shopify Storefront & Crawl4AI Extraction Adapter.

Workflow:
1. Validate URL, store domain, and product handle.
2. Check authorized Shopify Storefront API access (Storefront GraphQL API if token configured,
   plus authorized public Storefront JSON `/products/{handle}.json` and Ajax `/products/{handle}.js`).
3. Use Crawl4AIClient for permitted webpage extraction (JSON-LD, CSS/XPath selectors,
   and HTML garment size guide tables).
4. Merge and normalize into unified ProductResponse without fabricating any missing fields.
"""

from __future__ import annotations
import html as html_stdlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

from .adapters.common import (
    build_size_chart_from_rows,
    compute_discount_percentage,
    convert_to_cm,
    infer_garment_type,
    normalize_size_label,
    parse_float,
)
from .crawl4ai_client import Crawl4AIClient, Crawl4AIExtractionResult
from .product_validator import validate_safe_image_url
from .schemas import (
    ProductAvailability,
    ProductImages,
    ProductPricing,
    ProductResponse,
    ProductSizes,
    SizeMeasurementRow,
    SizeVariant,
)


class ShopifyExtractor:
    RETAILER_NAME = "Shopify"

    def __init__(
        self,
        crawl4ai_client: Optional[Crawl4AIClient] = None,
        storefront_token: Optional[str] = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.crawl4ai = crawl4ai_client or Crawl4AIClient(timeout_seconds=timeout_seconds)
        self.storefront_token = (
            storefront_token
            if storefront_token is not None
            else os.environ.get("SHOPIFY_STOREFRONT_ACCESS_TOKEN", "")
        ).strip()
        self.timeout_seconds = timeout_seconds

    def extract_product(
        self,
        url: str,
        store_domain: str,
        product_handle: str,
        raw_html_override: Optional[str] = None,
        storefront_json_override: Optional[Dict[str, Any]] = None,
        ajax_js_override: Optional[Dict[str, Any]] = None,
        http_fetcher: Optional[Callable[[str, Dict[str, str], Optional[bytes], float], Tuple[int, str]]] = None,
    ) -> ProductResponse:
        start_ts = time.perf_counter()
        fetcher = http_fetcher or self.crawl4ai._default_http_request

        product = ProductResponse(
            product_id=product_handle,
            retailer=self.RETAILER_NAME,
            original_url=url,
            store_domain=store_domain,
            product_handle=product_handle,
        )
        product.diagnostics.submitted_url = url
        product.diagnostics.detected_retailer = f"Shopify ({store_domain})"
        product.diagnostics.store_domain = store_domain
        product.diagnostics.product_handle = product_handle

        sources_used: List[str] = []
        http_statuses: List[int] = []

        # Step 1: Query Authorized Shopify Storefront Data
        storefront_product: Optional[Dict[str, Any]] = None
        ajax_product: Optional[Dict[str, Any]] = ajax_js_override

        if storefront_json_override is not None:
            storefront_product = storefront_json_override.get("product") or storefront_json_override
            sources_used.append("shopify_storefront_json")
            http_statuses.append(200)
        elif raw_html_override is None:
            # 1a. Optional Storefront GraphQL API if token is configured
            if self.storefront_token:
                gql_prod, gql_status = self._fetch_storefront_graphql(store_domain, product_handle, fetcher)
                if gql_status:
                    http_statuses.append(gql_status)
                if gql_prod:
                    storefront_product = gql_prod
                    sources_used.append("shopify_storefront_graphql")

            # 1b. Authorized Shopify Storefront Product JSON (/products/{handle}.json)
            if not storefront_product:
                json_url = f"https://{store_domain}/products/{product_handle}.json"
                sf_prod, sf_status = self._fetch_json_endpoint(json_url, fetcher)
                if sf_status:
                    http_statuses.append(sf_status)
                if isinstance(sf_prod, dict) and isinstance(sf_prod.get("product"), dict):
                    storefront_product = sf_prod["product"]
                    sources_used.append("shopify_storefront_json")

            # 1c. Shopify Ajax Product API (/products/{handle}.js) for real-time variant availability & currency
            if ajax_product is None:
                js_url = f"https://{store_domain}/products/{product_handle}.js"
                aj_prod, aj_status = self._fetch_json_endpoint(js_url, fetcher)
                if aj_status and not http_statuses:
                    http_statuses.append(aj_status)
                if isinstance(aj_prod, dict) and aj_prod.get("variants"):
                    ajax_product = aj_prod
                    if "shopify_ajax_js" not in sources_used:
                        sources_used.append("shopify_ajax_js")

        if storefront_product:
            self._populate_from_storefront_json(product, storefront_product, ajax_product)

        # Step 2: Run Crawl4AI Engine on the Product Webpage for HTML Size Charts, JSON-LD, and CSS/XPath metadata
        crawl_res: Crawl4AIExtractionResult = self.crawl4ai.crawl_product_page(
            url,
            raw_html_override=raw_html_override,
            http_fetcher=fetcher,
        )
        if crawl_res.http_status:
            http_statuses.append(crawl_res.http_status)

        product.diagnostics.crawl4ai_connection_status = crawl_res.crawl4ai_connection_status
        product.diagnostics.crawl4ai_endpoint = crawl_res.crawl4ai_endpoint
        product.diagnostics.browser_rendering_status = crawl_res.browser_rendering_status
        product.diagnostics.css_strategy_used = bool(crawl_res.css_extracted)
        product.diagnostics.xpath_strategy_used = bool(crawl_res.xpath_extracted)
        product.diagnostics.json_ld_found = bool(crawl_res.json_ld_objects)

        if crawl_res.blocked and not storefront_product:
            product.extraction.status = "blocked"
            product.extraction.source = "none"
            product.extraction.error_code = "RETAILER_ACCESS_BLOCKED"
            product.extraction.error_message = crawl_res.error_message
            product.diagnostics.http_response_status = crawl_res.http_status or 403
            product.diagnostics.error_details = crawl_res.error_message
            product.diagnostics.extraction_duration_ms = round((time.perf_counter() - start_ts) * 1000, 1)
            return product

        if crawl_res.success:
            sources_used.append("crawl4ai_engine")
            self._merge_crawl4ai_result(product, crawl_res)
        elif crawl_res.error_message and not storefront_product:
            product.extraction.status = "failed"
            product.extraction.error_code = "EXTRACTION_FAILED"
            product.extraction.error_message = crawl_res.error_message
            product.diagnostics.error_details = crawl_res.error_message

        # Record provenance & diagnostics
        if "shopify_storefront_json" in sources_used and "crawl4ai_engine" in sources_used:
            product.extraction.source = "shopify_storefront_and_crawl4ai"
            product.diagnostics.authorized_data_source = "Shopify Storefront JSON + Crawl4AI Webpage Engine"
            product.diagnostics.extraction_method = "Storefront API + Crawl4AI (JSON-LD + CSS/XPath + Size Table)"
        elif any(s.startswith("shopify_") for s in sources_used):
            product.extraction.source = "shopify_storefront_api"
            product.diagnostics.authorized_data_source = "Shopify Storefront API"
            product.diagnostics.extraction_method = "Shopify Storefront JSON / Ajax API"
        elif "crawl4ai_engine" in sources_used:
            product.extraction.source = "crawl4ai_engine"
            product.diagnostics.authorized_data_source = "Crawl4AI Permitted Webpage Extraction"
            product.diagnostics.extraction_method = "Crawl4AI (JSON-LD + CSS + XPath)"
        else:
            product.extraction.source = "none"
            product.diagnostics.authorized_data_source = "None"
            product.diagnostics.extraction_method = "Failed"

        product.diagnostics.http_response_status = http_statuses[0] if http_statuses else crawl_res.http_status
        product.diagnostics.extraction_duration_ms = round((time.perf_counter() - start_ts) * 1000, 1)
        return product

    def _fetch_json_endpoint(
        self,
        endpoint_url: str,
        fetcher: Callable[[str, Dict[str, str], Optional[bytes], float], Tuple[int, str]],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AtelierFit/1.0)",
            "Accept": "application/json",
        }
        try:
            status, body = fetcher(endpoint_url, headers, None, self.timeout_seconds)
            if 200 <= status < 300 and body.strip():
                return json.loads(body), status
            return None, status
        except Exception:
            return None, None

    def _fetch_storefront_graphql(
        self,
        store_domain: str,
        handle: str,
        fetcher: Callable[[str, Dict[str, str], Optional[bytes], float], Tuple[int, str]],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        endpoint = f"https://{store_domain}/api/2024-10/graphql.json"
        query = """
        query getProductByHandle($handle: String!) {
          product(handle: $handle) {
            id
            title
            handle
            vendor
            productType
            description
            availableForSale
            images(first: 12) {
              edges { node { url altText } }
            }
            variants(first: 30) {
              edges {
                node {
                  id
                  title
                  sku
                  availableForSale
                  price { amount currencyCode }
                  compareAtPrice { amount currencyCode }
                }
              }
            }
          }
        }
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Shopify-Storefront-Access-Token": self.storefront_token,
        }
        payload = json.dumps({"query": query, "variables": {"handle": handle}}).encode("utf-8")
        try:
            status, body = fetcher(endpoint, headers, payload, self.timeout_seconds)
            if 200 <= status < 300:
                parsed = json.loads(body)
                node = (parsed.get("data") or {}).get("product")
                if isinstance(node, dict):
                    return self._convert_graphql_node_to_rest_shape(node), status
            return None, status
        except Exception:
            return None, None

    @staticmethod
    def _convert_graphql_node_to_rest_shape(node: Dict[str, Any]) -> Dict[str, Any]:
        images = [
            {"src": edge["node"]["url"]}
            for edge in ((node.get("images") or {}).get("edges") or [])
            if isinstance(edge, dict) and isinstance(edge.get("node"), dict) and edge["node"].get("url")
        ]
        variants = []
        currency = "USD"
        for edge in ((node.get("variants") or {}).get("edges") or []):
            vnode = edge.get("node") if isinstance(edge, dict) else None
            if not isinstance(vnode, dict):
                continue
            price_obj = vnode.get("price") or {}
            comp_obj = vnode.get("compareAtPrice") or {}
            if price_obj.get("currencyCode"):
                currency = price_obj["currencyCode"]
            variants.append(
                {
                    "id": vnode.get("id"),
                    "title": vnode.get("title"),
                    "sku": vnode.get("sku"),
                    "available": bool(vnode.get("availableForSale", True)),
                    "price": price_obj.get("amount"),
                    "compare_at_price": comp_obj.get("amount"),
                    "currency": currency,
                }
            )
        return {
            "id": node.get("id"),
            "title": node.get("title"),
            "handle": node.get("handle"),
            "vendor": node.get("vendor"),
            "product_type": node.get("productType"),
            "body_html": node.get("description") or "",
            "images": images,
            "variants": variants,
            "currency": currency,
        }

    def _populate_from_storefront_json(
        self,
        product: ProductResponse,
        sf: Dict[str, Any],
        ajax_js: Optional[Dict[str, Any]] = None,
    ) -> None:
        if sf.get("id"):
            product.sku = str(sf["id"])
        product.name = str(sf.get("title") or "").strip() or product.name
        product.brand = str(sf.get("vendor") or "").strip() or product.brand
        product.category = str(sf.get("product_type") or "").strip() or product.category

        # Parse tags for gender/category/specifications
        raw_tags = sf.get("tags")
        tags_list: List[str] = []
        if isinstance(raw_tags, str):
            tags_list = [t.strip() for t in raw_tags.split(",") if t.strip()]
        elif isinstance(raw_tags, list):
            tags_list = [str(t).strip() for t in raw_tags if str(t).strip()]

        for tag in tags_list:
            lower_t = tag.lower()
            if lower_t in ("men", "mens", "men's"):
                product.gender = "Men"
            elif lower_t in ("women", "womens", "women's"):
                product.gender = "Women"
            elif lower_t == "unisex":
                product.gender = "Unisex"
            if ":" in tag:
                k, v = tag.split(":", 1)
                k_clean = k.strip()
                v_clean = v.strip()
                if k_clean and v_clean and len(k_clean) < 28 and not k_clean.lower().startswith("category -"):
                    product.specifications[k_clean] = v_clean

        if not product.gender and product.name:
            lname = product.name.lower()
            if "women" in lname:
                product.gender = "Women"
            elif "men" in lname:
                product.gender = "Men"

        # Clean body_html description
        body_html = str(sf.get("body_html") or "")
        if body_html:
            clean_desc = re.sub(r"<[^>]+>", " ", body_html)
            clean_desc = re.sub(r"\s+", " ", html_stdlib.unescape(clean_desc)).strip()
            if clean_desc:
                product.description = clean_desc

        # Images
        gallery: List[str] = []
        thumbnails: List[str] = []
        raw_images = sf.get("images") if isinstance(sf.get("images"), list) else []
        for img in raw_images:
            src = img.get("src") if isinstance(img, dict) else str(img)
            safe_src = validate_safe_image_url(src)
            if safe_src and safe_src not in gallery:
                gallery.append(safe_src)
                # Build Shopify CDN thumbnail URL (_400x) if applicable
                thumb_src = re.sub(r"\.(jpg|jpeg|png|webp)(\?.*)?$", r"_400x.\1\2", safe_src, flags=re.I)
                thumbnails.append(thumb_src)

        if gallery:
            product.images = ProductImages(
                primary_image=gallery[0],
                gallery=gallery,
                thumbnails=thumbnails or gallery,
                high_res_images=gallery,
            )

        # Build availability map from ajax_js if present
        ajax_avail_by_id: Dict[str, bool] = {}
        if isinstance(ajax_js, dict) and isinstance(ajax_js.get("variants"), list):
            for av in ajax_js["variants"]:
                if isinstance(av, dict) and av.get("id") is not None and "available" in av:
                    ajax_avail_by_id[str(av["id"])] = bool(av["available"])

        # Variants & Pricing
        raw_variants = sf.get("variants") if isinstance(sf.get("variants"), list) else []
        size_variants: List[SizeVariant] = []
        size_availability: Dict[str, str] = {}
        available_labels: List[str] = []
        seen_labels = set()

        first_selling_price: Optional[float] = None
        first_mrp: Optional[float] = None
        currency = str(sf.get("currency") or "USD")

        for v in raw_variants:
            if not isinstance(v, dict):
                continue
            vid = str(v.get("id") or "")
            raw_title = str(v.get("option1") or v.get("title") or "").strip()
            if not raw_title or raw_title.lower() == "default title":
                raw_title = "One Size"

            # Parse labels like "XS - 36" or "S - 38" or "32"
            parts = [p.strip() for p in re.split(r"[\u2013\u2014\-/]", raw_title) if p.strip()]
            if len(parts) >= 2 and parts[0].upper() in ("XXS", "XS", "S", "M", "L", "XL", "XXL", "2XL", "3XL"):
                norm_label = parts[0].upper()
            elif len(parts) >= 2 and parts[-1].upper() in ("XXS", "XS", "S", "M", "L", "XL", "XXL", "2XL", "3XL"):
                norm_label = parts[-1].upper()
            else:
                norm_label = normalize_size_label(parts[0] if parts else raw_title)

            v_price = parse_float(v.get("price"))
            v_compare = parse_float(v.get("compare_at_price"))
            if first_selling_price is None and v_price is not None:
                first_selling_price = v_price
            if first_mrp is None and v_compare is not None and v_compare > 0:
                first_mrp = v_compare

            if vid in ajax_avail_by_id:
                is_avail = ajax_avail_by_id[vid]
            elif "available" in v and v.get("available") is not None:
                is_avail = bool(v.get("available"))
            else:
                is_avail = True

            # Deduplicate multi-inseam variants by normalized size label while preserving availability if any variant of that size is in stock
            if norm_label in seen_labels:
                if is_avail:
                    size_availability[norm_label] = "in_stock"
                    if norm_label not in available_labels:
                        available_labels.append(norm_label)
                    for existing_sv in size_variants:
                        if existing_sv.normalized_label == norm_label:
                            existing_sv.available = True
                continue

            seen_labels.add(norm_label)
            size_variants.append(
                SizeVariant(
                    label=raw_title,
                    normalized_label=norm_label,
                    sku=str(v.get("sku") or vid) if (v.get("sku") or vid) else None,
                    variant_id=vid or None,
                    available=is_avail,
                    price=v_price,
                    compare_at_price=v_compare,
                )
            )
            size_availability[norm_label] = "in_stock" if is_avail else "out_of_stock"
            if is_avail:
                available_labels.append(norm_label)

        if first_mrp is None and first_selling_price is not None:
            first_mrp = first_selling_price
        discount_pct = compute_discount_percentage(first_mrp, first_selling_price)

        product.pricing = ProductPricing(
            mrp=first_mrp,
            selling_price=first_selling_price,
            discount_percentage=discount_pct,
            discount_label=f"{discount_pct}% OFF" if discount_pct else None,
            currency=currency,
        )
        product.sizes.available_sizes = size_variants
        product.availability = ProductAvailability(
            product_status="in_stock" if available_labels else ("out_of_stock" if size_variants else "unknown"),
            available_variants=available_labels,
            size_availability=size_availability,
        )

    def _merge_crawl4ai_result(self, product: ProductResponse, crawl_res: Crawl4AIExtractionResult) -> None:
        # 1. Enrich from JSON-LD (`Product` or `ProductGroup`)
        for ld in crawl_res.json_ld_objects:
            if not product.name and ld.get("name"):
                product.name = str(ld["name"]).strip()
            if not product.brand:
                brand = ld.get("brand")
                if isinstance(brand, dict):
                    product.brand = brand.get("name")
                elif isinstance(brand, str):
                    product.brand = brand
            # Prefer richer JSON-LD description if Storefront body_html was just a 1-liner
            ld_desc = str(ld.get("description") or "").strip()
            if ld_desc and (not product.description or len(ld_desc) > len(product.description)):
                product.description = html_stdlib.unescape(re.sub(r"<[^>]+>", " ", ld_desc)).strip()

            if not product.images.primary_image and ld.get("image"):
                imgs = ld["image"] if isinstance(ld["image"], list) else [ld["image"]]
                safe_imgs = [validate_safe_image_url(str(i)) for i in imgs if isinstance(i, str)]
                clean_imgs = [i for i in safe_imgs if i]
                if clean_imgs:
                    product.images = ProductImages(
                        primary_image=clean_imgs[0],
                        gallery=clean_imgs,
                        thumbnails=clean_imgs,
                        high_res_images=clean_imgs,
                    )

            offers = ld.get("offers")
            if isinstance(offers, list) and offers:
                offers = offers[0]
            if isinstance(offers, dict):
                if offers.get("priceCurrency"):
                    product.pricing.currency = str(offers["priceCurrency"])
                if product.pricing.selling_price is None:
                    sp = parse_float(offers.get("price") or offers.get("lowPrice"))
                    if sp is not None:
                        product.pricing.selling_price = sp
                        product.pricing.mrp = parse_float(offers.get("highPrice")) or sp
                        product.pricing.discount_percentage = compute_discount_percentage(
                            product.pricing.mrp, product.pricing.selling_price
                        )

            # Check ProductGroup.hasVariant if variants weren't populated yet
            if not product.sizes.available_sizes and isinstance(ld.get("hasVariant"), list):
                self._populate_variants_from_json_ld_group(product, ld["hasVariant"])

        # 2. Enrich from Crawl4AI CSS & XPath strategies
        css = crawl_res.css_extracted
        xpath = crawl_res.xpath_extracted

        if not product.name:
            product.name = css.get("title") or xpath.get("og_title")
        if not product.brand:
            product.brand = css.get("vendor")
        if not product.description:
            product.description = css.get("description") or xpath.get("og_description")
        if product.pricing.selling_price is None:
            sp = parse_float(css.get("price") or xpath.get("og_price"))
            if sp is not None:
                product.pricing.selling_price = sp
                product.pricing.mrp = parse_float(css.get("compare_at_price")) or sp
        if xpath.get("og_currency"):
            product.pricing.currency = str(xpath["og_currency"])

        if not product.images.primary_image:
            og_img = validate_safe_image_url(xpath.get("og_image"))
            candidate_imgs = [og_img] if og_img else []
            for m_img in crawl_res.media_images:
                if m_img not in candidate_imgs:
                    candidate_imgs.append(m_img)
            if candidate_imgs:
                product.images = ProductImages(
                    primary_image=candidate_imgs[0],
                    gallery=candidate_imgs[:12],
                    thumbnails=candidate_imgs[:12],
                    high_res_images=candidate_imgs[:12],
                )

        # 3. Populate Garment Size Chart extracted by Crawl4AI HTML Table Parser
        if crawl_res.extracted_size_chart_rows and not product.sizes.size_chart:
            unit = crawl_res.size_chart_unit or "in"
            chart_rows: List[SizeMeasurementRow] = []
            for r in crawl_res.extracted_size_chart_rows:
                sz = normalize_size_label(str(r.get("size") or ""))
                if not sz:
                    continue
                row = SizeMeasurementRow(
                    size=sz,
                    chest_cm=convert_to_cm(r.get("chest"), unit),
                    shoulder_cm=convert_to_cm(r.get("shoulder"), unit),
                    waist_cm=convert_to_cm(r.get("waist"), unit),
                    hip_cm=convert_to_cm(r.get("hip"), unit),
                    sleeve_length_cm=convert_to_cm(r.get("sleeve"), unit),
                    garment_length_cm=convert_to_cm(r.get("length"), unit),
                    inseam_cm=convert_to_cm(r.get("inseam"), unit),
                    rise_cm=convert_to_cm(r.get("rise"), unit),
                    neck_cm=convert_to_cm(r.get("neck"), unit),
                    thigh_cm=convert_to_cm(r.get("thigh"), unit),
                    original_values=r,
                )
                chart_rows.append(row)

                # Attach per-size measurements onto matching SizeVariant objects
                for sv in product.sizes.available_sizes:
                    if sv.normalized_label == sz:
                        sv.measurements = {
                            k: getattr(row, k)
                            for k in (
                                "chest_cm",
                                "shoulder_cm",
                                "waist_cm",
                                "hip_cm",
                                "sleeve_length_cm",
                                "garment_length_cm",
                                "inseam_cm",
                                "rise_cm",
                                "neck_cm",
                            )
                            if getattr(row, k) is not None
                        }

            garment_type, _ = infer_garment_type(product.category, product.name)
            product.sizes.size_chart = build_size_chart_from_rows(
                chart_rows,
                garment_type=garment_type,
                source_unit=unit,
                notes=f"Extracted from retailer size guide table via Crawl4AI and normalized from {unit} to centimeters (cm).",
            )

    @staticmethod
    def _populate_variants_from_json_ld_group(product: ProductResponse, variants_ld: List[ Any]) -> None:
        size_variants: List[SizeVariant] = []
        size_availability: Dict[str, str] = {}
        available_labels: List[str] = []
        seen = set()

        for v in variants_ld:
            if not isinstance(v, dict):
                continue
            raw_size = str(v.get("size") or v.get("name") or "").strip()
            if not raw_size:
                continue
            norm = normalize_size_label(raw_size)
            if norm in seen:
                continue
            seen.add(norm)
            offers = v.get("offers") if isinstance(v.get("offers"), dict) else {}
            avail_str = str(offers.get("availability") or "").lower()
            is_avail = "outofstock" not in avail_str
            v_price = parse_float(offers.get("price"))
            if product.pricing.selling_price is None and v_price is not None:
                product.pricing.selling_price = v_price
                product.pricing.mrp = v_price
                if offers.get("priceCurrency"):
                    product.pricing.currency = str(offers["priceCurrency"])

            size_variants.append(
                SizeVariant(
                    label=raw_size,
                    normalized_label=norm,
                    sku=str(v.get("sku") or ""),
                    available=is_avail,
                    price=v_price,
                )
            )
            size_availability[norm] = "in_stock" if is_avail else "out_of_stock"
            if is_avail:
                available_labels.append(norm)

        if size_variants:
            product.sizes.available_sizes = size_variants
            product.availability = ProductAvailability(
                product_status="in_stock" if available_labels else "out_of_stock",
                available_variants=available_labels,
                size_availability=size_availability,
            )
