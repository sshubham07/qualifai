"""Load test (manual). Measures next-question latency under concurrent interviews.
Run: make load  (against a running API with a fast hosted model or FakeLLM mode)."""

from locust import HttpUser, between, task  # type: ignore[import-not-found]


class Candidate(HttpUser):
    wait_time = between(20, 60)  # humans type slowly

    @task
    def health(self) -> None:
        self.client.get("/healthz")

    # TODO: create interview with fixture docs → start → loop answers,
    # asserting p95 next-question latency < 8 s (NFR-1).
