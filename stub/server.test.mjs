import { test, before, after, describe } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from './server.mjs';

const KEY = 'pk_test_stub';

async function startStub(opts = {}) {
  const stub = createServer({ port: 0, ...opts });
  await stub.start();
  const { port } = stub.server.address();
  return { stub, base: `http://127.0.0.1:${port}` };
}

const api = (base, path, init = {}) =>
  fetch(`${base}${path}`, {
    ...init,
    headers: { 'x-publishable-api-key': KEY, ...(init.headers ?? {}) },
  });

const json = (base, path, init) => api(base, path, init).then((r) => r.json());

describe('stub storefront', () => {
  let stub;
  let base;

  before(async () => {
    ({ stub, base } = await startStub());
  });

  after(async () => {
    await stub.stop();
  });

  test('health returns ok', async () => {
    const res = await fetch(`${base}/health`);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { status: 'ok' });
  });

  test('catalog lists 8 product cards', async () => {
    const res = await fetch(`${base}/`);
    assert.equal(res.status, 200);
    const html = await res.text();
    assert.match(html, /^<!doctype html>/i);
    const cards = html.match(/data-testid="product-card"/g) ?? [];
    assert.equal(cards.length, 8);
    assert.match(html, /<h1>Shopfront<\/h1>/);
  });

  test('product page for classic-tee shows the $25.00 price', async () => {
    const res = await fetch(`${base}/products/classic-tee`);
    assert.equal(res.status, 200);
    const html = await res.text();
    assert.match(html, /data-testid="product-title">Classic Tee</);
    assert.match(html, /\$25\.00/);
  });

  test('unknown product page returns 404 with not-found marker', async () => {
    const res = await fetch(`${base}/products/no-such-product`);
    assert.equal(res.status, 404);
    assert.match(await res.text(), /data-testid="not-found"/);
  });

  test('form post adds to cart, redirects 303, and cart-count becomes 1', async () => {
    const post = await fetch(`${base}/cart/items`, {
      method: 'POST',
      redirect: 'manual',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: 'handle=classic-tee',
    });
    assert.equal(post.status, 303);
    assert.equal(post.headers.get('location'), '/cart');
    const setCookie = post.headers.get('set-cookie');
    assert.match(setCookie, /^cart_id=cart_\d+; Path=\/; HttpOnly/);
    const cookie = setCookie.split(';')[0];

    const cart = await fetch(`${base}/cart`, { headers: { cookie } });
    assert.equal(cart.status, 200);
    const html = await cart.text();
    assert.match(html, /<span data-testid="cart-count">1<\/span>/);
    assert.equal((html.match(/data-testid="cart-line"/g) ?? []).length, 1);
  });

  test('REST without publishable key is rejected with 400', async () => {
    const res = await fetch(`${base}/store/products`);
    assert.equal(res.status, 400);
    assert.deepEqual(await res.json(), {
      type: 'not_allowed',
      message: 'Publishable API key required',
    });
  });

  test('REST product list returns count 8 and q=tee filters', async () => {
    const all = await json(base, '/store/products');
    assert.equal(all.count, 8);
    assert.equal(all.products.length, 8);
    assert.equal(all.offset, 0);
    assert.equal(all.limit, 50);

    const filtered = await json(base, '/store/products?q=tee');
    assert.equal(filtered.count, 1);
    assert.equal(filtered.products[0].handle, 'classic-tee');
  });

  test('REST get product by id, and 404 for unknown id', async () => {
    const body = await json(base, '/store/products/prod_01');
    assert.equal(body.product.id, 'prod_01');
    assert.equal(body.product.variants[0].id, 'variant_01');
    assert.equal(body.product.variants[0].calculated_price.calculated_amount, 25);

    const missing = await api(base, '/store/products/prod_99');
    assert.equal(missing.status, 404);
    assert.equal((await missing.json()).type, 'not_found');
  });

  test('REST cart: create, add same line twice merges quantity, total 50', async () => {
    const created = await json(base, '/store/carts', { method: 'POST' });
    const cartId = created.cart.id;
    assert.match(cartId, /^cart_\d+$/);
    assert.equal(created.cart.total, 0);

    const addOnce = (qty) =>
      json(base, `/store/carts/${cartId}/line-items`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ variant_id: 'variant_01', quantity: qty }),
      });

    await addOnce(1);
    const second = await addOnce(1);
    assert.equal(second.cart.items.length, 1);
    assert.equal(second.cart.items[0].quantity, 2);
    assert.equal(second.cart.items[0].variant_id, 'variant_01');
    assert.equal(second.cart.items[0].unit_price, 25);
    assert.equal(second.cart.items[0].total, 50);
    assert.equal(second.cart.total, 50);

    const fetched = await json(base, `/store/carts/${cartId}`);
    assert.equal(fetched.cart.total, 50);
  });

  test('REST cart: invalid quantity and unknown variant return 400', async () => {
    const created = await json(base, '/store/carts', { method: 'POST' });
    const url = `/store/carts/${created.cart.id}/line-items`;
    const post = (body) =>
      api(base, url, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
      });

    for (const quantity of [0, -1, 1.5, 'two']) {
      const res = await post({ variant_id: 'variant_01', quantity });
      assert.equal(res.status, 400, `quantity ${quantity} should be rejected`);
    }
    const badVariant = await post({ variant_id: 'variant_zz', quantity: 1 });
    assert.equal(badVariant.status, 400);
    assert.equal((await badVariant.json()).type, 'invalid_data');
  });

  test('GraphQL products(first: 3) returns 3 edges and totalCount 8', async () => {
    const res = await fetch(`${base}/graphql`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        query: '{ products(first: 3) { edges { node { name slug } } totalCount } }',
      }),
    });
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.data.products.edges.length, 3);
    assert.equal(body.data.products.totalCount, 8);
    assert.equal(body.data.products.edges[0].node.name, 'Classic Tee');
    assert.equal(body.data.products.edges[0].node.slug, 'classic-tee');
  });

  test('GraphQL product(slug: classic-tee) pricing is 25 USD', async () => {
    const res = await fetch(`${base}/graphql`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        query:
          '{ product(slug: "classic-tee") { name pricing { priceRange { start { gross { amount currency } } } } } }',
      }),
    });
    const body = await res.json();
    const gross = body.data.product.pricing.priceRange.start.gross;
    assert.equal(gross.amount, 25);
    assert.equal(gross.currency, 'USD');
  });

  test('GraphQL without query returns 400', async () => {
    const res = await fetch(`${base}/graphql`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({}),
    });
    assert.equal(res.status, 400);
    assert.equal((await res.json()).errors[0].message, 'query is required');
  });

  test('unknown route returns 404 JSON', async () => {
    const res = await fetch(`${base}/nope`);
    assert.equal(res.status, 404);
    assert.deepEqual(await res.json(), { type: 'not_found' });
  });
});

describe('fault injection', () => {
  test('flakeRate=1 gives 503 on / but health stays 200', async () => {
    const { stub, base } = await startStub({ flakeRate: 1 });
    try {
      const page = await fetch(`${base}/`);
      assert.equal(page.status, 503);
      assert.deepEqual(await page.json(), { type: 'unavailable' });

      const health = await fetch(`${base}/health`);
      assert.equal(health.status, 200);
      assert.deepEqual(await health.json(), { status: 'ok' });
    } finally {
      await stub.stop();
    }
  });

  test('latencyMs=50 makes / take at least 50 ms', async () => {
    const { stub, base } = await startStub({ latencyMs: 50 });
    try {
      const t0 = performance.now();
      const res = await fetch(`${base}/`);
      const elapsed = performance.now() - t0;
      assert.equal(res.status, 200);
      await res.text();
      assert.ok(elapsed >= 50, `elapsed ${elapsed.toFixed(1)} ms`);
    } finally {
      await stub.stop();
    }
  });
});
