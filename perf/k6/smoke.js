// k6 smoke test for the shopfront API (stub storefront by default).
//
// Browse flow per iteration: list products, view one product, create a cart,
// add a line item, run a GraphQL product query, then pause for 1 s.
//
// Env:
//   API_URL          base URL (default http://127.0.0.1:3100)
//   PUBLISHABLE_KEY  x-publishable-api-key header (default pk_test_stub)
//   VUS              virtual users (default 5)
//   DURATION         run length (default 30s)
//   RUN_ID           folder name under reports/raw/k6/ (default local)
//
// CI invocation (documented, not run locally):
//   k6 run --summary-export reports/raw/k6/$RUN_ID/summary.json perf/k6/smoke.js
//
// The report generator (tools/report/k6.py) reads the flat --summary-export format, so that flag
// is the only writer of summary.json. handleSummary below prints a one-line stdout summary and
// writes nothing to disk. This avoids two writers with different formats on the same path.

import http from 'k6/http';
import { check, group, sleep } from 'k6';

export const options = {
  scenarios: {
    browse: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS || 5),
      duration: __ENV.DURATION || '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
    checks: ['rate>0.99'],
  },
};

const BASE = __ENV.API_URL || 'http://127.0.0.1:3100';
const KEY = __ENV.PUBLISHABLE_KEY || 'pk_test_stub';
const JSON_HEADERS = {
  'Content-Type': 'application/json',
  'x-publishable-api-key': KEY,
};
const KEY_HEADERS = { 'x-publishable-api-key': KEY };

export default function () {
  group('browse', () => {
    const list = http.get(`${BASE}/store/products`, { headers: KEY_HEADERS });
    check(list, {
      'list products: status 200': (r) => r.status === 200,
      'list products: count > 0': (r) => r.status === 200 && r.json('count') > 0,
    });

    const product = http.get(`${BASE}/store/products/prod_01`, { headers: KEY_HEADERS });
    check(product, {
      'product detail: status 200': (r) => r.status === 200,
    });

    const cart = http.post(`${BASE}/store/carts`, null, { headers: KEY_HEADERS });
    check(cart, {
      'create cart: status 200': (r) => r.status === 200,
    });
    const cartId = cart.status === 200 ? cart.json('cart.id') : null;

    if (cartId) {
      const line = http.post(
        `${BASE}/store/carts/${cartId}/line-items`,
        JSON.stringify({ variant_id: 'variant_01', quantity: 1 }),
        { headers: JSON_HEADERS },
      );
      check(line, {
        'add line item: status 200': (r) => r.status === 200,
        'add line item: items length 1': (r) => r.status === 200 && r.json('cart.items').length === 1,
      });
    }

    const gql = http.post(
      `${BASE}/graphql`,
      JSON.stringify({ query: '{ products(first: 5) { edges { node { slug } } } }' }),
      { headers: JSON_HEADERS },
    );
    check(gql, {
      'graphql products: status 200': (r) => r.status === 200,
      'graphql products: no errors': (r) => r.status === 200 && !r.json('errors'),
    });
  });

  sleep(1);
}

export function handleSummary(data) {
  const runId = __ENV.RUN_ID || 'local';
  const p95 = data.metrics.http_req_duration
    ? data.metrics.http_req_duration.values['p(95)']
    : null;
  const failRate = data.metrics.http_req_failed
    ? data.metrics.http_req_failed.values.rate
    : null;
  return {
    stdout: JSON.stringify({ run_id: runId, http_req_duration_p95_ms: p95, http_req_failed_rate: failRate }) + '\n',
  };
}
