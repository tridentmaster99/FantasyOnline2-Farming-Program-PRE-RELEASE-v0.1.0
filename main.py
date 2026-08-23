import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from src.database import FO2Database
from src.market import MarketClient
from src.optimizer import FarmingOptimizer
from src.output import write_recommendation
from src.equipment import EquipmentCalculator


# =========================================================
# PATHS
# =========================================================

ROOT = Path(__file__).resolve().parent

CONFIG_FILE = ROOT / "config.json"
PLAYER_FILE = ROOT / "player.json"

ITEMS_FILE = ROOT / "data" / "game" / "items.json"
MOBS_FILE = ROOT / "data" / "game" / "mobs.json"
MARKET_FILE = ROOT / "data" / "market.json"

FILE_LOGS_DIR = ROOT / "file_logs"


# =========================================================
# LOAD JSON
# =========================================================

def load_json(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing file: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


# =========================================================
# PLAYER OBJECT
# =========================================================

class Player:

    def __init__(
        self,
        data,
    ):
        self.level = int(
            data.get(
                "level",
                1,
            )
        )

        self.equipment = data.get(
            "equipment",
            {}
        )


# =========================================================
# CONFIG
# =========================================================

def load_config():
    return load_json(CONFIG_FILE)


# =========================================================
# RECOMMENDATION LOG PATH
# =========================================================

def create_recommendation_path():

    now = datetime.now()

    date_folder = now.strftime(
        "%d.%m.%y"
    )

    timestamp = now.strftime(
        "%d.%m.%y--%H-%M-%S.%f"
    )[:-3]

    folder = (
        FILE_LOGS_DIR
        / date_folder
    )

    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    return (
        folder
        / f"R{timestamp}.txt"
    )


# =========================================================
# DATABASE UPDATE
# =========================================================

def update_database():

    config = load_config()

    database_config = config.get(
        "database",
        {},
    )

    database = FO2Database(
        base_url=database_config.get(
            "base_url",
            "https://db.fantasyonline2.com",
        ),
        cache_directory=(
            ROOT
            / "data"
            / "game"
        ),
        delay=database_config.get(
            "request_delay_seconds",
            0.25,
        ),
        max_pages=database_config.get(
            "max_pages",
            100,
        ),
    )

    database.update_all(
        force=True
    )


# =========================================================
# MARKET UPDATE
# =========================================================

def update_market():

    config = load_config()

    api_config = config.get(
        "api",
        {}
    )

    market = MarketClient(
        base_url=api_config.get(
            "base_url",
            "https://fantasyonline2.com/api/public",
        ),
        timeout_seconds=api_config.get(
            "timeout_seconds",
            15,
        ),
        cache_minutes=api_config.get(
            "market_cache_minutes",
            5,
        ),
        requests_per_10_seconds=api_config.get(
            "requests_per_10_seconds",
            5,
        ),
    )

    print(
        "Updating current market..."
    )

    market.update_cache(
        cache_file=str(
            MARKET_FILE
        ),
        max_pages=100,
    )

    print(
        "Market update complete."
    )


# =========================================================
# OPTIMIZE
# =========================================================

def optimize(
    force_market=False,
):

    config = load_config()

    if not ITEMS_FILE.exists():

        print(
            "items.json is missing."
        )

        print(
            "Run:"
        )

        print(
            "  python main.py --update-db"
        )

        return 1

    if not MOBS_FILE.exists():

        print(
            "mobs.json is missing."
        )

        print(
            "Run:"
        )

        print(
            "  python main.py --update-db"
        )

        return 1

    if not PLAYER_FILE.exists():

        print(
            "player.json is missing."
        )

        return 1

    items = load_json(
        ITEMS_FILE
    )

    mobs = load_json(
        MOBS_FILE
    )

    player_data = load_json(
        PLAYER_FILE
    )

    player = Player(
        player_data
    )

    api_config = config.get(
        "api",
        {}
    )

    market = MarketClient(
        base_url=api_config.get(
            "base_url",
            "https://fantasyonline2.com/api/public",
        ),
        timeout_seconds=api_config.get(
            "timeout_seconds",
            15,
        ),
        cache_minutes=api_config.get(
            "market_cache_minutes",
            5,
        ),
        requests_per_10_seconds=api_config.get(
            "requests_per_10_seconds",
            5,
        ),
    )

    market_data = market.get_market(
        cache_file=str(
            MARKET_FILE
        ),
        max_pages=100,
        force_refresh=force_market,
    )

    equipment_calculator = EquipmentCalculator(
        items
    )

    optimizer_config = config.get(
        "optimizer",
        {}
    )

    combat_config = config.get(
        "combat",
        {}
    )

    merged_optimizer_config = {
        **optimizer_config,
        **combat_config,
    }

    optimizer = FarmingOptimizer(
        items=items,
        mobs=mobs,
        market=market_data,
        player=player,
        equipment_calculator=equipment_calculator,
        config=merged_optimizer_config,
    )

    print()
    print(
        "Calculating farming targets..."
    )

    results = optimizer.optimize()

    output_path = create_recommendation_path()

    write_recommendation(
        results=results,
        player=player,
        player_stats=optimizer.player_stats,
        output_file=str(output_path),
        database_file=ITEMS_FILE,
        market_file=MARKET_FILE,
        config=config,
    )

    print()
    print(
        "OPTIMIZATION COMPLETE"
    )

    print(
        f"Results: {len(results)}"
    )

    print(
        f"Output: {output_path}"
    )

    if results:

        print()
        print(
            "BEST TARGET:"
        )

        best = results[0]

        print(
            f"  {best['mob_name']}"
        )

        print(
            f"  Zone: {best['zone']}"
        )

        print(
            f"  Profit/hour: "
            f"{best['expected_coins_per_hour']:.0f}"
        )

    return 0


# =========================================================
# CLI
# =========================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Fantasy Online 2 "
            "Farming Optimizer"
        )
    )

    parser.add_argument(
        "--update-db",
        action="store_true",
        help="Update the local FO2 database",
    )

    parser.add_argument(
        "--update-market",
        action="store_true",
        help="Download current broker market data",
    )

    parser.add_argument(
        "--force-market",
        action="store_true",
        help="Ignore market cache and download fresh data",
    )

    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Calculate the best mobs to farm",
    )

    args = parser.parse_args()

    try:

        if args.update_db:
            update_database()
            return 0

        if args.update_market:
            update_market()
            return 0

        if (
            args.optimize
            or not (
                args.update_db
                or args.update_market
            )
        ):

            return optimize(
                force_market=args.force_market
            )

        return 0

    except KeyboardInterrupt:

        print(
            "\nCancelled."
        )

        return 130

    except Exception as error:

        print()
        print(
            "ERROR:"
        )

        print(
            str(error)
        )

        return 1


if __name__ == "__main__":
    sys.exit(
        main()
    )