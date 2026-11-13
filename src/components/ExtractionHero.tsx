import React, { useState } from 'react';
import {
  Search,
  ArrowRight,
  AlertCircle,
  Code2,
  PenLine,
  Loader2,
  CheckCircle2,
  Activity,
} from 'lucide-react';

interface ExtractionHeroProps {
  urlInput: string;
  onUrlChange: (val: string) => void;
  onSubmitExtract: (url: string, rawHtml?: string, useGeminiAssist?: boolean) => Promise<void>;
  onOpenDiagnostics: () => void;
  isExtracting: boolean;
  errorMessage: string | null;
  errorCode: string | null;
  onOpenManualEntry: () => void;
}

const AUTHORIZED_SHOPIFY_HOSTS = [
  'taylorstitch.com',
  'www.taylorstitch.com',
  'allbirds.com',
  'www.allbirds.com',
  'kotn.com',
  'www.kotn.com',
  'gymshark.com',
  'www.gymshark.com',
];

export function detectClientRetailer(rawUrl: string): {
  status: 'idle' | 'valid' | 'unsupported' | 'invalid';
  retailer: 'Shopify' | 'Myntra' | 'AJIO' | null;
  message: string;
} {
  const trimmed = rawUrl.trim();
  if (!trimmed) {
    return {
      status: 'idle',
      retailer: null,
      message: 'Supports authorized Shopify stores (/products/<handle>), Myntra, and AJIO product URLs',
    };
  }

  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    return {
      status: 'invalid',
      retailer: null,
      message: 'Enter a complete URL starting with https://',
    };
  }

  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return {
      status: 'invalid',
      retailer: null,
      message: 'Only http:// and https:// URLs are permitted',
    };
  }

  const host = parsed.hostname.toLowerCase();
  const path = parsed.pathname || '';

  if (
    AUTHORIZED_SHOPIFY_HOSTS.includes(host) ||
    host.endsWith('.myshopify.com')
  ) {
    const handleMatch = path.match(/\/products\/([a-zA-Z0-9_-]+)/i);
    if (!handleMatch) {
      return {
        status: 'invalid',
        retailer: 'Shopify',
        message: `Shopify store "${host}" detected · Provide a /products/<handle> URL`,
      };
    }
    return {
      status: 'valid',
      retailer: 'Shopify',
      message: `Authorized Shopify store (${host}) · Handle: "${handleMatch[1]}" · Uses Storefront API + Crawl4AI`,
    };
  }

  if (host === 'myntra.com' || host.endsWith('.myntra.com')) {
    return {
      status: 'valid',
      retailer: 'Myntra',
      message: 'Myntra adapter detected · Uses embedded pdpData + JSON-LD pipeline',
    };
  }
  if (host === 'ajio.com' || host.endsWith('.ajio.com')) {
    return {
      status: 'valid',
      retailer: 'AJIO',
      message: 'AJIO adapter detected · Uses __PRELOADED_STATE__ + JSON-LD pipeline',
    };
  }

  if (/\/products\/[a-zA-Z0-9_-]+/i.test(path)) {
    return {
      status: 'unsupported',
      retailer: null,
      message: `Shopify store "${host}" is not in the authorized store list (taylorstitch.com, allbirds.com, kotn.com, gymshark.com).`,
    };
  }

  return {
    status: 'unsupported',
    retailer: null,
    message: `Unsupported domain "${host}". Only authorized Shopify stores, Myntra, and AJIO are accepted.`,
  };
}

export const ExtractionHero: React.FC<ExtractionHeroProps> = ({
  urlInput,
  onUrlChange,
  onSubmitExtract,
  onOpenDiagnostics,
  isExtracting,
  errorMessage,
  errorCode,
  onOpenManualEntry,
}) => {
  const [showAdvancedPaste, setShowAdvancedPaste] = useState(false);
  const [rawHtmlSnippet, setRawHtmlSnippet] = useState('');
  const [useGeminiAssist, setUseGeminiAssist] = useState(false);

  const detection = detectClientRetailer(urlInput);

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmitExtract(
      urlInput,
      rawHtmlSnippet.trim() ? rawHtmlSnippet : undefined,
      useGeminiAssist
    );
  };

  return (
    <div className="py-12 md:py-20">
      <section className="mx-auto max-w-4xl px-6 text-center">
        <p className="text-xs font-medium tracking-wider uppercase text-[var(--text-muted)]">
          FitCheck · Shopify Storefront + Crawl4AI + Myntra &amp; AJIO Extraction Engine
        </p>

        <h1
          className="mt-3 font-serif-display text-4xl font-semibold tracking-tight text-[var(--text-primary)] sm:text-5xl md:text-6xl"
          style={{ textWrap: 'balance' }}
        >
          See how it fits before you buy.
        </h1>

        <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-[var(--text-secondary)]">
          Paste an authorized Shopify, Myntra, or AJIO product URL to extract verified garment imagery,
          live variant pricing, stock availability, and normalized centimeter size charts.
        </p>

        {/* URL Extraction Form */}
        <form onSubmit={handleFormSubmit} className="mt-8 text-left">
          <div className="flex flex-col gap-3 rounded-xl border border-[var(--border-strong)] bg-[var(--bg-surface)] p-2.5 shadow-xs sm:flex-row sm:items-center">
            <div className="flex flex-1 items-center gap-3 px-3 py-1.5">
              <Search className="h-4 w-4 shrink-0 text-[var(--text-muted)]" />
              <input
                type="text"
                value={urlInput}
                onChange={(e) => onUrlChange(e.target.value)}
                placeholder="Paste a Shopify, Myntra, or AJIO product URL..."
                className="w-full bg-transparent text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none"
                aria-label="Product URL"
              />
            </div>

            <button
              type="submit"
              disabled={isExtracting || !urlInput.trim()}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-[var(--accent-bg)] px-6 py-3 text-xs font-semibold text-[var(--accent-text)] transition-colors hover:bg-[var(--accent-hover)] disabled:opacity-50 whitespace-nowrap shrink-0 cursor-pointer"
            >
              {isExtracting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Extracting Product...
                </>
              ) : (
                <>
                  Extract Product
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </div>

          {/* Minimal Supporting Instructions & Retailer Detection Status Line */}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 px-1 text-xs">
            <div className="flex items-center gap-2">
              {detection.status === 'valid' && (
                <span className="inline-flex items-center gap-1.5 font-medium text-[var(--status-success-text)]">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  {detection.message}
                </span>
              )}
              {detection.status === 'unsupported' && (
                <span className="inline-flex items-center gap-1.5 font-medium text-[var(--status-error-text)]">
                  <AlertCircle className="h-3.5 w-3.5" />
                  {detection.message}
                </span>
              )}
              {detection.status === 'invalid' && (
                <span className="inline-flex items-center gap-1.5 text-[var(--status-warning-text)]">
                  <AlertCircle className="h-3.5 w-3.5" />
                  {detection.message}
                </span>
              )}
              {detection.status === 'idle' && (
                <span className="text-[var(--text-muted)]">{detection.message}</span>
              )}
            </div>

            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={onOpenDiagnostics}
                className="inline-flex items-center gap-1 text-[var(--text-secondary)] underline underline-offset-4 hover:text-[var(--text-primary)] whitespace-nowrap shrink-0 cursor-pointer"
              >
                <Activity className="h-3.5 w-3.5" />
                Diagnostics &amp; Live Test
              </button>
              <button
                type="button"
                onClick={() => setShowAdvancedPaste((prev) => !prev)}
                className="inline-flex items-center gap-1 text-[var(--text-secondary)] underline underline-offset-4 hover:text-[var(--text-primary)] whitespace-nowrap shrink-0 cursor-pointer"
              >
                <Code2 className="h-3.5 w-3.5" />
                {showAdvancedPaste ? 'Hide HTML Source Input' : 'Paste Page HTML'}
              </button>
              <button
                type="button"
                onClick={onOpenManualEntry}
                className="inline-flex items-center gap-1 text-[var(--text-secondary)] underline underline-offset-4 hover:text-[var(--text-primary)] whitespace-nowrap shrink-0 cursor-pointer"
              >
                <PenLine className="h-3.5 w-3.5" />
                Manual Entry
              </button>
            </div>
          </div>

          {/* Optional HTML/JSON Paste Drawer */}
          {showAdvancedPaste && (
            <div className="mt-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <label className="text-xs font-semibold text-[var(--text-primary)]">
                  Optional Page HTML or JSON-LD Source Override
                </label>
                <label className="inline-flex items-center gap-2 text-xs text-[var(--text-secondary)] cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useGeminiAssist}
                    onChange={(e) => setUseGeminiAssist(e.target.checked)}
                    className="rounded border-[var(--border-strong)]"
                  />
                  Enable optional Gemini-assisted fallback if deterministic selectors are incomplete
                </label>
              </div>
              <p className="mt-1 text-xs text-[var(--text-muted)]">
                Paste HTML source here to run the deterministic Crawl4AI CSS/XPath/JSON-LD and size chart extractors directly.
              </p>
              <textarea
                rows={4}
                value={rawHtmlSnippet}
                onChange={(e) => setRawHtmlSnippet(e.target.value)}
                placeholder="Paste page HTML, JSON-LD, or <dialog class='dialog--size-guide'>..."
                className="mt-2.5 w-full rounded-lg border border-[var(--border-strong)] bg-[var(--bg-page)] p-3 font-mono-tabular text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:border-[var(--text-primary)] focus:outline-none"
              />
            </div>
          )}
        </form>

        {/* Error Banner */}
        {errorMessage && (
          <div className="mt-5 rounded-xl border border-[var(--status-error-border)] bg-[var(--status-error-bg)] p-4 text-left">
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--status-error-text)]" />
              <div className="flex-1">
                <p className="text-xs font-semibold text-[var(--status-error-text)]">
                  Extraction Notice {errorCode ? `(${errorCode})` : ''}
                </p>
                <p className="mt-1 text-xs text-[var(--text-primary)]">{errorMessage}</p>
                <div className="mt-3 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={onOpenManualEntry}
                    className="rounded-md bg-[var(--accent-bg)] px-3 py-1.5 text-xs font-medium text-[var(--accent-text)] hover:bg-[var(--accent-hover)] cursor-pointer"
                  >
                    Switch to Manual Product Entry
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowAdvancedPaste(true)}
                    className="rounded-md border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--bg-hover)] cursor-pointer"
                  >
                    Paste Page HTML Source
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
};
