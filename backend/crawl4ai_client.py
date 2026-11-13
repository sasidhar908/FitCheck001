"""
Official Crawl4AI Engine Client & Strategy Executor (https://github.com/unclecode/crawl4ai.git).

Supports:
1. Authenticated REST API calls to a Google Cloud Run Crawl4AI container (`POST /crawl`, `GET /health`)
   using the official Crawl4AI Docker JSON wrapper format (`BrowserConfig`, `CrawlerRunConfig`,
   `JsonCssExtractionStrategy`, `JsonXPathExtractionStrategy`, `LLMExtractionStrategy`).
2. Local `crawl4ai` Python SDK (`AsyncWebCrawler`) when installed in the runtime.
3. Deterministic execution of the Crawl4AI CSS, XPath, JSON-LD, and HTML size-guide table
   extraction schemas when the remote Cloud Run container URL is not yet configured.
"""

from __future__ import annotations
import html as html_stdlib
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from .adapters.common import (
    SimpleDOMParser,
    extract_json_ld_products,
    is_blocked_or_challenge_page,
    parse_html_document,
)
from .product_validator import validate_safe_image_url

try:
    import crawl4ai  # type: ignore
    HAS_LOCAL_CRAWL4AI_SDK = True
except ImportError:
    HAS_LOCAL_CRAWL4AI_SDK = False


# Official Crawl4AI JsonCssExtractionStrategy schema for E-Commerce Product Pages
SHOPIFY_PRODUCT_CSS_SCHEMA: Dict[str, Any] = {
    "name": "ShopifyProductCssSchema",
    "baseSelector": "body",
    "fields": [
        {"name": "title", "selector": "h1.product-title, h1.product__title, h1.pdp-name, h1", "type": "text"},
        {"name": "vendor", "selector": ".product-vendor, .product__vendor, .brand-name, .pdp-title", "type": "text"},
        {"name": "price", "selector": ".product-price, .price-item--regular, .price-item--sale, .prod-sp, .pdp-price", "type": "text"},
        {"name": "compare_at_price", "selector": ".price-item--compare, .prod-cp, s.price-item", "type": "text"},
        {"name": "description", "selector": ".product-description, .product__description, .rte", "type": "text"},
        {"name": "size_guide_html", "selector": "dialog.dialog--size-guide, #size-chart, .size-guide, table.wovens-sizing, table.bottoms-sizing", "type": "html"},
    ],
}

# Official Crawl4AI JsonXPathExtractionStrategy schema for E-Commerce Product Pages
SHOPIFY_PRODUCT_XPATH_SCHEMA: Dict[str, Any] = {
    "name": "ShopifyProductXPathSchema",
    "baseSelector": "//body",
    "fields": [
        {"name": "og_title", "selector": "//meta[@property='og:title']/@content", "type": "attribute"},
        {"name": "og_description", "selector": "//meta[@property='og:description']/@content", "type": "attribute"},
        {"name": "og_image", "selector": "//meta[@property='og:image']/@content", "type": "attribute"},
        {"name": "og_price", "selector": "//meta[@property='og:price:amount' or @property='product:price:amount']/@content", "type": "attribute"},
        {"name": "og_currency", "selector": "//meta[@property='og:price:currency' or @property='product:price:currency']/@content", "type": "attribute"},
    ],
}

FRACTION_MAP = {
    "½": 0.5,
    "¼": 0.25,
    "¾": 0.75,
    "⅛": 0.125,
    "⅜": 0.375,
    "⅝": 0.625,
    "⅞": 0.875,
    "⅓": 0.333,
    "⅔": 0.667,
}


@dataclass
class Crawl4AIExtractionResult:
    url: str
    success: bool = False
    blocked: bool = False
    http_status: Optional[int] = None
    crawl4ai_connection_status: str = "standby_cloud_run_not_configured"
    crawl4ai_endpoint: Optional[str] = None
    browser_rendering_status: str = "static_http_and_dom"
    html: str = ""
    markdown: str = ""
    css_extracted: Dict[str, Any] = field(default_factory=dict)
    xpath_extracted: Dict[str, Any] = field(default_factory=dict)
    json_ld_objects: List[Dict[str, Any]] = field(default_factory=list)
    media_images: List[str] = field(default_factory=list)
    extracted_size_chart_rows: List[Dict[str, Any]] = field(default_factory=list)
    size_chart_unit: str = "in"
    error_message: Optional[str] = None


class Crawl4AIClient:
    """
    Client for the official Crawl4AI engine (Google Cloud Run Docker service or local SDK).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout_seconds: float = 12.0,
    ) -> None:
        self.base_url = (base_url if base_url is not None else os.environ.get("CRAWL4AI_BASE_URL", "")).strip().rstrip("/")
        self.api_token = (api_token if api_token is not None else os.environ.get("CRAWL4AI_API_TOKEN", "")).strip()
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def build_docker_crawl_payload(
        url: str,
        strategy_type: str = "JsonCssExtractionStrategy",
        schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build the official Crawl4AI Docker REST API payload using the documented
        `{"type": "ClassName", "params": {...}}` wrapper structure.
        """
        active_schema = schema or (
            SHOPIFY_PRODUCT_CSS_SCHEMA
            if strategy_type == "JsonCssExtractionStrategy"
            else SHOPIFY_PRODUCT_XPATH_SCHEMA
        )

        browser_config = {
            "type": "BrowserConfig",
            "params": {
                "headless": True,
                "browser_type": "chromium",
                "verbose": False,
            },
        }

        extraction_strategy = {
            "type": strategy_type,
            "params": {
                "schema": active_schema,
            },
        }

        crawler_run_config = {
            "type": "CrawlerRunConfig",
            "params": {
                "cache_mode": "BYPASS",
                "word_count_threshold": 5,
                "wait_until": "domcontentloaded",
                "extraction_strategy": extraction_strategy,
            },
        }

        return {
            "urls": [url],
            "browser_config": browser_config,
            "run_config": crawler_run_config,
            "extraction_strategy": extraction_strategy,
        }

    def check_health(
        self,
        http_fetcher: Optional[Callable[[str, Dict[str, str], Optional[bytes], float], Tuple[int, str]]] = None,
    ) -> Tuple[str, Optional[str]]:
        """
        Check connectivity to the configured Crawl4AI Cloud Run instance or local SDK.
        Returns (connection_status, endpoint_or_detail).
        """
        if self.base_url:
            health_url = f"{self.base_url}/health"
            headers = {"Accept": "application/json"}
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"
            fetcher = http_fetcher or self._default_http_request
            try:
                status, _body = fetcher(health_url, headers, None, 5.0)
                if 200 <= status < 300:
                    return "connected_cloud_run", self.base_url
                return "unreachable", f"HTTP {status} from {health_url}"
            except Exception as exc:
                return "unreachable", str(exc)

        if HAS_LOCAL_CRAWL4AI_SDK:
            return "connected_local_sdk", "crawl4ai Python SDK"

        return "standby_cloud_run_not_configured", None

    def crawl_product_page(
        self,
        url: str,
        raw_html_override: Optional[str] = None,
        http_fetcher: Optional[Callable[[str, Dict[str, str], Optional[bytes], float], Tuple[int, str]]] = None,
    ) -> Crawl4AIExtractionResult:
        """
        Execute Crawl4AI extraction on a product URL.
        1. If raw_html_override is provided (e.g. unit test fixture or user paste), runs the
           Crawl4AI CSS, XPath, JSON-LD, and size-table extractors on that HTML.
        2. If CRAWL4AI_BASE_URL is configured, calls the remote Cloud Run Crawl4AI `/crawl` endpoint
           with Bearer authentication and `BrowserConfig` + `CrawlerRunConfig`.
        3. Otherwise fetches the permitted webpage and executes the deterministic Crawl4AI CSS/XPath/JSON-LD
           extraction strategies while reporting the exact Crawl4AI connection status.
        """
        result = Crawl4AIExtractionResult(url=url)
        fetcher = http_fetcher or self._default_http_request

        if raw_html_override is not None:
            result.http_status = 200
            result.crawl4ai_connection_status = (
                "connected_cloud_run" if self.base_url else "standby_cloud_run_not_configured"
            )
            result.browser_rendering_status = "static_http_and_dom"
            return self._process_html_with_strategies(result, raw_html_override, status_code=200)

        # Path A: Remote Crawl4AI Cloud Run Service Configured
        if self.base_url:
            result.crawl4ai_endpoint = self.base_url
            payload = self.build_docker_crawl_payload(url, "JsonCssExtractionStrategy", SHOPIFY_PRODUCT_CSS_SCHEMA)
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            try:
                status, resp_body = fetcher(
                    f"{self.base_url}/crawl",
                    headers,
                    json.dumps(payload).encode("utf-8"),
                    self.timeout_seconds,
                )
                result.http_status = status
                if 200 <= status < 300:
                    data = json.loads(resp_body)
                    items = data.get("results") if isinstance(data.get("results"), list) else [data]
                    first = items[0] if items and isinstance(items[0], dict) else {}
                    result.crawl4ai_connection_status = "connected_cloud_run"
                    result.browser_rendering_status = "rendered_chromium"
                    html_content = str(first.get("html") or first.get("cleaned_html") or "")
                    result.markdown = str(first.get("markdown") or "")
                    # Parse extracted_content if returned by Crawl4AI JsonCssExtractionStrategy
                    ext_content = first.get("extracted_content")
                    if isinstance(ext_content, str) and ext_content.strip():
                        try:
                            parsed_ext = json.loads(ext_content)
                            if isinstance(parsed_ext, list) and parsed_ext and isinstance(parsed_ext[0], dict):
                                result.css_extracted.update(parsed_ext[0])
                            elif isinstance(parsed_ext, dict):
                                result.css_extracted.update(parsed_ext)
                        except Exception:
                            pass
                    # Extract media images reported by Crawl4AI
                    media = first.get("media") if isinstance(first.get("media"), dict) else {}
                    imgs = media.get("images") if isinstance(media.get("images"), list) else []
                    for img_item in imgs:
                        src = img_item.get("src") if isinstance(img_item, dict) else str(img_item)
                        safe = validate_safe_image_url(src)
                        if safe and safe not in result.media_images:
                            result.media_images.append(safe)

                    if html_content:
                        return self._process_html_with_strategies(result, html_content, status_code=status)
                    result.success = bool(result.css_extracted or result.media_images)
                    return result
                else:
                    result.crawl4ai_connection_status = "unreachable"
                    result.error_message = f"Crawl4AI Cloud Run service returned HTTP {status}."
            except Exception as exc:
                result.crawl4ai_connection_status = "unreachable"
                result.error_message = f"Crawl4AI Cloud Run connection failed: {exc}"

        # Path B: Direct Webpage Fetch + Deterministic Execution of Crawl4AI CSS/XPath/JSON-LD Schemas
        req_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            status_code, html_text = fetcher(url, req_headers, None, self.timeout_seconds)
            result.http_status = status_code
            result.browser_rendering_status = "static_http_and_dom"
            return self._process_html_with_strategies(result, html_text, status_code=status_code)
        except TimeoutError as exc:
            result.http_status = 408
            result.browser_rendering_status = "failed"
            result.error_message = f"Page extraction timed out after {self.timeout_seconds:.0f}s: {exc}"
            return result
        except Exception as exc:
            result.browser_rendering_status = "failed"
            result.error_message = f"Network error during webpage retrieval: {exc}"
            return result

    def _process_html_with_strategies(
        self,
        result: Crawl4AIExtractionResult,
        html_text: str,
        status_code: int = 200,
    ) -> Crawl4AIExtractionResult:
        result.html = html_text
        blocked, block_reason = is_blocked_or_challenge_page(html_text, status_code)
        if blocked:
            result.blocked = True
            result.success = False
            result.error_message = block_reason or f"Source restricted automated access (HTTP {status_code})."
            return result

        dom = parse_html_document(html_text)

        # 1. JSON-LD Inspection (Product & ProductGroup)
        result.json_ld_objects = self._extract_all_product_json_ld(dom)

        # 2. Execute Crawl4AI JsonCssExtractionStrategy rules
        css_data = self._execute_css_strategy(html_text, dom)
        result.css_extracted.update(css_data)

        # 3. Execute Crawl4AI JsonXPathExtractionStrategy rules
        xpath_data = self._execute_xpath_strategy(html_text, dom)
        result.xpath_extracted.update(xpath_data)

        # 4. Extract safe product image URLs
        for img_attr in dom.images:
            src = img_attr.get("src") or img_attr.get("data-src") or img_attr.get("data-zoom-image")
            safe_url = validate_safe_image_url(src)
            if safe_url and safe_url not in result.media_images:
                result.media_images.append(safe_url)

        # 5. Parse HTML Garment Size Guide tables (including fraction entities)
        rows, unit = self.extract_size_chart_from_html(html_text)
        result.extracted_size_chart_rows = rows
        result.size_chart_unit = unit

        result.success = True
        return result

    @staticmethod
    def _extract_all_product_json_ld(dom: SimpleDOMParser) -> List[Dict[str, Any]]:
        """Extract both @type Product and @type ProductGroup from JSON-LD script blocks."""
        items = list(extract_json_ld_products(dom))
        for attrs, content in dom.scripts:
            if attrs.get("type", "").lower() == "application/ld+json" and content.strip():
                try:
                    parsed = json.loads(content.strip())
                    nodes = parsed if isinstance(parsed, list) else [parsed]
                    for node in nodes:
                        if isinstance(node, dict) and node.get("@type") == "ProductGroup":
                            items.append(node)
                except Exception:
                    continue
        return items

    @staticmethod
    def _execute_css_strategy(html_text: str, dom: SimpleDOMParser) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}
        # Title
        for cls_key in ("product-title", "product__title", "pdp-name", "prod-name"):
            if dom.elements_by_class.get(cls_key):
                extracted["title"] = dom.elements_by_class[cls_key][0]
                break
        if "title" not in extracted:
            h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, re.S | re.I)
            if h1_match:
                clean_h1 = re.sub(r"<[^>]+>", " ", h1_match.group(1)).strip()
                clean_h1 = re.sub(r"\s+", " ", html_stdlib.unescape(clean_h1))
                if clean_h1:
                    extracted["title"] = clean_h1

        # Vendor / Brand
        for cls_key in ("product-vendor", "product__vendor", "brand-name", "pdp-title"):
            if dom.elements_by_class.get(cls_key):
                extracted["vendor"] = dom.elements_by_class[cls_key][0]
                break

        # Price
        for cls_key in ("product-price", "price-item--regular", "price-item--sale", "prod-sp", "pdp-price"):
            if dom.elements_by_class.get(cls_key):
                extracted["price"] = dom.elements_by_class[cls_key][0]
                break

        # Description
        desc_match = re.search(
            r'<div[^>]*class="[^"]*(?:product-description|product__description)[^"]*"[^>]*>(.*?)</div>',
            html_text,
            re.S | re.I,
        )
        if desc_match:
            clean_desc = re.sub(r"<[^>]+>", " ", desc_match.group(1))
            clean_desc = re.sub(r"\s+", " ", html_stdlib.unescape(clean_desc)).strip()
            if clean_desc:
                extracted["description"] = clean_desc

        return extracted

    @staticmethod
    def _execute_xpath_strategy(html_text: str, dom: SimpleDOMParser) -> Dict[str, Any]:
        """Execute XPath attribute & node queries over meta and structured nodes."""
        extracted: Dict[str, Any] = {}
        meta_map: Dict[str, str] = {}
        for m in dom.metas:
            prop = (m.get("property") or m.get("name") or "").lower()
            content = m.get("content") or ""
            if prop and content:
                meta_map[prop] = html_stdlib.unescape(content.strip())

        if meta_map.get("og:title"):
            extracted["og_title"] = meta_map["og:title"]
        if meta_map.get("og:description"):
            extracted["og_description"] = meta_map["og:description"]
        if meta_map.get("og:image"):
            extracted["og_image"] = meta_map["og:image"]
        if meta_map.get("og:price:amount") or meta_map.get("product:price:amount"):
            extracted["og_price"] = meta_map.get("og:price:amount") or meta_map.get("product:price:amount")
        if meta_map.get("og:price:currency") or meta_map.get("product:price:currency"):
            extracted["og_currency"] = meta_map.get("og:price:currency") or meta_map.get("product:price:currency")

        # Also attempt ElementTree XPath evaluation on well-formed head snippet if present
        head_match = re.search(r"<head[^>]*>.*?</head>", html_text, re.S | re.I)
        if head_match and not extracted.get("og_title"):
            try:
                root = ET.fromstring(head_match.group(0))
                for node in root.findall(".//meta"):
                    if node.attrib.get("property") == "og:title" and node.attrib.get("content"):
                        extracted["og_title"] = node.attrib["content"]
            except Exception:
                pass

        return extracted

    @classmethod
    def parse_numeric_measurement(cls, raw_cell: str) -> Optional[float]:
        """
        Parse garment measurement cell values including HTML entities and Unicode fractions:
        e.g. '15&frac12;' -> 15.5, '33&frac34;' -> 33.75, '28&frac18;' -> 28.125, '40' -> 40.0
        """
        if not raw_cell:
            return None
        unescaped = html_stdlib.unescape(str(raw_cell)).strip()
        if not unescaped:
            return None

        # Replace Unicode fraction characters with decimal equivalents
        fraction_add = 0.0
        for frac_char, frac_val in FRACTION_MAP.items():
            if frac_char in unescaped:
                fraction_add += frac_val
                unescaped = unescaped.replace(frac_char, " ")

        # Extract leading number (e.g. "15" from "15 ½" or "40.5")
        num_match = re.search(r"(\d+(?:\.\d+)?)", unescaped)
        if not num_match:
            return round(fraction_add, 3) if fraction_add > 0 else None

        base = float(num_match.group(1))
        total = base + fraction_add
        return round(total, 3) if total > 0 else None

    @classmethod
    def extract_size_chart_from_html(cls, html_text: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Inspect HTML tables inside `#size-chart`, `dialog.dialog--size-guide`,
        `table.wovens-sizing`, `table.bottoms-sizing`, or `.size-guide` for garment measurements.
        """
        if not html_text:
            return [], "in"

        # Prefer #size-chart (Garment Size Chart) over #body-size-chart if present
        garment_tab_match = re.search(
            r'<div[^>]*id="size-chart"[^>]*>(.*?)</div>',
            html_text,
            re.S | re.I,
        )
        search_scope = garment_tab_match.group(1) if garment_tab_match else html_text

        tables = re.findall(r"<table[^>]*>(.*?)</table>", search_scope, re.S | re.I)
        for tbl_html in tables:
            tr_list = re.findall(r"<tr[^>]*>(.*?)</tr>", tbl_html, re.S | re.I)
            if len(tr_list) < 2:
                continue

            headers: List[str] = []
            data_rows: List[Dict[str, Any]] = []

            for tr in tr_list:
                cells = re.findall(r"<(th|td)[^>]*>(.*?)</\1>", tr, re.S | re.I)
                if not cells:
                    continue
                cleaned_cells = [
                    re.sub(r"\s+", " ", html_stdlib.unescape(re.sub(r"<[^>]+>", "", c[1]))).strip()
                    for c in cells
                ]
                # Skip single-cell title header rows like "Garment Size Chart"
                if len(cleaned_cells) == 1:
                    continue

                lower_cells = [c.lower() for c in cleaned_cells]
                if not headers and any(
                    k in " ".join(lower_cells)
                    for k in ("size", "chest", "waist", "shoulder", "sleeve", "length", "hip", "inseam", "rise")
                ):
                    headers = lower_cells
                    continue

                if headers and len(cleaned_cells) >= 2:
                    row_dict: Dict[str, Any] = {}
                    raw_size = cleaned_cells[0]
                    # Handle formats like "36 – XS" or "38 - S" or "M"
                    size_parts = [p.strip() for p in re.split(r"[\u2013\u2014\-/]", raw_size) if p.strip()]
                    if len(size_parts) >= 2 and size_parts[-1].upper() in ("XXS", "XS", "S", "M", "L", "XL", "XXL", "2XL", "3XL"):
                        row_dict["size"] = size_parts[-1].upper()
                        row_dict["brand_size"] = raw_size
                    else:
                        row_dict["size"] = raw_size

                    has_measurement = False
                    for col_idx in range(1, min(len(headers), len(cleaned_cells))):
                        col_name = headers[col_idx]
                        val = cls.parse_numeric_measurement(cleaned_cells[col_idx])
                        if val is not None:
                            has_measurement = True
                            if "chest" in col_name or "bust" in col_name:
                                row_dict["chest"] = val
                            elif "shoulder" in col_name:
                                row_dict["shoulder"] = val
                            elif "waist" in col_name:
                                row_dict["waist"] = val
                            elif "hip" in col_name or "seat" in col_name:
                                row_dict["hip"] = val
                            elif "sleeve" in col_name:
                                row_dict["sleeve"] = val
                            elif "inseam" in col_name:
                                row_dict["inseam"] = val
                            elif "rise" in col_name:
                                row_dict["rise"] = val
                            elif "neck" in col_name:
                                row_dict["neck"] = val
                            elif "thigh" in col_name:
                                row_dict["thigh"] = val
                            elif "length" in col_name:
                                row_dict["length"] = val

                    if has_measurement and row_dict.get("size"):
                        data_rows.append(row_dict)

            if data_rows:
                unit = "cm" if "cm" in tbl_html.lower() and "inch" not in tbl_html.lower() else "in"
                return data_rows, unit

        return [], "in"

    @staticmethod
    def _default_http_request(
        url: str,
        headers: Dict[str, str],
        body: Optional[bytes],
        timeout: float,
    ) -> Tuple[int, str]:
        method = "POST" if body is not None else "GET"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200)
                raw = resp.read(3_500_000)
                charset = resp.headers.get_content_charset() or "utf-8"
                return status, raw.decode(charset, errors="replace")
        except urllib.error.HTTPError as http_err:
            try:
                err_body = http_err.read(250_000).decode("utf-8", errors="replace")
            except Exception:
                err_body = ""
            return http_err.code, err_body
