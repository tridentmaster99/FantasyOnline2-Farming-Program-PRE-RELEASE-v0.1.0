============================================================
             FANTASY ONLINE 2 FARMING OPTIMIZER
============================================================

A local farming optimizer for Fantasy Online 2.

The program uses:
- Your player level
- Your equipped gear
- Your calculated player stats
- The local FO2 database
- Current market prices
- Mob levels
- Mob HP and damage
- Drop chances
- Drop values
- Zone-specific drop profiles
- Your selected optimization goal

The program then calculates which mobs are currently the best
targets to farm.
============================================================
2. FIRST SETUP
============================================================

Make sure Python is installed.

Open PowerShell in the FantasyFarmOptimizer folder.

Install the required packages:

    pip install -r requirements.txt


============================================================
3. PLAYER SETUP
============================================================

The player is configured in:

    player.json

You must provide your player level and equipment.

The optimizer supports equipment slots such as:

    helmet
    body armor
    leg armor
    weapon
    offhand
    ring 1
    ring 2
    trinket 1
    trinket 2
    left arm implant
    right arm implant
    brain implant
    heart implant
    left leg implant
    right leg implant
    mount
    relic
    guild
    faction

The exact structure should follow the current player.json format
used by the program.

The optimizer calculates the player's stats from the equipped
items whenever their database information is available.

If an item cannot be resolved, it will be reported as unresolved
equipment instead of silently pretending that its stats exist.


============================================================
4. UPDATING THE DATABASE
============================================================

The local database contains the FO2 items and mobs.

Database website:

    https://db.fantasyonline2.com

To update the local database, run:

    python main.py --update-db

This downloads the current database information and stores it
locally in:

    data/game/items.json
    data/game/mobs.json

The database update can take some time because many individual
pages may need to be downloaded.

You should update the database when:

- New items are added to FO2
- New mobs are added
- Mob drops change
- Item stats change
- You notice information appears outdated


============================================================
5. UPDATING MARKET DATA
============================================================

The optimizer uses current market information to determine the
value of drops.

To manually update market data:

    python main.py --update-market

The market data is stored in:

    data/market.json

Normally you do not need to manually update it every time.

The program has a market cache controlled by:

    market_cache_minutes

in config.json.

If the cached market data is still considered fresh, the
optimizer can use it instead of downloading the market again.


============================================================
6. FORCING A MARKET UPDATE
============================================================

If you want completely fresh market data, run:

    python main.py --force-market

This ignores the normal market cache and requests fresh market
information.


============================================================
7. RUNNING THE OPTIMIZER
============================================================

To run the optimizer:

    python main.py

You can also explicitly use:

    python main.py --optimize

The program will:

1. Load your player.json
2. Load the local item database
3. Load the local mob database
4. Load current market data
5. Calculate your player stats
6. Check which mobs are eligible
7. Calculate drop values
8. Calculate expected value per kill
9. Estimate kills per hour
10. Apply survival rate
11. Rank farming targets
12. Create the recommendation report


============================================================
8. RECOMMENDATION FILE
============================================================

The recommendation is written according to:

    config.json

Currently:

    file_logs/recommendation.txt

The recommendation contains information such as:

- Player level
- Calculated player stats
- Unresolved equipment
- Recommended farming targets
- Mob level
- Zone
- Mob HP
- Mob damage
- Estimated kill time
- Estimated kills per hour
- Survival rate
- Expected value per kill
- Expected profit per hour
- Valuable drops
- Market prices
- Drop chances


============================================================
9. CONFIGURATION
============================================================

The main configuration file is:

    config.json

Current structure:

    {
      "api": {
        "base_url": "https://fantasyonline2.com/api/public",
        "timeout_seconds": 15,
        "market_cache_minutes": 5,
        "requests_per_10_seconds": 5
      },

      "database": {
        "base_url": "https://db.fantasyonline2.com",
        "request_delay_seconds": 0.25,
        "max_pages": 100
      },

      "optimizer": {
        "goal": "profit",
        "results": 15,
        "max_level_difference": 10,
        "include_elites": true,
        "include_bosses": true,
        "market_confidence_floor": 0.2,
        "sell_discount": 0.95
      },

      "combat": {
        "default_seconds_per_kill": 10.0,
        "default_survival_rate": 0.95
      },

      "output": {
        "file": "file_logs/recommendation.txt"
      }
    }


============================================================
10. OPTIMIZER SETTINGS
============================================================

goal

Controls what the optimizer tries to prioritize.

Current:

    "goal": "profit"

The current implementation is primarily designed around profit.

Additional optimization goals may be added in future versions.

Do not use a goal that the current optimizer code does not
support.


------------------------------------------------------------

results

Number of farming targets shown.

Example:

    "results": 15

means the report will contain the top 15 results.


------------------------------------------------------------

max_level_difference

Controls how far a mob's level may be from the player's level.

Example:

    "max_level_difference": 10

If the player is level 50, mobs more than 10 levels away can be
excluded.


------------------------------------------------------------

include_elites

Controls whether elite mobs are allowed.

    true

or:

    false


------------------------------------------------------------

include_bosses

Controls whether boss mobs are allowed.

    true

or:

    false


------------------------------------------------------------

market_confidence_floor

Controls the minimum market confidence accepted by the optimizer.

Example:

    "market_confidence_floor": 0.2

means market information with confidence below 20% is ignored.


------------------------------------------------------------

sell_discount

Represents the percentage of the listed market price that the
optimizer assumes can realistically be received.

Example:

    "sell_discount": 0.95

means the optimizer uses 95% of the market price.


============================================================
11. COMBAT SETTINGS
============================================================

default_seconds_per_kill

Fallback kill time when the program cannot calculate a more
specific value.

Example:

    "default_seconds_per_kill": 10.0


------------------------------------------------------------

default_survival_rate

Fallback survival probability.

Example:

    "default_survival_rate": 0.95

means the optimizer assumes a 95% survival rate.

The value must be between:

    0.0 and 1.0


============================================================
12. DATABASE SETTINGS
============================================================

base_url

The FO2 database website:

    https://db.fantasyonline2.com


------------------------------------------------------------

request_delay_seconds

Delay between database requests.

Increasing this value makes requests slower but reduces the
request frequency.

Example:

    "request_delay_seconds": 0.25


------------------------------------------------------------

max_pages

Maximum number of pages the updater is allowed to process.

Example:

    "max_pages": 100

Do not reduce this unless you intentionally want an incomplete
database.


============================================================
13. API SETTINGS
============================================================

base_url

The public Fantasy Online 2 API:

    https://fantasyonline2.com/api/public


------------------------------------------------------------

timeout_seconds

Maximum time the program waits for an API request.

Example:

    "timeout_seconds": 15


------------------------------------------------------------

market_cache_minutes

How long market information can remain cached before a new market
request is normally required.

Example:

    "market_cache_minutes": 5


------------------------------------------------------------

requests_per_10_seconds

Maximum configured request rate for the market API.

Example:

    "requests_per_10_seconds": 5


============================================================
14. MARKET FAILURES
============================================================

If the market API is temporarily unavailable, market information
may be unavailable or incomplete.

Do not immediately assume that the database is broken.

Try:

    python main.py --force-market

If the problem continues:

1. Check your internet connection.
2. Check that Fantasy Online 2 is online.
3. Check that the API is responding.
4. Try again later.

The optimizer should not invent market prices when real market
information is unavailable.


============================================================
15. DATABASE VS MARKET
============================================================

These are two different data sources.

DATABASE:

    https://db.fantasyonline2.com

Contains game information such as:

- Items
- Item stats
- Mobs
- Mob HP
- Mob damage
- XP
- Coins
- Drop chances
- Drop profiles
- Zones


MARKET:

    https://fantasyonline2.com/api/public

Contains current market information used to estimate the value
of items.


You may therefore need to update both separately.


============================================================
16. IMPORTANT: DROP PROFILES
============================================================

Some mobs have different drops depending on the zone.

For example, the same mob can have:

    Gemster's Shop
    Hidden Reef
    Noob Island
    Whispering Wilds

with different drop tables.

The optimizer evaluates these profiles separately and chooses the
most valuable available profile.

This is important because farming the same mob in a different zone
can produce a completely different expected value.


============================================================
17. MARKET PRICES AND UNSELLABLE ITEMS
============================================================

The optimizer attempts to value drops using market information.

If an item has no usable market information, its market value is
not treated as reliable.

Do not manually enter market prices into the game database.

Manual price overrides, when supported, belong in:

    data/overrides/item_prices.json


============================================================
18. DATA FILES
============================================================

Do not normally edit these files manually:

    data/game/items.json
    data/game/mobs.json
    data/market.json

They are generated/updated by the program.

Manual modifications may be overwritten during an update.


============================================================
19. COMMON COMMANDS
============================================================

Normal optimization:

    python main.py

Explicit optimization:

    python main.py --optimize

Update database:

    python main.py --update-db

Update market:

    python main.py --update-market

Force fresh market:

    python main.py --force-market


============================================================
20. RECOMMENDED WORKFLOW
============================================================

After installing the program for the first time:

    1. Configure player.json
    2. Run:
           python main.py --update-db

    3. Run:
           python main.py --update-market

    4. Run:
           python main.py

After normal game updates:

    1. Update the database:
           python main.py --update-db

    2. Run the optimizer:
           python main.py

The optimizer will use the market cache according to the
configuration.

If you specifically want fresh market prices:

    python main.py --force-market


============================================================
21. TROUBLESHOOTING
============================================================

"items.json is missing."

Run:

    python main.py --update-db


"mobs.json is missing."

Run:

    python main.py --update-db


"player.json is missing."

Create player.json in the main FantasyFarmOptimizer folder.


Market information appears old:

Run:

    python main.py --force-market


Database information appears old:

Run:

    python main.py --update-db


The program reports unresolved equipment:

Check that:

- The item exists in the database.
- The item name/ID in player.json is correct.
- The local database has been updated.


No farming targets are found:

Check:

- Player level
- max_level_difference
- include_elites
- include_bosses
- Database contents
- Drop profiles
- Market confidence
- Market availability


============================================================
22. DO NOT DELETE THESE FILES
============================================================

Do not delete:

    config.json
    player.json
    data/game/items.json
    data/game/mobs.json

unless you intentionally want to rebuild the data.

The cache and generated files can generally be rebuilt by the
program, but deleting files should be done intentionally.


============================================================
23. UPDATES
============================================================

When a new version of the optimizer is released, update the
program files while keeping your personal configuration and
player information.

Important personal files include:

    config.json
    player.json
    data/overrides/item_prices.json


============================================================
24. QUICK START
============================================================

Open PowerShell in:

    FantasyFarmOptimizer

Then run:

    python main.py --update-db

After the database finishes:

    python main.py --update-market

Then:

    python main.py

Open the generated recommendation file in:

    file_logs/


============================================================
                 END OF README
============================================================
