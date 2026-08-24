import json
import time
from pathlib import Path
from statistics import median

import requests


class MarketClient:

    def __init__(
        self,
        base_url,
        timeout_seconds=15,
        cache_minutes=5,
        requests_per_10_seconds=5,
    ):

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds
        self.cache_minutes = cache_minutes
        self.requests_per_10_seconds = (
            requests_per_10_seconds
        )

        self.endpoint = (
            f"{self.base_url}/broker/search"
        )

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent":
                    "FantasyFarmOptimizer/0.2.0-pre",
                "Accept":
                    "application/json",
            }
        )

        self.request_times = []

        self.last_error = None

        self.used_fallback = False

        self.last_cache_age_seconds = None

    # =========================================================
    # RATE LIMIT
    # =========================================================

    def _wait_for_rate_limit(self):

        now = time.time()

        self.request_times = [
            timestamp
            for timestamp in self.request_times
            if now - timestamp < 10
        ]

        limit = max(
            1,
            self.requests_per_10_seconds,
        )

        if len(self.request_times) >= limit:

            wait_time = (
                10
                - (
                    now
                    - self.request_times[0]
                )
            )

            if wait_time > 0:
                time.sleep(
                    wait_time
                )

        self.request_times.append(
            time.time()
        )

    # =========================================================
    # REQUEST
    # =========================================================

    def request(self, params=None):

        self._wait_for_rate_limit()

        try:

            response = self.session.get(
                self.endpoint,
                params=params or {},
                timeout=self.timeout,
            )

            response.raise_for_status()

            self.last_error = None

            return response.json()

        except requests.RequestException as error:

            self.last_error = (
                f"Market API request failed: {error}"
            )

            raise

        except ValueError as error:

            self.last_error = (
                f"Market API returned invalid JSON: {error}"
            )

            raise

    # =========================================================
    # NORMALIZE RESPONSE
    # =========================================================

    @staticmethod
    def normalize_response(data):

        if not isinstance(data, dict):

            return {
                "orders": [],
                "items": [],
                "pagination": {},
            }

        return {
            "orders": data.get(
                "orders",
                [],
            ),
            "items": data.get(
                "items",
                [],
            ),
            "pagination": data.get(
                "pagination",
                {},
            ),
        }

    # =========================================================
    # ITEM MARKET INFORMATION
    # =========================================================

    def build_market(self, data):

        data = self.normalize_response(
            data
        )

        orders = data["orders"]
        items = data["items"]

        names = {}

        for item in items:

            try:

                item_id = int(
                    item.get("id")
                )

            except (
                TypeError,
                ValueError,
            ):

                continue

            translations = item.get(
                "t",
                {}
            )

            english = translations.get(
                "en",
                {}
            )

            name = english.get(
                "n"
            )

            if name:
                names[item_id] = name

        grouped = {}

        for order in orders:

            try:

                item_id = int(
                    order.get(
                        "ItemDefinitionId"
                    )
                )

                price = float(
                    order.get(
                        "Price",
                        0,
                    )
                )

                quantity = int(
                    order.get(
                        "TotalCount",
                        0,
                    )
                )

            except (
                TypeError,
                ValueError,
            ):

                continue

            if price <= 0:
                continue

            if quantity <= 0:
                continue

            grouped.setdefault(
                item_id,
                [],
            ).append(
                {
                    "order_id":
                        order.get("Id"),
                    "price":
                        price,
                    "quantity":
                        quantity,
                    "duration":
                        order.get("Duration"),
                    "listed":
                        order.get("Listed"),
                    "level_requirement":
                        order.get(
                            "LevelRequirement",
                            0,
                        ),
                    "type_id":
                        order.get("TypeId"),
                    "subtype_id":
                        order.get(
                            "SubTypeId"
                        ),
                }
            )

        result = {}

        for item_id, listings in grouped.items():

            prices = [
                listing["price"]
                for listing in listings
            ]

            prices.sort()

            lowest = prices[0]

            med = median(prices)

            average = (
                sum(prices)
                / len(prices)
            )

            total_quantity = sum(
                listing["quantity"]
                for listing in listings
            )

            listing_count = len(
                listings
            )

            confidence = (
                self.calculate_confidence(
                    listing_count,
                    total_quantity,
                    lowest,
                    med,
                )
            )

            result[item_id] = {
                "item_id":
                    item_id,
                "name":
                    names.get(
                        item_id,
                        f"Item {item_id}",
                    ),
                "listings":
                    listings,
                "lowest_price":
                    lowest,
                "median_price":
                    med,
                "average_price":
                    average,
                "total_quantity":
                    total_quantity,
                "listing_count":
                    listing_count,
                "confidence":
                    confidence,
            }

        return result

    # =========================================================
    # CONFIDENCE
    # =========================================================

    @staticmethod
    def calculate_confidence(
        listing_count,
        total_quantity,
        lowest_price,
        median_price,
    ):

        if listing_count <= 0:
            return 0.0

        if median_price <= 0:
            return 0.0

        listing_factor = min(
            1.0,
            listing_count / 10.0,
        )

        quantity_factor = min(
            1.0,
            total_quantity / 100.0,
        )

        ratio = (
            lowest_price
            / median_price
        )

        if ratio >= 0.8:

            price_factor = 1.0

        elif ratio >= 0.5:

            price_factor = 0.75

        elif ratio >= 0.25:

            price_factor = 0.5

        else:

            price_factor = 0.25

        confidence = (
            listing_factor * 0.35
            + quantity_factor * 0.25
            + price_factor * 0.40
        )

        return round(
            min(
                1.0,
                max(
                    0.0,
                    confidence,
                ),
            ),
            4,
        )

    # =========================================================
    # FETCH ALL PAGES
    # =========================================================

    def fetch_all(
        self,
        max_pages=100,
    ):

        all_orders = []
        all_items = []

        seen_order_ids = set()

        for page in range(
            1,
            max_pages + 1,
        ):

            print(
                f"Fetching market page "
                f"{page}..."
            )

            data = self.request(
                {
                    "page": page
                }
            )

            normalized = (
                self.normalize_response(
                    data
                )
            )

            page_orders = normalized[
                "orders"
            ]

            page_items = normalized[
                "items"
            ]

            for order in page_orders:

                order_id = order.get(
                    "Id"
                )

                if (
                    order_id is not None
                    and order_id
                    in seen_order_ids
                ):
                    continue

                if order_id is not None:

                    seen_order_ids.add(
                        order_id
                    )

                all_orders.append(
                    order
                )

            all_items.extend(
                page_items
            )

            pagination = normalized[
                "pagination"
            ]

            total_pages = int(
                pagination.get(
                    "totalPages",
                    page,
                )
                or page
            )

            current_page = int(
                pagination.get(
                    "currentPage",
                    page,
                )
                or page
            )

            if (
                current_page
                >= total_pages
            ):
                break

            if not page_orders:
                break

        return {
            "orders": all_orders,
            "items": all_items,
        }

    # =========================================================
    # CACHE
    # =========================================================

    def update_cache(
        self,
        cache_file="data/market.json",
        max_pages=100,
    ):

        path = Path(
            cache_file
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = self.fetch_all(
            max_pages=max_pages
        )

        now = int(
            time.time()
        )

        payload = {
            "updated_at":
                now,
            "data":
                data,
        }

        path.write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        self.last_cache_age_seconds = 0

        self.used_fallback = False

        return data

    def load_cache(
        self,
        cache_file="data/market.json",
        allow_expired=False,
    ):

        path = Path(
            cache_file
        )

        if not path.exists():
            return None

        try:

            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ):

            return None

        updated_at = payload.get(
            "updated_at",
            0,
        )

        try:

            updated_at = float(
                updated_at
            )

        except (
            TypeError,
            ValueError,
        ):

            updated_at = 0

        if updated_at <= 0:
            return None

        age_seconds = max(
            0,
            time.time()
            - updated_at,
        )

        self.last_cache_age_seconds = (
            age_seconds
        )

        if (
            not allow_expired
            and age_seconds
            > self.cache_minutes * 60
        ):
            return None

        data = payload.get(
            "data"
        )

        if not isinstance(
            data,
            dict,
        ):
            return None

        return data

    # =========================================================
    # GET MARKET
    # =========================================================

    def get_market(
        self,
        cache_file="data/market.json",
        max_pages=100,
        force_refresh=False,
    ):

        self.used_fallback = False

        self.last_error = None

        # -----------------------------------------------------
        # NORMAL FRESH CACHE
        # -----------------------------------------------------

        if not force_refresh:

            cached = self.load_cache(
                cache_file,
                allow_expired=False,
            )

            if cached is not None:

                print(
                    "Using cached market data."
                )

                return self.build_market(
                    cached
                )

        # -----------------------------------------------------
        # TRY API
        # -----------------------------------------------------

        try:

            print(
                "Downloading current market..."
            )

            data = self.update_cache(
                cache_file=cache_file,
                max_pages=max_pages,
            )

            return self.build_market(
                data
            )

        except Exception as error:

            self.last_error = str(
                error
            )

            # -------------------------------------------------
            # FALLBACK TO STALE CACHE
            # -------------------------------------------------

            stale = self.load_cache(
                cache_file,
                allow_expired=True,
            )

            if stale is None:

                print(
                    "Market update failed and "
                    "no cached market data is available."
                )

                raise

            self.used_fallback = True

            age = (
                self.last_cache_age_seconds
            )

            if age is None:

                age_text = "unknown age"

            else:

                age_minutes = (
                    age / 60
                )

                if age_minutes < 60:

                    age_text = (
                        f"{age_minutes:.0f} minutes old"
                    )

                else:

                    age_text = (
                        f"{age_minutes / 60:.1f} hours old"
                    )

            print(
                "WARNING: Market API update failed."
            )

            print(
                f"Using stale cached market data "
                f"({age_text})."
            )

            return self.build_market(
                stale
            )