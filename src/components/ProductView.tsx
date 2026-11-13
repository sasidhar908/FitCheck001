import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  ExternalLink,
  Ruler,
  ZoomIn,
  ZoomOut,
  ImageOff,
  Check,
  AlertTriangle,
  Activity,
  PenLine,
} from 'lucide-react';
import type { ProductResponse, SizeMeasurementRow } from '../types/product';
import { VirtualTryOnPanel } from './VirtualTryOnPanel';

interface ProductViewProps {
  product: ProductResponse | null;
  selectedSize: string | null;
  onSelectSize: (size: string) => void;
  onOpenSizeChart: () => void;
  onOpenDiagnostics: () => void;
  onOpenManualFallback: () => void;
  onBackToCatalog: () => void;
}

const MEASUREMENT_LABELS: Record<string, string> = {
  chest_cm: 'Chest',
  shoulder_cm: 'Shoulder',
  waist_cm: 'Waist',
  hip_cm: 'Hip',
  sleeve_length_cm: 'Sleeve',
  garment_length_cm: 'Length',
  inseam_cm: 'Inseam',
  rise_cm: 'Rise',
  neck_cm: 'Neck',
};

export const ProductView: React.FC<ProductViewProps> = ({
  product,
  selectedSize,
  onSelectSize,
  onOpenSizeChart,
  onOpenDiagnostics,
  onOpenManualFallback,
  onBackToCatalog,
}) => {
  const gallery =
    product?.images?.gallery && product.images.gallery.length > 0
      ? product.images.gallery
      : product?.images?.primary_image
      ? [product.images.primary_image]
      : [];

  const [activeImageIdx, setActiveImageIdx] = useState(0);
  const [imageErrorMap, setImageErrorMap] = useState<Record<number, boolean>>({});
  const [isZoomed, setIsZoomed] = useState(false);
  const [zoomOrigin, setZoomOrigin] = useState({ x: 50, y: 50 });

  useEffect(() => {
    setActiveImageIdx(0);
    setImageErrorMap({});
    setIsZoomed(false);
  }, [product?.product_id]);

  const activeImageUrl = gallery[activeImageIdx] || null;
  const isImageBrokenOrMissing = !activeImageUrl || Boolean(imageErrorMap[activeImageIdx]);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isZoomed) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setZoomOrigin({ x: Math.min(100, Math.max(0, x)), y: Math.min(100, Math.max(0, y)) });
  };

  const selectedSizeRow: SizeMeasurementRow | null =
    product?.sizes?.size_chart?.rows?.find((r) => r.size === selectedSize) || null;

  const hasSizeChart = Boolean(
    product?.sizes?.size_chart &&
      product.sizes.size_chart.rows &&
      product.sizes.size_chart.rows.length > 0
  );

  const formatPrice = (val: number | null | undefined): string => {
    if (val === null || val === undefined || typeof val !== 'number' || Number.isNaN(val)) {
      return '';
    }
    const curr = product?.pricing?.currency || 'INR';
    return new Intl.NumberFormat(curr === 'USD' ? 'en-US' : 'en-IN', {
      style: 'currency',
      currency: curr,
      maximumFractionDigits: 0,
    }).format(val);
  };

  const isBlockedOrFailed =
    !product ||
    product.extraction.status === 'blocked' ||
    (product.extraction.status === 'failed' && !product.name);

  const availabilityLabel =
    product?.availability?.product_status === 'in_stock'
      ? 'In Stock'
      : product?.availability?.product_status === 'out_of_stock'
      ? 'Out of Stock'
      : 'Availability Unknown';

  return (
    <section className="mx-auto w-full max-w-[1440px] overflow-x-hidden px-4 py-8 sm:px-6 md:py-10">
      {/* Top Breadcrumb / Back Action */}
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border-subtle)] pb-4">
        <button
          type="button"
          onClick={onBackToCatalog}
          className="inline-flex items-center gap-2 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)] whitespace-nowrap shrink-0 cursor-pointer"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to URL Extractor
        </button>

        {product && (
          <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)]">
            <span>{product.retailer}</span>
            {product.store_domain && (
              <>
                <span aria-hidden="true">·</span>
                <span className="font-mono-tabular">{product.store_domain}</span>
              </>
            )}
            <span aria-hidden="true">·</span>
            <span>{product.gender || 'Apparel'}</span>
            {product.category && (
              <>
                <span aria-hidden="true">·</span>
                <span>{product.category}</span>
              </>
            )}
            {product.sku && (
              <>
                <span aria-hidden="true">·</span>
                <span className="font-mono-tabular">ID {product.sku}</span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Desktop 75% / 25% Split Layout (Stacks Vertically on Mobile) */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 lg:items-start">
        {/* LEFT SIDE (75% width on desktop -> lg:col-span-9): Extracted Product Information */}
        <div className="lg:col-span-9 min-w-0">
          {isBlockedOrFailed ? (
            <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8">
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-[var(--text-primary)]">
                  <AlertTriangle className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <p className="text-xs font-medium text-[var(--text-muted)]">
                    {product
                      ? `${product.retailer} · Outcome: ${
                          product.diagnostics?.outcome_classification ||
                          product.extraction.status.toUpperCase()
                        }`
                      : 'No Product Selected'}
                  </p>
                  <h2 className="mt-1 font-serif-display text-2xl font-semibold text-[var(--text-primary)]">
                    {product
                      ? `Automated access was restricted by ${product.retailer}`
                      : 'Extract or Select a Garment'}
                  </h2>
                  <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                    {product?.extraction?.error_message ||
                      'Paste a product URL in the URL Extractor or enter product details manually. The Live Camera preview on the right operates independently at all times.'}
                  </p>

                  <div className="mt-6 flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={onOpenManualFallback}
                      className="inline-flex items-center gap-2 rounded-lg bg-[var(--accent-bg)] px-4 py-2.5 text-xs font-medium text-[var(--accent-text)] whitespace-nowrap shrink-0 transition-colors hover:bg-[var(--accent-hover)] cursor-pointer"
                    >
                      <PenLine className="h-3.5 w-3.5" />
                      Enter Product Details Manually
                    </button>
                    {product && (
                      <>
                        <button
                          type="button"
                          onClick={onOpenDiagnostics}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--bg-subtle)] px-4 py-2.5 text-xs font-medium text-[var(--text-primary)] whitespace-nowrap shrink-0 transition-colors hover:bg-[var(--bg-hover)] cursor-pointer"
                        >
                          <Activity className="h-3.5 w-3.5" />
                          Inspect Extraction Diagnostics
                        </button>
                        <a
                          href={product.original_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--bg-subtle)] px-4 py-2.5 text-xs font-medium text-[var(--text-primary)] whitespace-nowrap shrink-0 transition-colors hover:bg-[var(--bg-hover)]"
                        >
                          View on Original Website
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-10">
              {/* Top Row inside 75% Left Panel: Image Gallery + Core Product Details */}
              <div className="grid grid-cols-1 gap-8 xl:grid-cols-12 xl:items-start">
                {/* Product Image Gallery */}
                <div className="xl:col-span-6 xl:sticky xl:top-24">
                  <div className="flex flex-col-reverse gap-3.5 sm:flex-row">
                    {/* Thumbnail Image Selector */}
                    {gallery.length > 1 && (
                      <div className="flex flex-row gap-2.5 overflow-x-auto sm:flex-col sm:w-18 sm:max-h-[580px] sm:overflow-y-auto sm:shrink-0">
                        {gallery.map((imgUrl, idx) => {
                          const thumbUrl = product.images.thumbnails?.[idx] || imgUrl;
                          const isActive = idx === activeImageIdx;
                          return (
                            <button
                              key={idx}
                              type="button"
                              onClick={() => {
                                setActiveImageIdx(idx);
                                setIsZoomed(false);
                              }}
                              className={`relative aspect-[3/4] w-14 sm:w-18 shrink-0 overflow-hidden rounded-lg border transition-all cursor-pointer ${
                                isActive
                                  ? 'border-[var(--text-primary)] ring-1 ring-[var(--text-primary)]'
                                  : 'border-[var(--border-subtle)] opacity-75 hover:opacity-100'
                              } bg-[var(--bg-subtle)]`}
                              aria-label={`View product image ${idx + 1}`}
                            >
                              {!imageErrorMap[idx] ? (
                                <img
                                  src={thumbUrl}
                                  alt={`${product.name || 'Product'} view ${idx + 1}`}
                                  referrerPolicy="no-referrer"
                                  onError={() =>
                                    setImageErrorMap((prev) => ({ ...prev, [idx]: true }))
                                  }
                                  className="h-full w-full object-cover"
                                />
                              ) : (
                                <div className="flex h-full w-full items-center justify-center text-[var(--text-muted)]">
                                  <ImageOff className="h-4 w-4" />
                                </div>
                              )}
                            </button>
                          );
                        })}
                      </div>
                    )}

                    {/* Main Product Image */}
                    <div className="relative flex-1 overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-subtle)] aspect-[3/4]">
                      {!isImageBrokenOrMissing && activeImageUrl ? (
                        <div
                          onClick={() => setIsZoomed((prev) => !prev)}
                          onMouseMove={handleMouseMove}
                          onMouseLeave={() => setIsZoomed(false)}
                          className={`relative h-full w-full overflow-hidden ${
                            isZoomed ? 'cursor-zoom-out' : 'cursor-zoom-in'
                          }`}
                        >
                          <img
                            src={activeImageUrl}
                            alt={product.name || 'Extracted product image'}
                            referrerPolicy="no-referrer"
                            onError={() =>
                              setImageErrorMap((prev) => ({ ...prev, [activeImageIdx]: true }))
                            }
                            style={
                              isZoomed
                                ? {
                                    transformOrigin: `${zoomOrigin.x}% ${zoomOrigin.y}%`,
                                    transform: 'scale(1.85)',
                                  }
                                : undefined
                            }
                            className="h-full w-full object-cover transition-transform duration-200 ease-out"
                          />

                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setIsZoomed((prev) => !prev);
                            }}
                            className="absolute bottom-4 right-4 inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]/90 px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] backdrop-blur-xs transition-colors hover:bg-[var(--bg-surface)] cursor-pointer"
                          >
                            {isZoomed ? (
                              <>
                                <ZoomOut className="h-3.5 w-3.5" />
                                Reset Zoom
                              </>
                            ) : (
                              <>
                                <ZoomIn className="h-3.5 w-3.5" />
                                Click to Zoom
                              </>
                            )}
                          </button>
                        </div>
                      ) : (
                        <div className="flex h-full w-full flex-col items-center justify-center p-8 text-center">
                          <div className="flex h-14 w-14 items-center justify-center rounded-full border border-[var(--border-strong)] bg-[var(--bg-surface)] text-[var(--text-muted)]">
                            <ImageOff className="h-6 w-6" />
                          </div>
                          <p className="mt-4 text-sm font-semibold text-[var(--text-primary)]">
                            Product image unavailable
                          </p>
                          <p className="mt-1 max-w-xs text-xs text-[var(--text-muted)]">
                            No publicly accessible product image URL was returned by{' '}
                            {product.retailer}. Placeholder images are never substituted.
                          </p>
                          <button
                            type="button"
                            onClick={onOpenManualFallback}
                            className="mt-4 rounded-lg border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3.5 py-2 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--bg-hover)] cursor-pointer"
                          >
                            Supply Image URL Manually
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Product Information Column */}
                <div className="xl:col-span-6 space-y-6 min-w-0">
                  {/* Brand, Retailer & Product Name */}
                  <div>
                    <div className="flex flex-wrap items-center gap-2 text-xs font-medium text-[var(--text-muted)]">
                      <span className="uppercase tracking-wider text-[var(--text-primary)] font-semibold">
                        {product.brand || 'Brand Unavailable'}
                      </span>
                      <span aria-hidden="true">·</span>
                      <span>Verified {product.retailer} Listing</span>
                      <span aria-hidden="true">·</span>
                      <span
                        className={
                          product.availability.product_status === 'in_stock'
                            ? 'font-medium text-[var(--status-success-text)]'
                            : product.availability.product_status === 'out_of_stock'
                            ? 'font-medium text-[var(--status-error-text)]'
                            : ''
                        }
                      >
                        {availabilityLabel}
                      </span>
                    </div>

                    <h1 className="mt-2 font-serif-display text-3xl font-semibold leading-tight text-[var(--text-primary)] sm:text-4xl">
                      {product.name || 'Untitled Garment'}
                    </h1>
                  </div>

                  {/* Price and Discount */}
                  <div className="border-y border-[var(--border-subtle)] py-4">
                    {product.pricing.selling_price !== null ? (
                      <div className="flex flex-wrap items-baseline gap-3">
                        <span className="font-mono-tabular text-2xl font-semibold text-[var(--text-primary)]">
                          {formatPrice(product.pricing.selling_price)}
                        </span>
                        {product.pricing.mrp !== null &&
                          product.pricing.mrp > product.pricing.selling_price && (
                            <span className="font-mono-tabular text-sm text-[var(--text-muted)] line-through">
                              MRP {formatPrice(product.pricing.mrp)}
                            </span>
                          )}
                        {product.pricing.discount_percentage !== null &&
                          product.pricing.discount_percentage > 0 && (
                            <span className="font-mono-tabular text-sm font-medium text-[var(--status-warning-text)]">
                              ({product.pricing.discount_percentage}% OFF)
                            </span>
                          )}
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <span className="text-base font-medium text-[var(--text-secondary)]">
                          Price unavailable
                        </span>
                        <span className="text-xs text-[var(--text-muted)]">
                          Not exposed in public markup
                        </span>
                      </div>
                    )}
                    <p className="mt-1 text-xs text-[var(--text-muted)]">
                      Extracted Price · Currency: {product.pricing.currency || 'INR'} ·{' '}
                      {availabilityLabel}
                    </p>
                  </div>

                  {/* Available Sizes, Variants & Extracted Garment Measurements */}
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                        Available Sizes &amp; Variants
                      </span>
                      <button
                        type="button"
                        onClick={onOpenSizeChart}
                        className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--text-primary)] underline underline-offset-4 hover:text-[var(--text-secondary)] whitespace-nowrap shrink-0 cursor-pointer"
                      >
                        <Ruler className="h-3.5 w-3.5" />
                        Size Chart &amp; Measurements
                      </button>
                    </div>

                    {product.sizes.available_sizes &&
                    product.sizes.available_sizes.length > 0 ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {product.sizes.available_sizes.map((sz) => {
                          const isSelected = selectedSize === sz.normalized_label;
                          const isAvailable = sz.available !== false;
                          return (
                            <button
                              key={`${sz.label}_${sz.normalized_label}`}
                              type="button"
                              onClick={() => onSelectSize(sz.normalized_label)}
                              className={`group relative flex min-w-[3.25rem] flex-col items-center justify-center rounded-lg border px-3 py-2 text-xs transition-all whitespace-nowrap shrink-0 cursor-pointer ${
                                isSelected
                                  ? 'border-[var(--accent-bg)] bg-[var(--accent-bg)] text-[var(--accent-text)]'
                                  : isAvailable
                                  ? 'border-[var(--border-strong)] bg-[var(--bg-surface)] text-[var(--text-primary)] hover:border-[var(--text-primary)]'
                                  : 'border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-[var(--text-muted)] line-through opacity-60'
                              }`}
                            >
                              <span className="font-mono-tabular font-semibold">
                                {sz.normalized_label}
                              </span>
                              {sz.label !== sz.normalized_label && (
                                <span
                                  className={`text-[10px] font-mono-tabular ${
                                    isSelected ? 'opacity-80' : 'text-[var(--text-muted)]'
                                  }`}
                                >
                                  ({sz.label})
                                </span>
                              )}
                            </button>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="mt-2 text-xs text-[var(--text-muted)]">
                        Size variants were not listed in the extracted product data.
                      </p>
                    )}

                    {/* Selected Size Extracted Garment Measurements */}
                    {selectedSize && (
                      <div className="mt-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-medium text-[var(--text-primary)]">
                            Selected Size{' '}
                            <strong className="font-mono-tabular">{selectedSize}</strong>{' '}
                            Garment Measurements
                          </span>
                          <span className="text-[var(--text-secondary)]">
                            {product.availability.size_availability?.[selectedSize] ===
                            'out_of_stock'
                              ? 'Out of stock in this size'
                              : 'In Stock'}
                          </span>
                        </div>

                        {selectedSizeRow ? (
                          <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-[var(--border-subtle)] pt-3 sm:grid-cols-3">
                            {Object.entries(MEASUREMENT_LABELS).map(([key, label]) => {
                              const val = selectedSizeRow[key as keyof SizeMeasurementRow];
                              if (typeof val !== 'number') return null;
                              return (
                                <div key={key} className="text-xs">
                                  <span className="text-[var(--text-muted)]">{label}: </span>
                                  <span className="font-mono-tabular font-medium text-[var(--text-primary)]">
                                    {val.toFixed(1)} cm
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <p className="mt-2 text-xs text-[var(--text-muted)]">
                            {hasSizeChart
                              ? `Specific garment measurements for size ${selectedSize} were not listed in the extracted size chart.`
                              : `Size chart measurements were not provided by ${product.retailer} for this product.`}
                          </p>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Primary Action Buttons */}
                  <div className="flex flex-col gap-3 sm:flex-row">
                    <button
                      type="button"
                      onClick={onOpenSizeChart}
                      className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-[var(--accent-bg)] px-4 py-3 text-xs font-medium text-[var(--accent-text)] transition-colors hover:bg-[var(--accent-hover)] whitespace-nowrap shrink-0 cursor-pointer"
                    >
                      <Ruler className="h-4 w-4" />
                      Inspect Full Size Chart
                    </button>

                    <a
                      href={product.original_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-center gap-2 rounded-lg border border-[var(--border-strong)] bg-[var(--bg-surface)] px-4 py-3 text-xs font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)] whitespace-nowrap shrink-0"
                    >
                      View on Original Website
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </div>

                  {/* Product Description & Garment Specifications */}
                  <div className="space-y-4 border-t border-[var(--border-subtle)] pt-5">
                    <div>
                      <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                        Product Description
                      </h2>
                      <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                        {product.description ||
                          'Product description was not provided by the retailer.'}
                      </p>
                    </div>

                    {product.fabric_care && product.fabric_care.length > 0 && (
                      <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                          Material &amp; Care
                        </h3>
                        <ul className="mt-1.5 space-y-1 text-xs text-[var(--text-secondary)]">
                          {product.fabric_care.map((fc, idx) => (
                            <li key={idx}>· {fc}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {product.specifications &&
                      Object.keys(product.specifications).length > 0 && (
                        <div>
                          <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                            Garment Specifications
                          </h3>
                          <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                            {Object.entries(product.specifications).map(([key, val]) => (
                              <div key={key} className="border-b border-[var(--border-subtle)] pb-1.5">
                                <dt className="text-[var(--text-muted)]">{key}</dt>
                                <dd className="font-medium text-[var(--text-primary)]">{val}</dd>
                              </div>
                            ))}
                          </dl>
                        </div>
                      )}
                  </div>

                  {/* Compact Extraction Provenance */}
                  <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Activity className="h-3.5 w-3.5 text-[var(--text-primary)]" />
                        <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                          Extraction Provenance
                        </span>
                      </div>
                      <span className="font-mono-tabular text-xs font-semibold text-[var(--text-primary)]">
                        {product.diagnostics?.outcome_classification ||
                          product.extraction.status.toUpperCase()}{' '}
                        ({product.diagnostics?.extracted_field_count ?? 0}/
                        {product.diagnostics?.total_expected_fields ?? 11} Fields)
                      </span>
                    </div>

                    {product.extraction.missing_fields &&
                    product.extraction.missing_fields.length > 0 ? (
                      <p className="text-xs text-[var(--status-warning-text)]">
                        {product.extraction.missing_fields.length} field(s) not exposed in
                        public markup.
                      </p>
                    ) : (
                      <div className="flex items-center gap-1.5 text-xs text-[var(--text-primary)]">
                        <Check className="h-3.5 w-3.5" />
                        <span>
                          All garment, image, pricing, variant, and size chart fields verified.
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Inline Extracted Size Chart Table inside 75% Left Section */}
              <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-subtle)] pb-4">
                  <div>
                    <h2 className="font-serif-display text-xl font-semibold text-[var(--text-primary)]">
                      Size Chart &amp; Extracted Garment Measurements
                    </h2>
                    <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                      {hasSizeChart
                        ? `Normalized garment measurements in centimeters (source unit: ${product.sizes.size_chart?.source_unit || 'cm'}). Click any row to select that size.`
                        : `Public size chart status for ${product.name || 'this garment'}.`}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={onOpenSizeChart}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--bg-subtle)] px-3.5 py-2 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--bg-hover)] cursor-pointer"
                  >
                    <Ruler className="h-3.5 w-3.5" />
                    Open Interactive Size Modal (cm / in)
                  </button>
                </div>

                {hasSizeChart && product.sizes.size_chart ? (
                  <div className="mt-4 overflow-x-auto">
                    <table className="w-full border-collapse text-left text-xs">
                      <thead>
                        <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                          <th className="py-2.5 px-3">Size</th>
                          {Object.entries(MEASUREMENT_LABELS).map(([key, label]) => {
                            const hasCol = product.sizes.size_chart!.rows.some(
                              (r) => typeof r[key as keyof SizeMeasurementRow] === 'number'
                            );
                            if (!hasCol) return null;
                            return (
                              <th key={key} className="py-2.5 px-3">
                                {label} (cm)
                              </th>
                            );
                          })}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border-subtle)]">
                        {product.sizes.size_chart.rows.map((row) => {
                          const isRowSelected = row.size === selectedSize;
                          return (
                            <tr
                              key={row.size}
                              onClick={() => onSelectSize(row.size)}
                              className={`cursor-pointer transition-colors ${
                                isRowSelected
                                  ? 'bg-[var(--accent-bg)] text-[var(--accent-text)]'
                                  : 'hover:bg-[var(--bg-subtle)] text-[var(--text-primary)]'
                              }`}
                            >
                              <td className="py-2.5 px-3 font-mono-tabular font-semibold">
                                {row.size}
                              </td>
                              {Object.keys(MEASUREMENT_LABELS).map((key) => {
                                const hasCol = product.sizes.size_chart!.rows.some(
                                  (r) => typeof r[key as keyof SizeMeasurementRow] === 'number'
                                );
                                if (!hasCol) return null;
                                const val = row[key as keyof SizeMeasurementRow];
                                return (
                                  <td
                                    key={key}
                                    className="py-2.5 px-3 font-mono-tabular"
                                  >
                                    {typeof val === 'number' ? val.toFixed(1) : '—'}
                                  </td>
                                );
                              })}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="mt-4 text-xs text-[var(--text-muted)]">
                    No structured size chart table was exposed on the retailer product page.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT SIDE (25% width on desktop -> lg:col-span-3): Live 9:16 Portrait Camera */}
        <div className="lg:col-span-3 lg:sticky lg:top-24 min-w-0">
          <VirtualTryOnPanel
            product={product}
            selectedSize={selectedSize}
            selectedSizeRow={selectedSizeRow}
          />
        </div>
      </div>
    </section>
  );
};
