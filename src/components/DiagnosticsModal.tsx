import React, { useState } from 'react';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Play,
  Loader2,
  Server,
  ShieldCheck,
  Clock,
} from 'lucide-react';
import type {
  ExtractionDiagnostics,
  ProductResponse,
  ProductVerificationReport,
} from '../types/product';

interface DiagnosticsModalProps {
  isOpen: boolean;
  onClose: () => void;
  product: ProductResponse | null;
  onRunDiagnosticTest: (url: string) => Promise<void>;
  isRunningTest: boolean;
}

const LIVE_SHOPIFY_TEST_TARGETS = [
  {
    label: 'Taylor Stitch — The Glacier Shirt (11/11 Fields + Size Chart)',
    url: 'https://www.taylorstitch.com/products/glacier-shirt-in-topsoil-corded-denim-2610',
  },
  {
    label: 'Taylor Stitch — The Forest Cargo Pant (Bottoms Size Chart)',
    url: 'https://www.taylorstitch.com/products/forest-cargo-pant-in-coal-broken-twill-2610',
  },
  {
    label: 'Allbirds — Men’s Tree Runner (10/11 PARTIAL — No Garment Size Chart)',
    url: 'https://www.allbirds.com/products/mens-tree-runners',
  },
];

export const DiagnosticsModal: React.FC<DiagnosticsModalProps> = ({
  isOpen,
  onClose,
  product,
  onRunDiagnosticTest,
  isRunningTest,
}) => {
  const [testUrlInput, setTestUrlInput] = useState(
    product?.original_url || LIVE_SHOPIFY_TEST_TARGETS[0].url
  );

  if (!isOpen) return null;

  const diag: ExtractionDiagnostics | null = product?.diagnostics || null;
  const report: ProductVerificationReport | null = product?.verification_report || null;

  const outcome = diag?.outcome_classification || 'FAILED';

  const getOutcomeStyle = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return {
          bg: 'bg-[var(--status-success-bg)]',
          border: 'border-[var(--status-success-border)]',
          text: 'text-[var(--status-success-text)]',
          label: 'SUCCESS — All Required Fields Verified',
        };
      case 'PARTIAL':
        return {
          bg: 'bg-[var(--status-warning-bg)]',
          border: 'border-[var(--status-warning-border)]',
          text: 'text-[var(--status-warning-text)]',
          label: 'PARTIAL — Core Product Extracted; Some Fields Unavailable from Source',
        };
      case 'BLOCKED':
        return {
          bg: 'bg-[var(--status-error-bg)]',
          border: 'border-[var(--status-error-border)]',
          text: 'text-[var(--status-error-text)]',
          label: 'BLOCKED — Source Restricted Automated Access',
        };
      default:
        return {
          bg: 'bg-[var(--status-error-bg)]',
          border: 'border-[var(--status-error-border)]',
          text: 'text-[var(--status-error-text)]',
          label: 'FAILED — Technical or Validation Failure',
        };
    }
  };

  const outcomeStyle = getOutcomeStyle(outcome);

  const formatCrawl4AIStatus = (status?: string) => {
    if (status === 'connected_cloud_run') {
      return 'Connected (Remote Google Cloud Run Container)';
    }
    if (status === 'connected_local_sdk') {
      return 'Connected (Local Crawl4AI Python SDK)';
    }
    if (status === 'standby_cloud_run_not_configured') {
      return 'Standby (Executing Crawl4AI CSS/XPath/JSON-LD Schemas Locally; Set CRAWL4AI_BASE_URL for Cloud Run Container)';
    }
    if (status === 'unreachable') {
      return 'Unreachable (Remote Crawl4AI Container Error)';
    }
    return status || 'Not Invoked';
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="diagnostics-modal-title"
    >
      <div className="relative flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-page)] text-[var(--text-primary)] shadow-xl">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-[var(--border-subtle)] px-6 py-5">
          <div>
            <p className="text-xs font-medium text-[var(--text-muted)]">
              FitCheck Developer Diagnostics &amp; Real Product Verification (`POST /api/products/extract/test`)
            </p>
            <h2
              id="diagnostics-modal-title"
              className="mt-1 font-serif-display text-2xl font-semibold text-[var(--text-primary)]"
            >
              Crawl4AI &amp; Storefront Extraction Telemetry
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 items-center justify-center rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)] cursor-pointer"
            aria-label="Close diagnostics panel"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto p-6 space-y-6">
          {/* Live Real Product Verification Runner */}
          <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
              Run Live Diagnostic Extraction Test
            </p>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              Test an actual authorized Shopify product URL end-to-end and generate a field-by-field verification report.
            </p>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (testUrlInput.trim()) {
                  onRunDiagnosticTest(testUrlInput.trim());
                }
              }}
              className="mt-3 flex flex-col gap-2.5 sm:flex-row"
            >
              <input
                type="url"
                value={testUrlInput}
                onChange={(e) => setTestUrlInput(e.target.value)}
                placeholder="https://www.taylorstitch.com/products/glacier-shirt-in-topsoil-corded-denim-2610"
                className="flex-1 rounded-lg border border-[var(--border-strong)] bg-[var(--bg-page)] px-3.5 py-2 font-mono-tabular text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--text-primary)] focus:outline-none"
              />
              <button
                type="submit"
                disabled={isRunningTest || !testUrlInput.trim()}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-[var(--accent-bg)] px-4 py-2 text-xs font-medium text-[var(--accent-text)] hover:bg-[var(--accent-hover)] disabled:opacity-50 whitespace-nowrap shrink-0 cursor-pointer"
              >
                {isRunningTest ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Running Diagnostic...
                  </>
                ) : (
                  <>
                    <Play className="h-3.5 w-3.5" />
                    Run Diagnostic Test
                  </>
                )}
              </button>
            </form>

            <div className="mt-3 flex flex-wrap gap-2">
              {LIVE_SHOPIFY_TEST_TARGETS.map((target) => (
                <button
                  key={target.url}
                  type="button"
                  disabled={isRunningTest}
                  onClick={() => {
                    setTestUrlInput(target.url);
                    onRunDiagnosticTest(target.url);
                  }}
                  className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-2.5 py-1 text-[11px] font-medium text-[var(--text-secondary)] hover:border-[var(--text-primary)] hover:text-[var(--text-primary)] disabled:opacity-50 cursor-pointer"
                >
                  {target.label}
                </button>
              ))}
            </div>
          </div>

          {diag && (
            <>
              {/* Outcome Banner */}
              <div className={`rounded-xl border ${outcomeStyle.border} ${outcomeStyle.bg} p-4`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {outcome === 'SUCCESS' ? (
                      <CheckCircle2 className={`h-4 w-4 ${outcomeStyle.text}`} />
                    ) : outcome === 'PARTIAL' ? (
                      <AlertTriangle className={`h-4 w-4 ${outcomeStyle.text}`} />
                    ) : (
                      <XCircle className={`h-4 w-4 ${outcomeStyle.text}`} />
                    )}
                    <span className={`text-xs font-semibold ${outcomeStyle.text}`}>
                      {outcomeStyle.label}
                    </span>
                  </div>
                  <span className="font-mono-tabular text-xs font-medium text-[var(--text-primary)]">
                    Verified Fields: {diag.extracted_field_count} / {diag.total_expected_fields} · Duration: {diag.extraction_duration_ms} ms
                  </span>
                </div>
                {diag.error_details && (
                  <p className={`mt-2 text-xs ${outcomeStyle.text}`}>
                    Error Details: {diag.error_details}
                  </p>
                )}
              </div>

              {/* Extraction Pipeline Diagnostics */}
              <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                  Extraction Pipeline Diagnostics
                </h3>

                <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-3 text-xs sm:grid-cols-2">
                  <div className="border-b border-[var(--border-subtle)] pb-2 sm:col-span-2">
                    <dt className="text-[var(--text-muted)]">Submitted URL</dt>
                    <dd className="mt-0.5 break-all font-mono-tabular font-medium text-[var(--text-primary)]">
                      {diag.submitted_url}
                    </dd>
                  </div>

                  <div className="border-b border-[var(--border-subtle)] pb-2">
                    <dt className="text-[var(--text-muted)]">Detected Retailer &amp; Domain</dt>
                    <dd className="mt-0.5 font-medium text-[var(--text-primary)]">
                      {diag.detected_retailer} {diag.store_domain ? `(${diag.store_domain})` : ''}
                    </dd>
                  </div>

                  <div className="border-b border-[var(--border-subtle)] pb-2">
                    <dt className="text-[var(--text-muted)]">Product Handle / ID</dt>
                    <dd className="mt-0.5 font-mono-tabular font-medium text-[var(--text-primary)]">
                      {diag.product_handle || product?.product_id || 'N/A'}
                    </dd>
                  </div>

                  <div className="border-b border-[var(--border-subtle)] pb-2">
                    <dt className="text-[var(--text-muted)]">Authorized Data Source</dt>
                    <dd className="mt-0.5 font-medium text-[var(--text-primary)]">
                      {diag.authorized_data_source}
                    </dd>
                  </div>

                  <div className="border-b border-[var(--border-subtle)] pb-2">
                    <dt className="text-[var(--text-muted)]">Extraction Method</dt>
                    <dd className="mt-0.5 font-medium text-[var(--text-primary)]">
                      {diag.extraction_method}
                    </dd>
                  </div>

                  <div className="border-b border-[var(--border-subtle)] pb-2 sm:col-span-2">
                    <dt className="flex items-center gap-1.5 text-[var(--text-muted)]">
                      <Server className="h-3.5 w-3.5 text-[var(--text-primary)]" />
                      Crawl4AI Connection Status
                    </dt>
                    <dd className="mt-0.5 font-mono-tabular font-medium text-[var(--text-primary)]">
                      {formatCrawl4AIStatus(diag.crawl4ai_connection_status)}
                      {diag.crawl4ai_endpoint ? ` · Endpoint: ${diag.crawl4ai_endpoint}` : ''}
                    </dd>
                  </div>

                  <div className="border-b border-[var(--border-subtle)] pb-2">
                    <dt className="text-[var(--text-muted)]">HTTP Response Status</dt>
                    <dd className="mt-0.5 font-mono-tabular font-medium text-[var(--text-primary)]">
                      {diag.http_response_status ?? 'N/A'}
                    </dd>
                  </div>

                  <div className="border-b border-[var(--border-subtle)] pb-2">
                    <dt className="text-[var(--text-muted)]">Browser Rendering Status</dt>
                    <dd className="mt-0.5 font-mono-tabular font-medium text-[var(--text-primary)]">
                      {diag.browser_rendering_status}
                    </dd>
                  </div>

                  <div className="border-b border-[var(--border-subtle)] pb-2">
                    <dt className="text-[var(--text-muted)]">Extracted Image Count</dt>
                    <dd className="mt-0.5 font-mono-tabular font-medium text-[var(--text-primary)]">
                      {diag.extracted_image_count} images
                    </dd>
                  </div>

                  <div className="border-b border-[var(--border-subtle)] pb-2">
                    <dt className="flex items-center gap-1 text-[var(--text-muted)]">
                      <Clock className="h-3.5 w-3.5" />
                      Extraction Duration
                    </dt>
                    <dd className="mt-0.5 font-mono-tabular font-medium text-[var(--text-primary)]">
                      {diag.extraction_duration_ms} ms
                    </dd>
                  </div>

                  <div className="sm:col-span-2">
                    <dt className="text-[var(--text-muted)]">Missing Fields</dt>
                    <dd className="mt-0.5 font-mono-tabular text-[var(--text-primary)]">
                      {diag.missing_fields && diag.missing_fields.length > 0
                        ? diag.missing_fields.join(', ')
                        : 'None (0 missing fields)'}
                    </dd>
                  </div>
                </dl>
              </div>
            </>
          )}

          {/* Field-by-Field Verification Report */}
          {report && (
            <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-primary)]">
                    11-Point Field-by-Field Verification Report
                  </h3>
                  <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                    Unfabricated verification of extracted fields against source availability.
                  </p>
                </div>
                <span className="font-mono-tabular text-xs font-semibold text-[var(--text-primary)]">
                  {report.verified_field_count} / {report.total_fields_checked} Verified
                </span>
              </div>

              <div className="overflow-x-auto rounded-lg border border-[var(--border-subtle)]">
                <table className="w-full border-collapse text-left text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-subtle)] text-[var(--text-secondary)]">
                      <th className="px-3.5 py-2.5">Field</th>
                      <th className="px-3.5 py-2.5">Status</th>
                      <th className="px-3.5 py-2.5">Extracted Value Summary</th>
                      <th className="px-3.5 py-2.5">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-subtle)]">
                    {report.fields.map((f) => (
                      <tr key={f.field_key} className="hover:bg-[var(--bg-subtle)]">
                        <td className="px-3.5 py-2.5 font-medium text-[var(--text-primary)] whitespace-nowrap">
                          {f.field_label}
                        </td>
                        <td className="px-3.5 py-2.5 whitespace-nowrap">
                          {f.extracted ? (
                            <span className="inline-flex items-center gap-1 font-mono-tabular font-semibold text-[var(--status-success-text)]">
                              <CheckCircle2 className="h-3.5 w-3.5" />
                              EXTRACTED
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 font-mono-tabular font-semibold text-[var(--status-warning-text)]">
                              <AlertTriangle className="h-3.5 w-3.5" />
                              UNAVAILABLE
                            </span>
                          )}
                        </td>
                        <td className="px-3.5 py-2.5 font-mono-tabular text-[var(--text-primary)] max-w-xs truncate">
                          {f.value_summary || 'null'}
                        </td>
                        <td className="px-3.5 py-2.5 text-[var(--text-secondary)]">{f.notes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Cloud Run Deployment Reference */}
          <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-4 text-xs text-[var(--text-secondary)]">
            <div className="flex items-center gap-2 font-semibold text-[var(--text-primary)]">
              <ShieldCheck className="h-4 w-4" />
              <span>Independent Crawl4AI Cloud Run Deployment Configuration Ready</span>
            </div>
            <p className="mt-1 leading-relaxed">
              The official <code className="font-mono-tabular">unclecode/crawl4ai:latest</code> Docker configuration is prepared in{' '}
              <code className="font-mono-tabular">deploy/crawl4ai/Dockerfile</code>,{' '}
              <code className="font-mono-tabular">deploy/crawl4ai/config.yml</code>, and{' '}
              <code className="font-mono-tabular">deploy/crawl4ai/cloudbuild.yaml</code>. Once deployed to Google Cloud Run, set{' '}
              <code className="font-mono-tabular">CRAWL4AI_BASE_URL</code> and{' '}
              <code className="font-mono-tabular">CRAWL4AI_API_TOKEN</code> in AI Studio Secrets to connect remote browser rendering.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end border-t border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg bg-[var(--accent-bg)] px-5 py-2 text-xs font-medium text-[var(--accent-text)] hover:bg-[var(--accent-hover)] cursor-pointer"
          >
            Close Diagnostics
          </button>
        </div>
      </div>
    </div>
  );
};
