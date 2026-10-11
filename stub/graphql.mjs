// Saleor-shaped GraphQL schema for the stub storefront.
import { buildSchema as buildSchemaFromSdl, graphql } from 'graphql';

export const SDL = `
type Money { amount: Float!, currency: String! }
type TaxedMoney { gross: Money! }
type PriceRange { start: TaxedMoney }
type ProductPricingInfo { priceRange: PriceRange }
type Product { id: ID!, name: String!, slug: String!, description: String, pricing: ProductPricingInfo }
type ProductCountableEdge { node: Product! }
type ProductCountableConnection { edges: [ProductCountableEdge!]!, totalCount: Int! }
type Query {
  products(first: Int, channel: String, search: String): ProductCountableConnection!
  product(slug: String!, channel: String): Product
}
`;

// Maps a seed product (products.json shape) to the GraphQL Product shape.
export function toGraphqlProduct(p) {
  return {
    id: p.id,
    name: p.title,
    slug: p.handle,
    description: p.description ?? null,
    pricing: {
      priceRange: {
        start: {
          gross: { amount: p.price_cents / 100, currency: p.currency.toUpperCase() },
        },
      },
    },
  };
}

// Root value (resolvers) bound to a product list.
export function makeRootValue(products) {
  return {
    products({ first, search } = {}) {
      const needle = typeof search === 'string' ? search.toLowerCase() : null;
      const matched = needle
        ? products.filter((p) => p.title.toLowerCase().includes(needle))
        : products;
      const limit = Number.isInteger(first) ? first : 100;
      const edges = matched
        .slice(0, Math.max(0, limit))
        .map((p) => ({ node: toGraphqlProduct(p) }));
      return { edges, totalCount: matched.length };
    },
    product({ slug }) {
      const found = products.find((p) => p.handle === slug);
      return found ? toGraphqlProduct(found) : null;
    },
  };
}

// Returns a GraphQLSchema for the given products. Pair it with makeRootValue(products).
export function buildSchema(products) {
  void products; // schema shape is static; data is supplied through the root value
  return buildSchemaFromSdl(SDL);
}

// Executes a GraphQL request body ({query, variables?, operationName?}).
export async function executeGraphql(schema, rootValue, body) {
  if (!body || typeof body.query !== 'string') {
    return { status: 400, json: { errors: [{ message: 'query is required' }] } };
  }
  const json = await graphql({
    schema,
    source: body.query,
    rootValue,
    variableValues: body.variables ?? undefined,
    operationName: body.operationName ?? undefined,
  });
  return { status: 200, json };
}
