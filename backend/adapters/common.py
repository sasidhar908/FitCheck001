"""
Shared utilities for retailer adapters: measurement unit normalization,
anti-bot/block detection, JSON-LD extraction, and garment category classification.
"""

from __future__ import annotations
import json
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple
from ..schemas import (
    MissingFieldExplanation,
    ProductResponse,
    SizeChart,
    SizeMeasurementRow,
)

INCH_TO_CM = 2.54

STANDARD_SIZE_MAP = {
    "36": "XS",
    "38": "S",
    "39": "M",
    "40": "M",
    "42": "L",
    "44": "XL",
    "46": "XXL",
    "28": "28",
    "30": "30",
    "32": "32",
    "34": "34",
    "xs": "XS",
    "small": "S",
    "s": "S",
    "medium": "M",
    "m": "M",
    "large": "L",
    "l": "L",
    "xl": "XL",
    "x-large": "XL",
    "xxl": "XXL",
    "2xl": "XXL",
    "xxxl": "3XL",
    "3xl": "3XL",
}


class SimpleDOMParser(HTMLParser):
    """Lightweight stdlib HTML parser for extracting script tags, meta tags, and specific selectors."""

    def __init__(self) -> None:
        super().__init__()
        self.scripts: List[Tuple[Dict[str, str], str]] = []
        self.metas: List[Dict[str, str]] = []
        self.title: str = ""
        self.elements_by_class: Dict[str, List[str]] = {}
        self.images: List[Dict[str, str]] = []
        self._in_script: bool = False
        self._current_script_attrs: Dict[str, str] = {}
        self._current_script_buf: List[str] = []
        self._in_title: bool = False
        self._active_classes: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "script":
            self._in_script = True
            self._current_script_attrs = attr_dict
            self._current_script_buf = []
        elif tag.lower() == "meta":
            self.metas.append(attr_dict)
        elif tag.lower() == "title":
            self._in_title = True
        elif tag.lower() == "img":
            self.images.append(attr_dict)

        cls_str = attr_dict.get("class", "")
        if cls_str:
            self._active_classes.append(cls_str)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._in_script:
            self._in_script = False
            self.scripts.append((self._current_script_attrs, "".join(self._current_script_buf)))
            self._current_script_buf = []
        elif tag.lower() == "title":
            self._in_title = False
        if self._active_classes:
            self._active_classes.pop()

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._current_script_buf.append(data)
        elif self._in_title:
            self.title += data
        text = data.strip()
        if text and self._active_classes:
            for cls_group in self._active_classes:
                for cls_name in cls_group.split():
                    self.elements_by_class.setdefault(cls_name, []).append(text)


def parse_html_document(html: str) -> SimpleDOMParser:
    parser = SimpleDOMParser()
    parser.feed(html or "")
    return parser


def is_blocked_or_challenge_page(html: str, status_code: int = 200) -> Tuple[bool, Optional[str]]:
    """
    Detect if the response is an anti-bot challenge, CAPTCHA, or WAF block page.
    Never attempts to bypass protection; simply detects and reports honestly.
    """
    if status_code in (401, 403, 429, 503):
        return True, f"Retailer server denied automated access (HTTP {status_code})."

    if not html or len(html.strip()) < 40:
        return True, "Retailer returned an empty or truncated response."

    lowered = html.lower()
    has_product_signals = any(
        marker in lowered
        for marker in (
            "pdpdata",
            "__myx",
            "__preloaded_state__",
            "application/ld+json",
            "pdp-title",
            "prod-name",
        )
    )
    if has_product_signals:
        return False, None

    block_markers = [
        ("access denied", "Retailer WAF returned Access Denied (Akamai/Edge protection)."),
        ("edgesuite.net", "Retailer edge firewall blocked automated request."),
        ("verify you are human", "Retailer presented a human verification challenge (CAPTCHA)."),
        ("captcha-delivery", "Retailer presented a CAPTCHA security challenge."),
        ("cf-chl-bypass", "Cloudflare security challenge detected."),
        ("oops! something went wrong", "Retailer returned an error page instead of product details."),
    ]
    for marker, reason in block_markers:
        if marker in lowered:
            return True, reason

    return False, None


def normalize_size_label(raw_label: str) -> str:
    if not raw_label:
        return ""
    cleaned = str(raw_label).strip()
    key = cleaned.lower()
    return STANDARD_SIZE_MAP.get(key, cleaned.upper())


def parse_float(val: Any) -> Optional[float]:
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val) if val >= 0 else None
    text = str(val).strip()
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", text)
    if not cleaned:
        return None
    try:
        num = float(cleaned)
        return num if num >= 0 else None
    except ValueError:
        return None


def convert_to_cm(val: Any, unit: str = "in") -> Optional[float]:
    num = parse_float(val)
    if num is None or num <= 0:
        return None
    if unit.lower().startswith("in"):
        return round(num * INCH_TO_CM, 1)
    return round(num, 1)


def infer_garment_type(category: Optional[str], name: Optional[str]) -> Tuple[str, str]:
    """
    Infer normalized garment_type ('shirt', 'trousers', 'outerwear', 'dress', 'top', 'other')
    and try-on category class ('upper_body', 'lower_body', 'full_body').
    """
    combined = f"{category or ''} {name or ''}".lower()
    if any(k in combined for k in ("trouser", "pant", "jean", "chino", "cargo", "jogger", "short", "skirt")):
        return "trousers", "lower_body"
    if any(k in combined for k in ("blazer", "jacket", "coat", "cardigan", "sweater", "hoodie", "sweatshirt")):
        return "outerwear", "upper_body"
    if any(k in combined for k in ("dress", "gown", "jumpsuit", "kurta set", "saree")):
        return "dress", "full_body"
    if any(k in combined for k in ("shirt", "t-shirt", "tshirt", "polo", "kurta", "top", "blouse", "tunic")):
        return "shirt", "upper_body"
    return "other", "upper_body"


def extract_json_ld_products(dom: SimpleDOMParser) -> List[Dict[str, Any]]:
    """Extract all JSON-LD blocks representing @type Product."""
    products: List[Dict[str, Any]] = []
    for attrs, content in dom.scripts:
        if attrs.get("type", "").lower() == "application/ld+json" and content.strip():
            try:
                parsed = json.loads(content.strip())
                items = parsed if isinstance(parsed, list) else [parsed]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    item_type = item.get("@type", "")
                    if item_type == "Product" or (isinstance(item_type, list) and "Product" in item_type):
                        products.append(item)
                    elif "@graph" in item and isinstance(item["@graph"], list):
                        for node in item["@graph"]:
                            if isinstance(node, dict) and node.get("@type") == "Product":
                                products.append(node)
            except Exception:
                continue
    return products


def compute_discount_percentage(mrp: Optional[float], selling_price: Optional[float]) -> Optional[int]:
    if mrp is not None and selling_price is not None and mrp > 0 and selling_price <= mrp:
        diff = mrp - selling_price
        if diff <= 0:
            return 0
        return int(round((diff / mrp) * 100))
    return None


def build_size_chart_from_rows(
    rows: List[SizeMeasurementRow],
    garment_type: str,
    source_unit: str = "in",
    notes: Optional[str] = None,
) -> Optional[SizeChart]:
    if not rows:
        return None

    # Determine which measurement columns actually have non-null values
    candidate_columns = [
        ("chest_cm", "Chest (cm)"),
        ("shoulder_cm", "Shoulder (cm)"),
        ("waist_cm", "Waist (cm)"),
        ("hip_cm", "Hip (cm)"),
        ("sleeve_length_cm", "Sleeve (cm)"),
        ("garment_length_cm", "Length (cm)"),
        ("inseam_cm", "Inseam (cm)"),
        ("rise_cm", "Rise (cm)"),
        ("neck_cm", "Neck (cm)"),
    ]
    active_columns: List[str] = []
    for attr_name, _label in candidate_columns:
        if any(getattr(r, attr_name, None) is not None for r in rows):
            active_columns.append(attr_name)

    if not active_columns:
        # Even if only size labels were present without measurements, don't fabricate a chart
        return None

    return SizeChart(
        unit="cm",
        source_unit=source_unit,
        garment_category=garment_type,
        columns=active_columns,
        rows=rows,
        notes=notes,
    )


def finalize_product_response(product: ProductResponse) -> ProductResponse:
    """
    Evaluate field-level confidence, populate missing_fields with clear explanations,
    and update try_on_compatibility metadata.
    """
    missing: List[MissingFieldExplanation] = []
    confidence_map: Dict[str, float] = {}

    source_weight = {
        "official_endpoint": 0.98,
        "embedded_json": 0.96,
        "json_ld": 0.85,
        "html_selectors": 0.72,
        "playwright": 0.88,
        "gemini_assisted": 0.68,
        "manual_entry": 1.0,
    }.get(product.extraction.source, 0.5)

    if product.name:
        confidence_map["name"] = source_weight
    else:
        confidence_map["name"] = 0.0
        missing.append(MissingFieldExplanation("name", "Product title could not be found in page data."))

    if product.brand:
        confidence_map["brand"] = source_weight
    else:
        confidence_map["brand"] = 0.0
        missing.append(MissingFieldExplanation("brand", "Brand name was not present in extracted metadata."))

    if product.description:
        confidence_map["description"] = source_weight
    else:
        confidence_map["description"] = 0.0
        missing.append(MissingFieldExplanation("description", "Product description was not provided on page."))

    if product.images.primary_image:
        confidence_map["images"] = source_weight
    else:
        confidence_map["images"] = 0.0
        missing.append(MissingFieldExplanation("images", "No publicly accessible product images were found."))

    if product.pricing.selling_price is not None:
        confidence_map["pricing"] = source_weight
    else:
        confidence_map["pricing"] = 0.0
        missing.append(MissingFieldExplanation("pricing", "Selling price was unavailable in accessible markup."))

    if product.sizes.available_sizes:
        confidence_map["sizes"] = source_weight
    else:
        confidence_map["sizes"] = 0.0
        missing.append(MissingFieldExplanation("sizes", "Size variants were not exposed in static or embedded data."))

    if product.sizes.size_chart and product.sizes.size_chart.rows:
        confidence_map["size_chart"] = source_weight
    else:
        confidence_map["size_chart"] = 0.0
        missing.append(
            MissingFieldExplanation(
                "size_chart",
                "Garment measurement size chart was not provided by the retailer for this item.",
            )
        )

    product.extraction.field_confidence = confidence_map
    product.extraction.missing_fields = missing

    scores = list(confidence_map.values())
    product.extraction.overall_confidence = round(sum(scores) / len(scores), 2) if scores else 0.0

    if product.extraction.status not in ("blocked", "failed"):
        if product.name and (product.pricing.selling_price is not None or product.images.primary_image):
            if len(missing) == 0:
                product.extraction.status = "success"
            else:
                product.extraction.status = "partial"
        else:
            product.extraction.status = "failed"
            if not product.extraction.error_message:
                product.extraction.error_message = "Insufficient product data could be extracted from the page."

    # Update try-on compatibility metadata for Phase 2 modules
    garment_type, category_class = infer_garment_type(product.category, product.name)
    product.garment_type = garment_type
    in_stock_sizes = [s.normalized_label for s in product.sizes.available_sizes if s.available is not False]
    default_selected_size = in_stock_sizes[0] if in_stock_sizes else (
        product.sizes.available_sizes[0].normalized_label if product.sizes.available_sizes else None
    )
    measurement_keys = product.sizes.size_chart.columns if product.sizes.size_chart else []

    product.try_on_compatibility.ready_for_try_on = bool(product.images.primary_image and product.name)
    product.try_on_compatibility.selected_garment_image_url = product.images.primary_image
    product.try_on_compatibility.selected_size = default_selected_size
    product.try_on_compatibility.garment_category_class = category_class
    product.try_on_compatibility.measurement_keys_available = measurement_keys

    return product
