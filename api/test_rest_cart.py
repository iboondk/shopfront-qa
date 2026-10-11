"""REST cart tests (Medusa v2 store shape): /store/carts and /store/carts/{id}/line-items.

Each test creates its own cart, so there is no ordering dependency between tests.
All REST tests skip when TARGET=saleor, because Saleor has no Medusa REST API.
"""

import pytest


@pytest.fixture(autouse=True)
def _skip_rest_on_saleor(target):
    if target == "saleor":
        pytest.skip("Saleor has no Medusa REST API")


def _create_cart(store, api_url):
    resp = store.post(api_url + "/store/carts")
    assert resp.status_code == 200, resp.text
    return resp.json()["cart"]


def _add_line(store, api_url, cart_id, variant_id, quantity):
    return store.post(
        f"{api_url}/store/carts/{cart_id}/line-items",
        json={"variant_id": variant_id, "quantity": quantity},
    )


def test_rest_cart_create_returns_empty_cart(store, api_url):
    cart = _create_cart(store, api_url)
    assert cart["id"].startswith("cart_")
    assert cart["items"] == []


def test_rest_cart_add_same_variant_twice_merges_into_one_line(store, api_url):
    cart = _create_cart(store, api_url)
    first = _add_line(store, api_url, cart["id"], "variant_01", 1)
    assert first.status_code == 200, first.text
    second = _add_line(store, api_url, cart["id"], "variant_01", 1)
    assert second.status_code == 200, second.text

    updated = second.json()["cart"]
    assert len(updated["items"]) == 1
    assert updated["items"][0]["quantity"] == 2
    assert updated["total"] == 50.0


def test_rest_cart_add_unknown_variant_returns_400(store, api_url):
    cart = _create_cart(store, api_url)
    resp = _add_line(store, api_url, cart["id"], "variant_does_not_exist", 1)
    assert resp.status_code == 400


def test_rest_cart_add_quantity_zero_returns_400(store, api_url):
    cart = _create_cart(store, api_url)
    resp = _add_line(store, api_url, cart["id"], "variant_01", 0)
    assert resp.status_code == 400


def test_rest_cart_add_non_integer_quantity_returns_400(store, api_url):
    cart = _create_cart(store, api_url)
    resp = _add_line(store, api_url, cart["id"], "variant_01", "abc")
    assert resp.status_code == 400


def test_rest_cart_get_unknown_cart_returns_404(store, api_url):
    resp = store.get(api_url + "/store/carts/cart_does_not_exist")
    assert resp.status_code == 404
