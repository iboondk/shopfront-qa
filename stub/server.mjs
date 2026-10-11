// Stub storefront: server-rendered HTML, Medusa-shaped REST, Saleor-shaped GraphQL,
// and optional latency / flake fault injection. Uses only node:http.
import http from 'node:http';
import { readFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { buildSchema, makeRootValue, executeGraphql } from './graphql.mjs';

const PRODUCTS_PATH = fileURLToPath(new URL('./data/products.json', import.meta.url));
const products = JSON.parse(readFileSync(PRODUCTS_PATH, 'utf8'));

// mulberry32: small seeded PRNG returning floats in [0, 1).
export function mulberry32(seed) {
  let a = seed >>> 0;
  return function rng() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const sleep = (ms) =>
  new Promise((resolve) => {
    const start = performance.now();
    const tick = () => {
      const remaining = ms - (performance.now() - start);
      if (remaining <= 0) return resolve();
      setTimeout(tick, Math.ceil(remaining));
    };
    tick();
  });

const escapeHtml = (value) =>
  String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const formatPrice = (cents) => `$${(cents / 100).toFixed(2)}`;

const PAGE_CSS = `
body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 720px; padding: 0 1rem; color: #111; background: #fff; }
h1 { font-size: 1.75rem; }
ul { list-style: none; padding: 0; }
li { padding: 0.5rem 0; border-bottom: 1px solid #e5e5e5; }
button { font: inherit; padding: 0.5rem 1rem; cursor: pointer; }
a { color: #1a4fb3; }
`;

function htmlPage(title, body) {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>${escapeHtml(title)}</title>
<style>${PAGE_CSS}</style>
</head>
<body>
${body}
</body>
</html>
`;
}

function renderCatalog(list) {
  const items = list
    .map(
      (p) =>
        `<li data-testid="product-card" data-handle="${escapeHtml(p.handle)}"><a data-testid="product-link" href="/products/${escapeHtml(p.handle)}">${escapeHtml(p.title)}</a> <span data-testid="product-price">${formatPrice(p.price_cents)}</span></li>`,
    )
    .join('\n');
  return htmlPage(
    'Shopfront',
    `<h1>Shopfront</h1>\n<ul data-testid="product-list">\n${items}\n</ul>`,
  );
}

function renderProduct(p) {
  return htmlPage(
    p.title,
    `<h1 data-testid="product-title">${escapeHtml(p.title)}</h1>
<p data-testid="product-price">${formatPrice(p.price_cents)}</p>
<p>${escapeHtml(p.description)}</p>
<form method="post" action="/cart/items">
<input type="hidden" name="handle" value="${escapeHtml(p.handle)}">
<button data-testid="add-to-cart" type="submit">Add to cart</button>
</form>`,
  );
}

function renderNotFound(what) {
  return htmlPage(
    'Not found',
    `<h1 data-testid="not-found">Not found</h1>\n<p>${escapeHtml(what)}</p>`,
  );
}

function renderCart(cart) {
  const lines = cart ? cart.lines : [];
  const count = lines.reduce((sum, line) => sum + line.quantity, 0);
  const items = lines
    .map((line) => {
      const p = productByVariant(line.variant_id);
      const title = p ? p.title : line.variant_id;
      return `<li data-testid="cart-line">${escapeHtml(title)} x ${line.quantity} (${formatPrice(line.unit_cents * line.quantity)})</li>`;
    })
    .join('\n');
  return htmlPage(
    'Cart',
    `<h1>Cart</h1>\n<p>Items in cart: <span data-testid="cart-count">${count}</span></p>\n<ul>\n${items}\n</ul>`,
  );
}

const productByVariant = (variantId) => products.find((p) => p.variant_id === variantId);
const productByHandle = (handle) => products.find((p) => p.handle === handle);
const productById = (id) => products.find((p) => p.id === id);

function toStoreProduct(p) {
  return {
    id: p.id,
    handle: p.handle,
    title: p.title,
    description: p.description,
    variants: [
      {
        id: p.variant_id,
        title: 'Default',
        calculated_price: {
          calculated_amount: p.price_cents / 100,
          currency_code: 'usd',
        },
      },
    ],
  };
}

export function createServer({
  port = 3100,
  host = '127.0.0.1',
  latencyMs = 0,
  flakeRate = 0,
  seed = 42,
  publishableKey = 'pk_test_stub',
} = {}) {
  const rng = mulberry32(seed);
  const carts = new Map(); // cart id -> { id, lines: [{ id, variant_id, quantity, unit_cents }] }
  let cartSeq = 0;
  let lineSeq = 0;
  const schema = buildSchema(products);
  const rootValue = makeRootValue(products);

  const newCart = () => {
    cartSeq += 1;
    const cart = { id: `cart_${cartSeq}`, lines: [] };
    carts.set(cart.id, cart);
    return cart;
  };

  const serializeCart = (cart) => {
    const items = cart.lines.map((line) => {
      const unit_price = line.unit_cents / 100;
      return {
        id: line.id,
        variant_id: line.variant_id,
        quantity: line.quantity,
        unit_price,
        total: (line.unit_cents * line.quantity) / 100,
      };
    });
    const totalCents = cart.lines.reduce((sum, line) => sum + line.unit_cents * line.quantity, 0);
    return {
      id: cart.id,
      items,
      total: totalCents / 100,
      currency_code: 'usd',
    };
  };

  const addToCart = (cart, variantId, quantity) => {
    const p = productByVariant(variantId);
    const existing = cart.lines.find((line) => line.variant_id === variantId);
    if (existing) {
      existing.quantity += quantity;
    } else {
      lineSeq += 1;
      cart.lines.push({
        id: `item_${lineSeq}`,
        variant_id: variantId,
        quantity,
        unit_cents: p.price_cents,
      });
    }
  };

  const readBody = (req) =>
    new Promise((resolve, reject) => {
      const chunks = [];
      req.on('data', (chunk) => chunks.push(chunk));
      req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
      req.on('error', reject);
    });

  const sendJson = (res, status, body) => {
    res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify(body));
  };

  const sendHtml = (res, status, html, headers = {}) => {
    res.writeHead(status, { 'content-type': 'text/html; charset=utf-8', ...headers });
    res.end(html);
  };

  const cartIdFromCookie = (req) => {
    const header = req.headers.cookie ?? '';
    for (const part of header.split(';')) {
      const [name, ...rest] = part.trim().split('=');
      if (name === 'cart_id') return rest.join('=');
    }
    return null;
  };

  const requireKey = (req, res) => {
    if (req.headers['x-publishable-api-key'] !== publishableKey) {
      sendJson(res, 400, {
        type: 'not_allowed',
        message: 'Publishable API key required',
      });
      return false;
    }
    return true;
  };

  const parseIntParam = (value, fallback) => {
    if (value === null || value === undefined || value === '') return fallback;
    const n = Number(value);
    return Number.isInteger(n) && n >= 0 ? n : fallback;
  };

  async function handleStore(req, res, url) {
    const method = req.method;
    const path = url.pathname;

    if (!requireKey(req, res)) return;

    if (method === 'GET' && path === '/store/products') {
      const limit = parseIntParam(url.searchParams.get('limit'), 50);
      const offset = parseIntParam(url.searchParams.get('offset'), 0);
      const q = url.searchParams.get('q');
      const needle = q ? q.toLowerCase() : null;
      const matched = needle
        ? products.filter((p) => p.title.toLowerCase().includes(needle))
        : products;
      const page = matched.slice(offset, offset + limit).map(toStoreProduct);
      return sendJson(res, 200, {
        products: page,
        count: matched.length,
        offset,
        limit,
      });
    }

    const productMatch = path.match(/^\/store\/products\/([^/]+)$/);
    if (method === 'GET' && productMatch) {
      const id = decodeURIComponent(productMatch[1]);
      const p = productById(id);
      if (!p) {
        return sendJson(res, 404, {
          type: 'not_found',
          message: `Product with id: ${id} was not found`,
        });
      }
      return sendJson(res, 200, { product: toStoreProduct(p) });
    }

    if (method === 'POST' && path === '/store/carts') {
      const cart = newCart();
      return sendJson(res, 200, { cart: serializeCart(cart) });
    }

    const cartMatch = path.match(/^\/store\/carts\/([^/]+)$/);
    if (method === 'GET' && cartMatch) {
      const cart = carts.get(decodeURIComponent(cartMatch[1]));
      if (!cart) {
        return sendJson(res, 404, {
          type: 'not_found',
          message: `Cart with id: ${cartMatch[1]} was not found`,
        });
      }
      return sendJson(res, 200, { cart: serializeCart(cart) });
    }

    const lineMatch = path.match(/^\/store\/carts\/([^/]+)\/line-items$/);
    if (method === 'POST' && lineMatch) {
      const cart = carts.get(decodeURIComponent(lineMatch[1]));
      if (!cart) {
        return sendJson(res, 404, {
          type: 'not_found',
          message: `Cart with id: ${lineMatch[1]} was not found`,
        });
      }
      let payload;
      try {
        payload = JSON.parse((await readBody(req)) || '{}');
      } catch {
        return sendJson(res, 400, { type: 'invalid_data', message: 'Body must be valid JSON' });
      }
      const { variant_id: variantId, quantity } = payload ?? {};
      if (!Number.isInteger(quantity) || quantity < 1) {
        return sendJson(res, 400, {
          type: 'invalid_data',
          message: 'quantity must be an integer greater than or equal to 1',
        });
      }
      if (!productByVariant(variantId)) {
        return sendJson(res, 400, {
          type: 'invalid_data',
          message: `Variant with id: ${variantId} was not found`,
        });
      }
      addToCart(cart, variantId, quantity);
      return sendJson(res, 200, { cart: serializeCart(cart) });
    }

    return sendJson(res, 404, { type: 'not_found' });
  }

  async function handleRoute(req, res) {
    const url = new URL(req.url ?? '/', 'http://localhost');
    const path = url.pathname;
    const method = req.method;

    if (method === 'GET' && path === '/') {
      return sendHtml(res, 200, renderCatalog(products));
    }

    const pageMatch = path.match(/^\/products\/([^/]+)$/);
    if (method === 'GET' && pageMatch) {
      const p = productByHandle(decodeURIComponent(pageMatch[1]));
      if (!p) return sendHtml(res, 404, renderNotFound('Product not found'));
      return sendHtml(res, 200, renderProduct(p));
    }

    if (method === 'POST' && path === '/cart/items') {
      const form = new URLSearchParams(await readBody(req));
      const handle = form.get('handle') ?? '';
      const p = productByHandle(handle);
      if (!p) return sendHtml(res, 404, renderNotFound('Product not found'));
      let cart = carts.get(cartIdFromCookie(req) ?? '');
      const headers = {};
      if (!cart) {
        cart = newCart();
        headers['set-cookie'] = `cart_id=${cart.id}; Path=/; HttpOnly`;
      }
      addToCart(cart, p.variant_id, 1);
      res.writeHead(303, { location: '/cart', ...headers });
      return res.end();
    }

    if (method === 'GET' && path === '/cart') {
      const cart = carts.get(cartIdFromCookie(req) ?? '');
      return sendHtml(res, 200, renderCart(cart));
    }

    if (path.startsWith('/store/')) {
      return handleStore(req, res, url);
    }

    if (method === 'POST' && path === '/graphql') {
      let body;
      try {
        body = JSON.parse((await readBody(req)) || 'null');
      } catch {
        return sendJson(res, 400, { errors: [{ message: 'Body must be valid JSON' }] });
      }
      const result = await executeGraphql(schema, rootValue, body);
      return sendJson(res, result.status, result.json);
    }

    return sendJson(res, 404, { type: 'not_found' });
  }

  const handler = async (req, res) => {
    try {
      const url = new URL(req.url ?? '/', 'http://localhost');
      if (req.method === 'GET' && url.pathname === '/health') {
        return sendJson(res, 200, { status: 'ok' });
      }
      if (latencyMs > 0) await sleep(latencyMs);
      if (flakeRate > 0 && rng() < flakeRate) {
        return sendJson(res, 503, { type: 'unavailable' });
      }
      await handleRoute(req, res);
    } catch (err) {
      if (!res.headersSent) sendJson(res, 500, { type: 'internal_error', message: String(err?.message ?? err) });
      else res.end();
    }
  };

  const server = http.createServer(handler);

  return {
    server,
    start() {
      return new Promise((resolve, reject) => {
        server.once('error', reject);
        server.listen(port, host, () => {
          server.removeListener('error', reject);
          const addr = server.address();
          resolve({ url: `http://${host}:${addr.port}` });
        });
      });
    },
    stop() {
      return new Promise((resolve) => {
        if (!server.listening) return resolve();
        server.close(() => resolve());
        server.closeAllConnections();
      });
    },
  };
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const port = Number(process.env.PORT ?? 3100);
  const stub = createServer({
    port,
    host: '127.0.0.1',
    latencyMs: Number(process.env.STUB_LATENCY_MS ?? 0),
    flakeRate: Number(process.env.STUB_FLAKE_RATE ?? 0),
    seed: Number(process.env.STUB_SEED ?? 42),
    publishableKey: process.env.PUBLISHABLE_KEY ?? 'pk_test_stub',
  });
  const { url } = await stub.start();
  console.log(`stub listening on ${url}`);
  const shutdown = () => stub.stop().then(() => process.exit(0));
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}
