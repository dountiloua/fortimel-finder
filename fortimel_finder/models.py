from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ProductVariant(str, Enum):
    POWDER_335G = "powder_335g"
    POWDER_400G = "powder_400g"
    POWDER_800G = "powder_800g"
    RTD_200ML = "rtd_200ml"
    RTD_400ML = "rtd_400ml"
    COMPACT_125ML = "compact_125ml"
    COMPACT_PROTEIN = "compact_protein"
    UNKNOWN = "unknown"


class Flavor(str, Enum):
    VANILLA = "vanilla"
    CHOCOLATE = "chocolate"
    STRAWBERRY = "strawberry"
    BANANA = "banana"
    COFFEE = "coffee"
    NEUTRAL = "neutral"
    FRUITS = "fruits"
    CAPPUCCINO = "cappuccino"
    UNKNOWN = "unknown"


@dataclass
class Product:
    name: str
    variant: ProductVariant = ProductVariant.UNKNOWN
    flavor: Flavor = Flavor.UNKNOWN
    size: str = ""
    brand: str = "Nutricia"
    description: str = ""


@dataclass
class Offer:
    product: Product
    source_name: str
    source_url: str
    price: float
    currency: str
    price_local: Optional[float] = None
    currency_local: str = "DZD"
    in_stock: bool = True
    shipping_available: Optional[bool] = None
    shipping_cost: Optional[float] = None
    shipping_currency: str = "EUR"
    shipping_days: Optional[str] = None
    ships_to_algeria: bool = False
    seller_rating: Optional[float] = None
    review_count: int = 0
    reliability_score: float = 5.0
    notes: list[str] = field(default_factory=list)
    search_url: str = ""

    @property
    def total_cost_eur(self) -> Optional[float]:
        if self.price is None:
            return None
        total = self.price
        if self.shipping_cost:
            total += self.shipping_cost
        return total

    @property
    def total_cost_local(self) -> Optional[float]:
        local = self.price_local if self.price_local else self.price
        if local is None:
            return None
        if self.shipping_cost:
            return local + self.shipping_cost
        return local


@dataclass
class SearchResult:
    query: str
    offers: list[Offer]
    errors: list[str] = field(default_factory=list)
    search_duration: float = 0.0
    sources_searched: int = 0
    sources_succeeded: int = 0
