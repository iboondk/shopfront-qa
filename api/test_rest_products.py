"""REST product tests (Medusa v2 store shape): GET /store/products and GET /store/products/{id}.

All REST tests skip when TARGET=saleor, because Saleor has no Medusa REST API.
"""

import pytest
import requests

REQUEST_TIMEOUT_S = 10

PRODUCT_LIST_SCHEMA = {"products": list, "count": int, "offset": int, "limit": int}
PRODUCT_SCHEMA = {"id": str, "handle": str, "title": str, "variants": list}


@pytest.fixture(autouse=True)
def _skip_rest_on_saleor(target):
    if target == "saleor":
        pytest.skip("Saleor has no Medusa REST API")


def _is_type(value, expected):
    if expected is int:
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, expected)


def validate_types(obj, spec):
    """Hand-rolled schema check: each key in `spec` must exist on `obj` with the given Python type.

    Returns a list of error strings; an empty list means the object conforms.
    """
    if not isinstance(obj, dict):
        return [f"expected an object, got {type(obj).__name__}"]
    errors = []
    for key, expected in spec.items():
        if key not in obj:
            errors.append(f"missing key '{key}'")
        elif not _is_type(obj[key], expected):
            errors.append(f"'{key}' expected {expected.__name__}, got {type(obj[key]).__name__}")
    return errors


def _list(store, api_url, **params):
    resp = store.get(api_url + "/store/products", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_rest_products_list_returns_eight(store, api_url):
    body = _list(store, api_url)
    assert body["count"] == 8
    assert len(body["products"]) == 8


def test_rest_products_each_has_id_handle_title_and_price(store, api_url):
    body = _list(store, api_url)
    for product in body["products"]:
        assert isinstance(product.get("id"), str) and product["id"]
        assert isinstance(product.get("handle"), str) and product["handle"]
        assert isinstance(product.get("title"), str) and product["title"]
        amount = product["variants"][0]["calculated_price"]["calculated_amount"]
        assert amount > 0, f"{product['handle']} has non-positive price {amount}"


def test_rest_products_response_top_level_schema(store, api_url):
    body = _list(store, api_url)
    assert validate_types(body, PRODUCT_LIST_SCHEMA) == []
    for product in body["products"]:
        assert validate_types(product, PRODUCT_SCHEMA) == []


def test_rest_products_pagination_limit_and_offset(store, api_url):
    first_page = _list(store, api_url, limit=2, offset=0)
    second_page = _list(store, api_url, limit=2, offset=2)
    assert len(second_page["products"]) == 2
    first_ids = {p["id"] for p in first_page["products"]}
    second_ids = {p["id"] for p in second_page["products"]}
    assert second_ids.isdisjoint(first_ids)


def test_rest_products_search_q_tee_filters_titles(store, api_url):
    body = _list(store, api_url, q="tee")
    assert body["products"], "expected at least one match for q=tee"
    for product in body["products"]:
        assert "tee" in product["title"].lower(), product["title"]


def test_rest_products_get_by_id_prod_01_is_classic_tee(store, api_url):
    resp = store.get(api_url + "/store/products/prod_01")
    assert resp.status_code == 200, resp.text
    assert resp.json()["product"]["handle"] == "classic-tee"


def test_rest_products_unknown_id_returns_404_not_found(store, api_url):
    resp = store.get(api_url + "/store/products/prod_does_not_exist")
    assert resp.status_code == 404
    assert resp.json()["type"] == "not_found"


def test_rest_products_missing_key_returns_400(api_url):
    # Plain requests call on purpose: no publishable key header.
    resp = requests.get(api_url + "/store/products", timeout=REQUEST_TIMEOUT_S)
    assert resp.status_code == 400
