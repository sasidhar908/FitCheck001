"""
Myntra-specific product extraction adapter.
Priority order:
1. Embedded Myntra hydration state (`window.__myx` / `pdpData`)
2. JSON-LD (`@type: Product`)
3. OpenGraph / HTML Meta + Myntra DOM selectors
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


class MyntraExtractor:
    RETAILER_NAME = "Myntra"

    @classmethod
    def extract_from_html(
        cls,
        html: str,
        url: str,
        product_id: Optional[str] = None,
        status_code: int = 200,
    ) -> ProductResponse:
        resolved_id = product_id or cls._extract_id_from_url(url) or "myntra_unknown"
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
                or "Myntra blocked automated access to this product page. Please use Manual Entry or paste page source."
            )
            return finalize_product_response(product)

        dom = parse_html_document(html)

        # Priority 1: Embedded JSON (`window.__myx` / `pdpData`)
        pdp_data = cls._extract_pdp_data(html, dom)
        if pdp_data:
            cls._populate_from_pdp_data(product, pdp_data)
            product.extraction.source = "embedded_json"

        # Priority 2: JSON-LD structured product metadata
        json_ld_items = extract_json_ld_products(dom)
        if json_ld_items:
            cls._populate_from_json_ld(product, json_ld_items[0])
            if product.extraction.source == "unknown":
                product.extraction.source = "json_ld"

        # Priority 3: HTML metadata and Myntra-specific selectors
        cls._populate_from_html_meta_and_selectors(product, dom)
        if product.extraction.source == "unknown" and (product.name or product.images.primary_image):
            product.extraction.source = "html_selectors"

        return finalize_product_response(product)

    @staticmethod
    def _extract_id_from_url(url: str) -> Optional[str]:
        match = re.search(r"/(\d{5,12})(?:/buy)?/?$", url)
        return match.group(1) if match else None

    @classmethod
    def _extract_pdp_data(cls, html: str, dom: SimpleDOMParser) -> Optional[Dict[str, Any]]:
        for _attrs, script_text in dom.scripts:
            text = script_text.strip()
            if "pdpData" not in text and "__myx" not in text:
                continue

            # Pattern 1: window.__myx = {...}
            idx = text.find("window.__myx")
            if idx != -1:
                eq_idx = text.find("=", idx)
                if eq_idx != -1:
                    candidate = text[eq_idx + 1 :].strip().rstrip(";")
                    parsed = cls._safe_extract_json_object(candidate)
                    if parsed:
                        if isinstance(parsed.get("pdpData"), dict):
                            return parsed["pdpData"]
                        return parsed

            # Pattern 2: direct {"pdpData": {...}}
            parsed = cls._safe_extract_json_object(text)
            if parsed:
                if isinstance(parsed.get("pdpData"), dict):
                    return parsed["pdpData"]
                if "id" in parsed and ("sizes" in parsed or "mrp" in parsed):
                    return parsed

        return None

    @staticmethod
    def _safe_extract_json_object(raw: str) -> Optional[Dict[str, Any]]:
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
                        snippet = raw[start : i + 1]
                        try:
                            obj = json.loads(snippet)
                            return obj if isinstance(obj, dict) else None
                        except Exception:
                            return None
        return None

    @classmethod
    def _populate_from_pdp_data(cls, product: ProductResponse, pdp: Dict[str, Any]) -> None:
        if pdp.get("id"):
            product.product_id = str(pdp["id"])
            product.sku = str(pdp["id"])

        product.name = pdp.get("name") or product.name
        if isinstance(pdp.get("brand"), dict):
            product.brand = pdp["brand"].get("name") or product.brand
        elif isinstance(pdp.get("brand"), str):
            product.brand = pdp["brand"]

        # Category & Gender
        analytics = pdp.get("analytics") if isinstance(pdp.get("analytics"), dict) else {}
        article_type = pdp.get("articleType") if isinstance(pdp.get("articleType"), dict) else {}
        product.category = (
            article_type.get("typeName")
            or analytics.get("articleType")
            or analytics.get("subCategory")
            or product.category
        )
        product.sub_category = analytics.get("subCategory") or analytics.get("masterCategory")
        product.gender = pdp.get("gender") or analytics.get("gender") or product.gender

        # Description & Specifications
        descriptors = pdp.get("productDetails")
        if isinstance(descriptors, list):
            desc_parts: List[str] = []
            for item in descriptors:
                if not isinstance(item, dict):
                    continue
                title = (item.get("title") or "").strip().lower()
                desc_html = item.get("description") or ""
                clean_text = re.sub(r"<[^>]+>", " ", str(desc_html)).strip()
                clean_text = re.sub(r"\s+", " ", clean_text)
                if not clean_text:
                    continue
                if "material" in title or "care" in title:
                    product.fabric_care.append(clean_text)
                else:
                    desc_parts.append(clean_text)
            if desc_parts:
                product.description = " ".join(desc_parts)

        article_attr = pdp.get("articleAttributes")
        if isinstance(article_attr, dict):
            for k, v in article_attr.items():
                if v and isinstance(v, (str, int, float)):
                    product.specifications[str(k)] = str(v)

        # Images
        gallery: List[str] = []
        thumbnails: List[str] = []
        media = pdp.get("media") if isinstance(pdp.get("media"), dict) else {}
        albums = media.get("albums") if isinstance(media.get("albums"), list) else []
        for album in albums:
            if not isinstance(album, dict):
                continue
            images = album.get("images") if isinstance(album.get("images"), list) else []
            for img in images:
                if not isinstance(img, dict):
                    continue
                src = img.get("imageURL") or img.get("src") or img.get("secureSrc")
                if src and isinstance(src, str):
                    high_res = (
                        src.replace("($height)", "1440")
                        .replace("($width)", "1080")
                        .replace("($quality)", "90")
                    )
                    thumb = (
                        src.replace("($height)", "240")
                        .replace("($width)", "180")
                        .replace("($quality)", "75")
                    )
                    if high_res not in gallery:
                        gallery.append(high_res)
                    if thumb not in thumbnails:
                        thumbnails.append(thumb)

        if gallery:
            product.images = ProductImages(
                primary_image=gallery[0],
                gallery=gallery,
                thumbnails=thumbnails or gallery,
                high_res_images=gallery,
            )

        # Pricing
        mrp = parse_float(pdp.get("mrp"))
        price_obj = pdp.get("price") if isinstance(pdp.get("price"), dict) else {}
        if mrp is None:
            mrp = parse_float(price_obj.get("mrp"))

        selling_price = parse_float(price_obj.get("discounted"))
        if selling_price is None:
            selling_price = parse_float(pdp.get("discountedPrice") or pdp.get("sellingPrice") or mrp)

        discount_obj = pdp.get("discount") if isinstance(pdp.get("discount"), dict) else {}
        discount_label = discount_obj.get("displayLabel") or discount_obj.get("label")
        discount_pct = compute_discount_percentage(mrp, selling_price)

        offers: List[str] = []
        offers_list = pdp.get("offers") if isinstance(pdp.get("offers"), list) else []
        for off in offers_list:
            if isinstance(off, dict) and off.get("title"):
                offers.append(str(off["title"]))

        product.pricing = ProductPricing(
            mrp=mrp,
            selling_price=selling_price,
            discount_percentage=discount_pct,
            discount_label=discount_label,
            currency="INR",
            offers=offers,
        )

        # Sizes, Availability, and Size Chart Measurements
        raw_sizes = pdp.get("sizes") if isinstance(pdp.get("sizes"), list) else []
        size_variants: List[SizeVariant] = []
        chart_rows: List[SizeMeasurementRow] = []
        size_availability: Dict[str, str] = {}
        available_labels: List[str] = []

        for s in raw_sizes:
            if not isinstance(s, dict):
                continue
            raw_label = str(s.get("label") or s.get("size") or "").strip()
            if not raw_label:
                continue
            norm_label = normalize_size_label(raw_label)
            is_avail = bool(s.get("available", True))
            inv_count: Optional[int] = None
            seller_data = s.get("sizeSellerData")
            if isinstance(seller_data, list) and seller_data:
                total_inv = sum(
                    int(sd.get("availableCount", 0))
                    for sd in seller_data
                    if isinstance(sd, dict) and isinstance(sd.get("availableCount"), (int, float))
                )
                inv_count = total_inv
                if total_inv == 0 and "available" not in s:
                    is_avail = False

            # Parse size-specific garment measurements if Myntra provides them
            meas_list = s.get("measurements") if isinstance(s.get("measurements"), list) else []
            row = SizeMeasurementRow(size=norm_label, original_values={"brand_size": raw_label})
            meas_dict: Dict[str, Optional[float]] = {}
            has_row_meas = False

            for m in meas_list:
                if not isinstance(m, dict):
                    continue
                m_type = str(m.get("type") or m.get("name") or "").strip().lower()
                m_val = m.get("value") or m.get("minValue")
                m_unit = str(m.get("unit") or "in")
                cm_val = convert_to_cm(m_val, m_unit)
                if cm_val is None:
                    continue
                has_row_meas = True
                row.original_values[m_type] = f"{m_val} {m_unit}"
                if "chest" in m_type or "bust" in m_type:
                    row.chest_cm = cm_val
                    meas_dict["chest_cm"] = cm_val
                elif "shoulder" in m_type:
                    row.shoulder_cm = cm_val
                    meas_dict["shoulder_cm"] = cm_val
                elif "waist" in m_type:
                    row.waist_cm = cm_val
                    meas_dict["waist_cm"] = cm_val
                elif "hip" in m_type:
                    row.hip_cm = cm_val
                    meas_dict["hip_cm"] = cm_val
                elif "sleeve" in m_type:
                    row.sleeve_length_cm = cm_val
                    meas_dict["sleeve_length_cm"] = cm_val
                elif "inseam" in m_type:
                    row.inseam_cm = cm_val
                    meas_dict["inseam_cm"] = cm_val
                elif "rise" in m_type:
                    row.rise_cm = cm_val
                    meas_dict["rise_cm"] = cm_val
                elif "neck" in m_type:
                    row.neck_cm = cm_val
                    meas_dict["neck_cm"] = cm_val
                elif "length" in m_type or "front length" in m_type:
                    row.garment_length_cm = cm_val
                    meas_dict["garment_length_cm"] = cm_val

            if has_row_meas:
                chart_rows.append(row)

            size_variants.append(
                SizeVariant(
                    label=raw_label,
                    normalized_label=norm_label,
                    sku=str(s.get("skuId")) if s.get("skuId") else None,
                    available=is_avail,
                    inventory_count=inv_count,
                    measurements=meas_dict,
                )
            )
            size_availability[norm_label] = "in_stock" if is_avail else "out_of_stock"
            if is_avail:
                available_labels.append(norm_label)

        # Also check dedicated `sizeChart` block if present in pdpData
        if not chart_rows and isinstance(pdp.get("sizeChart"), dict):
            sc_rows = pdp["sizeChart"].get("rows")
            if isinstance(sc_rows, list):
                for r in sc_rows:
                    if not isinstance(r, dict):
                        continue
                    sz = normalize_size_label(str(r.get("size") or ""))
                    if not sz:
                        continue
                    unit = str(pdp["sizeChart"].get("unit") or "in")
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
                        original_values=r,
                    )
                    chart_rows.append(row)

        garment_type, _ = infer_garment_type(product.category, product.name)
        size_chart = build_size_chart_from_rows(
            chart_rows,
            garment_type=garment_type,
            source_unit="in",
            notes="Measurements normalized to centimeters (cm) from Myntra garment specifications.",
        )

        product.sizes = ProductSizes(
            available_sizes=size_variants,
            size_chart=size_chart,
        )

        flags = pdp.get("flags") if isinstance(pdp.get("flags"), dict) else {}
        out_of_stock_flag = bool(flags.get("outOfStock", False))
        if out_of_stock_flag or (size_variants and not available_labels):
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

        if not product.brand and dom.elements_by_class.get("pdp-title"):
            product.brand = dom.elements_by_class["pdp-title"][0]
        if not product.name and dom.elements_by_class.get("pdp-name"):
            product.name = dom.elements_by_class["pdp-name"][0]
        if not product.name and meta_map.get("og:title"):
            raw_title = re.sub(r"\s*\|\s*Myntra.*$", "", meta_map["og:title"], flags=re.IGNORECASE)
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

        if product.pricing.selling_price is None and dom.elements_by_class.get("pdp-price"):
            sp = parse_float(dom.elements_by_class["pdp-price"][0])
            if sp is not None:
                product.pricing.selling_price = sp
