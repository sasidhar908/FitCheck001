import React, { useState } from 'react';
import { X, Ruler, AlertCircle } from 'lucide-react';
import type { SizeChart, SizeMeasurementRow } from '../types/product';

interface SizeChartModalProps {
  isOpen: boolean;
  onClose: () => void;
  productName: string | null;
  brand: string | null;
  garmentType: string;
  selectedSize: string | null;
  onSelectSize: (size: string) => void;
  sizeChart: SizeChart | null;
}

const COLUMN_METADATA: Record<string, { label: string; shirtRelevant: boolean; trouserRelevant: boolean }> = {
  chest_cm: { label: 'Chest', shirtRelevant: true, trouserRelevant: false },
  shoulder_cm: { label: 'Shoulder', shirtRelevant: true, trouserRelevant: false },
  waist_cm: { label: 'Waist', shirtRelevant: true, trouserRelevant: true },
  hip_cm: { label: 'Hip', shirtRelevant: false, trouserRelevant: true },
  sleeve_length_cm: { label: 'Sleeve Length', shirtRelevant: true, trouserRelevant: false },
  garment_length_cm: { label: 'Garment Length', shirtRelevant: true, trouserRelevant: true },
  inseam_cm: { label: 'Inseam', shirtRelevant: false, trouserRelevant: true },
  rise_cm: { label: 'Front Rise', shirtRelevant: false, trouserRelevant: true },
  neck_cm: { label: 'Neck', shirtRelevant: true, trouserRelevant: false },
};

export const SizeChartModal: React.FC<SizeChartModalProps> = ({
  isOpen,
  onClose,
  productName,
  brand,
  garmentType,
  selectedSize,
  onSelectSize,
  sizeChart,
}) => {
  const [displayUnit, setDisplayUnit] = useState<'cm' | 'in'>('cm');

  if (!isOpen) return null;

  // Determine dynamic columns based on garment category and available data
  const getDynamicColumns = (): string[] => {
    if (!sizeChart || !sizeChart.rows || sizeChart.rows.length === 0) return [];

    const existingCols = sizeChart.columns || [];
    if (garmentType === 'trousers') {
      const preferredOrder = ['waist_cm', 'hip_cm', 'inseam_cm', 'rise_cm', 'garment_length_cm'];
      const matched = preferredOrder.filter((col) => existingCols.includes(col));
      return matched.length > 0 ? matched : existingCols;
    }

    const shirtOrder = ['chest_cm', 'shoulder_cm', 'sleeve_length_cm', 'garment_length_cm', 'waist_cm', 'neck_cm'];
    const matched = shirtOrder.filter((col) => existingCols.includes(col));
    return matched.length > 0 ? matched : existingCols;
  };

  const columns = getDynamicColumns();

  const formatMeasurement = (row: SizeMeasurementRow, colKey: string): string => {
    const rawVal = row[colKey as keyof SizeMeasurementRow];
    if (typeof rawVal !== 'number' || Number.isNaN(rawVal)) {
      return 'Not provided';
    }
    if (displayUnit === 'in') {
      return `${(rawVal / 2.54).toFixed(1)}"`;
    }
    return `${rawVal.toFixed(1)} cm`;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-[2px] transition-opacity"
      role="dialog"
      aria-modal="true"
      aria-labelledby="size-chart-title"
    >
      <div className="relative flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-page)] text-[var(--text-primary)] shadow-xl">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-[var(--border-subtle)] px-6 py-5">
          <div>
            <p className="text-xs font-medium text-[var(--text-muted)]">
              {brand || 'FitCheck Specification'} · {garmentType === 'trousers' ? 'Trousers & Bottomwear' : 'Apparel & Topwear'}
            </p>
            <h2 id="size-chart-title" className="mt-1 font-serif-display text-2xl font-semibold text-[var(--text-primary)]">
              Garment Size &amp; Measurement Guide
            </h2>
            {productName && <p className="mt-0.5 text-sm text-[var(--text-secondary)]">{productName}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)] cursor-pointer"
            aria-label="Close size chart"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto p-6">
          {!sizeChart || !sizeChart.rows || sizeChart.rows.length === 0 || columns.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-6 py-12 text-center">
              <AlertCircle className="h-8 w-8 text-[var(--text-muted)]" />
              <h3 className="mt-3 text-base font-semibold text-[var(--text-primary)]">Size chart unavailable</h3>
              <p className="mt-1 max-w-md text-sm text-[var(--text-secondary)]">
                The retailer did not provide garment measurement dimensions for this item. No fabricated measurements are shown.
              </p>
            </div>
          ) : (
            <>
              {/* Unit Toggle & Instruction */}
              <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
                  <Ruler className="h-4 w-4 text-[var(--text-primary)]" />
                  <span>Click any row to select that size for fit analysis. Unavailable dimensions are marked as &ldquo;Not provided&rdquo;.</span>
                </div>

                <div className="flex items-center rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-1">
                  <button
                    type="button"
                    onClick={() => setDisplayUnit('cm')}
                    className={`rounded-md px-3 py-1.5 text-xs font-medium whitespace-nowrap shrink-0 transition-colors cursor-pointer ${
                      displayUnit === 'cm'
                        ? 'bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-xs'
                        : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                    }`}
                  >
                    Centimeters (cm)
                  </button>
                  <button
                    type="button"
                    onClick={() => setDisplayUnit('in')}
                    className={`rounded-md px-3 py-1.5 text-xs font-medium whitespace-nowrap shrink-0 transition-colors cursor-pointer ${
                      displayUnit === 'in'
                        ? 'bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-xs'
                        : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                    }`}
                  >
                    Inches (in)
                  </button>
                </div>
              </div>

              {/* Dynamic Measurement Table */}
              <div className="overflow-x-auto rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
                <table className="w-full border-collapse text-left text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-xs font-semibold text-[var(--text-secondary)]">
                      <th className="px-4 py-3.5 whitespace-nowrap">Size</th>
                      {columns.map((colKey) => (
                        <th key={colKey} className="px-4 py-3.5 whitespace-nowrap">
                          {COLUMN_METADATA[colKey]?.label || colKey} ({displayUnit})
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-subtle)]">
                    {sizeChart.rows.map((row) => {
                      const isSelected = selectedSize === row.size;
                      const brandSize =
                        row.original_values && typeof row.original_values.brand_size === 'string'
                          ? row.original_values.brand_size
                          : null;
                      return (
                        <tr
                          key={row.size}
                          onClick={() => onSelectSize(row.size)}
                          className={`cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-[var(--accent-bg)] text-[var(--accent-text)]'
                              : 'hover:bg-[var(--bg-subtle)] text-[var(--text-primary)]'
                          }`}
                        >
                          <td className="px-4 py-3.5 font-mono-tabular font-semibold whitespace-nowrap">
                            <span>{row.size}</span>
                            {brandSize && brandSize !== row.size && (
                              <span className={`ml-1.5 text-xs font-normal ${isSelected ? 'opacity-80' : 'text-[var(--text-muted)]'}`}>
                                ({brandSize})
                              </span>
                            )}
                          </td>
                          {columns.map((colKey) => {
                            const formatted = formatMeasurement(row, colKey);
                            const isMissing = formatted === 'Not provided';
                            return (
                              <td
                                key={colKey}
                                className={`px-4 py-3.5 font-mono-tabular whitespace-nowrap ${
                                  isMissing ? 'opacity-60 italic' : ''
                                }`}
                              >
                                {formatted}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {sizeChart.notes && (
                <p className="mt-3 text-xs text-[var(--text-muted)]">{sizeChart.notes}</p>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-6 py-4">
          <p className="text-xs text-[var(--text-secondary)]">
            Selected Size: <strong className="font-mono-tabular text-[var(--text-primary)]">{selectedSize || 'None'}</strong>
          </p>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg bg-[var(--accent-bg)] px-5 py-2 text-xs font-medium text-[var(--accent-text)] whitespace-nowrap shrink-0 transition-colors hover:bg-[var(--accent-hover)] cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
