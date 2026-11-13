"""
Unified ProductResponse, ExtractionDiagnostics, and ProductVerificationReport schemas
using Pydantic (with stdlib dataclass compatibility fallback).
Supports Shopify (via Storefront API + Crawl4AI), Myntra, and AJIO.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel as _PydanticBaseModel
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    _PydanticBaseModel = object


@dataclass
class ProductImages:
    primary_image: Optional[str] = None
    gallery: List[str] = field(default_factory=list)
    thumbnails: List[str] = field(default_factory=list)
    high_res_images: List[str] = field(default_factory=list)


@dataclass
class ProductPricing:
    mrp: Optional[float] = None
    selling_price: Optional[float] = None
    discount_percentage: Optional[int] = None
    discount_label: Optional[str] = None
    currency: str = "INR"
    offers: List[str] = field(default_factory=list)


@dataclass
class SizeMeasurementRow:
    size: str
    chest_cm: Optional[float] = None
    shoulder_cm: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    sleeve_length_cm: Optional[float] = None
    garment_length_cm: Optional[float] = None
    inseam_cm: Optional[float] = None
    rise_cm: Optional[float] = None
    neck_cm: Optional[float] = None
    thigh_cm: Optional[float] = None
    original_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SizeChart:
    unit: str = "cm"
    source_unit: str = "in"
    garment_category: str = "shirt"
    columns: List[str] = field(default_factory=list)
    rows: List[SizeMeasurementRow] = field(default_factory=list)
    notes: Optional[str] = None


@dataclass
class SizeVariant:
    label: str
    normalized_label: str
    sku: Optional[str] = None
    variant_id: Optional[str] = None
    available: Optional[bool] = None
    inventory_count: Optional[int] = None
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    seller: Optional[str] = None
    measurements: Dict[str, Optional[float]] = field(default_factory=dict)


@dataclass
class ProductSizes:
    available_sizes: List[SizeVariant] = field(default_factory=list)
    size_chart: Optional[SizeChart] = None


@dataclass
class ProductAvailability:
    product_status: str = "unknown"  # "in_stock" | "out_of_stock" | "unknown"
    available_variants: List[str] = field(default_factory=list)
    size_availability: Dict[str, str] = field(default_factory=dict)


@dataclass
class MissingFieldExplanation:
    field: str
    reason: str


@dataclass
class ExtractionMetadata:
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "unknown"  # "shopify_storefront_and_crawl4ai" | "shopify_storefront_api" | "crawl4ai_engine" | "embedded_json" | "json_ld" | "html_selectors" | "manual_entry"
    status: str = "pending"  # "success" | "partial" | "blocked" | "failed"
    overall_confidence: float = 0.0
    field_confidence: Dict[str, float] = field(default_factory=dict)
    missing_fields: List[MissingFieldExplanation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ExtractionDiagnostics:
    """Phase 8 Developer Diagnostics telemetry for every extraction run."""
    submitted_url: str = ""
    detected_retailer: str = "Unknown"
    store_domain: Optional[str] = None
    product_handle: Optional[str] = None
    authorized_data_source: str = "None"
    crawl4ai_connection_status: str = "not_configured"  # "connected_cloud_run" | "connected_local_sdk" | "standby_cloud_run_not_configured" | "unreachable"
    crawl4ai_endpoint: Optional[str] = None
    http_response_status: Optional[int] = None
    browser_rendering_status: str = "not_invoked"  # "rendered_chromium" | "static_http_and_dom" | "skipped_api_sufficient" | "failed"
    extraction_method: str = "unknown"
    css_strategy_used: bool = False
    xpath_strategy_used: bool = False
    json_ld_found: bool = False
    extracted_image_count: int = 0
    extracted_field_count: int = 0
    total_expected_fields: int = 11
    missing_fields: List[str] = field(default_factory=list)
    extraction_duration_ms: float = 0.0
    outcome_classification: str = "FAILED"  # "SUCCESS" | "PARTIAL" | "BLOCKED" | "FAILED"
    error_details: Optional[str] = None


@dataclass
class FieldVerificationItem:
    """Single item in the Phase 9 11-point Real Product Test verification report."""
    field_key: str
    field_label: str
    extracted: bool
    value_summary: Optional[str] = None
    source_method: str = "none"
    notes: Optional[str] = None


@dataclass
class ProductVerificationReport:
    """Phase 9 Field-by-Field Verification Report."""
    tested_url: str
    store_domain: str
    product_handle: str
    overall_outcome: str  # "SUCCESS" | "PARTIAL" | "BLOCKED" | "FAILED"
    verified_field_count: int
    total_fields_checked: int
    fields: List[FieldVerificationItem] = field(default_factory=list)


@dataclass
class TryOnCompatibility:
    ready_for_try_on: bool = False
    selected_garment_image_url: Optional[str] = None
    selected_size: Optional[str] = None
    garment_category_class: str = "upper_body"
    supported_pose_landmarks: List[str] = field(
        default_factory=lambda: ["left_shoulder", "right_shoulder", "left_hip", "right_hip", "left_elbow", "right_elbow"]
    )
    measurement_keys_available: List[str] = field(default_factory=list)


@dataclass
class ProductResponse:
    product_id: str
    retailer: str  # "Shopify" | "Myntra" | "AJIO" | "Manual"
    original_url: str
    store_domain: Optional[str] = None
    product_handle: Optional[str] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    gender: Optional[str] = None
    garment_type: str = "other"
    sku: Optional[str] = None
    fabric_care: List[str] = field(default_factory=list)
    specifications: Dict[str, str] = field(default_factory=dict)
    images: ProductImages = field(default_factory=ProductImages)
    pricing: ProductPricing = field(default_factory=ProductPricing)
    sizes: ProductSizes = field(default_factory=ProductSizes)
    availability: ProductAvailability = field(default_factory=ProductAvailability)
    extraction: ExtractionMetadata = field(default_factory=ExtractionMetadata)
    diagnostics: ExtractionDiagnostics = field(default_factory=ExtractionDiagnostics)
    verification_report: Optional[ProductVerificationReport] = None
    try_on_compatibility: TryOnCompatibility = field(default_factory=TryOnCompatibility)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
