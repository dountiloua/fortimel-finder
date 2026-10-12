from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SourceResult:
    name: str
    url: str
    title: str
    price_text: str
    price: float | None
    currency: str | None
    in_stock: bool
    shipping_info: str
    product_url: str


class MarketplaceSource(ABC):
    name: str = "base"
    search_url_template: str = ""
    base_currency: str = "EUR"

    @abstractmethod
    def build_search_url(self, query: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def parse_price(self, price_text: str) -> tuple[float | None, str | None]:
        raise NotImplementedError
