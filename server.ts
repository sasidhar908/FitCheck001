import { spawn } from 'child_process';
import dotenv from 'dotenv';
import express, { Request, Response, NextFunction } from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { GoogleGenAI, Type } from '@google/genai';
import { createServer as createViteServer } from 'vite';
import type {
  DiagnosticTestBundle,
  ProductResponse,
} from './src/types/product.ts';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = 3000;

const productStore = new Map<string, ProductResponse>();

const rateLimitBuckets = new Map<string, number[]>();
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX_REQUESTS = 30;

function rateLimitMiddleware(req: Request, res: Response, next: NextFunction): void {
  const clientIp = req.ip || req.socket.remoteAddress || 'unknown';
  const now = Date.now();
  const bucket = (rateLimitBuckets.get(clientIp) || []).filter((ts) => now - ts < RATE_LIMIT_WINDOW_MS);
  if (bucket.length >= RATE_LIMIT_MAX_REQUESTS) {
    res.status(429).json({
      code: 'RATE_LIMITED',
      message: 'Too many requests. Please wait a moment before trying again.',
    });
    return;
  }
  bucket.push(now);
  rateLimitBuckets.set(clientIp, bucket);
  next();
}

interface PythonBridgeResult<T = ProductResponse> {
  ok: boolean;
  code?: string;
  message?: string;
  data?: T;
}

/**
 * Invokes the authoritative Python extraction & VTON service (`backend.main`) via child process.
 */
function runPythonExtractor<T = ProductResponse>(
  args: string[],
  stdinText?: string,
  timeoutMs = 20_000,
  autoAppendStdinHtmlFlag = true
): Promise<PythonBridgeResult<T>> {
  return new Promise((resolve) => {
    const finalArgs = ['-m', 'backend.main', ...args];
    if (
      autoAppendStdinHtmlFlag &&
      stdinText !== undefined &&
      stdinText !== null &&
      stdinText.trim().length > 0
    ) {
      finalArgs.push('--stdin-html');
    }

    const child = spawn('python3', finalArgs, {
      cwd: __dirname,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env },
    });

    let stdout = '';
    let stderr = '';
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      resolve({
        ok: false,
        code: 'EXTRACTION_TIMEOUT',
        message: 'Python service timed out while processing the request.',
      });
    }, timeoutMs);

    child.stdout.on('data', (chunk: Buffer) => {
      stdout += chunk.toString('utf-8');
    });

    child.stderr.on('data', (chunk: Buffer) => {
      stderr += chunk.toString('utf-8');
    });

    child.on('error', (err) => {
      clearTimeout(timer);
      resolve({
        ok: false,
        code: 'PYTHON_EXEC_ERROR',
        message: `Failed to invoke Python service: ${err.message}`,
      });
    });

    child.on('close', () => {
      clearTimeout(timer);
      const trimmed = stdout.trim();
      if (!trimmed) {
        resolve({
          ok: false,
          code: 'EMPTY_BRIDGE_OUTPUT',
          message: stderr.trim() || 'Python service returned no output.',
        });
        return;
      }
      try {
        const lastLine = trimmed.split('\n').pop() || trimmed;
        const parsed = JSON.parse(lastLine) as PythonBridgeResult<T>;
        resolve(parsed);
      } catch (err) {
        resolve({
          ok: false,
          code: 'BRIDGE_PARSE_ERROR',
          message: `Failed to parse Python response: ${(err as Error).message}`,
        });
      }
    });

    if (stdinText !== undefined && stdinText !== null && stdinText.trim().length > 0) {
      child.stdin.write(stdinText, 'utf-8');
    }
    child.stdin.end();
  });
}

async function enrichWithGeminiIfNeeded(
  product: ProductResponse,
  accessibleContent?: string
): Promise<ProductResponse> {
  if (!accessibleContent || accessibleContent.trim().length < 50) {
    return product;
  }
  if (!process.env.GEMINI_API_KEY || process.env.GEMINI_API_KEY === 'MY_GEMINI_API_KEY') {
    return product;
  }
  if (product.extraction.status === 'blocked' || product.extraction.status === 'success') {
    return product;
  }

  try {
    const ai = new GoogleGenAI({
      apiKey: process.env.GEMINI_API_KEY,
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        },
      },
    });

    const snippet = accessibleContent.slice(0, 18_000);
    const response = await ai.models.generateContent({
      model: 'gemini-4-hydrogen',
      contents: `Extract only explicitly stated product facts from the following retailer page snippet.
CRITICAL RULES:
- Never invent, guess, or estimate prices, discounts, stock status, sizes, or measurements.
- If a field is not explicitly present in the text, return null or an empty array.

Snippet:
${snippet}`,
      config: {
        responseMimeType: 'application/json',
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            name: { type: Type.STRING, nullable: true },
            brand: { type: Type.STRING, nullable: true },
            description: { type: Type.STRING, nullable: true },
            category: { type: Type.STRING, nullable: true },
            gender: { type: Type.STRING, nullable: true },
            selling_price: { type: Type.NUMBER, nullable: true },
            mrp: { type: Type.NUMBER, nullable: true },
            available_sizes: {
              type: Type.ARRAY,
              items: { type: Type.STRING },
            },
          },
        },
      },
    });

    const rawJson = (response.text ?? '{}').trim();
    const parsed = JSON.parse(rawJson) as {
      name?: string | null;
      brand?: string | null;
      description?: string | null;
      category?: string | null;
      gender?: string | null;
      selling_price?: number | null;
      mrp?: number | null;
    };

    let enrichedAny = false;
    if (!product.name && parsed.name) {
      product.name = parsed.name;
      product.extraction.field_confidence.name = 0.68;
      enrichedAny = true;
    }
    if (!product.brand && parsed.brand) {
      product.brand = parsed.brand;
      product.extraction.field_confidence.brand = 0.68;
      enrichedAny = true;
    }
    if (!product.description && parsed.description) {
      product.description = parsed.description;
      product.extraction.field_confidence.description = 0.68;
      enrichedAny = true;
    }
    if (product.pricing.selling_price === null && typeof parsed.selling_price === 'number' && parsed.selling_price > 0) {
      product.pricing.selling_price = parsed.selling_price;
      product.pricing.mrp = typeof parsed.mrp === 'number' && parsed.mrp >= parsed.selling_price ? parsed.mrp : parsed.selling_price;
      product.extraction.field_confidence.pricing = 0.68;
      enrichedAny = true;
    }

    if (enrichedAny) {
      product.extraction.warnings.push(
        'Supplemented missing fields using Gemini-assisted parsing of accessible page content.'
      );
    }
  } catch (err) {
    product.extraction.warnings.push(`Optional Gemini parsing skipped: ${(err as Error).message}`);
  }

  return product;
}

function mapValidationStatusCode(code?: string): number {
  const clientErrorCodes = new Set([
    'UNSUPPORTED_RETAILER',
    'UNAUTHORIZED_SHOPIFY_STORE',
    'INVALID_SHOPIFY_URL',
    'INVALID_URL',
    'MALFORMED_URL',
    'INVALID_SCHEME',
    'MISSING_HOST',
    'SSRF_BLOCKED',
    'INVALID_MYNTRA_URL',
    'INVALID_AJIO_URL',
    'NOT_A_PRODUCT_PATH',
    'EMPTY_URL',
  ]);
  return code && clientErrorCodes.has(code) ? 400 : 502;
}

async function seedInitialCatalog(): Promise<void> {
  const seedIds = ['24891024', '469482190_sand', '469710338_charcoal'];
  for (const id of seedIds) {
    const res = await runPythonExtractor(['--get-id', id]);
    if (res.ok && res.data) {
      productStore.set(res.data.product_id, res.data);
    }
  }

  const liveShopifyUrl =
    'https://www.taylorstitch.com/products/glacier-shirt-in-topsoil-corded-denim-2610';
  const liveRes = await runPythonExtractor(['--extract-url', liveShopifyUrl]);
  if (liveRes.ok && liveRes.data && liveRes.data.name) {
    productStore.set(liveRes.data.product_id, liveRes.data);
  }
}

async function startServer(): Promise<void> {
  await seedInitialCatalog();

  const app = express();
  app.use(express.json({ limit: '12mb' }));

  // GET /api/products - Retrieve list of extracted products
  app.get('/api/products', (_req: Request, res: Response) => {
    const items = Array.from(productStore.values()).reverse();
    res.json({ products: items });
  });

  // POST /api/products/extract - Extract normalized product data from Shopify, Myntra, or AJIO URL
  app.post('/api/products/extract', rateLimitMiddleware, async (req: Request, res: Response) => {
    const url = typeof req.body?.url === 'string' ? req.body.url.trim() : '';
    const rawHtml =
      typeof req.body?.raw_html === 'string' && req.body.raw_html.trim()
        ? req.body.raw_html
        : undefined;
    const useGeminiAssist = Boolean(req.body?.use_gemini_assist);

    if (!url) {
      res.status(400).json({
        code: 'EMPTY_URL',
        message: 'Please provide a valid Shopify, Myntra, or AJIO product URL.',
      });
      return;
    }

    const result = await runPythonExtractor<ProductResponse>(['--extract-url', url], rawHtml);
    if (!result.ok || !result.data) {
      res.status(mapValidationStatusCode(result.code)).json({
        code: result.code || 'EXTRACTION_ERROR',
        message: result.message || 'Unable to extract product information from the provided URL.',
      });
      return;
    }

    let product = result.data;
    if (useGeminiAssist && rawHtml) {
      product = await enrichWithGeminiIfNeeded(product, rawHtml);
    }

    productStore.set(product.product_id, product);
    res.status(200).json(product);
  });

  // POST /api/products/extract/test - Run diagnostic extraction & return field-by-field verification report
  app.post('/api/products/extract/test', rateLimitMiddleware, async (req: Request, res: Response) => {
    const url = typeof req.body?.url === 'string' ? req.body.url.trim() : '';
    const rawHtml =
      typeof req.body?.raw_html === 'string' && req.body.raw_html.trim()
        ? req.body.raw_html
        : undefined;

    if (!url) {
      res.status(400).json({
        code: 'EMPTY_URL',
        message: 'Please provide a product URL to run the diagnostic extraction test.',
      });
      return;
    }

    const result = await runPythonExtractor<DiagnosticTestBundle>(['--test-url', url], rawHtml);
    if (!result.ok || !result.data) {
      res.status(mapValidationStatusCode(result.code)).json({
        code: result.code || 'DIAGNOSTIC_TEST_ERROR',
        message: result.message || 'Unable to complete diagnostic extraction test.',
      });
      return;
    }

    if (result.data.product) {
      productStore.set(result.data.product.product_id, result.data.product);
    }
    res.status(200).json(result.data);
  });

  // GET /api/products/:product_id - Retrieve a previously extracted product
  app.get('/api/products/:product_id', async (req: Request, res: Response) => {
    const productId = String(req.params.product_id || '').trim();
    const cached = productStore.get(productId);
    if (cached) {
      res.json(cached);
      return;
    }

    const pyResult = await runPythonExtractor<ProductResponse>(['--get-id', productId]);
    if (pyResult.ok && pyResult.data) {
      productStore.set(pyResult.data.product_id, pyResult.data);
      res.json(pyResult.data);
      return;
    }

    res.status(404).json({
      code: 'PRODUCT_NOT_FOUND',
      message: `No extracted product found with ID '${productId}'.`,
    });
  });

  // GET /api/products/:product_id/sizes - Retrieve product size & measurement chart information
  app.get('/api/products/:product_id/sizes', async (req: Request, res: Response) => {
    const productId = String(req.params.product_id || '').trim();
    let product = productStore.get(productId);
    if (!product) {
      const pyResult = await runPythonExtractor<ProductResponse>(['--get-id', productId]);
      if (pyResult.ok && pyResult.data) {
        product = pyResult.data;
        productStore.set(product.product_id, product);
      }
    }

    if (!product) {
      res.status(404).json({
        code: 'PRODUCT_NOT_FOUND',
        message: `No extracted product found with ID '${productId}'.`,
      });
      return;
    }

    res.json({
      product_id: product.product_id,
      name: product.name,
      brand: product.brand,
      retailer: product.retailer,
      garment_type: product.garment_type,
      sizes: product.sizes,
      availability: product.availability,
      try_on_compatibility: product.try_on_compatibility,
    });
  });

  // POST /api/products/manual - Manual product entry fallback when automated access is blocked
  app.post('/api/products/manual', async (req: Request, res: Response) => {
    const body = req.body || {};
    if (!body.name || typeof body.name !== 'string' || !body.name.trim()) {
      res.status(400).json({
        code: 'MISSING_NAME',
        message: 'Product name is required for manual product entry.',
      });
      return;
    }

    const pyResult = await runPythonExtractor<ProductResponse>([
      '--manual-json',
      JSON.stringify(body),
    ]);
    if (!pyResult.ok || !pyResult.data) {
      res.status(400).json({
        code: pyResult.code || 'MANUAL_ENTRY_ERROR',
        message: pyResult.message || 'Failed to normalize manual product entry.',
      });
      return;
    }

    productStore.set(pyResult.data.product_id, pyResult.data);
    res.status(201).json(pyResult.data);
  });


  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(__dirname, 'dist');
    app.use(express.static(distPath));
    app.get('*', (_req: Request, res: Response) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`FitCheck server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
