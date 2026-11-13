"""
FastAPI backend & CLI interface for the AtelierFit Product Extraction & Crawl4AI Service.
Exposes:
- POST /api/products/extract
- POST /api/products/extract/test
- GET /api/products/{product_id}
- GET /api/products/{product_id}/sizes
- POST /api/products/manual
"""

from __future__ import annotations
import argparse
import json
import sys
from typing import Any, Dict
from .product_extractor import ProductExtractionOrchestrator
from .product_validator import URLValidationError

service = ProductExtractionOrchestrator(timeout_seconds=10.0)

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(
        title="FitCheck Crawl4AI & Product Extraction API",
        description="Shopify Storefront + Crawl4AI + Myntra/AJIO extraction and size normalization engine",
        version="2.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/api/products/extract")
    async def extract_product_endpoint(body: Dict[str, Any]) -> Dict[str, Any]:
        url = str(body.get("url") or "").strip()
        raw_html = body.get("raw_html")
        try:
            result = service.extract_from_url(url, raw_html_override=raw_html)
            return result.to_dict()
        except URLValidationError as exc:
            raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message}) from exc

    @app.post("/api/products/extract/test")
    async def extract_product_test_endpoint(body: Dict[str, Any]) -> Dict[str, Any]:
        url = str(body.get("url") or "").strip()
        raw_html = body.get("raw_html")
        try:
            return service.run_diagnostic_extraction_test(url, raw_html_override=raw_html)
        except URLValidationError as exc:
            raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message}) from exc

    @app.get("/api/products/{product_id}")
    async def get_product_endpoint(product_id: str) -> Dict[str, Any]:
        prod = service.get_product(product_id)
        if not prod:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Product not found."})
        return prod.to_dict()

    @app.get("/api/products/{product_id}/sizes")
    async def get_product_sizes_endpoint(product_id: str) -> Dict[str, Any]:
        prod = service.get_product(product_id)
        if not prod:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Product not found."})
        data = prod.to_dict()
        return {
            "product_id": prod.product_id,
            "name": prod.name,
            "brand": prod.brand,
            "garment_type": prod.garment_type,
            "sizes": data["sizes"],
            "availability": data["availability"],
            "try_on_compatibility": data["try_on_compatibility"],
        }

    @app.post("/api/products/manual")
    async def create_manual_product_endpoint(body: Dict[str, Any]) -> Dict[str, Any]:
        result = service.create_manual_product(body)
        return result.to_dict()

except ImportError:
    app = None


def main() -> int:
    parser = argparse.ArgumentParser(description="FitCheck Product & Crawl4AI CLI")
    parser.add_argument("--extract-url", type=str, help="Product URL (Shopify, Myntra, or AJIO) to extract")
    parser.add_argument("--test-url", type=str, help="Run diagnostic extraction & verification report on URL")
    parser.add_argument("--stdin-html", action="store_true", help="Read raw HTML override from stdin")
    parser.add_argument("--manual-json", type=str, help="JSON payload for manual product creation")
    parser.add_argument("--get-id", type=str, help="Retrieve product by ID")
    args = parser.parse_args()

    try:
        raw_stdin = None
        if args.stdin_html:
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                raw_stdin = stdin_data

        if args.extract_url:
            res = service.extract_from_url(args.extract_url, raw_html_override=raw_stdin)
            print(json.dumps({"ok": True, "data": res.to_dict()}))
            return 0
        if args.test_url:
            diag_res = service.run_diagnostic_extraction_test(args.test_url, raw_html_override=raw_stdin)
            print(json.dumps({"ok": True, "data": diag_res}))
            return 0
        if args.manual_json:
            payload = json.loads(args.manual_json)
            res = service.create_manual_product(payload)
            print(json.dumps({"ok": True, "data": res.to_dict()}))
            return 0
        if args.get_id:
            prod = service.get_product(args.get_id)
            if not prod:
                print(json.dumps({"ok": False, "code": "NOT_FOUND", "message": "Product not found"}))
                return 1
            print(json.dumps({"ok": True, "data": prod.to_dict()}))
            return 0
    except URLValidationError as exc:
        print(json.dumps({"ok": False, "code": exc.code, "message": exc.message}))
        return 2
    except Exception as exc:
        print(json.dumps({"ok": False, "code": "INTERNAL_ERROR", "message": str(exc)}))
        return 3

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
