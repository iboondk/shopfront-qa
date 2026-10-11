"""The three shared storefront scenarios, implemented with Selenium.

Scenario IDs (see docs/design-notes.md) are carried through parametrize ids, so the JUnit
test names contain them, e.g. test_catalog_lists_products[catalog.lists-products].
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

WAIT_S = 10


def _wait(driver):
    return WebDriverWait(driver, WAIT_S)


def _by_testid(testid):
    return (By.CSS_SELECTOR, f'[data-testid="{testid}"]')


@pytest.mark.parametrize("scenario", ["catalog.lists-products"], ids=lambda s: s)
def test_catalog_lists_products(driver, base_url, scenario):
    """catalog.lists-products: open /, see 8 product cards, first title is "Classic Tee"."""
    driver.get(base_url + "/")
    _wait(driver).until(EC.presence_of_element_located(_by_testid("product-list")))
    cards = _wait(driver).until(lambda d: d.find_elements(*_by_testid("product-card")) or False)
    assert len(cards) == 8
    first_link = cards[0].find_element(*_by_testid("product-link"))
    assert first_link.text == "Classic Tee"


@pytest.mark.parametrize("scenario", ["product.shows-detail"], ids=lambda s: s)
def test_product_shows_detail(driver, base_url, scenario):
    """product.shows-detail: open /, click "Classic Tee", see product-title and price $25.00."""
    driver.get(base_url + "/")
    link = _wait(driver).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Classic Tee"))
    )
    link.click()
    _wait(driver).until(EC.url_matches(r"/products/classic-tee$"))
    title = _wait(driver).until(EC.visibility_of_element_located(_by_testid("product-title")))
    assert title.text == "Classic Tee"
    assert driver.find_element(*_by_testid("product-price")).text == "$25.00"


@pytest.mark.parametrize("scenario", ["cart.add-item"], ids=lambda s: s)
def test_cart_add_item(driver, base_url, scenario):
    """cart.add-item: open /products/classic-tee, click add-to-cart, land on /cart, cart-count is 1."""
    driver.get(base_url + "/products/classic-tee")
    button = _wait(driver).until(EC.element_to_be_clickable(_by_testid("add-to-cart")))
    button.click()
    _wait(driver).until(EC.url_matches(r"/cart$"))
    _wait(driver).until(EC.text_to_be_present_in_element(_by_testid("cart-count"), "1"))
    assert driver.find_element(*_by_testid("cart-count")).text == "1"
