from __future__ import annotations

import logging
import re
import time
from typing import Any

import requests
from bs4 import BeautifulSoup

from ..models import Flavor, Offer, Product, ProductVariant
from .base import BaseSearcher, SearchError

logger = logging.getLogger(__name__)

DDG_LITE_URL = "https://lite.duckduckgo.com/lite"
DDG_HTML_URL = "https://html.duckduckgo.com/html"

VARIANT_PATTERNS: list[tuple[ProductVariant, re.Pattern]] = [
    (ProductVariant.COMPACT_PROTEIN, re.compile(r"compact\s+protein", re.I)),
    (ProductVariant.COMPACT_125ML, re.compile(r"compact\b|125\s*ml", re.I)),
    (ProductVariant.RTD_400ML, re.compile(r"400\s*ml", re.I)),
    (ProductVariant.RTD_200ML, re.compile(r"200\s*ml|ready.to.drink|rtd", re.I)),
    (ProductVariant.POWDER_800G, re.compile(r"800\s*g", re.I)),
    (ProductVariant.POWDER_400G, re.compile(r"400\s*g", re.I)),
    (ProductVariant.POWDER_335G, re.compile(r"335\s*g", re.I)),
]

FLAVOR_PATTERNS: list[tuple[Flavor, re.Pattern]] = [
    (Flavor.CHOCOLATE, re.compile(r"chocolate|chocolat", re.I)),
    (Flavor.VANILLA, re.compile(r"vanilla|vanille", re.I)),
    (Flavor.STRAWBERRY, re.compile(r"strawberry|fraise|fresa", re.I)),
    (Flavor.BANANA, re.compile(r"banana|banane", re.I)),
    (Flavor.COFFEE, re.compile(r"cafe|coffee", re.I)),
    (Flavor.CAPPUCCINO, re.compile(r"cappuccino", re.I)),
    (Flavor.FRUITS, re.compile(r"fruits?|tropical", re.I)),
]

PRICE_RE = re.compile(r"(\d[\d\s.,]*)\s*(€|EUR|USD|\$|DZD|dzd|eur|usd)", re.I)


def _detect_variant(text: str) -> ProductVariant:
    for variant, pattern in VARIANT_PATTERNS:
        if pattern.search(text):
            return variant
    return ProductVariant.UNKNOWN


def _detect_flavor(text: str) -> Flavor:
    for flavor, pattern in FLAVOR_PATTERNS:
        if pattern.search(text):
            return flavor
    return Flavor.UNKNOWN


class DuckDuckGoSearcher(BaseSearcher):
    name = "DuckDuckGo"
    reliability = 7.0

    def __init__(self, timeout: int = 15, delay: float = 0.8):
        self.timeout = timeout
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9,fr;q=0.8,ar;q=0.7",
            }
        )

    def search(self, query: str, max_results: int = 10, **kwargs) -> list[Offer]:
        offers: list[Offer] = []
        try:
            results = self._search(query, max_results=max_results)
        except Exception as exc:
            raise SearchError(f"DuckDuckGo search failed: {exc}") from exc

        for title, url, snippet in results:
            text = f"{title} {snippet}"
            variant = _detect_variant(text)
            flavor = _detect_flavor(text)
            size_match = re.search(r"(\d+\s*(?:g|ml|kg|l)\b)", text, re.I)
            size = size_match.group(1) if size_match else ""
            product = Product(
                name=title.strip(),
                variant=variant,
                flavor=flavor,
                size=size,
                description=snippet.strip(),
            )
            price, currency = self._extract_price(text)
            notes: list[str] = []
            if re.search(r"ship|livraison|envío|shipping", text, re.I):
                notes.append("shipping mentioned")
            if re.search(r"algeria|algérie|argelia|dz\b", text, re.I):
                notes.append("Algeria-related")
            offers.append(
                self._create_offer(
                    product=product,
                    url=url,
                    price=price,
                    currency=currency or "EUR",
                    notes=notes,
                    search_url=DDG_HTML_URL,
                )
            )
            time.sleep(self.delay)
        return offers

    def _search(self, query: str, max_results: int = 10) -> list[tuple[str, str, str]]:
        results: list[tuple[str, str, str]] = []
        for endpoint in (DDG_LITE_URL, DDG_HTML_URL):
            try:
                resp = self.session.post(
                    endpoint,
                    data={"q": query},
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                results = self._parse_results(soup, endpoint)
                if results:
                    break
            except requests.RequestException as exc:
                logger.warning("DDG endpoint %s failed: %s", endpoint, exc)
        return results[:max_results]

    def _parse_results(
        self, soup: BeautifulSoup, endpoint: str
    ) -> list[tuple[str, str, str]]:
        results: list[tuple[str, str, str]] = []
        if endpoint == DDG_LITE_URL:
            for row in soup.select("table tr"):
                link = row.select_one("a")
                if not link:
                    continue
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if href.startswith("//"):
                    href = "https:" + href
                snippet = ""
                snippet_tag = row.select_one(".result-snippet")
                if snippet_tag:
                    snippet = snippet_tag.get_text(strip=True)
                if title and href and "duckduckgo" not in href:
                    results.append((title, href, snippet))
        else:
            for result in soup.select(".result"):
                link = result.select_one(".result__a")
                snippet_tag = result.select_one(".result__snippet")
                if not link:
                    continue
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if href.startswith("//duckduckgo.com/l/?uddg="):
                    href = requests.utils.unquote(href.split("uddg=")[1].split("&")[0])
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                if title and href:
                    results.append((title, href, snippet))
        return results

    def _extract_price(self, text: str) -> tuple[float | None, str | None]:
        match = PRICE_RE.search(text)
        if not match:
            return None, None
        raw_price = match.group(1).replace("\xa0", "").replace(" ", "")
        raw_price = raw_price.replace(",", ".") if raw_price.count(",") == 1 and "." not in raw_price else raw_price.replace(",", "")
        try:
            price = float(raw_price)
        except ValueError:
            return None, None
        currency = match.group(2).upper()
        currency_map = {"€": "EUR", "$": "USD", "DZD": "DZD"}
        return price, currency_map.get(currency, currency)
