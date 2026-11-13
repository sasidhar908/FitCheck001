# AtelierFit — Crawl4AI Cloud Integration & Product Extraction Engine

**Virtual Try-On & Size Recommendation System (Phase 1: Product URL Extraction, Crawl4AI Integration & Visual Interface)**

AtelierFit is a retailer-aware product extraction and visual fashion e-commerce interface supporting **authorized Shopify stores** (via Shopify Storefront APIs + the open-source **Crawl4AI** engine), **Myntra**, and **AJIO**.

---

## Architecture Overview

1. **Google Cloud Run Crawl4AI Service (`/deploy/crawl4ai/`)**
   - Uses the official open-source [`unclecode/crawl4ai`](https://github.com/unclecode/crawl4ai.git) Docker container (`unclecode/crawl4ai:latest`) on port `11235`.
   - Configured via `deploy/crawl4ai/Dockerfile`, `deploy/crawl4ai/config.yml`, `deploy/crawl4ai/cloudbuild.yaml`, and `deploy/crawl4ai/deploy-cloud-run.sh`.
   - Authenticates requests between the AtelierFit backend and the Cloud Run Crawl4AI container via `Authorization: Bearer <CRAWL4AI_API_TOKEN>`.

2. **Modular Python FastAPI Extraction Engine (`/backend`)**
   - `backend/crawl4ai_client.py`: Official Crawl4AI client building `BrowserConfig`, `CrawlerRunConfig`, `JsonCssExtractionStrategy`, and `JsonXPathExtractionStrategy` payloads (`POST /crawl`, `GET /health`), plus deterministic execution of CSS, XPath, JSON-LD, and HTML size-guide table extraction with fraction entity decoding (`15&frac12;` -> `15.5 in` -> `39.4 cm`).
   - `backend/shopify_adapter.py`: Validates store domain and product handle, queries authorized Shopify Storefront APIs (`POST /api/2024-10/graphql.json`, `/products/{handle}.json`, and `/products/{handle}.js`), and merges Crawl4AI webpage extraction.
   - `backend/product_validator.py`: URL validation, SSRF protection, safe image URL verification, Shopify store/handle identification, and Myntra/AJIO retailer detection.
   - `backend/product_normalizer.py`: Normalizes product data into `ProductResponse`, computes Phase 8 `ExtractionDiagnostics` (`SUCCESS`, `PARTIAL`, `BLOCKED`, `FAILED`), and generates the Phase 9 11-point `ProductVerificationReport`.
   - `backend/product_extractor.py`: Orchestrates Shopify, Myntra, AJIO, and manual product extraction workflows.
   - `backend/tests/test_extraction.py`: 30 deterministic automated unit tests covering URL validation, Shopify store identification, Storefront API integration, Crawl4AI connectivity, CSS/XPath/JSON-LD extraction, image/price/variant/size-chart extraction, missing fields, blocked pages, network failures, timeouts, and normalization.

3. **Backend API Endpoints (`server.ts` & `backend/main.py`)**
   - `POST /api/products/extract`: Extracts and normalizes a Shopify, Myntra, or AJIO product URL.
   - `POST /api/products/extract/test`: Runs a diagnostic extraction and returns the product, Phase 8 `ExtractionDiagnostics`, and the Phase 9 11-point `ProductVerificationReport`.
   - `GET /api/products/:product_id`: Retrieves a previously extracted product.
   - `GET /api/products/:product_id/sizes`: Retrieves normalized size variants and centimeter size chart measurements.
   - `POST /api/products/manual`: Creates a normalized product record from manual user entry when automated access is restricted.

---

## Running Tests & Development Server

```bash
# Run all 30 automated Python unit tests
npm test
# or directly:
python3 -m unittest discover -s backend/tests -v

# Run a live Phase 9 diagnostic verification test against an authorized Shopify product URL
python3 -m backend.main --test-url "https://www.taylorstitch.com/products/glacier-shirt-in-topsoil-corded-denim-2610"

# Start the full-stack server on port 3000
npm run dev
```
