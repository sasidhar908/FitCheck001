import React, { useState } from 'react';
import { X, Plus, Trash2 } from 'lucide-react';
import type { ManualProductInput } from '../types/product';

interface ManualEntryModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialUrl?: string;
  initialRetailer?: 'Myntra' | 'AJIO' | 'Manual';
  onSubmitManual: (payload: ManualProductInput) => Promise<void>;
  isSubmitting: boolean;
}

export const ManualEntryModal: React.FC<ManualEntryModalProps> = ({
  isOpen,
  onClose,
  initialUrl = '',
  initialRetailer = 'Myntra',
  onSubmitManual,
  isSubmitting,
}) => {
  const [url, setUrl] = useState(initialUrl);
  const [retailer, setRetailer] = useState<'Myntra' | 'AJIO' | 'Manual'>(initialRetailer);
  const [name, setName] = useState('');
  const [brand, setBrand] = useState('');
  const [category, setCategory] = useState('Shirts');
  const [gender, setGender] = useState('Men');
  const [sellingPrice, setSellingPrice] = useState('');
  const [mrp, setMrp] = useState('');
  const [primaryImage, setPrimaryImage] = useState('');
  const [additionalImages, setAdditionalImages] = useState('');
  const [description, setDescription] = useState('');
  const [sizesInput, setSizesInput] = useState('S, M, L, XL');
  const [measurementUnit, setMeasurementUnit] = useState<'cm' | 'in'>('in');
  const [chartRows, setChartRows] = useState<
    Array<{ size: string; chest: string; shoulder: string; waist: string; sleeve_length: string; garment_length: string }>
  >([
    { size: 'S', chest: '38', shoulder: '17', waist: '34', sleeve_length: '24.5', garment_length: '28.5' },
    { size: 'M', chest: '40', shoulder: '17.8', waist: '36', sleeve_length: '25.0', garment_length: '29.5' },
    { size: 'L', chest: '42', shoulder: '18.5', waist: '38', sleeve_length: '25.5', garment_length: '30.5' },
  ]);
  const [formError, setFormError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAddRow = () => {
    setChartRows((prev) => [
      ...prev,
      { size: '', chest: '', shoulder: '', waist: '', sleeve_length: '', garment_length: '' },
    ]);
  };

  const handleRemoveRow = (index: number) => {
    setChartRows((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleRowChange = (index: number, field: string, value: string) => {
    setChartRows((prev) =>
      prev.map((row, idx) => (idx === index ? { ...row, [field]: value } : row))
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!name.trim()) {
      setFormError('Product name is required.');
      return;
    }

    const parsedSelling = sellingPrice.trim() ? Number(sellingPrice) : null;
    const parsedMrp = mrp.trim() ? Number(mrp) : null;

    const imageList = [
      ...(primaryImage.trim() ? [primaryImage.trim()] : []),
      ...additionalImages
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
    ];

    const parsedRows = chartRows
      .filter((r) => r.size.trim())
      .map((r) => ({
        size: r.size.trim(),
        chest: r.chest.trim() ? Number(r.chest) : null,
        shoulder: r.shoulder.trim() ? Number(r.shoulder) : null,
        waist: r.waist.trim() ? Number(r.waist) : null,
        sleeve_length: r.sleeve_length.trim() ? Number(r.sleeve_length) : null,
        garment_length: r.garment_length.trim() ? Number(r.garment_length) : null,
      }));

    await onSubmitManual({
      original_url: url.trim() || 'https://www.myntra.com/manual-entry',
      retailer,
      name: name.trim(),
      brand: brand.trim() || 'Independent Label',
      category: category.trim(),
      gender,
      description: description.trim() || undefined,
      selling_price: parsedSelling,
      mrp: parsedMrp,
      primary_image: imageList[0] || undefined,
      images: imageList,
      available_sizes: sizesInput
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      measurement_unit: measurementUnit,
      size_chart_rows: parsedRows,
    });
  };

  const inputClass =
    'mt-1.5 w-full rounded-lg border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3.5 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--text-primary)] focus:outline-none';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="manual-entry-title"
    >
      <div className="relative flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-page)] text-[var(--text-primary)] shadow-xl">
        <div className="flex items-start justify-between border-b border-[var(--border-subtle)] px-6 py-5">
          <div>
            <p className="text-xs font-medium text-[var(--text-muted)]">FitCheck Fallback Product Entry</p>
            <h2 id="manual-entry-title" className="mt-1 font-serif-display text-2xl font-semibold text-[var(--text-primary)]">
              Manual Garment Specification
            </h2>
            <p className="mt-0.5 text-sm text-[var(--text-secondary)]">
              Enter verified product details when a retailer blocks automated extraction. Leave unknown fields blank.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)] cursor-pointer"
            aria-label="Close manual entry modal"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="overflow-y-auto p-6 space-y-5">
          {formError && (
            <div className="rounded-lg border border-[var(--status-error-border)] bg-[var(--status-error-bg)] px-4 py-3 text-xs font-medium text-[var(--status-error-text)]">
              {formError}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)]">Retailer Source</label>
              <select
                value={retailer}
                onChange={(e) => setRetailer(e.target.value as 'Myntra' | 'AJIO' | 'Manual')}
                className={inputClass}
              >
                <option value="Myntra">Myntra</option>
                <option value="AJIO">AJIO</option>
                <option value="Manual">Manual / Direct</option>
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-[var(--text-secondary)]">Original Product URL</label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.myntra.com/shirts/..."
                className={inputClass}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)]">Brand Name *</label>
              <input
                type="text"
                required
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                placeholder="e.g. Polo Ralph Lauren"
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)]">Product Name *</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Men Navy Tailored Fit Oxford Shirt"
                className={inputClass}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)]">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className={inputClass}
              >
                <option value="Shirts">Shirts</option>
                <option value="Blazers">Blazers &amp; Outerwear</option>
                <option value="Trousers">Trousers &amp; Pants</option>
                <option value="T-Shirts">T-Shirts &amp; Tops</option>
                <option value="Dresses">Dresses</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)]">Gender</label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className={inputClass}
              >
                <option value="Men">Men</option>
                <option value="Women">Women</option>
                <option value="Unisex">Unisex</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)]">Selling Price (INR)</label>
              <input
                type="number"
                min="0"
                value={sellingPrice}
                onChange={(e) => setSellingPrice(e.target.value)}
                placeholder="e.g. 2499"
                className={`${inputClass} font-mono-tabular`}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)]">Original MRP (INR)</label>
              <input
                type="number"
                min="0"
                value={mrp}
                onChange={(e) => setMrp(e.target.value)}
                placeholder="e.g. 3499"
                className={`${inputClass} font-mono-tabular`}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)]">Primary Image URL</label>
              <input
                type="text"
                value={primaryImage}
                onChange={(e) => setPrimaryImage(e.target.value)}
                placeholder="https://... or /src/assets/images/..."
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-secondary)]">Available Sizes (comma-separated)</label>
              <input
                type="text"
                value={sizesInput}
                onChange={(e) => setSizesInput(e.target.value)}
                placeholder="S, M, L, XL"
                className={inputClass}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-[var(--text-secondary)]">Additional Image URLs (comma-separated, optional)</label>
            <input
              type="text"
              value={additionalImages}
              onChange={(e) => setAdditionalImages(e.target.value)}
              placeholder="https://image2.jpg, https://image3.jpg"
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-[var(--text-secondary)]">Product Description</label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Fabric composition, fit details, and styling notes..."
              className={inputClass}
            />
          </div>

          {/* Optional Size Chart Measurements */}
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="text-xs font-semibold text-[var(--text-primary)]">Garment Size Chart Measurements (Optional)</h3>
                <p className="text-xs text-[var(--text-muted)]">Normalized automatically into centimeters for the fit recommendation engine.</p>
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={measurementUnit}
                  onChange={(e) => setMeasurementUnit(e.target.value as 'cm' | 'in')}
                  className="rounded-md border border-[var(--border-strong)] bg-[var(--bg-subtle)] px-2.5 py-1 text-xs font-medium text-[var(--text-primary)]"
                >
                  <option value="in">Input in Inches (in)</option>
                  <option value="cm">Input in Centimeters (cm)</option>
                </select>
                <button
                  type="button"
                  onClick={handleAddRow}
                  className="inline-flex items-center gap-1 rounded-md border border-[var(--border-strong)] bg-[var(--bg-subtle)] px-2.5 py-1 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--bg-hover)] cursor-pointer"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add Size Row
                </button>
              </div>
            </div>

            {chartRows.length > 0 && (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] text-[var(--text-secondary)]">
                      <th className="pb-2 pr-2">Size</th>
                      <th className="pb-2 px-2">Chest</th>
                      <th className="pb-2 px-2">Shoulder</th>
                      <th className="pb-2 px-2">Waist</th>
                      <th className="pb-2 px-2">Sleeve</th>
                      <th className="pb-2 px-2">Length</th>
                      <th className="pb-2 pl-2"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-subtle)]">
                    {chartRows.map((row, idx) => (
                      <tr key={idx}>
                        <td className="py-1.5 pr-2">
                          <input
                            type="text"
                            value={row.size}
                            onChange={(e) => handleRowChange(idx, 'size', e.target.value)}
                            placeholder="M"
                            className="w-14 rounded border border-[var(--border-strong)] bg-[var(--bg-page)] px-2 py-1 font-mono-tabular text-[var(--text-primary)]"
                          />
                        </td>
                        <td className="py-1.5 px-2">
                          <input
                            type="number"
                            step="0.1"
                            value={row.chest}
                            onChange={(e) => handleRowChange(idx, 'chest', e.target.value)}
                            className="w-16 rounded border border-[var(--border-strong)] bg-[var(--bg-page)] px-2 py-1 font-mono-tabular text-[var(--text-primary)]"
                          />
                        </td>
                        <td className="py-1.5 px-2">
                          <input
                            type="number"
                            step="0.1"
                            value={row.shoulder}
                            onChange={(e) => handleRowChange(idx, 'shoulder', e.target.value)}
                            className="w-16 rounded border border-[var(--border-strong)] bg-[var(--bg-page)] px-2 py-1 font-mono-tabular text-[var(--text-primary)]"
                          />
                        </td>
                        <td className="py-1.5 px-2">
                          <input
                            type="number"
                            step="0.1"
                            value={row.waist}
                            onChange={(e) => handleRowChange(idx, 'waist', e.target.value)}
                            className="w-16 rounded border border-[var(--border-strong)] bg-[var(--bg-page)] px-2 py-1 font-mono-tabular text-[var(--text-primary)]"
                          />
                        </td>
                        <td className="py-1.5 px-2">
                          <input
                            type="number"
                            step="0.1"
                            value={row.sleeve_length}
                            onChange={(e) => handleRowChange(idx, 'sleeve_length', e.target.value)}
                            className="w-16 rounded border border-[var(--border-strong)] bg-[var(--bg-page)] px-2 py-1 font-mono-tabular text-[var(--text-primary)]"
                          />
                        </td>
                        <td className="py-1.5 px-2">
                          <input
                            type="number"
                            step="0.1"
                            value={row.garment_length}
                            onChange={(e) => handleRowChange(idx, 'garment_length', e.target.value)}
                            className="w-16 rounded border border-[var(--border-strong)] bg-[var(--bg-page)] px-2 py-1 font-mono-tabular text-[var(--text-primary)]"
                          />
                        </td>
                        <td className="py-1.5 pl-2 text-right">
                          <button
                            type="button"
                            onClick={() => handleRemoveRow(idx)}
                            className="text-[var(--text-muted)] hover:text-[var(--status-error-text)] cursor-pointer"
                            aria-label="Remove size row"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-[var(--border-strong)] bg-[var(--bg-surface)] px-4 py-2.5 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--bg-hover)] cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg bg-[var(--accent-bg)] px-5 py-2.5 text-xs font-medium text-[var(--accent-text)] hover:bg-[var(--accent-hover)] disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting ? 'Saving Product...' : 'Create Product Page'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
