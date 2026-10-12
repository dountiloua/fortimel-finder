from __future__ import annotations

import logging

from .models import Flavor, Offer, ProductVariant

logger = logging.getLogger(__name__)

WEIGHT_PRICE = 40
WEIGHT_RELIABILITY = 30
WEIGHT_SHIPPING = 20
WEIGHT_STOCK = 10

MAX_REFERENCE_PRICE = 80.0


def score_offer(offer: Offer) -> float:
    price_score = 0.0
    if offer.total_cost_eur and offer.total_cost_eur > 0:
        price_score = max(0.0, 1.0 - (offer.total_cost_eur / MAX_REFERENCE_PRICE))

    reliability_score = offer.reliability_score / 10.0

    if offer.shipping_available is True:
        shipping_score = 1.0
    elif offer.shipping_available is False:
        shipping_score = 0.2
    else:
        shipping_score = 0.5

    stock_score = 1.0 if offer.in_stock else 0.1

    total = (
        WEIGHT_PRICE * price_score
        + WEIGHT_RELIABILITY * reliability_score
        + WEIGHT_SHIPPING * shipping_score
        + WEIGHT_STOCK * stock_score
    )
    return round(min(total, 100.0), 1)


def rank_offers(offers: list[Offer]) -> list[Offer]:
    scored = [(offer, score_offer(offer)) for offer in offers]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    ranked = []
    for offer, score in scored:
        offer.notes.insert(0, f"Score: {score}/100")
        ranked.append(offer)
    return ranked


def group_by_variant(offers: list[Offer]) -> dict[ProductVariant, list[Offer]]:
    groups: dict[ProductVariant, list[Offer]] = {}
    for offer in offers:
        groups.setdefault(offer.product.variant, []).append(offer)
    return dict(sorted(groups.items(), key=lambda kv: rank_offers(kv[1])[0] if kv[1] else None, reverse=True))


def group_by_flavor(offers: list[Offer]) -> dict[Flavor, list[Offer]]:
    groups: dict[Flavor, list[Offer]] = {}
    for offer in offers:
        groups.setdefault(offer.product.flavor, []).append(offer)
    return dict(sorted(groups.items()))


def get_best_per_variant(offers: list[Offer]) -> dict[ProductVariant, Offer]:
    ranked = rank_offers(offers)
    best: dict[ProductVariant, Offer] = {}
    for offer in ranked:
        variant = offer.product.variant
        if variant not in best:
            best[variant] = offer
    return best


def estimate_shipping_to_algeria(source_name: str) -> tuple[bool, float | None, str | None]:
    source_lower = source_name.lower()
    if "aliexpress" in source_lower:
        return True, 5.0, "7-20 days"
    if "amazon" in source_lower:
        return True, 10.0, "5-12 days"
    if "pharmac" in source_lower:
        return None, None, None
    if "facebook" in source_lower or "marketplace" in source_lower:
        return False, None, None
    return None, None, None
