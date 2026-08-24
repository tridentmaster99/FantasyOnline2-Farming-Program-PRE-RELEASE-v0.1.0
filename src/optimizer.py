import math


class FarmingOptimizer:

    def __init__(
        self,
        items,
        mobs,
        market,
        player,
        equipment_calculator,
        config,
    ):
        self.items = items
        self.mobs = mobs
        self.market = market
        self.player = player
        self.equipment_calculator = equipment_calculator
        self.config = config

        self.items_by_id = {}

        for item in items:
            try:
                item_id = int(item.get("id"))
            except (TypeError, ValueError):
                continue

            self.items_by_id[item_id] = item

        self.player_stats = (
            equipment_calculator.calculate_player_stats(
                player
            )
        )

        self.rejected_mobs = []

    # =========================================================
    # PLAYER
    # =========================================================

    def player_level(self):
        try:
            return int(self.player.level)
        except (TypeError, ValueError):
            return 1

    # =========================================================
    # SAFE NUMBER
    # =========================================================

    @staticmethod
    def safe_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def safe_int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    # =========================================================
    # ITEM SELLABILITY
    # =========================================================

    def is_item_sellable(self, item_id):

        item_id = self.safe_int(item_id)

        item = self.items_by_id.get(item_id)

        if not item:
            return False

        # Explicit database information takes priority.
        if "sellable" in item:
            return bool(item.get("sellable"))

        # Market-related database fields.
        if item.get("mmp") is not None:
            return True

        if item.get("mrsf") is not None:
            return True

        # Vendor sell price.
        if (
            self.safe_float(
                item.get("vsp", 0)
            ) > 0
        ):
            return True

        return False

    # =========================================================
    # MOB ELIGIBILITY
    # =========================================================

    def get_mob_rejection_reason(self, mob):

        level = self.safe_int(
            mob.get("level", 0)
        )

        player_level = self.player_level()

        max_difference = self.safe_int(
            self.config.get(
                "max_level_difference",
                20,
            ),
            20,
        )

        if level <= 0:
            return "Mob has no valid level."

        if abs(level - player_level) > max_difference:
            return (
                "Mob level is outside the configured "
                "level range."
            )

        is_boss = bool(
            mob.get("boss", False)
        )

        is_elite = bool(
            mob.get("elite", False)
        )

        if (
            is_boss
            and not self.config.get(
                "include_bosses",
                False,
            )
        ):
            return "Bosses are disabled in configuration."

        if (
            is_elite
            and not self.config.get(
                "include_elites",
                True,
            )
        ):
            return "Elites are disabled in configuration."

        profiles = mob.get(
            "drop_profiles",
            [],
        )

        if not profiles:
            return "Mob has no drop profiles."

        return None

    def is_mob_eligible(self, mob):

        return (
            self.get_mob_rejection_reason(mob)
            is None
        )

    # =========================================================
    # DROP PRICE
    # =========================================================

    def get_item_market_value(self, item_id):

        item_id = self.safe_int(item_id)

        market = self.market.get(item_id)

        if not market:

            return {
                "price": 0.0,
                "confidence": 0.0,
                "available": False,
            }

        confidence = self.safe_float(
            market.get(
                "confidence",
                0,
            )
        )

        floor = self.safe_float(
            self.config.get(
                "market_confidence_floor",
                0.2,
            ),
            0.2,
        )

        if confidence < floor:

            return {
                "price": 0.0,
                "confidence": confidence,
                "available": False,
            }

        price = self.safe_float(
            market.get(
                "median_price",
                0,
            )
        )

        if price <= 0:

            price = self.safe_float(
                market.get(
                    "lowest_price",
                    0,
                )
            )

        discount = self.safe_float(
            self.config.get(
                "sell_discount",
                0.95,
            ),
            0.95,
        )

        discount = max(
            0.0,
            min(
                1.0,
                discount,
            ),
        )

        price *= discount

        return {
            "price": price,
            "confidence": confidence,
            "available": price > 0,
        }

    # =========================================================
    # DROP VALUE
    # =========================================================

    def calculate_drop_value(self, drop):

        item_id = self.safe_int(
            drop.get("item_id")
        )

        chance = self.safe_float(
            drop.get(
                "chance",
                0,
            )
        )

        quantity = self.safe_float(
            drop.get(
                "quantity",
                1,
            ),
            1.0,
        )

        chance = max(
            0.0,
            chance,
        )

        quantity = max(
            0.0,
            quantity,
        )

        sellable = self.is_item_sellable(
            item_id
        )

        market_info = (
            self.get_item_market_value(
                item_id
            )
        )

        price = market_info["price"]

        if not sellable:
            price = 0.0

        expected_value = (
            chance
            * quantity
            * price
        )

        return {
            "item_id": item_id,
            "item_name": drop.get(
                "item_name",
                f"Item {item_id}",
            ),
            "chance": chance,
            "quantity": quantity,
            "market_price": price,
            "confidence": market_info[
                "confidence"
            ],
            "market_available": market_info[
                "available"
            ],
            "sellable": sellable,
            "expected_value": expected_value,
            "roll_type": drop.get(
                "roll_type",
                "unknown",
            ),
        }

    # =========================================================
    # PROFILE VALUE
    # =========================================================

    def calculate_profile_value(self, profile):

        value = 0.0

        valued_drops = []
        unsellable_drops = []
        unavailable_market_drops = []

        for drop in profile.get(
            "drops",
            [],
        ):

            result = (
                self.calculate_drop_value(
                    drop
                )
            )

            if not result["sellable"]:

                unsellable_drops.append(
                    result
                )

                continue

            if not result[
                "market_available"
            ]:

                unavailable_market_drops.append(
                    result
                )

                continue

            value += result[
                "expected_value"
            ]

            if result[
                "expected_value"
            ] > 0:

                valued_drops.append(
                    result
                )

        coin_min = self.safe_float(
            profile.get(
                "coin_min",
                0,
            )
        )

        coin_max = self.safe_float(
            profile.get(
                "coin_max",
                coin_min,
            ),
            coin_min,
        )

        expected_coins = (
            coin_min
            + coin_max
        ) / 2.0

        value += expected_coins

        return {
            "zone": profile.get(
                "zone",
                "Unknown",
            ),
            "profile": profile.get(
                "profile"
            ),
            "expected_value_per_kill": value,
            "expected_coins": expected_coins,
            "drops": valued_drops,
            "unsellable_drops": unsellable_drops,
            "unavailable_market_drops":
                unavailable_market_drops,
        }

    # =========================================================
    # TIME TO KILL
    # =========================================================

    def estimate_seconds_per_kill(self, mob):

        default = self.safe_float(
            self.config.get(
                "default_seconds_per_kill",
                10.0,
            ),
            10.0,
        )

        mob_hp = self.safe_float(
            mob.get(
                "hp",
                0,
            )
        )

        if mob_hp <= 0:
            return max(
                1.0,
                default,
            )

        stats = self.player_stats.get(
            "stats",
            {}
        )

        damage = self.safe_float(
            stats.get(
                "damage",
                0,
            )
        )

        if damage <= 0:

            damage = self.safe_float(
                stats.get(
                    "attack",
                    0,
                )
            )

        if damage <= 0:
            return max(
                1.0,
                default,
            )

        kills = math.ceil(
            mob_hp
            / max(
                1.0,
                damage,
            )
        )

        return max(
            1.0,
            float(kills),
        )

    # =========================================================
    # SURVIVAL
    # =========================================================

    def estimate_survival(self, mob):

        configured = self.safe_float(
            self.config.get(
                "default_survival_rate",
                0.95,
            ),
            0.95,
        )

        return max(
            0.0,
            min(
                1.0,
                configured,
            ),
        )

    # =========================================================
    # REASONS
    # =========================================================

    def generate_reasons(self, result):

        reasons = []

        player_level = self.player_level()

        mob_level = self.safe_int(
            result.get(
                "mob_level",
                0,
            )
        )

        level_difference = abs(
            mob_level
            - player_level
        )

        profit = self.safe_float(
            result.get(
                "expected_coins_per_hour",
                0,
            )
        )

        value_per_kill = self.safe_float(
            result.get(
                "expected_value_per_kill",
                0,
            )
        )

        survival = self.safe_float(
            result.get(
                "survival_rate",
                0,
            )
        )

        kills_per_hour = self.safe_float(
            result.get(
                "kills_per_hour",
                0,
            )
        )

        seconds = self.safe_float(
            result.get(
                "seconds_per_kill",
                0,
            )
        )

        if profit > 0:
            reasons.append(
                (
                    profit,
                    "Strong expected profit per hour."
                )
            )

        if value_per_kill > 0:
            reasons.append(
                (
                    value_per_kill,
                    "Drops have meaningful expected value per kill."
                )
            )

        if level_difference <= 3:
            reasons.append(
                (
                    1_000_000
                    - level_difference,
                    "Mob level is close to your character level."
                )
            )

        if survival >= 0.9:
            reasons.append(
                (
                    survival * 100_000,
                    "Estimated survival rate is high."
                )
            )

        if kills_per_hour >= 100:
            reasons.append(
                (
                    kills_per_hour * 1_000,
                    "High kills-per-hour potential."
                )
            )

        if seconds <= 5:
            reasons.append(
                (
                    500_000 / max(
                        seconds,
                        1,
                    ),
                    "The estimated kill time is very fast."
                )
            )

        confidence_values = []

        for profile in result.get(
            "profile_results",
            [],
        ):

            for drop in profile.get(
                "drops",
                [],
            ):

                confidence_values.append(
                    self.safe_float(
                        drop.get(
                            "confidence",
                            0,
                        )
                    )
                )

        if confidence_values:

            average_confidence = (
                sum(confidence_values)
                / len(confidence_values)
            )

            if average_confidence >= 0.8:

                reasons.append(
                    (
                        average_confidence
                        * 100_000,
                        "Market data has high confidence."
                    )
                )

        reasons.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        return [
            reason
            for _, reason in reasons[:4]
        ]

    def generate_why_not(self, result):

        reasons = []

        player_level = self.player_level()

        mob_level = self.safe_int(
            result.get(
                "mob_level",
                0,
            )
        )

        level_difference = abs(
            mob_level
            - player_level
        )

        seconds = self.safe_float(
            result.get(
                "seconds_per_kill",
                0,
            )
        )

        survival = self.safe_float(
            result.get(
                "survival_rate",
                0,
            )
        )

        value_per_kill = self.safe_float(
            result.get(
                "expected_value_per_kill",
                0,
            )
        )

        profit = self.safe_float(
            result.get(
                "expected_coins_per_hour",
                0,
            )
        )

        if level_difference >= 7:
            reasons.append(
                (
                    level_difference,
                    "The mob is relatively far from your level."
                )
            )

        if seconds >= 20:
            reasons.append(
                (
                    seconds,
                    "Kill time is relatively slow."
                )
            )

        if survival < 0.8:
            reasons.append(
                (
                    100
                    - survival * 100,
                    "Estimated survival rate is low."
                )
            )

        if value_per_kill < 10:
            reasons.append(
                (
                    10
                    - value_per_kill,
                    "Expected value per kill is low."
                )
            )

        if profit <= 0:
            reasons.append(
                (
                    100,
                    "No meaningful market profit was calculated."
                )
            )

        low_confidence = False

        for profile in result.get(
            "profile_results",
            [],
        ):

            for drop in profile.get(
                "drops",
                [],
            ):

                if (
                    self.safe_float(
                        drop.get(
                            "confidence",
                            0,
                        )
                    )
                    < 0.5
                ):

                    low_confidence = True
                    break

            if low_confidence:
                break

        if low_confidence:

            reasons.append(
                (
                    1,
                    "Some market prices have limited confidence."
                )
            )

        reasons.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        return [
            reason
            for _, reason in reasons[:4]
        ]

    # =========================================================
    # MOB VALUE
    # =========================================================

    def evaluate_mob(self, mob):

        rejection_reason = (
            self.get_mob_rejection_reason(
                mob
            )
        )

        if rejection_reason:

            self.rejected_mobs.append(
                {
                    "mob_id": mob.get("id"),
                    "mob_name": mob.get(
                        "name",
                        "Unknown",
                    ),
                    "reason": rejection_reason,
                }
            )

            return None

        profiles = mob.get(
            "drop_profiles",
            [],
        )

        profile_results = []

        for profile in profiles:

            result = (
                self.calculate_profile_value(
                    profile
                )
            )

            profile_results.append(
                result
            )

        if not profile_results:
            return None

        best_profile = max(
            profile_results,
            key=lambda result:
                result[
                    "expected_value_per_kill"
                ],
        )

        seconds = (
            self.estimate_seconds_per_kill(
                mob
            )
        )

        survival = (
            self.estimate_survival(
                mob
            )
        )

        value_per_kill = (
            best_profile[
                "expected_value_per_kill"
            ]
        )

        expected_kills_per_hour = (
            3600.0
            / max(
                1.0,
                seconds,
            )
        )

        gross_per_hour = (
            value_per_kill
            * expected_kills_per_hour
            * survival
        )

        xp_per_kill = self.safe_float(
            mob.get(
                "xp",
                mob.get(
                    "experience",
                    0,
                ),
            )
        )

        xp_per_hour = (
            xp_per_kill
            * expected_kills_per_hour
            * survival
        )

        result = {
            "mob_id": mob.get(
                "id"
            ),
            "mob_name": mob.get(
                "name",
                "Unknown",
            ),
            "mob_level": self.safe_int(
                mob.get(
                    "level",
                    0,
                )
            ),
            "hp": self.safe_int(
                mob.get(
                    "hp",
                    0,
                )
            ),
            "damage_min": self.safe_int(
                mob.get(
                    "damage_min",
                    0,
                )
            ),
            "damage_max": self.safe_int(
                mob.get(
                    "damage_max",
                    0,
                )
            ),
            "xp_per_kill": xp_per_kill,
            "xp_per_hour": xp_per_hour,
            "zone": best_profile[
                "zone"
            ],
            "profile": best_profile[
                "profile"
            ],
            "seconds_per_kill": seconds,
            "kills_per_hour":
                expected_kills_per_hour,
            "survival_rate": survival,
            "expected_value_per_kill":
                value_per_kill,
            "expected_coins_per_hour":
                gross_per_hour,
            "profile_results":
                profile_results,
        }

        result["why"] = (
            self.generate_reasons(
                result
            )
        )

        result["why_not"] = (
            self.generate_why_not(
                result
            )
        )

        return result

    # =========================================================
    # RUN
    # =========================================================

    def optimize(self):

        results = []

        self.rejected_mobs = []

        for mob in self.mobs:

            result = self.evaluate_mob(
                mob
            )

            if result is not None:

                results.append(
                    result
                )

        # Current 0.2.0 behavior remains
        # profit-first. Goal weighting will be
        # introduced in the goal-system update.
        results.sort(
            key=lambda result:
                result.get(
                    "expected_coins_per_hour",
                    0,
                ),
            reverse=True,
        )

        result_count = self.safe_int(
            self.config.get(
                "results",
                15,
            ),
            15,
        )

        result_count = max(
            1,
            result_count,
        )

        return results[
            :result_count
        ]