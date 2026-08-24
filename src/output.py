from datetime import datetime
from pathlib import Path


def format_money(value):

    value = float(
        value or 0
    )

    if value >= 1_000_000_000:
        return (
            f"{value / 1_000_000_000:.2f}B"
        )

    if value >= 1_000_000:
        return (
            f"{value / 1_000_000:.2f}M"
        )

    if value >= 1_000:
        return (
            f"{value / 1_000:.2f}K"
        )

    return f"{value:.0f}"


def get_file_age(path):

    if not path.exists():
        return None

    modified = datetime.fromtimestamp(
        path.stat().st_mtime
    )

    return datetime.now() - modified


def age_string(delta):

    if delta is None:
        return "unknown"

    seconds = int(
        delta.total_seconds()
    )

    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60

    if minutes < 60:
        return f"{minutes}m"

    hours = minutes // 60

    if hours < 24:
        return f"{hours}h"

    days = hours // 24

    return f"{days}d"


def write_recommendation(
    results,
    player,
    player_stats,
    output_file,
    database_file=None,
    market_file=None,
    config=None,
):

    config = config or {}

    path = Path(
        output_file
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    lines = []

    generated = datetime.now()

    lines.append(
        "=" * 70
    )

    lines.append(
        "FANTASY ONLINE 2 FARMING OPTIMIZER"
    )

    lines.append(
        "=" * 70
    )

    lines.append(
        ""
    )

    lines.append(
        "Generated:"
    )

    lines.append(
        datetime.now().strftime(
    "R%d.%m.%y--%H-%M-%S.%f"
    )[:-3]
    )
    lines.append(
        ""
    )

    lines.append(
        f"Player level: {player.level}"
    )

    optimizer_config = config.get(
        "optimizer",
        {}
    )

    lines.append(
        "Goal: "
        + str(
            optimizer_config.get(
                "goal",
                "profit"
            )
        )
    )

    # =========================================================
    # DATABASE AGE
    # =========================================================

    lines.append("")

    lines.append(
        "DATA STATUS"
    )

    lines.append(
        "-" * 70
    )

    if database_file:

        database_path = Path(
            database_file
        )

        database_age = get_file_age(
            database_path
        )

        if database_age is None:

            lines.append(
                "WARNING: Local database "
                "file was not found."
            )

        else:

            lines.append(
                "Database age: "
                + age_string(
                    database_age
                )
            )

            if database_age.total_seconds() > (
                7 * 24 * 60 * 60
            ):

                lines.append(
                    "WARNING: Database is older "
                    "than 7 days."
                )

            elif database_age.total_seconds() > (
                24 * 60 * 60
            ):

                lines.append(
                    "NOTICE: Database is older "
                    "than 24 hours."
                )

            else:

                lines.append(
                    "Database status: Recent"
                )

    if market_file:

        market_path = Path(
            market_file
        )

        market_age = get_file_age(
            market_path
        )

        if market_age is None:

            lines.append(
                "WARNING: Market cache "
                "was not found."
            )

        else:

            lines.append(
                "Market cache age: "
                + age_string(
                    market_age
                )
            )

            if market_age.total_seconds() > (
                60 * 60
            ):

                lines.append(
                    "WARNING: Market data "
                    "is older than 1 hour."
                )

    # =========================================================
    # PLAYER STATS
    # =========================================================

    lines.append("")

    lines.append(
        "CALCULATED PLAYER STATS"
    )

    lines.append(
        "-" * 70
    )

    stats = player_stats.get(
        "stats",
        {}
    )

    if stats:

        for key in sorted(
            stats.keys()
        ):

            try:
                value = stats[key]

                if float(
                    value
                ).is_integer():

                    value = int(
                        value
                    )

                lines.append(
                    f"  {key}: {value}"
                )

            except (
                TypeError,
                ValueError,
            ):

                lines.append(
                    f"  {key}: {stats[key]}"
                )

    else:

        lines.append(
            "  No numerical equipment "
            "stats were resolved."
        )

    # =========================================================
    # UNRESOLVED EQUIPMENT
    # =========================================================

    unresolved = player_stats.get(
        "unresolved",
        []
    )

    if unresolved:

        lines.append("")

        lines.append(
            "UNRESOLVED EQUIPMENT"
        )

        for item in unresolved:

            lines.append(
                f"  {item['slot']}: "
                f"{item['item']}"
            )

    # =========================================================
    # RESULTS
    # =========================================================

    lines.append("")

    lines.append(
        "BEST FARMING TARGETS"
    )

    lines.append(
        "-" * 70
    )

    if not results:

        lines.append(
            "No eligible mobs found."
        )

    for index, result in enumerate(
        results,
        1,
    ):

        lines.append("")

        lines.append(
            f"#{index} "
            f"{result['mob_name']}"
        )

        lines.append(
            f"  Level: "
            f"{result['mob_level']}"
        )

        lines.append(
            f"  Zone: "
            f"{result['zone']}"
        )

        lines.append(
            f"  HP: "
            f"{result['hp']}"
        )

        lines.append(
            f"  Damage: "
            f"{result['damage_min']}"
            f"-"
            f"{result['damage_max']}"
        )

        lines.append(
            f"  Estimated kill time: "
            f"{result['seconds_per_kill']:.1f}s"
        )

        lines.append(
            f"  Estimated kills/hour: "
            f"{result['kills_per_hour']:.1f}"
        )

        lines.append(
            f"  Survival rate: "
            f"{result['survival_rate'] * 100:.1f}%"
        )

        lines.append(
            f"  Expected value/kill: "
            f"{format_money(result['expected_value_per_kill'])}"
        )

        lines.append(
            f"  Expected profit/hour: "
            f"{format_money(result['expected_coins_per_hour'])}"
        )

        # =====================================================
        # WHY
        # =====================================================

        why = result.get(
            "why",
            []
        )

        if why:

            lines.append("")

            lines.append(
                "  WHY THIS IS RECOMMENDED:"
            )

            for reason in why[:4]:

                lines.append(
                    f"    + {reason}"
                )

        # =====================================================
        # WHY NOT
        # =====================================================

        why_not = result.get(
            "why_not",
            []
        )

        if why_not:

            lines.append("")

            lines.append(
                "  WHY IT MAY NOT BE IDEAL:"
            )

            for reason in why_not[:4]:

                lines.append(
                    f"    - {reason}"
                )

        # =====================================================
        # DROP BREAKDOWN
        # =====================================================

        best_profile = None

        for profile in result.get(
            "profile_results",
            [],
        ):

            if (
                profile.get("profile")
                == result.get("profile")
            ):

                best_profile = profile
                break

        if best_profile:

            drops = best_profile.get(
                "drops",
                []
            )

            if drops:

                lines.append("")

                lines.append(
                    "  DROP VALUE BREAKDOWN:"
                )

                sorted_drops = sorted(
                    drops,
                    key=lambda drop:
                        drop.get(
                            "expected_value",
                            0,
                        ),
                    reverse=True,
                )

                for drop in sorted_drops[:10]:

                    sellable = (
                        "SELLABLE"
                        if drop.get(
                            "sellable",
                            False
                        )
                        else "UNSELLABLE"
                    )

                    lines.append(
                        "    - "
                        f"{drop['item_name']}: "
                        f"{drop['chance'] * 100:.3f}% "
                        f"x{drop['quantity']:.0f} "
                        f"| Market: "
                        f"{format_money(drop['market_price'])} "
                        f"| Expected: "
                        f"{format_money(drop['expected_value'])}/kill "
                        f"| {sellable}"
                    )

                unsellable = (
                    best_profile.get(
                        "unsellable_drops",
                        []
                    )
                )

                if unsellable:

                    lines.append(
                        "  FILTERED UNSSELLABLE DROPS:"
                    )

                    unique_names = set()

                    for drop in unsellable:

                        name = drop[
                            "item_name"
                        ]

                        if name in unique_names:
                            continue

                        unique_names.add(
                            name
                        )

                        lines.append(
                            f"    - {name}"
                        )

        lines.append(
            "-" * 70
        )

    lines.append("")

    lines.append(
        "Market prices are based on "
        "current broker data and the configured "
        "sell discount."
    )

    lines.append(
        "=" * 70
    )

    path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    return path