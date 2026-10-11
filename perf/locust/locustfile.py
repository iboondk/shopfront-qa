"""Locust user model for the shopfront API (stub storefront by default).

Run headless (see the perf:locust script in package.json):

    .venv/bin/locust -f perf/locust/locustfile.py --headless -u 10 -r 5 -t 20s \
        --csv reports/raw/locust/$RUN_ID/locust --only-summary

Env:
    API_URL          base URL (default http://127.0.0.1:3100)
    PUBLISHABLE_KEY  x-publishable-api-key header (default pk_test_stub)
"""

import os
import random

from locust import HttpUser, between, task

PUBLISHABLE_KEY = os.environ.get("PUBLISHABLE_KEY", "pk_test_stub")
PRODUCT_IDS = [f"prod_0{n}" for n in range(1, 9)]
GRAPHQL_QUERY = "{ products(first: 5) { edges { node { slug } } } }"


class ShopperUser(HttpUser):
    host = os.environ.get("API_URL", "http://127.0.0.1:3100")
    wait_time = between(0.5, 2)

    def on_start(self):
        self.client.headers.update({"x-publishable-api-key": PUBLISHABLE_KEY})

    @task(3)
    def browse_catalog(self):
        self.client.get("/store/products?limit=10", name="/store/products")

    @task(2)
    def view_product(self):
        product_id = random.choice(PRODUCT_IDS)
        self.client.get(
            f"/store/products/{product_id}",
            name="/store/products/[id]",
        )

    @task(1)
    def add_to_cart(self):
        with self.client.post(
            "/store/carts",
            name="/store/carts",
            catch_response=True,
        ) as created:
            if created.status_code != 200:
                created.failure(f"create cart returned {created.status_code}")
                return
            created.success()
            cart_id = created.json()["cart"]["id"]

        with self.client.post(
            f"/store/carts/{cart_id}/line-items",
            json={"variant_id": "variant_01", "quantity": 1},
            name="/store/carts/[id]/line-items",
            catch_response=True,
        ) as line:
            if line.status_code != 200:
                line.failure(f"add line item returned {line.status_code}")
            else:
                line.success()

    @task(1)
    def graphql_search(self):
        self.client.post(
            "/graphql",
            json={"query": GRAPHQL_QUERY},
            name="/graphql",
        )
