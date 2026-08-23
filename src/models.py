from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Item:
    id: int
    name: str
    url: str = ""
    description: str = ""
    level_requirement: int = 0
    type_id: int = 0
    subtype_id: int = 0
    stats: dict = field(default_factory=dict)


@dataclass
class MarketOrder:
    order_id: int
    item_id: int
    price: int
    quantity: int
    listed: int
    duration: int = 0
    level_requirement: int = 0
    type_id: int = 0
    subtype_id: int = 0


@dataclass
class MarketData:
    item_id: int
    name: str
    lowest: Optional[int]
    median: Optional[float]
    average: Optional[float]
    highest: Optional[int]
    order_count: int
    total_quantity: int
    confidence: float


@dataclass
class Drop:
    item_id: int
    chance: float
    quantity: float = 1.0
    source: str = "database"


@dataclass
class Mob:
    id: int
    name: str
    url: str = ""
    level: int = 0
    hp: int = 0
    damage_min: int = 0
    damage_max: int = 0
    xp: int = 0
    coin_min: int = 0
    coin_max: int = 0
    zones: list[str] = field(default_factory=list)
    drops: list[Drop] = field(default_factory=list)
    is_boss: bool = False
    is_elite: bool = False


@dataclass
class Player:
    level: int
    equipment: dict
    settings: dict
    stats: dict = field(default_factory=dict)


@dataclass
class FarmingResult:
    mob_id: int
    mob: str
    zone: str
    score: float
    profit_per_kill: float
    profit_per_hour: float
    xp_per_kill: float
    xp_per_hour: float
    kills_per_hour: float
    drop_value: float
    coin_value: float
    survival_rate: float
    confidence: float
    warnings: list[str] = field(
        default_factory=list
    )
    drop_breakdown: list[dict] = field(
        default_factory=list
    )