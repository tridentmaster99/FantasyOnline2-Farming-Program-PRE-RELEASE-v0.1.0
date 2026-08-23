import time
import requests


class RateLimiter:
    def __init__(self, maximum=5, period=10):
        self.maximum = maximum
        self.period = period
        self.requests = []

    def wait(self):
        now = time.time()

        self.requests = [
            t for t in self.requests
            if now - t < self.period
        ]

        if len(self.requests) >= self.maximum:
            wait_time = self.period - (now - self.requests[0])

            if wait_time > 0:
                time.sleep(wait_time)

        self.requests.append(time.time())


class FO2API:
    def __init__(
        self,
        base_url="https://fantasyonline2.com/api/public",
        timeout=15
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self.session = requests.Session()

        self.rate_limiter = RateLimiter(5, 10)

    def post(self, endpoint, payload):
        self.rate_limiter.wait()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        response = self.session.post(
            url,
            json=payload,
            timeout=self.timeout
        )

        response.raise_for_status()

        return response.json()

    def broker_search(self, payload=None):
        if payload is None:
            payload = {}

        return self.post(
            "broker/search",
            payload
        )