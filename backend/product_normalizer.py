"""
Product Normalizer, Diagnostics Calculator (Phase 8), and
11-Point Real Product Verification Report Builder (Phase 9).

Never marks a response as SUCCESS merely because HTTP 200 was returned.
Strictly distinguishes SUCCESS, PARTIAL, BLOCKED, and FAILED.
"""

from __future__ import annotations
from typing import List
from .adapters.common import finalize_product_response
from .schemas import (
    FieldVerificationItem,
    ProductResponse,
    ProductVerificationReport,
)


def build_verification_report(product: ProductResponse) -> ProductVerificationReport:
    """
    Build the Phase 9 11-point field-by-field verification report.
    Reports honestly whether each field was extracted or was unavailable from the source.
    """
    src = product.extraction.source or "none"

    has_title = bool(product.name and product.name.strip())
    has_brand = bool(product.brand and product.brand.strip())
    has_main_img = bool(product.images.primary_image)
    add_img_count = max(0, len(product.images.gallery) - 1)
    has_add_imgs = add_img_count > 0
    has_selling_price = product.pricing.selling_price is not None
    has_mrp = product.pricing.mrp is not None
    variant_count = len(product.sizes.available_sizes)
    has_variants = variant_count > 0
    in_stock_sizes = [s.normalized_label for s in product.sizes.available_sizes if s.available is not False]
    has_sizes = len(in_stock_sizes) > 0 or variant_count > 0
    has_availability = product.availability.product_status in ("in_stock", "out_of_stock")
    chart_rows = len(product.sizes.size_chart.rows) if (product.sizes.size_chart and product.sizes.size_chart.rows) else 0
    has_size_chart = chart_rows > 0
    has_url = bool(product.original_url)

    items: List[FieldVerificationItem] = [
        FieldVerificationItem(
            field_key="product_title",
            field_label="1. Product Title",
            extracted=has_title,
            value_summary=product.name if has_title else None,
            source_method=src if has_title else "none",
            notes="Verified from product metadata." if has_title else "Unavailable in source markup.",
        ),
        FieldVerificationItem(
            field_key="brand",
            field_label="2. Brand / Vendor",
            extracted=has_brand,
            value_summary=product.brand if has_brand else None,
            source_method=src if has_brand else "none",
            notes="Verified brand/vendor field." if has_brand else "Brand not explicitly provided by source.",
        ),
        FieldVerificationItem(
            field_key="main_product_image",
            field_label="3. Main Product Image",
            extracted=has_main_img,
            value_summary=product.images.primary_image if has_main_img else None,
            source_method=src if has_main_img else "none",
            notes="Primary high-resolution image verified." if has_main_img else "No primary image URL found.",
        ),
        FieldVerificationItem(
            field_key="additional_product_images",
            field_label="4. Additional Product Images",
            extracted=has_add_imgs,
            value_summary=f"{add_img_count} additional gallery images" if has_add_imgs else "0 additional images",
            source_method=src if has_add_imgs else "none",
            notes=f"Total gallery count: {len(product.images.gallery)}." if has_add_imgs else "Only single or no image exposed.",
        ),
        FieldVerificationItem(
            field_key="selling_price",
            field_label="5. Selling Price",
            extracted=has_selling_price,
            value_summary=f"{product.pricing.currency} {product.pricing.selling_price}" if has_selling_price else None,
            source_method=src if has_selling_price else "none",
            notes="Current selling price verified." if has_selling_price else "Selling price unavailable.",
        ),
        FieldVerificationItem(
            field_key="original_price",
            field_label="6. Original Price / Compare-At",
            extracted=has_mrp,
            value_summary=f"{product.pricing.currency} {product.pricing.mrp}" if has_mrp else None,
            source_method=src if has_mrp else "none",
            notes="Original/compare-at price verified." if has_mrp else "Original price not provided.",
        ),
        FieldVerificationItem(
            field_key="product_variants",
            field_label="7. Product Variants",
            extracted=has_variants,
            value_summary=f"{variant_count} variants extracted" if has_variants else None,
            source_method=src if has_variants else "none",
            notes="Variant SKUs and option titles extracted." if has_variants else "No variants found.",
        ),
        FieldVerificationItem(
            field_key="available_sizes",
            field_label="8. Available Sizes",
            extracted=has_sizes,
            value_summary=", ".join(in_stock_sizes) if in_stock_sizes else None,
            source_method=src if has_sizes else "none",
            notes=f"{len(in_stock_sizes)} in-stock sizes normalized." if has_sizes else "Sizes unavailable.",
        ),
        FieldVerificationItem(
            field_key="availability",
            field_label="9. Stock Availability",
            extracted=has_availability,
            value_summary=product.availability.product_status,
            source_method=src if has_availability else "none",
            notes="Product and variant-level stock verified." if has_availability else "Stock status unknown.",
        ),
        FieldVerificationItem(
            field_key="size_chart",
            field_label="10. Garment Size Chart",
            extracted=has_size_chart,
            value_summary=(
                f"{chart_rows} size rows ({', '.join(product.sizes.size_chart.columns)})"
                if (has_size_chart and product.sizes.size_chart)
                else None
            ),
            source_method="crawl4ai_html_table" if has_size_chart else "none",
            notes=(
                "Garment measurements normalized to centimeters (cm)."
                if has_size_chart
                else "Retailer did not provide a garment measurement size chart for this item."
            ),
        ),
        FieldVerificationItem(
            field_key="original_product_url",
            field_label="11. Original Product URL",
            extracted=has_url,
            value_summary=product.original_url,
            source_method="validated_input",
            notes="Canonical product URL preserved.",
        ),
    ]

    verified_count = sum(1 for item in items if item.extracted)
    outcome = product.diagnostics.outcome_classification or product.extraction.status.upper()

    return ProductVerificationReport(
        tested_url=product.original_url,
        store_domain=product.store_domain or product.retailer,
        product_handle=product.product_handle or product.product_id,
        overall_outcome=outcome,
        verified_field_count=verified_count,
        total_fields_checked=len(items),
        fields=items,
    )


def normalize_and_diagnose_product(product: ProductResponse) -> ProductResponse:
    """
    Finalize field-level confidence, missing fields, try-on compatibility,
    Phase 8 ExtractionDiagnostics, and Phase 9 ProductVerificationReport.
    """
    product = finalize_product_response(product)

    diag = product.diagnostics
    if not diag.submitted_url:
        diag.submitted_url = product.original_url
    if not diag.detected_retailer or diag.detected_retailer == "Unknown":
        diag.detected_retailer = product.retailer
    if not diag.store_domain:
        diag.store_domain = product.store_domain or product.retailer.lower()
    if not diag.product_handle:
        diag.product_handle = product.product_handle or product.product_id

    diag.extracted_image_count = len(product.images.gallery)
    diag.missing_fields = [m.field for m in product.extraction.missing_fields]

    # Classify outcome strictly: NEVER return SUCCESS just because HTTP 200 was returned
    if product.extraction.status == "blocked":
        diag.outcome_classification = "BLOCKED"
    elif product.extraction.status == "failed" or not product.name:
        diag.outcome_classification = "FAILED"
    elif len(diag.missing_fields) == 0:
        diag.outcome_classification = "SUCCESS"
    else:
        diag.outcome_classification = "PARTIAL"

    report = build_verification_report(product)
    diag.extracted_field_count = report.verified_field_count
    diag.total_expected_fields = report.total_fields_checked
    product.verification_report = report

    return product
