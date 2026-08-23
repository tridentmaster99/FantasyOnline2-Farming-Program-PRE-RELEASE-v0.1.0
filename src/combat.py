def estimate_kills_per_hour(
    player,
    mob,
    seconds_per_kill=None
):
    if seconds_per_kill is None:
        seconds_per_kill = player.settings.get(
            "seconds_per_kill",
            10
        )

    seconds_per_kill = max(
        float(seconds_per_kill),
        0.1
    )

    return 3600 / seconds_per_kill


def estimate_survival(player):
    return float(
        player.settings.get(
            "survival_rate",
            0.95
        )
    )