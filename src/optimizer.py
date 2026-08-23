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
                item_id = int(
                    item.get("id")
                )
            except (
                TypeError,
                ValueError,
            ):
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
        return int(
            self.player.level
        )

    # =========================================================
    # ITEM SELLABILITY
    # =========================================================

    def is_item_sellable(
        self,
        item_id,
    ):
        item = self.items_by_id.get(
            int(item_id)
        )

        if not item:
            return False

        # Explicit database information takes priority.
        if "sellable" in item:
            return bool(
                item.get("sellable")
            )

        # FO2 database fields:
        # vbc = vendor buy currency
        # vbp = vendor buy price
        # vsc = vendor sell currency
        # vsp = vendor sell price
        #
        # An item with a positive market reference
        # is considered potentially sellable.
        if item.get("mmp") is not None:
            return True

        if item.get("mrsf") is not None:
            return True

        # Vendor value can also indicate that the item
        # has an economic value.
        if (
            float(
                item.get(
                    "vsp",
                    0,
                )
                or 0
            )
            > 0
        ):
            return True

        return False

    # =========================================================
    # MOB ELIGIBILITY
    # =========================================================

    def is_mob_eligible(
        self,
        mob,
    ):

        level = int(
            mob.get(
                "level",
                0,
            )
            or 0
        )

        player_level = self.player_level()

        max_difference = int(
            self.config.get(
                "max_level_difference",
                20,
            )
        )

        if level <= 0:

            return False

        if (
            abs(
                level
                - player_level
            )
            > max_difference
        ):

            return False

        is_boss = bool(
            mob.get(
                "boss",
                False,
            )
        )

        is_elite = bool(
            mob.get(
                "elite",
                False,
            )
        )

        if (
            is_boss
            and not self.config.get(
                "include_bosses",
                False,
            )
        ):

            return False

        if (
            is_elite
            and not self.config.get(
                "include_elites",
                True,
            )
        ):

            return False

        return True

    # =========================================================
    # DROP PRICE
    # =========================================================

    def get_item_market_value(
        self,
        item_id,
    ):

        market = self.market.get(
            item_id
        )

        if not market:

            return {
                "price": 0.0,
                "confidence": 0.0,
                "available": False,
            }

        confidence = float(
            market.get(
                "confidence",
                0,
            )
        )

        floor = float(
            self.config.get(
                "market_confidence_floor",
                0.2,
            )
        )

        if confidence < floor:

            return {
                "price": 0.0,
                "confidence": confidence,
                "available": False,
            }

        price = float(
            market.get(
                "median_price",
                0,
            )
        )

        if price <= 0:

            price = float(
                market.get(
                    "lowest_price",
                    0,
                )
            )

        discount = float(
            self.config.get(
                "sell_discount",
                0.95,
            )
        )

        price *= discount

        return {
            "price": price,
            "confidence": confidence,
            "available": True,
        }

    # =========================================================
    # DROP VALUE
    # =========================================================

    def calculate_drop_value(
        self,
        drop,
    ):

        item_id = drop.get(
            "item_id"
        )

        try:
            item_id = int(
                item_id
            )
        except (
            TypeError,
            ValueError,
        ):
            item_id = 0

        chance = float(
            drop.get(
                "chance",
                0,
            )
            or 0
        )

        quantity = float(
            drop.get(
                "quantity",
                1,
            )
            or 1
        )

        sellable = self.is_item_sellable(
            item_id
        )

        market_info = (
            self.get_item_market_value(
                item_id
            )
        )

        price = market_info[
            "price"
        ]

        # An item that cannot realistically be sold
        # contributes zero market profit.
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

    def calculate_profile_value(
        self,
        profile,
    ):

        value = 0.0

        valued_drops = []

        unsellable_drops = []

        for drop in profile.get(
            "drops",
            [],
        ):

            result = (
                self.calculate_drop_value(
                    drop
                )
            )

            if result["sellable"]:

                value += result[
                    "expected_value"
                ]

                if result[
                    "expected_value"
                ] > 0:

                    valued_drops.append(
                        result
                    )

            else:

                unsellable_drops.append(
                    result
                )

        coin_min = float(
            profile.get(
                "coin_min",
                0,
            )
            or 0
        )

        coin_max = float(
            profile.get(
                "coin_max",
                coin_min,
            )
            or coin_min
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
        }

    # =========================================================
    # TIME TO KILL
    # =========================================================

    def estimate_seconds_per_kill(
        self,
        mob,
    ):

        default = float(
            self.config.get(
                "default_seconds_per_kill",
                10.0,
            )
        )

        mob_hp = float(
            mob.get(
                "hp",
                0,
            )
            or 0
        )

        if mob_hp <= 0:
            return default

        stats = self.player_stats[
            "stats"
        ]

        damage = stats.get(
            "damage",
            0,
        )

        if damage <= 0:

            damage = stats.get(
                "attack",
                0,
            )

        if damage <= 0:
            return default

        kills = math.ceil(
            mob_hp / max(
                1.0,
                damage,
            )
        )

        return max(
            1.0,
            kills,
        )

    # =========================================================
    # SURVIVAL
    # =========================================================

    def estimate_survival(
        self,
        mob,
    ):

        configured = self.config.get(
            "default_survival_rate",
            0.95,
        )

        configured = float(
            configured
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

    def generate_reasons(
        self,
        result,
    ):

        reasons = []

        player_level = self.player_level()
        mob_level = int(
            result["mob_level"]
        )

        level_difference = abs(
            mob_level
            - player_level
        )

        if result[
            "expected_coins_per_hour"
        ] > 0:

            reasons.append(
                (
                    result[
                        "expected_coins_per_hour"
                    ],
                    "Strong expected profit per hour."
                )
            )

        if result[
            "expected_value_per_kill"
        ] > 0:

            reasons.append(
                (
                    result[
                        "expected_value_per_kill"
                    ],
                    "Drops have meaningful expected value per kill."
                )
            )

        if level_difference <= 3:

            reasons.append(
                (
                    1000000
                    - level_difference,
                    "Mob level is close to your character level."
                )
            )

        if result[
            "survival_rate"
        ] >= 0.9:

            reasons.append(
                (
                    result[
                        "survival_rate"
                    ] * 100000,
                    "Estimated survival rate is high."
                )
            )

        if result[
            "kills_per_hour"
        ] >= 100:

            reasons.append(
                (
                    result[
                        "kills_per_hour"
                    ] * 1000,
                    "High kills-per-hour potential."
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
                    drop.get(
                        "confidence",
                        0,
                    )
                )

        if confidence_values:

            average_confidence = (
                sum(
                    confidence_values
                )
                / len(
                    confidence_values
                )
            )

            if average_confidence >= 0.8:

                reasons.append(
                    (
                        average_confidence
                        * 100000,
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

    def generate_why_not(
        self,
        result,
    ):

        reasons = []

        player_level = self.player_level()
        mob_level = int(
            result["mob_level"]
        )

        level_difference = abs(
            mob_level
            - player_level
        )

        if level_difference >= 7:

            reasons.append(
                (
                    level_difference,
                    "The mob is relatively far from your level."
                )
            )

        if result[
            "seconds_per_kill"
        ] >= 20:

            reasons.append(
                (
                    result[
                        "seconds_per_kill"
                    ],
                    "Kill time is relatively slow."
                )
            )

        if result[
            "survival_rate"
        ] < 0.8:

            reasons.append(
                (
                    100
                    - result[
                        "survival_rate"
                    ] * 100,
                    "Estimated survival rate is low."
                )
            )

        if result[
            "expected_value_per_kill"
        ] < 10:

            reasons.append(
                (
                    10
                    - result[
                        "expected_value_per_kill"
                    ],
                    "Expected value per kill is low."
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

                if drop.get(
                    "confidence",
                    0,
                ) < 0.5:

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

    def evaluate_mob(
        self,
        mob,
    ):

        if not self.is_mob_eligible(
            mob
        ):
            return None

        profiles = mob.get(
            "drop_profiles",
            [],
        )

        if not profiles:
            return None

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
            / seconds
        )

        gross_per_hour = (
            value_per_kill
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
            "mob_level": mob.get(
                "level",
                0,
            ),
            "hp": mob.get(
                "hp",
                0,
            ),
            "damage_min": mob.get(
                "damage_min",
                0,
            ),
            "damage_max": mob.get(
                "damage_max",
                0,
            ),
            "zone": best_profile[
                "zone"
            ],
            "profile": best_profile[
                "profile"
            ],
            "seconds_per_kill": seconds,
            "kills_per_hour": expected_kills_per_hour,
            "survival_rate": survival,
            "expected_value_per_kill": value_per_kill,
            "expected_coins_per_hour": gross_per_hour,
            "profile_results": profile_results,
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

        for mob in self.mobs:

            result = self.evaluate_mob(
                mob
            )

            if result is not None:

                results.append(
                    result
                )

        results.sort(
            key=lambda result:
                result[
                    "expected_coins_per_hour"
                ],
            reverse=True,
        )

        result_count = int(
            self.config.get(
                "results",
                15,
            )
        )

        return results[
            :result_count
        ]