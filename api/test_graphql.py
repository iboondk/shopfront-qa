"""GraphQL tests (Saleor-shaped): products connection, product by slug, and negative cases.

Exact-value assertions (price 25, currency USD) run only against the stub. Against
TARGET=saleor the tests check the response structure only.
"""

PRODUCTS_QUERY = """
query Products($first: Int, $channel: String, $search: String) {
  products(first: $first, channel: $channel, search: $search) {
    totalCount
    edges { node { name slug } }
  }
}
"""

PRODUCT_QUERY = """
query Product($slug: String!, $channel: String) {
  product(slug: $slug, channel: $channel) {
    name
    slug
    pricing { priceRange { start { gross { amount currency } } } }
  }
}
"""


def _data(body):
    assert not body.get("errors"), f"unexpected GraphQL errors: {body.get('errors')}"
    assert "data" in body, f"no data key in body: {body}"
    return body["data"]


def test_graphql_products_first_3_on_channel(gql, target):
    body = gql(PRODUCTS_QUERY, {"first": 3, "channel": "default-channel"})
    connection = _data(body)["products"]
    assert len(connection["edges"]) == 3
    assert connection["totalCount"] >= 3
    if target == "stub":
        assert connection["totalCount"] == 8


def test_graphql_products_every_node_has_name_and_slug(gql):
    body = gql(PRODUCTS_QUERY, {"first": 50, "channel": "default-channel"})
    edges = _data(body)["products"]["edges"]
    assert edges, "expected at least one product"
    for edge in edges:
        node = edge["node"]
        assert isinstance(node["name"], str) and node["name"].strip()
        assert isinstance(node["slug"], str) and node["slug"].strip()


def test_graphql_products_search_tee_returns_only_tee_names(gql):
    body = gql(PRODUCTS_QUERY, {"first": 50, "search": "tee"})
    edges = _data(body)["products"]["edges"]
    assert edges, "expected at least one match for search 'tee'"
    for edge in edges:
        assert "tee" in edge["node"]["name"].lower(), edge["node"]["name"]


def test_graphql_product_by_slug_has_pricing_structure(gql, target):
    body = gql(PRODUCT_QUERY, {"slug": "classic-tee", "channel": "default-channel"})
    product = _data(body)["product"]
    assert product is not None, "classic-tee not found"
    assert product["slug"] == "classic-tee"

    gross = product["pricing"]["priceRange"]["start"]["gross"]
    assert isinstance(gross["amount"], (int, float))
    assert isinstance(gross["currency"], str) and gross["currency"]

    if target == "stub":
        assert gross["amount"] == 25
        assert gross["currency"] == "USD"


def test_graphql_invalid_query_returns_errors_list(gql_raw):
    resp = gql_raw({"query": "{ nope }"})
    assert resp.status_code in (200, 400), resp.text
    body = resp.json()
    assert isinstance(body.get("errors"), list)
    assert len(body["errors"]) > 0


def test_graphql_empty_body_returns_400(gql_raw):
    resp = gql_raw({})
    assert resp.status_code == 400
