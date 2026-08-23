from .player import flatten_equipment


class EquipmentCalculator:

    def __init__(self, items):
        self.items = items

        self.by_name = {}
        self.by_id = {}

        for item in items:

            item_id = item.get("id")
            name = item.get("name", "")

            if item_id is not None:

                try:
                    self.by_id[
                        int(item_id)
                    ] = item
                except (
                    TypeError,
                    ValueError,
                ):
                    pass

            if name:
                self.by_name[
                    name.strip().lower()
                ] = item

    # =========================================================
    # FIND ITEM
    # =========================================================

    def find_item(self, value):

        if value is None:
            return None

        # Numeric ID.
        try:

            item_id = int(value)

            item = self.by_id.get(
                item_id
            )

            if item:
                return item

        except (
            TypeError,
            ValueError,
        ):
            pass

        # Exact name.
        name = str(
            value
        ).strip().lower()

        item = self.by_name.get(
            name
        )

        if item:
            return item

        # Fallback: normalized whitespace.
        normalized = " ".join(
            name.split()
        )

        return self.by_name.get(
            normalized
        )

    # =========================================================
    # STATS
    # =========================================================

    def calculate_player_stats(
        self,
        player,
    ):

        total_stats = {}

        equipped_items = []
        unresolved = []

        equipment = flatten_equipment(
            player.equipment
        )

        for equipped in equipment:

            slot = equipped[
                "slot"
            ]

            item_value = equipped[
                "item"
            ]

            item = self.find_item(
                item_value
            )

            if item is None:

                unresolved.append(
                    {
                        "slot": slot,
                        "item": item_value,
                    }
                )

                continue

            equipped_items.append(
                {
                    "slot": slot,
                    "item": item.get(
                        "name",
                        str(item_value),
                    ),
                    "id": item.get(
                        "id"
                    ),
                    "category": item.get(
                        "category",
                        "other",
                    ),
                    "kind": item.get(
                        "kind",
                        "",
                    ),
                    "level_requirement":
                        item.get(
                            "level_requirement",
                            0,
                        ),
                }
            )

            stats = item.get(
                "stats",
                {}
            )

            for stat, raw_value in stats.items():

                value = self.extract_numeric_stat(
                    raw_value
                )

                if value is None:
                    continue

                total_stats[stat] = (
                    total_stats.get(
                        stat,
                        0,
                    )
                    + value
                )

        return {
            "stats": total_stats,
            "equipped_items":
                equipped_items,
            "unresolved":
                unresolved,
        }

    # =========================================================
    # NUMERIC STAT PARSER
    # =========================================================

    @staticmethod
    def extract_numeric_stat(
        value
    ):

        if value is None:
            return None

        text = str(value)

        # Damage ranges such as:
        #
        # 10–20
        #
        # are handled as average damage.
        range_match = None

        import re

        range_match = re.search(
            r"(-?\d+(?:\.\d+)?)"
            r"\s*[–-]\s*"
            r"(-?\d+(?:\.\d+)?)",
            text,
        )

        if range_match:

            low = float(
                range_match.group(1)
            )

            high = float(
                range_match.group(2)
            )

            return (
                low + high
            ) / 2.0

        number_match = re.search(
            r"[-+]?\d+(?:\.\d+)?",
            text,
        )

        if not number_match:
            return None

        return float(
            number_match.group(0)
        )