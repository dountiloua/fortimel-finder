from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Offer, Product


class SearchError(Exception):
    pass


class BaseSearcher(ABC):
    name: str = "base"
    reliability: float = 5.0
    supports_international_shipping: bool = False

    @abstractmethod
    def search(self, query: str, **kwargs) -> list[Offer]:
        raise NotImplementedError

    def _create_offer(
        self,
        product: Product,
        url: str,
        price: float | None = None,
        currency: str = "EUR",
        price_local: float | None = None,
        currency_local: str = "DZD",
        in_stock: bool = True,
        shipping_cost: float | None = None,
        shipping_currency: str = "EUR",
        shipping_days: str | None = None,
        ships_to_algeria: bool = False,
        notes: list[str] | None = None,
        search_url: str = "",
    ) -> Offer:
        return Offer(
            product=product,
            source_name=self.name,
            source_url=url,
            price=price or 0.0,
            currency=currency,
            price_local=price_local,
            currency_local=currency_local,
            in_stock=in_stock,
            shipping_cost=shipping_cost,
            shipping_currency=shipping_currency,
            shipping_days=shipping_days,
            ships_to_algeria=ships_to_algeria,
            reliability_score=self.reliability,
            notes=notes or [],
            search_url=search_url,
        )
