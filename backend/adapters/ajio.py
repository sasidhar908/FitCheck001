"""
AJIO-specific product extraction adapter.
Priority order:
1. Embedded AJIO Redux state (`window.__PRELOADED_STATE__`)
2. JSON-LD (`@type: Product`)
3. OpenGraph / HTML Meta + AJIO DOM selectors
"""

from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Optional
from ..schemas import (
    ProductAvailability,
    ProductImages,
    ProductPricing,
    ProductResponse,
    ProductSizes,
    SizeMeasurementRow,
    SizeVariant,
)
from .common import (
    SimpleDOMParser,
    build_size_chart_from_rows,
    compute_discount_percentage,
    convert_to_cm,
    extract_json_ld_products,
    finalize_product_response,
    infer_garment_type,
    is_blocked_or_challenge_page,
    normalize_size_label,
    parse_float,
    parse_html_document,
)


class AjioExtractor:
    RETAILER_NAME = "AJIO"

    @classmethod
    def extract_from_html(
        cls,
        html: str,
        url: str,
        product_id: Optional[str] = None,
        status_code: int = 200,
    ) -> ProductResponse:
        resolved_id = product_id or cls._extract_id_from_url(url) or "ajio_unknown"
        product = ProductResponse(
            product_id=str(resolved_id),
            retailer=cls.RETAILER_NAME,
            original_url=url,
        )

        blocked, block_reason = is_blocked_or_challenge_page(html, status_code)
        if blocked:
            product.extraction.status = "blocked"
            product.extraction.source = "none"
            product.extraction.error_code = "RETAILER_ACCESS_BLOCKED"
            product.extraction.error_message = (
                block_reason
                or "AJIO blocked automated access to this product page. Please use Manual Entry or paste page source."
            )
            return finalize_product_response(product)

        dom = parse_html_document(html)

        # Priority 1: Embedded Redux State (`window.__PRELOADED_STATE__`)
        preloaded = cls._extract_preloaded_state(dom)
        if preloaded:
            cls._populate_from_preloaded_state(product, preloaded)
            product.extraction.source = "embedded_json"

        # Priority 2: JSON-LD structured product metadata
        json_ld_items = extract_json_ld_products(dom)
        if json_ld_items:
            cls._populate_from_json_ld(product, json_ld_items[0])
            if product.extraction.source == "unknown":
                product.extraction.source = "json_ld"

        # Priority 3: HTML metadata and AJIO-specific selectors
        cls._populate_from_html_meta_and_selectors(product, dom)
        if product.extraction.source == "unknown" and (product.name or product.images.primary_image):
            product.extraction.source = "html_selectors"

        return finalize_product_response(product)

    @staticmethod
    def _extract_id_from_url(url: str) -> Optional[str]:
        match = re.search(r"/p/([a-zA-Z0-9_-]{5,32})", url)
        return match.group(1) if match else None

    @classmethod
    def _extract_preloaded_state(cls, dom: SimpleDOMParser) -> Optional[Dict[str, Any]]:
        for _attrs, script_text in dom.scripts:
            text = script_text.strip()
            if "__PRELOADED_STATE__" not in text and "productDetails" not in text:
                continue

            idx = text.find("__PRELOADED_STATE__")
            if idx != -1:
                eq_idx = text.find("=", idx)
                if eq_idx != -1:
                    candidate = text[eq_idx + 1 :].strip().rstrip(";")
                    parsed = cls._safe_extract_json(candidate)
                    if parsed:
                        if isinstance(parsed.get("product"), dict) and isinstance(
                            parsed["product"].get("productDetails"), dict
                        ):
                            return parsed["product"]["productDetails"]
                        if isinstance(parsed.get("productDetails"), dict):
                            return parsed["productDetails"]
                        return parsed

            parsed = cls._safe_extract_json(text)
            if parsed and isinstance(parsed.get("productDetails"), dict):
                return parsed["productDetails"]

        return None

    @staticmethod
    def _safe_extract_json(raw: str) -> Optional[Dict[str, Any]]:
        start = raw.find("{")
        if start == -1:
            return None
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(raw)):
            ch = raw[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if not in_str:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            obj = json.loads(raw[start : i + 1])
                            return obj if isinstance(obj, dict) else None
                        except Exception:
                            return None
        return None

    @classmethod
    def _populate_from_preloaded_state(cls, product: ProductResponse, details: Dict[str, Any]) -> None:
        code = details.get("code") or details.get("baseProduct")
        if code:
            product.product_id = str(code)
            product.sku = str(code)

        product.name = details.get("name") or details.get("brickName") or product.name
        product.brand = (
            details.get("brandName")
            or (details.get("fnlColorVariantData", {}) or {}).get("brandName")
            or product.brand
        )
        product.category = details.get("brickName") or details.get("brickSubCategory") or product.category
        product.sub_category = details.get("brickSubCategory")
        product.gender = details.get("brickCategory") or details.get("gender") or product.gender

        # Description & featureData
        desc_parts: List[str] = []
        if details.get("description"):
            clean_desc = re.sub(r"<[^>]+>", " ", str(details["description"])).strip()
            if clean_desc:
                desc_parts.append(clean_desc)

        feature_data = details.get("featureData") if isinstance(details.get("featureData"), list) else []
        for feat in feature_data:
            if not isinstance(feat, dict):
                continue
            f_name = str(feat.get("name") or "").strip()
            vals = feat.get("featureValues") if isinstance(feat.get("featureValues"), list) else []
            v_str = ", ".join(str(v.get("value")) for v in vals if isinstance(v, dict) and v.get("value"))
            if not v_str:
                continue
            if "wash" in f_name.lower() or "fabric" in f_name.lower() or "material" in f_name.lower():
                product.fabric_care.append(f"{f_name}: {v_str}")
            if f_name:
                product.specifications[f_name] = v_str
                desc_parts.append(f"{f_name}: {v_str}")

        if desc_parts:
            product.description = " · ".join(desc_parts)

        # Images
        gallery: List[str] = []
        thumbnails: List[str] = []
        images = details.get("images") if isinstance(details.get("images"), list) else []
        for img in images:
            if not isinstance(img, dict):
                continue
            url = img.get("url")
            if not url or not isinstance(url, str):
                continue
            fmt = str(img.get("format") or "").lower()
            if fmt in ("superzoom", "zoom", "product", "main", ""):
                if url not in gallery:
                    gallery.append(url)
            elif fmt in ("thumbnail", "carticon", "listing"):
                if url not in thumbnails:
                    thumbnails.append(url)

        if not gallery and thumbnails:
            gallery = list(thumbnails)

        if gallery:
            product.images = ProductImages(
                primary_image=gallery[0],
                gallery=gallery,
                thumbnails=thumbnails or gallery,
                high_res_images=gallery,
            )

        # Pricing
        price_data = details.get("price") if isinstance(details.get("price"), dict) else {}
        was_price_data = details.get("wasPriceData") if isinstance(details.get("wasPriceData"), dict) else {}

        selling_price = parse_float(price_data.get("value") or price_data.get("formattedValue"))
        mrp = parse_float(was_price_data.get("value") or was_price_data.get("formattedValue") or selling_price)
        discount_pct = parse_float(details.get("discountPercent"))
        if discount_pct is not None:
            discount_int: Optional[int] = int(round(discount_pct))
        else:
            discount_int = compute_discount_percentage(mrp, selling_price)

        product.pricing = ProductPricing(
            mrp=mrp,
            selling_price=selling_price,
            discount_percentage=discount_int,
            discount_label=f"{discount_int}% OFF" if discount_int else None,
            currency="INR",
            offers=[],
        )

        # Sizes & Variant Options
        variant_options = details.get("variantOptions") if isinstance(details.get("variantOptions"), list) else []
        if not variant_options and isinstance(details.get("baseOptions"), list):
            for base_opt in details["baseOptions"]:
                if isinstance(base_opt, dict) and isinstance(base_opt.get("options"), list):
                    variant_options = base_opt["options"]
                    break

        size_variants: List[SizeVariant] = []
        size_availability: Dict[str, str] = {}
        available_labels: List[str] = []

        for opt in variant_options:
            if not isinstance(opt, dict):
                continue
            raw_label = str(opt.get("scDisplaySize") or opt.get("size") or opt.get("value") or "").strip()
            if not raw_label and isinstance(opt.get("variantOptionQualifiers"), list):
                for q in opt["variantOptionQualifiers"]:
                    if isinstance(q, dict) and q.get("qualifier") == "size":
                        raw_label = str(q.get("value") or "").strip()
            if not raw_label:
                continue

            norm_label = normalize_size_label(raw_label)
            stock_obj = opt.get("stock") if isinstance(opt.get("stock"), dict) else {}
            stock_status = str(stock_obj.get("stockLevelStatus") or "inStock").lower()
            stock_level = stock_obj.get("stockLevel")
            inv_count = int(stock_level) if isinstance(stock_level, (int, float)) else None
            is_avail = ("outofstock" not in stock_status) and (inv_count is None or inv_count > 0)

            size_variants.append(
                SizeVariant(
                    label=raw_label,
                    normalized_label=norm_label,
                    sku=str(opt.get("code")) if opt.get("code") else None,
                    available=is_avail,
                    inventory_count=inv_count,
                )
            )
            size_availability[norm_label] = "in_stock" if is_avail else "out_of_stock"
            if is_avail:
                available_labels.append(norm_label)

        # Size Chart (`sizeGuide` or `sizeChart` in AJIO details)
        chart_rows: List[SizeMeasurementRow] = []
        size_guide = details.get("sizeGuide") or details.get("sizeChart")
        unit = "in"
        if isinstance(size_guide, dict):
            unit = str(size_guide.get("unit") or "in")
            raw_rows = size_guide.get("measurements") or size_guide.get("rows") or []
            if isinstance(raw_rows, list):
                for r in raw_rows:
                    if not isinstance(r, dict):
                        continue
                    sz = normalize_size_label(str(r.get("size") or r.get("brandSize") or ""))
                    if not sz:
                        continue
                    chart_rows.append(
                        SizeMeasurementRow(
                            size=sz,
                            chest_cm=convert_to_cm(r.get("chest") or r.get("bust"), unit),
                            shoulder_cm=convert_to_cm(r.get("shoulder"), unit),
                            waist_cm=convert_to_cm(r.get("waist"), unit),
                            hip_cm=convert_to_cm(r.get("hip"), unit),
                            sleeve_length_cm=convert_to_cm(r.get("sleeve") or r.get("sleeveLength"), unit),
                            garment_length_cm=convert_to_cm(r.get("length") or r.get("garmentLength"), unit),
                            inseam_cm=convert_to_cm(r.get("inseam"), unit),
                            rise_cm=convert_to_cm(r.get("rise"), unit),
                            original_values=r,
                        )
                    )

        garment_type, _ = infer_garment_type(product.category, product.name)
        size_chart = build_size_chart_from_rows(
            chart_rows,
            garment_type=garment_type,
            source_unit=unit,
            notes="Measurements normalized to centimeters (cm) from AJIO size guide.",
        )

        product.sizes = ProductSizes(
            available_sizes=size_variants,
            size_chart=size_chart,
        )

        if size_variants and not available_labels:
            overall_status = "out_of_stock"
        elif available_labels or (not size_variants and selling_price is not None):
            overall_status = "in_stock"
        else:
            overall_status = "unknown"

        product.availability = ProductAvailability(
            product_status=overall_status,
            available_variants=available_labels,
            size_availability=size_availability,
        )

    @classmethod
    def _populate_from_json_ld(cls, product: ProductResponse, ld: Dict[str, Any]) -> None:
        if not product.name and ld.get("name"):
            product.name = str(ld["name"]).strip()
        if not product.brand:
            brand = ld.get("brand")
            if isinstance(brand, dict):
                product.brand = brand.get("name")
            elif isinstance(brand, str):
                product.brand = brand
        if not product.description and ld.get("description"):
            product.description = str(ld["description"]).strip()
        if not product.sku and ld.get("sku"):
            product.sku = str(ld["sku"])

        if not product.images.primary_image and ld.get("image"):
            imgs = ld["image"] if isinstance(ld["image"], list) else [ld["image"]]
            clean_imgs = [str(i) for i in imgs if isinstance(i, str) and i.startswith("http")]
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
            if product.pricing.selling_price is None:
                price = parse_float(offers.get("price") or offers.get("lowPrice"))
                if price is not None:
                    product.pricing.selling_price = price
                    if product.pricing.mrp is None:
                        product.pricing.mrp = parse_float(offers.get("highPrice")) or price
                    product.pricing.discount_percentage = compute_discount_percentage(
                        product.pricing.mrp, product.pricing.selling_price
                    )
            avail_str = str(offers.get("availability") or "").lower()
            if product.availability.product_status == "unknown":
                if "instock" in avail_str:
                    product.availability.product_status = "in_stock"
                elif "outofstock" in avail_str:
                    product.availability.product_status = "out_of_stock"

    @classmethod
    def _populate_from_html_meta_and_selectors(cls, product: ProductResponse, dom: SimpleDOMParser) -> None:
        meta_map: Dict[str, str] = {}
        for m in dom.metas:
            key = (m.get("property") or m.get("name") or "").lower()
            val = m.get("content") or ""
            if key and val:
                meta_map[key] = val

        if not product.brand and dom.elements_by_class.get("brand-name"):
            product.brand = dom.elements_by_class["brand-name"][0]
        if not product.name and dom.elements_by_class.get("prod-name"):
            product.name = dom.elements_by_class["prod-name"][0]
        if not product.name and meta_map.get("og:title"):
            raw_title = re.sub(r"\s*\|\s*AJIO.*$", "", meta_map["og:title"], flags=re.IGNORECASE)
            raw_title = re.sub(r"^Buy\s+", "", raw_title, flags=re.IGNORECASE).strip()
            product.name = raw_title

        if not product.description and meta_map.get("og:description"):
            product.description = meta_map["og:description"]

        if not product.images.primary_image and meta_map.get("og:image"):
            og_img = meta_map["og:image"]
            product.images = ProductImages(
                primary_image=og_img,
                gallery=[og_img],
                thumbnails=[og_img],
                high_res_images=[og_img],
            )

        if product.pricing.selling_price is None and dom.elements_by_class.get("prod-sp"):
            sp = parse_float(dom.elements_by_class["prod-sp"][0])
            if sp is not None:
                product.pricing.selling_price = sp
        if product.pricing.mrp is None and dom.elements_by_class.get("prod-cp"):
            cp = parse_float(dom.elements_by_class["prod-cp"][0])
            if cp is not None:
                product.pricing.mrp = cp
                product.pricing.discount_percentage = compute_discount_percentage(
                    product.pricing.mrp, product.pricing.selling_price
                )
