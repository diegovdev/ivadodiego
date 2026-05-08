"""Locust load test for Museums API — used by nightly CI (T25, V35)."""

import json
import random

from locust import HttpUser, between, task

_POPULATIONS = [500_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000]


class MuseumApiUser(HttpUser):
    wait_time = between(0.5, 2.0)

    @task(3)
    def get_health(self) -> None:
        self.client.get("/health")

    @task(5)
    def get_museums(self) -> None:
        self.client.get("/museums")

    @task(2)
    def get_cities(self) -> None:
        self.client.get("/cities")

    @task(4)
    def post_predict(self) -> None:
        population = random.choice(_POPULATIONS)
        self.client.post(
            "/predict",
            data=json.dumps({"population": population}),
            headers={"Content-Type": "application/json"},
            name="/predict",
        )
