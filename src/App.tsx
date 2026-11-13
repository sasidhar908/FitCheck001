/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useEffect } from 'react';
import { Sun, Moon } from 'lucide-react';
import { ExtractionHero, detectClientRetailer } from './components/ExtractionHero';
import { ProductView } from './components/ProductView';
import { SizeChartModal } from './components/SizeChartModal';
import { ManualEntryModal } from './components/ManualEntryModal';
import { DiagnosticsModal } from './components/DiagnosticsModal';
import type {
  DiagnosticTestBundle,
  ManualProductInput,
  ProductResponse,
} from './types/product';

type ThemeMode = 'light' | 'dark';

function getInitialTheme(): ThemeMode {
  if (typeof window === 'undefined') return 'light';
  try {
    const saved = window.localStorage.getItem('fitcheck-theme');
    if (saved === 'dark' || saved === 'light') {
      return saved;
    }
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
  } catch {
    // Ignore localStorage access errors
  }
  return 'light';
}

export default function App() {
  const [theme, setTheme] = useState<ThemeMode>(getInitialTheme);
  const [urlInput, setUrlInput] = useState('');
  const [currentProduct, setCurrentProduct] = useState<ProductResponse | null>(null);
  const [selectedSize, setSelectedSize] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<'extractor' | 'product'>('extractor');

  const [isExtracting, setIsExtracting] = useState(false);
  const [isRunningTest, setIsRunningTest] = useState(false);
  const [isSubmittingManual, setIsSubmittingManual] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  const [isSizeChartOpen, setIsSizeChartOpen] = useState(false);
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [isDiagnosticsOpen, setIsDiagnosticsOpen] = useState(false);

  // Sync theme to document root and persist to localStorage
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    try {
      window.localStorage.setItem('fitcheck-theme', theme);
    } catch {
      // Ignore storage errors
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  useEffect(() => {
    if (!currentProduct) {
      setSelectedSize(null);
      return;
    }
    const defaultSize =
      currentProduct.try_on_compatibility?.selected_size ||
      currentProduct.sizes?.available_sizes?.find((s) => s.available !== false)?.normalized_label ||
      currentProduct.sizes?.available_sizes?.[0]?.normalized_label ||
      null;
    setSelectedSize(defaultSize);
  }, [currentProduct]);

  const handleSelectSize = (size: string) => {
    setSelectedSize(size);
    setCurrentProduct((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        try_on_compatibility: {
          ...prev.try_on_compatibility,
          selected_size: size,
        },
      };
    });
  };

  const handleExtractProduct = async (
    targetUrl: string,
    rawHtml?: string,
    useGeminiAssist?: boolean
  ) => {
    const trimmed = targetUrl.trim();
    if (!trimmed) {
      setErrorCode('EMPTY_URL');
      setErrorMessage('Please paste a Shopify, Myntra, or AJIO product URL first.');
      return;
    }

    setIsExtracting(true);
    setErrorMessage(null);
    setErrorCode(null);

    try {
      const response = await fetch('/api/products/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: trimmed,
          raw_html: rawHtml,
          use_gemini_assist: useGeminiAssist,
        }),
      });

      const payload = await response.json();
      if (!response.ok) {
        setErrorCode(payload.code || 'EXTRACTION_ERROR');
        setErrorMessage(
          payload.message || 'Unable to extract product information from this URL.'
        );
        return;
      }

      const extracted = payload as ProductResponse;
      setCurrentProduct(extracted);
      setActiveView('product');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      setErrorCode('NETWORK_ERROR');
      setErrorMessage(
        `Network error while contacting extraction service: ${(err as Error).message}`
      );
    } finally {
      setIsExtracting(false);
    }
  };

  const handleRunDiagnosticTest = async (targetUrl: string) => {
    const trimmed = targetUrl.trim();
    if (!trimmed) return;

    setIsRunningTest(true);
    setErrorMessage(null);
    setErrorCode(null);

    try {
      const response = await fetch('/api/products/extract/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: trimmed }),
      });

      const payload = await response.json();
      if (!response.ok) {
        setErrorCode(payload.code || 'DIAGNOSTIC_TEST_ERROR');
        setErrorMessage(payload.message || 'Diagnostic test failed.');
        return;
      }

      const bundle = payload as DiagnosticTestBundle;
      if (bundle.product) {
        setCurrentProduct(bundle.product);
      }
    } finally {
      setIsRunningTest(false);
    }
  };

  const handleCreateManualProduct = async (manualInput: ManualProductInput) => {
    setIsSubmittingManual(true);
    try {
      const response = await fetch('/api/products/manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(manualInput),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.message || 'Failed to save manual product.');
      }

      const created = payload as ProductResponse;
      setCurrentProduct(created);
      setIsManualModalOpen(false);
      setErrorMessage(null);
      setErrorCode(null);
      setActiveView('product');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } finally {
      setIsSubmittingManual(false);
    }
  };

  const detectedRetailer = detectClientRetailer(urlInput).retailer;
  const detectedRetailerForManual: 'Myntra' | 'AJIO' | 'Manual' =
    detectedRetailer === 'Myntra' || detectedRetailer === 'AJIO'
      ? detectedRetailer
      : 'Manual';

  return (
    <div className="min-h-screen flex flex-col overflow-x-hidden bg-[var(--bg-page)] text-[var(--text-primary)] transition-colors duration-150">
      {/* Top Navbar */}
      <header className="sticky top-0 z-30 flex items-center justify-between gap-4 sm:gap-8 border-b border-[var(--border-subtle)] bg-[var(--bg-page)]/95 px-4 sm:px-6 py-4 backdrop-blur-xs">
        {/* Left: FitCheck wordmark */}
        <button
          type="button"
          onClick={() => setActiveView('extractor')}
          className="font-serif-display text-2xl font-semibold tracking-tight text-[var(--text-primary)] whitespace-nowrap shrink-0 cursor-pointer"
        >
          FitCheck
        </button>

        {/* Center: URL Extractor, Product View, Size Chart */}
        <nav
          aria-label="Main Navigation"
          className="flex items-center gap-4 sm:gap-8 text-xs sm:text-sm font-medium text-[var(--text-secondary)]"
        >
          <button
            type="button"
            onClick={() => setActiveView('extractor')}
            className={`transition-colors hover:text-[var(--text-primary)] whitespace-nowrap shrink-0 cursor-pointer ${
              activeView === 'extractor'
                ? 'text-[var(--text-primary)] font-semibold underline underline-offset-4'
                : ''
            }`}
          >
            URL Extractor
          </button>
          <button
            type="button"
            onClick={() => setActiveView('product')}
            className={`transition-colors hover:text-[var(--text-primary)] whitespace-nowrap shrink-0 cursor-pointer ${
              activeView === 'product'
                ? 'text-[var(--text-primary)] font-semibold underline underline-offset-4'
                : ''
            }`}
          >
            Product View
          </button>
          <button
            type="button"
            onClick={() => setIsSizeChartOpen(true)}
            className={`transition-colors hover:text-[var(--text-primary)] whitespace-nowrap shrink-0 cursor-pointer ${
              isSizeChartOpen
                ? 'text-[var(--text-primary)] font-semibold underline underline-offset-4'
                : ''
            }`}
          >
            Size Chart
          </button>
        </nav>

        {/* Right: Theme Toggle (Sun/Moon) + New Extraction Button */}
        <div className="flex items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--bg-surface)] px-3 text-xs font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)] cursor-pointer"
          >
            {theme === 'dark' ? (
              <>
                <Sun className="h-4 w-4 text-amber-400" />
                <span className="hidden sm:inline">Light</span>
              </>
            ) : (
              <>
                <Moon className="h-4 w-4 text-[var(--text-primary)]" />
                <span className="hidden sm:inline">Dark</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveView('extractor');
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            className="rounded-lg bg-[var(--accent-bg)] px-4 py-2 text-xs font-medium text-[var(--accent-text)] transition-colors hover:bg-[var(--accent-hover)] whitespace-nowrap shrink-0 cursor-pointer"
          >
            New Extraction
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1">
        {activeView === 'extractor' ? (
          <ExtractionHero
            urlInput={urlInput}
            onUrlChange={(val) => {
              setUrlInput(val);
              if (errorMessage) {
                setErrorMessage(null);
                setErrorCode(null);
              }
            }}
            onSubmitExtract={handleExtractProduct}
            onOpenDiagnostics={() => setIsDiagnosticsOpen(true)}
            isExtracting={isExtracting}
            errorMessage={errorMessage}
            errorCode={errorCode}
            onOpenManualEntry={() => setIsManualModalOpen(true)}
          />
        ) : (
          <ProductView
            product={currentProduct}
            selectedSize={selectedSize}
            onSelectSize={handleSelectSize}
            onOpenSizeChart={() => setIsSizeChartOpen(true)}
            onOpenDiagnostics={() => setIsDiagnosticsOpen(true)}
            onOpenManualFallback={() => setIsManualModalOpen(true)}
            onBackToCatalog={() => setActiveView('extractor')}
          />
        )}
      </main>

      {/* Editorial Footer */}
      <footer className="border-t border-[var(--border-subtle)] bg-[var(--bg-page)] px-6 py-8">
        <div className="mx-auto flex max-w-[1280px] flex-col items-start justify-between gap-4 text-xs text-[var(--text-muted)] sm:flex-row sm:items-center">
          <p>
            FitCheck — Product Extraction &amp; Size Recommendation System (Shopify Storefront + Crawl4AI + Myntra &amp; AJIO)
          </p>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => setIsDiagnosticsOpen(true)}
              className="hover:text-[var(--text-primary)] underline-offset-4 hover:underline cursor-pointer"
            >
              Extraction Diagnostics
            </button>
            <span aria-hidden="true">·</span>
            <button
              type="button"
              onClick={() => setIsManualModalOpen(true)}
              className="hover:text-[var(--text-primary)] underline-offset-4 hover:underline cursor-pointer"
            >
              Manual Fallback
            </button>
          </div>
        </div>
      </footer>

      {/* Responsive Size Chart Modal */}
      <SizeChartModal
        isOpen={isSizeChartOpen}
        onClose={() => setIsSizeChartOpen(false)}
        productName={currentProduct?.name || null}
        brand={currentProduct?.brand || null}
        garmentType={currentProduct?.garment_type || 'shirt'}
        selectedSize={selectedSize}
        onSelectSize={handleSelectSize}
        sizeChart={currentProduct?.sizes?.size_chart || null}
      />

      {/* Developer Diagnostics & 11-Point Verification Report Modal */}
      <DiagnosticsModal
        isOpen={isDiagnosticsOpen}
        onClose={() => setIsDiagnosticsOpen(false)}
        product={currentProduct}
        onRunDiagnosticTest={handleRunDiagnosticTest}
        isRunningTest={isRunningTest}
      />

      {/* Manual Product Entry Fallback Modal */}
      <ManualEntryModal
        isOpen={isManualModalOpen}
        onClose={() => setIsManualModalOpen(false)}
        initialUrl={urlInput}
        initialRetailer={detectedRetailerForManual}
        onSubmitManual={handleCreateManualProduct}
        isSubmitting={isSubmittingManual}
      />
    </div>
  );
}
