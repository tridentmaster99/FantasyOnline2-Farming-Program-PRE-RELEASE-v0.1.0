import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class FO2Database:

    BASE_URL = "https://db.fantasyonline2.com"

    def __init__(
        self,
        base_url=BASE_URL,
        cache_directory="data/game",
        delay=0.25,
        max_pages=100,
    ):
        self.base_url = base_url.rstrip("/")

        self.cache_directory = Path(cache_directory)
        self.cache_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.delay = max(0.0, float(delay))
        self.max_pages = max(1, int(max_pages))

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": (
                    "FantasyFarmOptimizer/0.1 "
                    "(database updater)"
                ),
                "Accept": "text/html,application/xhtml+xml",
            }
        )

    # =========================================================
    # HTTP
    # =========================================================

    def get(self, url):
        if self.delay > 0:
            time.sleep(self.delay)

        response = self.session.get(
            url,
            timeout=30,
        )

        response.raise_for_status()

        return response.text

    def soup(self, url):
        return BeautifulSoup(
            self.get(url),
            "html.parser",
        )

    # =========================================================
    # STORAGE
    # =========================================================

    def save_json(self, filename, data):
        path = self.cache_directory / filename

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def load_json(self, filename):
        path = self.cache_directory / filename

        if not path.exists():
            return None

        try:
            return json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )
        except (json.JSONDecodeError, OSError):
            return None

    # =========================================================
    # TEXT / NUMBER HELPERS
    # =========================================================

    @staticmethod
    def clean_text(text):
        if text is None:
            return ""

        return re.sub(
            r"\s+",
            " ",
            str(text),
        ).strip()

    @staticmethod
    def number(text):
        if text is None:
            return 0

        value = str(text)

        value = (
            value
            .replace(",", "")
            .replace("coins", "")
            .strip()
        )

        match = re.search(
            r"-?\d+(?:\.\d+)?",
            value,
        )

        if not match:
            return 0

        number = match.group(0)

        if "." in number:
            return float(number)

        return int(number)

    @staticmethod
    def percentage(text):
        if not text:
            return 0.0

        match = re.search(
            r"(\d+(?:\.\d+)?)\s*%",
            str(text),
        )

        if not match:
            return 0.0

        return float(match.group(1)) / 100.0

    @staticmethod
    def slug_id(url):
        if not url:
            return None

        match = re.search(
            r"-(\d+)(?:[/?#]|$)",
            str(url),
        )

        if match:
            return int(match.group(1))

        return None

    # =========================================================
    # PAGINATION
    # =========================================================

    def discover_page_urls(self, directory):
        first_url = (
            f"{self.base_url}/{directory}"
        )

        try:
            first_soup = self.soup(first_url)
        except requests.RequestException as error:
            print(
                f"[PAGE ERROR] "
                f"{first_url}: {error}"
            )
            return []

        page_urls = {
            first_url.rstrip("/")
        }

        for anchor in first_soup.select(
            "a[href]"
        ):
            href = anchor.get(
                "href",
                "",
            )

            absolute = urljoin(
                self.base_url,
                href,
            ).rstrip("/")

            if not absolute.startswith(
                f"{self.base_url}/{directory}"
            ):
                continue

            if re.search(
                rf"/{re.escape(directory)}/page/\d+$",
                absolute,
                re.I,
            ):
                page_urls.add(absolute)

        def page_number(url):
            match = re.search(
                r"/page/(\d+)$",
                url,
                re.I,
            )

            if match:
                return int(match.group(1))

            return 1

        sorted_pages = sorted(
            page_urls,
            key=page_number,
        )

        return sorted_pages[
            :self.max_pages
        ]

    # =========================================================
    # DETAIL LINK DISCOVERY
    # =========================================================

    def discover_directory(self, directory):
        links = {}

        page_urls = self.discover_page_urls(
            directory
        )

        print(
            f"Found {len(page_urls)} "
            f"{directory} pages."
        )

        for page_index, page_url in enumerate(
            page_urls,
            1,
        ):
            print(
                f"Scanning {directory} "
                f"page {page_index}/"
                f"{len(page_urls)}..."
            )

            try:
                soup = self.soup(page_url)
            except requests.RequestException as error:
                print(
                    f"[PAGE ERROR] "
                    f"{page_url}: {error}"
                )
                continue

            for anchor in soup.select(
                "a[href]"
            ):
                href = anchor.get(
                    "href",
                    "",
                )

                absolute = urljoin(
                    self.base_url,
                    href,
                ).rstrip("/")

                prefix = (
                    f"{self.base_url}/"
                    f"{directory}/"
                )

                if not absolute.startswith(prefix):
                    continue

                # Detail pages have a numeric ID at the
                # end of their slug:
                #
                # /items/fanny-pack-1
                # /mobs/soft-shelled-crab-1
                #
                # Pagination pages do not match this.
                if not re.search(
                    rf"/{re.escape(directory)}/"
                    rf"[^/?#]+-\d+$",
                    absolute,
                    re.I,
                ):
                    continue

                name = self.clean_text(
                    anchor.get_text(
                        " ",
                        strip=True,
                    )
                )

                if not name:
                    continue

                links[absolute] = name

        return links

    # =========================================================
    # ITEMS
    # =========================================================

    def discover_items(self):
        return self.discover_directory(
            "items"
        )

    def parse_item(self, url, fallback_name):
        soup = self.soup(url)

        item_id = self.slug_id(url)

        if item_id is None:
            return None

        # -----------------------------------------------------
        # Name
        # -----------------------------------------------------

        heading = soup.find("h1")

        if heading:
            name = self.clean_text(
                heading.get_text(
                    " ",
                    strip=True,
                )
            )
        else:
            name = fallback_name

        # -----------------------------------------------------
        # Item kind
        #
        # Actual page:
        #
        # <p class="item-detail_kind...">
        #     Bag
        # </p>
        #
        # -----------------------------------------------------

        kind_element = soup.select_one(
            "p[class*='item-detail_kind']"
        )

        kind = ""

        if kind_element:
            kind = self.clean_text(
                kind_element.get_text(
                    " ",
                    strip=True,
                )
            )

        # -----------------------------------------------------
        # Description
        # -----------------------------------------------------

        description_element = soup.select_one(
            "p[class*='item-detail_description']"
        )

        description = ""

        if description_element:
            description = (
                description_element
                .get_text(
                    "\n",
                    strip=True,
                )
            )

        # -----------------------------------------------------
        # Icon
        # -----------------------------------------------------

        icon = ""

        icon_element = soup.select_one(
            "div[class*='item-detail_iconFrame'] img"
        )

        if icon_element:
            icon = (
                icon_element.get(
                    "src",
                    "",
                )
            )

        if icon:
            icon = urljoin(
                self.base_url,
                icon,
            )

        # -----------------------------------------------------
        # Quick facts
        # -----------------------------------------------------

        facts = {}

        for fact in soup.select(
            "div[class*='item-detail_factList'] > div"
        ):
            key_element = fact.find("dt")
            value_element = fact.find("dd")

            if not key_element or not value_element:
                continue

            key = self.clean_text(
                key_element.get_text(
                    " ",
                    strip=True,
                )
            )

            value = self.clean_text(
                value_element.get_text(
                    " ",
                    strip=True,
                )
            )

            if key:
                facts[key] = value

        # -----------------------------------------------------
        # Details / stat grid
        # -----------------------------------------------------

        stats = {}

        for stat in soup.select(
            "div[class*='item-detail_stat']"
        ):
            spans = stat.find_all(
                "span",
                recursive=False,
            )

            strong = stat.find(
                "strong"
            )

            if not spans or not strong:
                continue

            key = self.clean_text(
                spans[0].get_text(
                    " ",
                    strip=True,
                )
            )

            value = self.clean_text(
                strong.get_text(
                    " ",
                    strip=True,
                )
            )

            if key:
                stats[
                    self.normalize_stat_name(key)
                ] = value

        # -----------------------------------------------------
        # Level requirement
        # -----------------------------------------------------

        level_requirement = 0

        level_patterns = [
            r"Required level\s+(\d+)",
            r"Level requirement\s+(\d+)",
        ]

        page_text = self.clean_text(
            soup.get_text(
                " ",
                strip=True,
            )
        )

        for pattern in level_patterns:
            match = re.search(
                pattern,
                page_text,
                re.I,
            )

            if match:
                level_requirement = int(
                    match.group(1)
                )
                break

        # -----------------------------------------------------
        # Some item pages expose level requirement
        # in structured preview rows.
        # -----------------------------------------------------

        for row in soup.select(
            "[class*='item-detail']"
        ):
            text = self.clean_text(
                row.get_text(
                    " ",
                    strip=True,
                )
            )

            match = re.search(
                r"Level requirement\s+(\d+)",
                text,
                re.I,
            )

            if match:
                level_requirement = int(
                    match.group(1)
                )
                break

        # -----------------------------------------------------
        # Category
        # -----------------------------------------------------

        category = self.normalize_item_category(
            kind
        )

        # -----------------------------------------------------
        # Shops pay
        # -----------------------------------------------------

        shop_price = 0

        if "Shops pay" in facts:
            shop_price = self.number(
                facts["Shops pay"]
            )

        # -----------------------------------------------------
        # Inventory slots
        # -----------------------------------------------------

        inventory_slots = 0

        if "Inventory slots" in facts:
            inventory_slots = self.number(
                facts["Inventory slots"]
            )

        # -----------------------------------------------------
        # Market reference
        #
        # These are NOT live market prices.
        # They are saved historical references.
        # The live broker API will be used separately.
        # -----------------------------------------------------

        median_price = 0
        latest_trusted_sale = 0

        market_stat_grid = soup.select(
            "div[class*='item-detail_statGrid'] "
            "div[class*='item-detail_stat']"
        )

        for block in market_stat_grid:
            label_element = block.find("span")
            value_element = block.find("strong")

            if not label_element or not value_element:
                continue

            label = self.clean_text(
                label_element.get_text(
                    " ",
                    strip=True,
                )
            )

            value = self.number(
                value_element.get_text(
                    " ",
                    strip=True,
                )
            )

            if label == "Median price":
                median_price = value

            elif label == "Latest trusted sale":
                latest_trusted_sale = value

        # -----------------------------------------------------
        # Sources
        # -----------------------------------------------------

        sources = {
            "shops": [],
            "battle_passes": [],
            "mobs": [],
        }

        for anchor in soup.select(
            "a[href]"
        ):
            href = anchor.get(
                "href",
                "",
            )

            title = self.clean_text(
                anchor.get_text(
                    " ",
                    strip=True,
                )
            )

            if "/mobs/" in href:
                if title:
                    sources["mobs"].append(
                        {
                            "name": title,
                            "url": urljoin(
                                self.base_url,
                                href,
                            ),
                        }
                    )

            elif "/battlepasses/" in href:
                if title:
                    sources["battle_passes"].append(
                        {
                            "name": title,
                            "url": urljoin(
                                self.base_url,
                                href,
                            ),
                        }
                    )

        # Deduplicate sources.
        for source_type in sources:
            seen = set()
            unique = []

            for source in sources[source_type]:
                key = (
                    source["name"],
                    source["url"],
                )

                if key in seen:
                    continue

                seen.add(key)
                unique.append(source)

            sources[source_type] = unique

        return {
            "id": item_id,
            "name": name,
            "url": url,
            "category": category,
            "kind": kind,
            "description": description,
            "icon": icon,
            "level_requirement": level_requirement,
            "stats": stats,
            "facts": facts,
            "shop_price": shop_price,
            "inventory_slots": inventory_slots,
            "market_reference": {
                "median_price": median_price,
                "latest_trusted_sale":
                    latest_trusted_sale,
            },
            "sources": sources,
        }

    # =========================================================
    # ITEM CATEGORY
    # =========================================================

    @staticmethod
    def normalize_item_category(kind):
        value = (
            str(kind)
            .strip()
            .lower()
        )

        mapping = {
            "helmet": "helmet",
            "head": "helmet",
            "hood": "helmet",

            "body": "body",
            "body armor": "body",
            "armor": "body",
            "chest": "body",

            "legs": "legs",
            "leg armor": "legs",
            "greaves": "legs",

            "weapon": "weapon",
            "sword": "weapon",
            "bow": "weapon",
            "axe": "weapon",
            "dagger": "weapon",
            "staff": "weapon",
            "wand": "weapon",
            "hammer": "weapon",

            "offhand": "offhand",
            "off-hand": "offhand",
            "shield": "offhand",

            "ring": "ring",
            "trinket": "trinket",
            "implant": "implant",
            "mount": "mount",
            "relic": "relic",
            "bag": "bag",
            "resource": "resource",
            "consumable": "consumable",
            "skill book": "skill_book",
        }

        return mapping.get(
            value,
            value if value else "other",
        )

    @staticmethod
    def normalize_stat_name(name):
        value = (
            str(name)
            .strip()
            .lower()
        )

        replacements = {
            "attack": "attack",
            "damage": "damage",
            "armor": "armor",
            "magic defense": "magic_defense",
            "health": "health",
            "energy": "energy",
            "energy regen": "energy_regen",
            "health regen": "health_regen",
            "critical": "critical",
            "accuracy": "accuracy",
            "dodge": "dodge",
            "strength": "strength",
            "agility": "agility",
            "intellect": "intellect",
            "vitality": "vitality",
            "luck": "luck",
        }

        return replacements.get(
            value,
            value.replace(
                " ",
                "_",
            ),
        )

    # =========================================================
    # MOBS
    # =========================================================

    def discover_mobs(self):
        return self.discover_directory(
            "mobs"
        )

    def parse_mob(self, url, fallback_name):
        soup = self.soup(url)

        mob_id = self.slug_id(url)

        if mob_id is None:
            return None

        # -----------------------------------------------------
        # Basic identity
        # -----------------------------------------------------

        heading = soup.find("h1")

        if heading:
            name = self.clean_text(
                heading.get_text(
                    " ",
                    strip=True,
                )
            )
        else:
            name = fallback_name

        # -----------------------------------------------------
        # Hero stats
        # -----------------------------------------------------

        level = 0
        hp = 0
        damage_min = 0
        damage_max = 0

        stat_values = {}

        for block in soup.select(
            "[class*='mob-detail_stat']"
        ):
            label_element = block.find(
                "span"
            )

            value_element = block.find(
                "strong"
            )

            if not label_element or not value_element:
                continue

            label = self.clean_text(
                label_element.get_text(
                    " ",
                    strip=True,
                )
            )

            value = self.clean_text(
                value_element.get_text(
                    " ",
                    strip=True,
                )
            )

            stat_values[
                label.lower()
            ] = value

        page_text = self.clean_text(
            soup.get_text(
                " ",
                strip=True,
            )
        )

        level_match = re.search(
            r"\bLevel\s+(\d+)\b",
            page_text,
            re.I,
        )

        if level_match:
            level = int(
                level_match.group(1)
            )

        health_value = (
            stat_values.get("health")
            or stat_values.get("hp")
        )

        if health_value:
            hp = self.number(
                health_value
            )

        damage_value = (
            stat_values.get("damage")
        )

        if damage_value:
            damage_match = re.search(
                r"([\d,]+)\s*[–-]\s*([\d,]+)",
                damage_value,
            )

            if damage_match:
                damage_min = self.number(
                    damage_match.group(1)
                )
                damage_max = self.number(
                    damage_match.group(2)
                )

        # Fallback from page text.
        if hp == 0:
            match = re.search(
                r"Health\s+([\d,]+)",
                page_text,
                re.I,
            )

            if match:
                hp = self.number(
                    match.group(1)
                )

        if damage_min == 0 and damage_max == 0:
            match = re.search(
                r"Damage\s+"
                r"([\d,]+)\s*[–-]\s*"
                r"([\d,]+)",
                page_text,
                re.I,
            )

            if match:
                damage_min = self.number(
                    match.group(1)
                )
                damage_max = self.number(
                    match.group(2)
                )

        # -----------------------------------------------------
        # Drop profiles
        # -----------------------------------------------------

        drop_profiles = []

        profile_elements = soup.select(
            "details[class*='mob-detail_context']"
        )

        for profile_index, details in enumerate(
            profile_elements,
            1,
        ):
            profile = self.parse_drop_profile(
                details,
                profile_index,
            )

            if profile:
                drop_profiles.append(
                    profile
                )

        # -----------------------------------------------------
        # Zones
        # -----------------------------------------------------

        zones = []

        for profile in drop_profiles:
            zone = profile.get(
                "zone"
            )

            if (
                zone
                and zone not in zones
            ):
                zones.append(zone)

        # -----------------------------------------------------
        # Legacy-compatible flat drops
        #
        # Keep a flattened list too, but DO NOT merge
        # different profiles into one chance.
        #
        # Every entry retains its zone/profile.
        # -----------------------------------------------------

        drops = []

        for profile in drop_profiles:
            for drop in profile["drops"]:

                flat = dict(drop)

                flat["zone"] = profile[
                    "zone"
                ]

                flat["profile"] = profile[
                    "profile"
                ]

                drops.append(flat)

        # -----------------------------------------------------
        # Coin fallback
        # -----------------------------------------------------

        coin_min = 0
        coin_max = 0

        for profile in drop_profiles:

            if coin_min == 0:
                coin_min = profile[
                    "coin_min"
                ]

            else:
                coin_min = min(
                    coin_min,
                    profile["coin_min"],
                )

            coin_max = max(
                coin_max,
                profile["coin_max"],
            )

        return {
            "id": mob_id,
            "name": name,
            "url": url,
            "level": level,
            "hp": hp,
            "damage_min": damage_min,
            "damage_max": damage_max,
            "coin_min": coin_min,
            "coin_max": coin_max,
            "xp": self.extract_xp(
                page_text
            ),
            "zones": zones,
            "drop_profiles": drop_profiles,
            "drops": drops,
        }

    # =========================================================
    # MOB DROP PROFILE
    # =========================================================

    def parse_drop_profile(
        self,
        details,
        fallback_profile_number,
    ):
        # -----------------------------------------------------
        # Profile title
        #
        # Example:
        # Gemster's Shop · Drop profile 1
        # -----------------------------------------------------

        summary = details.find(
            "summary"
        )

        if not summary:
            return None

        summary_text = self.clean_text(
            summary.get_text(
                " ",
                strip=True,
            )
        )

        profile_match = re.search(
            r"Drop profile\s+(\d+)",
            summary_text,
            re.I,
        )

        if profile_match:
            profile_number = int(
                profile_match.group(1)
            )
        else:
            profile_number = (
                fallback_profile_number
            )

        zone = ""

        # The actual page stores the zone in:
        #
        # <dt>Zone</dt>
        # <dd><a ...>Hidden Reef</a></dd>
        #
        for rule in details.select(
            "div[class*='mob-detail_rule']"
        ):
            dt = rule.find("dt")
            dd = rule.find("dd")

            if not dt or not dd:
                continue

            label = self.clean_text(
                dt.get_text(
                    " ",
                    strip=True,
                )
            )

            if label.lower() == "zone":

                anchor = dd.find("a")

                if anchor:
                    zone = self.clean_text(
                        anchor.get_text(
                            " ",
                            strip=True,
                        )
                    )
                else:
                    zone = self.clean_text(
                        dd.get_text(
                            " ",
                            strip=True,
                        )
                    )

                break

        # -----------------------------------------------------
        # Coin result
        # -----------------------------------------------------

        coin_min = 0
        coin_max = 0

        for rule in details.select(
            "div[class*='mob-detail_rule']"
        ):
            dt = rule.find("dt")
            dd = rule.find("dd")

            if not dt or not dd:
                continue

            label = self.clean_text(
                dt.get_text(
                    " ",
                    strip=True,
                )
            )

            if (
                label.lower()
                != "solo coin result"
            ):
                continue

            coin_text = self.clean_text(
                dd.get_text(
                    " ",
                    strip=True,
                )
            )

            range_match = re.search(
                r"([\d,]+)"
                r"(?:\s*[–-]\s*([\d,]+))?",
                coin_text,
            )

            if range_match:

                coin_min = self.number(
                    range_match.group(1)
                )

                if range_match.group(2):
                    coin_max = self.number(
                        range_match.group(2)
                    )
                else:
                    coin_max = coin_min

        # -----------------------------------------------------
        # Drops
        # -----------------------------------------------------

        drops = []

        # Only tables inside THIS <details> profile.
        tables = details.select(
            "table"
        )

        for table in tables:

            headers = [
                self.clean_text(
                    th.get_text(
                        " ",
                        strip=True,
                    )
                ).lower()
                for th in table.select(
                    "thead th"
                )
            ]

            # We specifically want the independent
            # item drop roll table.
            if not headers:
                continue

            if "item" not in headers:
                continue

            for row in table.select(
                "tbody tr"
            ):
                cells = row.find_all(
                    "td",
                    recursive=False,
                )

                if len(cells) < 4:
                    continue

                # -------------------------------------------------
                # Item
                # -------------------------------------------------

                item_anchor = cells[0].find(
                    "a",
                    href=re.compile(
                        r"/items/"
                    ),
                )

                if not item_anchor:
                    continue

                item_name = self.clean_text(
                    item_anchor.get_text(
                        " ",
                        strip=True,
                    )
                )

                item_url = urljoin(
                    self.base_url,
                    item_anchor.get(
                        "href",
                        "",
                    ),
                )

                item_id = self.slug_id(
                    item_url
                )

                if item_id is None:
                    continue

                # -------------------------------------------------
                # Roll type and chance
                # -------------------------------------------------

                roll_text = self.clean_text(
                    cells[1].get_text(
                        " ",
                        strip=True,
                    )
                )

                chance_text = self.clean_text(
                    cells[2].get_text(
                        " ",
                        strip=True,
                    )
                )

                roll_type = (
                    self.extract_roll_type(
                        roll_text
                    )
                )

                chance = self.percentage(
                    chance_text
                )

                # -------------------------------------------------
                # Maximum quantity
                # -------------------------------------------------

                quantity_text = self.clean_text(
                    cells[3].get_text(
                        " ",
                        strip=True,
                    )
                )

                quantity = self.extract_quantity(
                    quantity_text
                )

                drops.append(
                    {
                        "item_id": item_id,
                        "item_name": item_name,
                        "chance": chance,
                        "quantity": quantity,
                        "roll_type": roll_type,
                    }
                )

        # -----------------------------------------------------
        # Deduplicate ONLY identical rows within this profile.
        #
        # Different profiles remain separate.
        # -----------------------------------------------------

        unique = []
        seen = set()

        for drop in drops:

            key = (
                drop["item_id"],
                drop["chance"],
                drop["quantity"],
                drop["roll_type"],
            )

            if key in seen:
                continue

            seen.add(key)
            unique.append(drop)

        return {
            "profile": profile_number,
            "zone": zone,
            "coin_min": coin_min,
            "coin_max": coin_max,
            "drops": unique,
        }

    # =========================================================
    # DROP HELPERS
    # =========================================================

    @staticmethod
    def extract_roll_type(text):
        if not text:
            return "unknown"

        match = re.search(
            r"\b(Global|Zone|Spawn)\b",
            text,
            re.I,
        )

        if match:
            return match.group(1).lower()

        return "unknown"

    @staticmethod
    def extract_quantity(text):
        if not text:
            return 1

        match = re.search(
            r"(?:Up to\s*)?(\d+)",
            text,
            re.I,
        )

        if match:
            return int(
                match.group(1)
            )

        return 1

    def extract_xp(self, text):
        patterns = [
            r"(?:XP|Experience)\s*:?\s*([\d,]+)",
            r"([\d,]+)\s*(?:XP|experience)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.I,
            )

            if match:
                return self.number(
                    match.group(1)
                )

        return 0

    # =========================================================
    # UPDATE ITEMS
    # =========================================================

    def update_items(self, force=False):
        links = self.discover_items()

        print(
            f"Found {len(links)} "
            f"individual item pages."
        )

        items = []

        total = len(links)

        for index, (
            url,
            fallback_name,
        ) in enumerate(
            links.items(),
            1,
        ):

            try:

                item = self.parse_item(
                    url,
                    fallback_name,
                )

                if item:
                    items.append(item)

            except Exception as error:

                print(
                    f"[ITEM ERROR] "
                    f"{url}: {error}"
                )

            if (
                index % 25 == 0
                or index == total
            ):
                print(
                    f"Items: "
                    f"{index}/{total}"
                )

        self.save_json(
            "items.json",
            items,
        )

        print(
            f"Saved {len(items)} items."
        )

        return items

    # =========================================================
    # UPDATE MOBS
    # =========================================================

    def update_mobs(self, force=False):
        links = self.discover_mobs()

        print(
            f"Found {len(links)} "
            f"individual mob pages."
        )

        mobs = []

        total = len(links)

        for index, (
            url,
            fallback_name,
        ) in enumerate(
            links.items(),
            1,
        ):

            try:

                mob = self.parse_mob(
                    url,
                    fallback_name,
                )

                if mob:
                    mobs.append(mob)

            except Exception as error:

                print(
                    f"[MOB ERROR] "
                    f"{url}: {error}"
                )

            if (
                index % 10 == 0
                or index == total
            ):
                print(
                    f"Mobs: "
                    f"{index}/{total}"
                )

        self.save_json(
            "mobs.json",
            mobs,
        )

        print(
            f"Saved {len(mobs)} mobs."
        )

        return mobs

    # =========================================================
    # UPDATE EVERYTHING
    # =========================================================

    def update_all(self, force=False):

        print("=" * 65)
        print(
            "UPDATING FANTASY ONLINE 2 DATABASE"
        )
        print("=" * 65)
        print()

        items = self.update_items(
            force=force
        )

        print()

        mobs = self.update_mobs(
            force=force
        )

        print()

        print(
            "DATABASE UPDATE COMPLETE"
        )

        print(
            f"Items: {len(items)}"
        )

        print(
            f"Mobs: {len(mobs)}"
        )

        return items, mobs

    # =========================================================
    # LOAD
    # =========================================================

    def load_items(self):
        return (
            self.load_json(
                "items.json"
            )
            or []
        )

    def load_mobs(self):
        return (
            self.load_json(
                "mobs.json"
            )
            or []
        )