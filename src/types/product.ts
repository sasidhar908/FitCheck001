export interface ProductImages {
  primary_image: string | null;
  gallery: string[];
  thumbnails: string[];
  high_res_images: string[];
}

export interface ProductPricing {
  mrp: number | null;
  selling_price: number | null;
  discount_percentage: number | null;
  discount_label: string | null;
  currency: string;
  offers: string[];
}

export interface SizeMeasurementRow {
  size: string;
  chest_cm: number | null;
  shoulder_cm: number | null;
  waist_cm: number | null;
  hip_cm: number | null;
  sleeve_length_cm: number | null;
  garment_length_cm: number | null;
  inseam_cm: number | null;
  rise_cm: number | null;
  neck_cm: number | null;
  thigh_cm?: number | null;
  original_values: Record<string, unknown>;
}

export interface SizeChart {
  unit: string;
  source_unit: string;
  garment_category: string;
  columns: string[];
  rows: SizeMeasurementRow[];
  notes: string | null;
}

export interface SizeVariant {
  label: string;
  normalized_label: string;
  sku: string | null;
  variant_id?: string | null;
  available: boolean | null;
  inventory_count: number | null;
  price?: number | null;
  compare_at_price?: number | null;
  seller: string | null;
  measurements: Record<string, number | null>;
}

export interface ProductSizes {
  available_sizes: SizeVariant[];
  size_chart: SizeChart | null;
}

export interface ProductAvailability {
  product_status: 'in_stock' | 'out_of_stock' | 'unknown';
  available_variants: string[];
  size_availability: Record<string, 'in_stock' | 'out_of_stock' | 'unknown'>;
}

export interface MissingFieldExplanation {
  field: string;
  reason: string;
}

export interface ExtractionMetadata {
  timestamp: string;
  source:
    | 'shopify_storefront_and_crawl4ai'
    | 'shopify_storefront_api'
    | 'crawl4ai_engine'
    | 'official_endpoint'
    | 'embedded_json'
    | 'json_ld'
    | 'html_selectors'
    | 'playwright'
    | 'gemini_assisted'
    | 'manual_entry'
    | 'none'
    | 'unknown';
  status: 'success' | 'partial' | 'blocked' | 'failed' | 'pending';
  overall_confidence: number;
  field_confidence: Record<string, number>;
  missing_fields: MissingFieldExplanation[];
  warnings: string[];
  error_code: string | null;
  error_message: string | null;
}

export interface ExtractionDiagnostics {
  submitted_url: string;
  detected_retailer: string;
  store_domain: string | null;
  product_handle: string | null;
  authorized_data_source: string;
  crawl4ai_connection_status:
    | 'connected_cloud_run'
    | 'connected_local_sdk'
    | 'standby_cloud_run_not_configured'
    | 'unreachable'
    | string;
  crawl4ai_endpoint: string | null;
  http_response_status: number | null;
  browser_rendering_status: string;
  extraction_method: string;
  css_strategy_used: boolean;
  xpath_strategy_used: boolean;
  json_ld_found: boolean;
  extracted_image_count: number;
  extracted_field_count: number;
  total_expected_fields: number;
  missing_fields: string[];
  extraction_duration_ms: number;
  outcome_classification: 'SUCCESS' | 'PARTIAL' | 'BLOCKED' | 'FAILED';
  error_details: string | null;
}

export interface FieldVerificationItem {
  field_key: string;
  field_label: string;
  extracted: boolean;
  value_summary: string | null;
  source_method: string;
  notes: string | null;
}

export interface ProductVerificationReport {
  tested_url: string;
  store_domain: string;
  product_handle: string;
  overall_outcome: 'SUCCESS' | 'PARTIAL' | 'BLOCKED' | 'FAILED';
  verified_field_count: number;
  total_fields_checked: number;
  fields: FieldVerificationItem[];
}

export interface TryOnCompatibility {
  ready_for_try_on: boolean;
  selected_garment_image_url: string | null;
  selected_size: string | null;
  garment_category_class: 'upper_body' | 'lower_body' | 'full_body';
  supported_pose_landmarks: string[];
  measurement_keys_available: string[];
}

export interface ProductResponse {
  product_id: string;
  retailer: 'Shopify' | 'Myntra' | 'AJIO' | 'Manual' | string;
  original_url: string;
  store_domain?: string | null;
  product_handle?: string | null;
  name: string | null;
  brand: string | null;
  description: string | null;
  category: string | null;
  sub_category: string | null;
  gender: string | null;
  garment_type: 'shirt' | 'trousers' | 'outerwear' | 'dress' | 'top' | 'other';
  sku: string | null;
  fabric_care: string[];
  specifications: Record<string, string>;
  images: ProductImages;
  pricing: ProductPricing;
  sizes: ProductSizes;
  availability: ProductAvailability;
  extraction: ExtractionMetadata;
  diagnostics: ExtractionDiagnostics;
  verification_report: ProductVerificationReport | null;
  try_on_compatibility: TryOnCompatibility;
}

export interface DiagnosticTestBundle {
  product: ProductResponse;
  diagnostics: ExtractionDiagnostics;
  verification_report: ProductVerificationReport;
}

export interface ManualProductInput {
  original_url?: string;
  retailer?: 'Shopify' | 'Myntra' | 'AJIO' | 'Manual';
  name: string;
  brand: string;
  category?: string;
  gender?: string;
  description?: string;
  selling_price?: number | null;
  mrp?: number | null;
  currency?: string;
  primary_image?: string;
  images?: string[];
  available_sizes?: string[];
  measurement_unit?: 'cm' | 'in';
  size_chart_rows?: Array<{
    size: string;
    chest?: number | null;
    shoulder?: number | null;
    waist?: number | null;
    hip?: number | null;
    sleeve_length?: number | null;
    garment_length?: number | null;
    inseam?: number | null;
    rise?: number | null;
  }>;
}


