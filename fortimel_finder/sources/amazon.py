from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

from .base import MarketplaceSource

logger = logging.getLogger(__name__)

AMAZON_DOMAINS = {
    "amazon.fr": "EUR",
    "amazon.com": "USD",
    "amazon.es": "EUR",
    "amazon.it": "EUR",
    "amazon.de": "EUR",
    "amazon.co.uk": "GBP",
    "amazon.ae": "AED",
}


class AmazonSource(MarketplaceSource):
    name = "Amazon"
    search_url_template = "https://{domain}/s?k={query}"
    base_currency = "EUR"

    def __init__(self, domain: str = "amazon.fr", timeout: int = 15):
        if domain not in AMAZON_DOMAINS:
            raise ValueError(f"Unsupported Amazon domain: {domain}")
        self.domain = domain
        self.currency = AMAZON_DOMAINS[domain]
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
            }
        )

    def build_search_url(self, query: str) -> str:
        return self.search_url_template.format(domain=self.domain, query=requests.utils.quote(query))

    def parse_price(self, price_text: str) -> tuple[float | None, str | None]:
        price_text = price_text.replace("\xa0", "").replace(" ", "").replace(",", ".")
        match = re.search(r"(\d+(?:\.\d{1,2})?)", price_text)
        if match:
            try:
                return float(match.group(1)), self.currency
            except ValueError:
                return None, None
        return None, None

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        url = self.build_search_url(query)
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Amazon %s request failed: %s", self.domain, exc)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        items: list[dict] = []
        for card in soup.select('[data-component-type="s-search-result"]'):
            if len(items) >= max_results:
                break
            title_tag = card.select_one("h2 a span")
            link_tag = card.select_one("h2 a")
            price_whole = card.select_one(".a-price .a-offscreen")
            if not title_tag or not link_tag:
                continue
            title = title_tag.get_text(strip=True)
            href = link_tag.get("href", "")
            if href.startswith("/"):
                href = f"https://{self.domain}{href}"
            price_text = price_whole.get_text(strip=True) if price_whole else ""
            price, currency = self.parse_price(price_text)
            in_stock = not card.select_one(".a-color-price")
            items.append(
                {
                    "title": title,
                    "url": href,
                    "price_text": price_text,
                    "price": price,
                    "currency": currency,
                    "in_stock": in_stock,
                    "source": f"Amazon ({self.domain})",
                }
            )
        return items
