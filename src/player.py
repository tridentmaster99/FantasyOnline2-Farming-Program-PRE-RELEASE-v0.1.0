import json

from .models import Player


SINGLE_SLOTS = [
    "helmet",
    "body",
    "legs",
    "weapon",
    "offhand",
    "mount",
    "relic",
    "guild",
    "faction"
]

MULTI_SLOTS = [
    "rings",
    "trinkets"
]

IMPLANT_SLOTS = [
    "left_arm",
    "right_arm",
    "brain",
    "heart",
    "left_leg",
    "right_leg"
]


def load_player(path="player.json"):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    level = int(
        data.get("level", 1)
    )

    if level < 1:
        raise ValueError(
            "Player level must be at least 1."
        )

    equipment = data.get(
        "equipment",
        {}
    )

    # Make sure every single slot exists.
    for slot in SINGLE_SLOTS:

        equipment.setdefault(
            slot,
            None
        )

    # Make sure multiple-item slots exist
    # and contain exactly two positions.
    for slot in MULTI_SLOTS:

        value = equipment.get(
            slot,
            [None, None]
        )

        if value is None:
            value = [None, None]

        if not isinstance(value, list):
            raise ValueError(
                f"'{slot}' must be an array."
            )

        while len(value) < 2:
            value.append(None)

        if len(value) > 2:
            raise ValueError(
                f"'{slot}' can contain "
                f"maximum 2 items."
            )

        equipment[slot] = value

    # Validate implants.
    implants = equipment.get(
        "implants",
        {}
    )

    if implants is None:
        implants = {}

    if not isinstance(implants, dict):
        raise ValueError(
            "'implants' must be an object."
        )

    for slot in IMPLANT_SLOTS:

        implants.setdefault(
            slot,
            None
        )

    equipment["implants"] = implants

    settings = data.get(
        "settings",
        {}
    )

    return Player(
        level=level,
        equipment=equipment,
        settings=settings,
        stats={}
    )


def flatten_equipment(equipment):

    result = []

    # Normal single equipment slots.
    for slot in SINGLE_SLOTS:

        item = equipment.get(
            slot
        )

        if item:
            result.append({
                "slot": slot,
                "item": item
            })

    # Rings and trinkets.
    for slot in MULTI_SLOTS:

        items = equipment.get(
            slot,
            []
        )

        for index, item in enumerate(
            items,
            1
        ):

            if item:

                result.append({
                    "slot": f"{slot}_{index}",
                    "base_slot": slot,
                    "index": index,
                    "item": item
                })

    # Implants.
    implants = equipment.get(
        "implants",
        {}
    )

    for slot in IMPLANT_SLOTS:

        item = implants.get(
            slot
        )

        if item:

            result.append({
                "slot": f"implant_{slot}",
                "base_slot": "implants",
                "implant_slot": slot,
                "item": item
            })

    return result