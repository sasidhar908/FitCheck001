"""
Automated unit tests for the Product URL Extraction & Crawl4AI Integration Engine.
Covers all 16 Phase 10 Shopify & Crawl4AI test scenarios + all 14 Myntra & AJIO scenarios
(30 total deterministic unit tests) using mocked responses and fixtures.
"""

from __future__ import annotations
import json
import unittest
from typing import Dict, Optional, Tuple
from backend.adapters.ajio import AjioExtractor
from backend.adapters.myntra import MyntraExtractor
from backend.crawl4ai_client import Crawl4AIClient
from backend.extractor import ProductExtractionService
from backend.fixtures import (
    AJIO_LINEN_BLAZER_HTML,
    AJIO_PLEATED_TROUSERS_HTML,
    JSON_LD_ONLY_MYNTRA_HTML,
    MISSING_IMAGES_AND_CHART_AJIO_HTML,
    MYNTRA_OXFORD_SHIRT_HTML,
    SHOPIFY_TAYLOR_STITCH_HTML,
    SHOPIFY_TAYLOR_STITCH_STOREFRONT_JSON,
    WAF_BLOCKED_HTML,
)
from backend.product_validator import (
    URLValidationError,
    detect_retailer,
    identify_shopify_store,
    validate_product_target,
    validate_product_url,
    validate_safe_image_url,
)
from backend.shopify_adapter import ShopifyExtractor


class TestProductExtractionEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ProductExtractionService(timeout_seconds=5.0)

    # =========================================================================
    # PART A: Myntra & AJIO Tests (Preserved 1-14)
    # =========================================================================
    def test_01_myntra_url_validation(self) -> None:
        url = "https://www.myntra.com/shirts/polo-ralph-lauren/men-navy-oxford-shirt/24891024/buy"
        norm_url, retailer, prod_id = validate_product_url(url)
        self.assertEqual(retailer, "Myntra")
        self.assertEqual(prod_id, "24891024")
        self.assertTrue(norm_url.startswith("https://www.myntra.com/"))

        with self.assertRaises(URLValidationError) as ctx:
            validate_product_url("https://www.myntra.com/men-shirts")
        self.assertEqual(ctx.exception.code, "INVALID_MYNTRA_URL")

    def test_02_ajio_url_validation(self) -> None:
        url = "https://www.ajio.com/massimo-dutti-linen-blazer/p/469482190_sand"
        norm_url, retailer, prod_id = validate_product_url(url)
        self.assertEqual(retailer, "AJIO")
        self.assertEqual(prod_id, "469482190_sand")
        self.assertTrue(norm_url.startswith("https://www.ajio.com/"))

        with self.assertRaises(URLValidationError) as ctx:
            validate_product_url("https://www.ajio.com/shop/women")
        self.assertEqual(ctx.exception.code, "INVALID_AJIO_URL")

    def test_03_retailer_detection(self) -> None:
        self.assertEqual(detect_retailer("https://www.myntra.com/shirts/b/p/12345678/buy"), "Myntra")
        self.assertEqual(detect_retailer("https://m.myntra.com/dresses/b/p/87654321/buy"), "Myntra")
        self.assertEqual(detect_retailer("https://www.ajio.com/item/p/469112233_blue"), "AJIO")
        self.assertEqual(detect_retailer("https://www.taylorstitch.com/products/glacier-shirt"), "Shopify")

    def test_04_json_ld_extraction(self) -> None:
        url = "https://www.myntra.com/tshirts/hm/unisex-classic-tee/19002100/buy"
        res = MyntraExtractor.extract_from_html(JSON_LD_ONLY_MYNTRA_HTML, url, product_id="19002100")
        self.assertEqual(res.extraction.source, "json_ld")
        self.assertEqual(res.name, "Unisex Classic Heavyweight Cotton Tee")
        self.assertEqual(res.brand, "H&M")
        self.assertEqual(res.pricing.selling_price, 1299.0)
        self.assertEqual(res.pricing.mrp, 1499.0)
        self.assertEqual(res.availability.product_status, "in_stock")

    def test_05_embedded_json_extraction(self) -> None:
        myntra_url = "https://www.myntra.com/shirts/polo-ralph-lauren/shirt/24891024/buy"
        m_res = MyntraExtractor.extract_from_html(MYNTRA_OXFORD_SHIRT_HTML, myntra_url, product_id="24891024")
        self.assertEqual(m_res.extraction.source, "embedded_json")
        self.assertEqual(m_res.extraction.status, "success")
        self.assertEqual(m_res.brand, "Polo Ralph Lauren")

        ajio_url = "https://www.ajio.com/massimo-dutti-blazer/p/469482190_sand"
        a_res = AjioExtractor.extract_from_html(AJIO_LINEN_BLAZER_HTML, ajio_url, product_id="469482190_sand")
        self.assertEqual(a_res.extraction.source, "embedded_json")
        self.assertEqual(a_res.extraction.status, "success")
        self.assertEqual(a_res.brand, "Massimo Dutti")

    def test_06_price_normalization(self) -> None:
        myntra_url = "https://www.myntra.com/shirts/polo-ralph-lauren/shirt/24891024/buy"
        m_res = MyntraExtractor.extract_from_html(MYNTRA_OXFORD_SHIRT_HTML, myntra_url)
        self.assertEqual(m_res.pricing.mrp, 10999.0)
        self.assertEqual(m_res.pricing.selling_price, 8799.0)
        self.assertEqual(m_res.pricing.discount_percentage, 20)

    def test_07_image_extraction(self) -> None:
        myntra_url = "https://www.myntra.com/shirts/polo-ralph-lauren/shirt/24891024/buy"
        m_res = MyntraExtractor.extract_from_html(MYNTRA_OXFORD_SHIRT_HTML, myntra_url)
        self.assertIsNotNone(m_res.images.primary_image)
        self.assertEqual(len(m_res.images.gallery), 2)

    def test_08_size_and_chart_extraction(self) -> None:
        myntra_url = "https://www.myntra.com/shirts/polo-ralph-lauren/shirt/24891024/buy"
        m_res = MyntraExtractor.extract_from_html(MYNTRA_OXFORD_SHIRT_HTML, myntra_url)
        self.assertEqual(len(m_res.sizes.available_sizes), 5)
        assert m_res.sizes.size_chart is not None
        self.assertAlmostEqual(m_res.sizes.size_chart.rows[0].chest_cm or 0.0, 100.3, places=1)

    def test_09_missing_size_chart(self) -> None:
        url = "https://www.myntra.com/tshirts/hm/unisex-classic-tee/19002100/buy"
        res = MyntraExtractor.extract_from_html(JSON_LD_ONLY_MYNTRA_HTML, url)
        self.assertIsNone(res.sizes.size_chart)
        self.assertEqual(res.extraction.status, "partial")

    def test_10_missing_images(self) -> None:
        url = "https://www.ajio.com/ms-overshirt/p/460009999_black"
        res = AjioExtractor.extract_from_html(MISSING_IMAGES_AND_CHART_AJIO_HTML, url)
        self.assertIsNone(res.images.primary_image)
        self.assertFalse(res.try_on_compatibility.ready_for_try_on)

    def test_11_blocked_page_handling(self) -> None:
        url = "https://www.myntra.com/shirts/brand/blocked-shirt/99999999/buy"
        res = MyntraExtractor.extract_from_html(WAF_BLOCKED_HTML, url, status_code=403)
        self.assertEqual(res.extraction.status, "blocked")
        self.assertIsNone(res.pricing.selling_price)

    def test_12_invalid_urls_and_ssrf(self) -> None:
        for bad_url in [
            "",
            "not-a-url",
            "ftp://www.myntra.com/shirts/12345678/buy",
            "http://localhost:8000/products/shirt",
            "http://127.0.0.1/products/shirt",
            "http://169.254.169.254/latest/meta-data/",
            "http://192.168.1.1/products/shirt",
        ]:
            with self.assertRaises(URLValidationError):
                validate_product_url(bad_url)

    def test_13_extraction_timeout_handling(self) -> None:
        def timeout_fetcher(_url: str, _timeout: float) -> Tuple[int, str]:
            raise TimeoutError("Simulated socket read timeout")

        url = "https://www.myntra.com/shirts/brand/slow-shirt/77665544/buy"
        res = self.service.extract_from_url(url, http_fetcher=timeout_fetcher)
        self.assertEqual(res.extraction.status, "failed")
        self.assertEqual(res.diagnostics.outcome_classification, "FAILED")

    def test_14_incorrect_retailer_domains(self) -> None:
        for unsupported_url in [
            "https://www.amazon.in/dp/B08N5WRWNW",
            "https://www.flipkart.com/shirt/p/itm123456",
            "https://www.unauthorized-random-shop.com/products/some-shirt",
        ]:
            with self.assertRaises(URLValidationError):
                validate_product_url(unsupported_url)

    # =========================================================================
    # PART B: Phase 10 Shopify & Crawl4AI Tests (15-30)
    # =========================================================================

    # 15. Shopify URL validation
    def test_15_shopify_url_validation(self) -> None:
        url = "https://www.taylorstitch.com/products/glacier-shirt-in-topsoil-corded-denim-2610"
        target = validate_product_target(url)
        self.assertEqual(target.retailer, "Shopify")
        self.assertEqual(target.store_domain, "www.taylorstitch.com")
        self.assertEqual(target.product_handle, "glacier-shirt-in-topsoil-corded-denim-2610")
        self.assertTrue(target.is_authorized_shopify_store)

        # Reject Shopify domain without /products/<handle>
        with self.assertRaises(URLValidationError) as ctx:
            validate_product_target("https://www.taylorstitch.com/collections/mens-shirts")
        self.assertEqual(ctx.exception.code, "INVALID_SHOPIFY_URL")

    # 16. Shopify store identification
    def test_16_shopify_store_and_handle_identification(self) -> None:
        domain, handle, is_auth = identify_shopify_store(
            "https://www.allbirds.com/collections/mens/products/mens-tree-runners"
        )
        self.assertEqual(domain, "www.allbirds.com")
        self.assertEqual(handle, "mens-tree-runners")
        self.assertTrue(is_auth)

        # Unauthorized Shopify store rejected by validate_product_target
        with self.assertRaises(URLValidationError) as ctx:
            validate_product_target("https://www.unapproved-store.com/products/test-shirt")
        self.assertEqual(ctx.exception.code, "UNAUTHORIZED_SHOPIFY_STORE")

    # 17. Storefront API integration
    def test_17_shopify_storefront_api_integration(self) -> None:
        url = "https://www.taylorstitch.com/products/glacier-shirt-in-topsoil-corded-denim-2610"
        res = self.service.extract_from_url(
            url,
            raw_html_override=SHOPIFY_TAYLOR_STITCH_HTML,
            storefront_json_override=SHOPIFY_TAYLOR_STITCH_STOREFRONT_JSON,
        )
        self.assertEqual(res.retailer, "Shopify")
        self.assertEqual(res.name, "The Glacier Shirt in Topsoil Corded Denim")
        self.assertEqual(res.brand, "Taylor Stitch")
        self.assertEqual(res.extraction.source, "shopify_storefront_and_crawl4ai")
        self.assertEqual(res.diagnostics.outcome_classification, "SUCCESS")

    # 18. Crawl4AI connectivity & Docker REST payload format
    def test_18_crawl4ai_connectivity_and_payload_format(self) -> None:
        client = Crawl4AIClient(
            base_url="https://atelierfit-crawl4ai-test.a.run.app",
            api_token="secret_token_123",
        )
        payload = client.build_docker_crawl_payload("https://www.taylorstitch.com/products/glacier-shirt")
        self.assertEqual(payload["browser_config"]["type"], "BrowserConfig")
        self.assertEqual(payload["run_config"]["type"], "CrawlerRunConfig")
        self.assertEqual(payload["extraction_strategy"]["type"], "JsonCssExtractionStrategy")

        # Mock /health endpoint
        def mock_health(url: str, headers: Dict[str, str], _body: Optional[bytes], _timeout: float) -> Tuple[int, str]:
            self.assertIn("Bearer secret_token_123", headers.get("Authorization", ""))
            self.assertTrue(url.endswith("/health"))
            return 200, '{"status":"ok"}'

        conn_status, endpoint = client.check_health(http_fetcher=mock_health)
        self.assertEqual(conn_status, "connected_cloud_run")
        self.assertEqual(endpoint, "https://atelierfit-crawl4ai-test.a.run.app")

    # 19. Crawl4AI CSS extraction
    def test_19_crawl4ai_css_extraction(self) -> None:
        client = Crawl4AIClient()
        res = client.crawl_product_page(
            "https://www.taylorstitch.com/products/glacier-shirt-in-topsoil-corded-denim-2610",
            raw_html_override=SHOPIFY_TAYLOR_STITCH_HTML,
        )
        self.assertTrue(res.success)
        self.assertEqual(res.css_extracted.get("title"), "The Glacier Shirt in Topsoil Corded Denim")
        self.assertEqual(res.css_extracted.get("vendor"), "Taylor Stitch")
        self.assertIn("8-oz 100% organic corded cotton denim", res.css_extracted.get("description", ""))

    # 20. JSON-LD & ProductGroup extraction
    def test_20_shopify_json_ld_and_product_group_extraction(self) -> None:
        client = Crawl4AIClient()
        res = client.crawl_product_page(
            "https://www.taylorstitch.com/products/glacier-shirt-in-topsoil-corded-denim-2610",
            raw_html_override=SHOPIFY_TAYLOR_STITCH_HTML,
        )
        self.assertEqual(len(res.json_ld_objects), 1)
        self.assertEqual(res.json_ld_objects[0]["@type"], "ProductGroup")

    # 21. Image extraction & safe URL filtering
    def test_21_shopify_image_extraction_and_safety(self) -> None:
        self.assertIsNone(validate_safe_image_url("http://127.0.0.1/secret.jpg"))
        self.assertIsNone(validate_safe_image_url("javascript:alert(1)"))
        self.assertEqual(
            validate_safe_image_url("//cdn.shopify.com/s/files/shirt.jpg"),
            "https://cdn.shopify.com/s/files/shirt.jpg",
        )
        url = "https://www.taylorstitch.com/products/glacier-shirt-in-topsoil-corded-denim-2610"
        res = self.service.extract_from_url(
            url,
            raw_html_override=SHOPIFY_TAYLOR_STITCH_HTML,
            storefront_json_override=SHOPIFY_TAYLOR_STITCH_STOREFRONT_JSON,
        )
        self.assertEqual(len(res.images.gallery), 2)
        self.assertTrue(res.images.primary_image.startswith("https://www.taylorstitch.com/cdn/shop/"))

    # 22. Price & discount extraction
    def test_22_shopify_price_and_discount_extraction(self) -> None:
        url = "https://www.taylorstitch.com/products/glacier-shirt-in-topsoil-corded-denim-2610"
        res = self.service.extract_from_url(
            url,
            raw_html_override=SHOPIFY_TAYLOR_STITCH_HTML,
            storefront_json_override=SHOPIFY_TAYLOR_STITCH_STOREFRONT_JSON,
        )
        self.assertEqual(res.pricing.selling_price, 168.0)
        self.assertEqual(res.pricing.mrp, 198.0)
        self.assertEqual(res.pricing.discount_percentage, 15)
        self.assertEqual(res.pricing.currency, "USD")

    # 23. Variant & HTML fraction size chart extraction
    def test_23_shopify_variant_and_size_chart_extraction(self) -> None:
        url = "https://www.taylorstitch.com/products/glacier-shirt-in-topsoil-corded-denim-2610"
        res = self.service.extract_from_url(
            url,
            raw_html_override=SHOPIFY_TAYLOR_STITCH_HTML,
            storefront_json_override=SHOPIFY_TAYLOR_STITCH_STOREFRONT_JSON,
        )
        self.assertEqual(len(res.sizes.available_sizes), 5)
        avail_map = {v.normalized_label: v.available for v in res.sizes.available_sizes}
        self.assertTrue(avail_map["S"])
        self.assertFalse(avail_map["XL"])

        # Verify HTML table size chart with fraction entities: 15&frac12; in = 15.5 * 2.54 = 39.4 cm
        assert res.sizes.size_chart is not None
        xs_row = res.sizes.size_chart.rows[0]
        self.assertEqual(xs_row.size, "XS")
        self.assertAlmostEqual(xs_row.chest_cm or 0.0, 101.6, places=1)  # 40 in * 2.54
        self.assertAlmostEqual(xs_row.neck_cm or 0.0, 39.4, places=1)   # 15.5 in * 2.54
        self.assertAlmostEqual(xs_row.shoulder_cm or 0.0, 43.8, places=1)  # 17.25 in * 2.54

    # 24. Missing size charts on Shopify
    def test_24_shopify_missing_size_chart_handling(self) -> None:
        html_no_chart = "<html><head><title>No Chart</title></head><body><h1 class='product-title'>Shirt</h1></body></html>"
        url = "https://www.taylorstitch.com/products/glacier-shirt-in-topsoil-corded-denim-2610"
        res = self.service.extract_from_url(
            url,
            raw_html_override=html_no_chart,
            storefront_json_override=SHOPIFY_TAYLOR_STITCH_STOREFRONT_JSON,
        )
        self.assertIsNone(res.sizes.size_chart)
        self.assertIn("size_chart", res.diagnostics.missing_fields)
        self.assertEqual(res.diagnostics.outcome_classification, "PARTIAL")

    # 25. Missing product images on Shopify
    def test_25_shopify_missing_images_handling(self) -> None:
        sf_no_img = {
            "product": {
                **SHOPIFY_TAYLOR_STITCH_STOREFRONT_JSON["product"],
                "images": [],
            }
        }
        html_no_img = "<html><body><h1 class='product-title'>No Image Shirt</h1></body></html>"
        url = "https://www.taylorstitch.com/products/glacier-shirt-in-topsoil-corded-denim-2610"
        res = self.service.extract_from_url(
            url,
            raw_html_override=html_no_img,
            storefront_json_override=sf_no_img,
        )
        self.assertIsNone(res.images.primary_image)
        self.assertIn("images", res.diagnostics.missing_fields)
        self.assertEqual(res.diagnostics.outcome_classification, "PARTIAL")

    # 26. Blocked Shopify page handling
    def test_26_shopify_blocked_page_handling(self) -> None:
        def blocked_fetcher(_url: str, _headers: Dict[str, str], _body: Optional[bytes], _timeout: float) -> Tuple[int, str]:
            return 403, WAF_BLOCKED_HTML

        url = "https://www.taylorstitch.com/products/blocked-item"
        res = self.service.extract_from_url(url, http_fetcher=blocked_fetcher)
        self.assertEqual(res.extraction.status, "blocked")
        self.assertEqual(res.diagnostics.outcome_classification, "BLOCKED")

    # 27. Network failure handling
    def test_27_shopify_network_failure_handling(self) -> None:
        def error_fetcher(_url: str, _headers: Dict[str, str], _body: Optional[bytes], _timeout: float) -> Tuple[int, str]:
            raise ConnectionError("DNS lookup failed")

        url = "https://www.taylorstitch.com/products/unreachable-item"
        res = self.service.extract_from_url(url, http_fetcher=error_fetcher)
        self.assertEqual(res.extraction.status, "failed")
        self.assertEqual(res.diagnostics.outcome_classification, "FAILED")

    # 28. Timeout handling
    def test_28_shopify_timeout_handling(self) -> None:
        def timeout_fetcher(_url: str, _headers: Dict[str, str], _body: Optional[bytes], _timeout: float) -> Tuple[int, str]:
            raise TimeoutError("Read timed out")

        url = "https://www.taylorstitch.com/products/slow-item"
        res = self.service.extract_from_url(url, http_fetcher=timeout_fetcher)
        self.assertEqual(res.extraction.status, "failed")
        self.assertEqual(res.diagnostics.http_response_status, 408)
        self.assertEqual(res.diagnostics.outcome_classification, "FAILED")

    # 29. Invalid responses from Crawl4AI / Server
    def test_29_crawl4ai_invalid_response_handling(self) -> None:
        client = Crawl4AIClient(base_url="https://crawl4ai.example.com")

        def malformed_fetcher(_url: str, _headers: Dict[str, str], _body: Optional[bytes], _timeout: float) -> Tuple[int, str]:
            return 500, "Internal Server Error"

        res = client.crawl_product_page(
            "https://www.taylorstitch.com/products/glacier-shirt",
            http_fetcher=malformed_fetcher,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.crawl4ai_connection_status, "unreachable")

    # 30. Product normalization & 11-point verification report
    def test_30_product_normalization_and_verification_report(self) -> None:
        url = "https://www.taylorstitch.com/products/glacier-shirt-in-topsoil-corded-denim-2610"
        diag_bundle = self.service.run_diagnostic_extraction_test(
            url,
            raw_html_override=SHOPIFY_TAYLOR_STITCH_HTML,
            storefront_json_override=SHOPIFY_TAYLOR_STITCH_STOREFRONT_JSON,
        )
        report = diag_bundle["verification_report"]
        self.assertEqual(report["total_fields_checked"], 11)
        self.assertEqual(report["verified_field_count"], 11)
        self.assertEqual(report["overall_outcome"], "SUCCESS")


if __name__ == "__main__":
    unittest.main()


