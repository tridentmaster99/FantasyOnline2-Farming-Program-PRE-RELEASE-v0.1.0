from datetime import datetime
from pathlib import Path


def money(value):
    return f"{value:,.0f}"


def generate_report(
    player,
    results,
    output_path
):

    path = Path(
        output_path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    lines = []

    lines.append(
        "=" * 72
    )

    lines.append(
        "             FANTASY ONLINE 2 FARM OPTIMIZER"
    )

    lines.append(
        "=" * 72
    )

    lines.append(
        "Generated: "
        + datetime.now().strftime( 
    "R%d.%m.%y--%H-%M-%S.%f"
        )[:-3]
    )

    lines.append(
        f"Player level: {player.level}"
    )

    lines.append(
        f"Goal: {player.settings.get('goal', 'profit')}"
    )

    lines.append("")

    lines.append(
        "EQUIPMENT"
    )

    for item in player.stats.get(
        "equipped_items",
        []
    ):

        lines.append(
            f"  {item['slot']}: "
            f"{item['item']}"
        )

    lines.append("")

    unresolved = player.stats.get(
        "unresolved",
        []
    )

    if unresolved:

        lines.append(
            "UNRESOLVED EQUIPMENT"
        )

        for item in unresolved:

            lines.append(
                f"  {item['slot']}: "
                f"{item['item']}"
            )

        lines.append("")

    stats = player.stats.get(
        "stats",
        {}
    )

    if stats:

        lines.append(
            "CALCULATED PLAYER STATS"
        )

        for stat, value in sorted(
            stats.items()
        ):

            if float(value).is_integer():

                value = int(value)

            lines.append(
                f"  {stat}: {value}"
            )

        lines.append("")

    lines.append(
        "=" * 72
    )

    lines.append(
        "TOP FARMING TARGETS"
    )

    lines.append(
        "=" * 72
    )

    if not results:

        lines.extend([
            "",
            "No valid farming targets found."
        ])

    for index, result in enumerate(
        results,
        1
    ):

        lines.append("")

        lines.append(
            f"#{index}  {result.mob}"
        )

        lines.append(
            f"Zone: {result.zone}"
        )

        lines.append(
            f"Score: {result.score:.3f}"
        )

        lines.append(
            f"Profit/hour: "
            f"{money(result.profit_per_hour)}"
        )

        lines.append(
            f"Profit/kill: "
            f"{money(result.profit_per_kill)}"
        )

        lines.append(
            f"XP/hour: "
            f"{money(result.xp_per_hour)}"
        )

        lines.append(
            f"Kills/hour: "
            f"{result.kills_per_hour:.1f}"
        )

        lines.append(
            f"Survival: "
            f"{result.survival_rate * 100:.1f}%"
        )

        lines.append(
            f"Market confidence: "
            f"{result.confidence * 100:.1f}%"
        )

        if result.warnings:

            lines.append(
                "Warnings:"
            )

            for warning in result.warnings:

                lines.append(
                    f"  - {warning}"
                )

        if result.drop_breakdown:

            lines.append(
                "Valuable drops:"
            )

            sorted_drops = sorted(
                result.drop_breakdown,
                key=lambda x: x[
                    "expected_value"
                ],
                reverse=True
            )

            for drop in sorted_drops[:10]:

                lines.append(
                    f"  - {drop['name']}: "
                    f"{drop['chance'] * 100:.3f}% "
                    f"| {money(drop['market_price'])} "
                    f"| ~{money(drop['expected_value'])}/kill"
                )

        lines.append(
            "-" * 72
        )

    path.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )