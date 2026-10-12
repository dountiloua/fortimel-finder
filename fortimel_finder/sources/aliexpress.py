from __future__ import annotations

import json
import logging
import re

import requests
from bs4 import BeautifulSoup

from .base import MarketplaceSource

logger = logging.getLogger(__name__)


class AliExpressSource(MarketplaceSource):
    name = "AliExpress"
    search_url_template = "https://www.aliexpress.com/wholesale?SearchText={query}"
    base_currency = "USD"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def build_search_url(self, query: str) -> str:
        return self.search_url_template.format(query=requests.utils.quote(query))

    def parse_price(self, price_text: str) -> tuple[float | None, str | None]:
        price_text = price_text.replace(",", "").replace("$", "").strip()
        match = re.search(r"(\d+(?:\.\d{1,2})?)", price_text)
        if match:
            try:
                return float(match.group(1)), self.base_currency
            except ValueError:
                return None, None
        return None, None

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        url = self.build_search_url(query)
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("AliExpress request failed: %s", exc)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items: list[dict] = []
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            if len(items) >= max_results:
                break
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            graph = data.get("@graph", []) if isinstance(data, dict) else []
            if not graph and isinstance(data, list):
                graph = data
            for node in graph:
                if isinstance(node, dict) and node.get("@type") == "Product":
                    offers = node.get("offers", {})
                    price = offers.get("price")
                    currency = offers.get("priceCurrency", self.base_currency)
                    availability = offers.get("availability", "")
                    in_stock = "InStock" in availability or "instock" in availability.lower()
                    item_url = node.get("url", url)
                    items.append(
                        {
                            "title": node.get("name", query),
                            "url": item_url,
                            "price_text": f"{price} {currency}" if price else "",
                            "price": float(price) if price else None,
                            "currency": currency,
                            "in_stock": in_stock,
                            "source": "AliExpress",
                        }
                    )
        if items:
            return items[:max_results]

        for card in soup.select(".search-card-item") or soup.select("[class*='card-item']"):
            if len(items) >= max_results:
                break
            title_tag = card.select_one("[class*='title']") or card.select_one("h3")
            link_tag = card.select_one("a")
            price_tag = card.select_one("[class*='price']")
            if not title_tag:
                continue
            href = link_tag.get("href", "") if link_tag else ""
            if href.startswith("//"):
                href = "https:" + href
            price_text = price_tag.get_text(strip=True) if price_tag else ""
            price, currency = self.parse_price(price_text)
            items.append(
                {
                    "title": title_tag.get_text(strip=True),
                    "url": href or url,
                    "price_text": price_text,
                    "price": price,
                    "currency": currency,
                    "in_stock": True,
                    "source": "AliExpress",
                }
            )
        return items
