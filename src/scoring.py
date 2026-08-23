def normalize(value, maximum):
    if maximum <= 0:
        return 0

    return value / maximum


def calculate_scores(results, goal="profit"):

    if not results:
        return []

    max_profit = max(
        r.profit_per_hour
        for r in results
    )

    max_xp = max(
        r.xp_per_hour
        for r in results
    )

    for result in results:

        profit_score = normalize(
            result.profit_per_hour,
            max_profit
        )

        xp_score = normalize(
            result.xp_per_hour,
            max_xp
        )

        if goal == "xp":
            score = xp_score

        elif goal == "balanced":
            score = (
                profit_score * 0.5
                + xp_score * 0.5
            )

        else:
            score = profit_score

        result.score = score

    results.sort(
        key=lambda x: x.score,
        reverse=True
    )

    return results