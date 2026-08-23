def expected_drop_value(mob, market):
    total = 0.0

    breakdown = []

    for drop in mob.drops:

        market_item = market.get(drop.item_id)

        if not market_item:
            continue

        if market_item.median is None:
            continue

        expected_quantity = (
            drop.chance *
            drop.quantity
        )

        value = (
            expected_quantity *
            market_item.median *
            market_item.confidence
        )

        total += value

        breakdown.append({
            "item_id": drop.item_id,
            "name": market_item.name,
            "chance": drop.chance,
            "expected_quantity": expected_quantity,
            "market_price": market_item.median,
            "confidence": market_item.confidence,
            "expected_value": value
        })

    return total, breakdown