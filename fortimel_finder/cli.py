from __future__ import annotations

import argparse
import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .analyzer import rank_offers
from .formatter import format_simple, format_summary
from .models import Flavor, Offer, Product, ProductVariant, SearchResult
from .search.duckduckgo import DuckDuckGoSearcher
from .sources.aliexpress import AliExpressSource
from .sources.amazon import AmazonSource

logger = logging.getLogger(__name__)

DEFAULT_VARIANT = ProductVariant.POWDER_335G
DEFAULT_FLAVOR = Flavor.UNKNOWN


def _build_queries(product_name: str, variant: ProductVariant, flavor: Flavor, country: str) -> list[str]:
    queries = []
    base = product_name.strip()
    if variant != ProductVariant.UNKNOWN:
        variant_str = variant.value.replace("_", " ")
        queries.append(f"{base} {variant_str}")
    if flavor != Flavor.UNKNOWN:
        queries.append(f"{base} {flavor.value}")
    queries.append(f"{base} buy online ship to {country}")
    queries.append(f"{base} price buy")
    queries.append(f"{base} {country}")
    queries.append(f"{base} pharmacy")
    return list(dict.fromkeys(queries))


def _merge_offers(offers: list[Offer]) -> list[Offer]:
    seen: set[tuple] = set()
    merged: list[Offer] = []
    for offer in offers:
        key = (
            offer.product.name.lower()[:40],
            offer.source_name,
            offer.price,
        )
        if key not in seen:
            seen.add(key)
            merged.append(offer)
    return merged


def run_search(
    product_name: str,
    variant: ProductVariant = DEFAULT_VARIANT,
    flavor: Flavor = DEFAULT_FLAVOR,
    country: str = "Algeria",
    max_results_per_source: int = 8,
    verbose: bool = False,
) -> SearchResult:
    if not product_name.strip():
        raise ValueError("Product name cannot be empty")

    queries = _build_queries(product_name, variant, flavor, country)
    all_offers: list[Offer] = []
    errors: list[str] = []
    sources_searched = 0
    sources_succeeded = 0

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}

        ddg_searcher = DuckDuckGoSearcher()
        for query in queries[:3]:
            future = executor.submit(_safe_search, ddg_searcher, query, max_results_per_source)
            futures[future] = f"DuckDuckGo: {query}"

        amazon = AmazonSource(domain="amazon.fr")
        future = executor.submit(_safe_search_amazon, amazon, f"{product_name} {variant.value.replace('_', ' ')}", max_results_per_source)
        futures[future] = "Amazon.fr"

        aliexpress = AliExpressSource()
        future = executor.submit(_safe_search_aliexpress, aliexpress, product_name, max_results_per_source)
        futures[future] = "AliExpress"

        for future in as_completed(futures, timeout=90):
            label = futures[future]
            sources_searched += 1
            try:
                offers = future.result()
                if offers is not None:
                    sources_succeeded += 1
                    if isinstance(offers, list) and offers and isinstance(offers[0], dict):
                        for item in offers:
                            product = Product(
                                name=item.get("title", product_name),
                                variant=variant,
                                flavor=flavor,
                            )
                            offer = Offer(
                                product=product,
                                source_name=item.get("source", label),
                                source_url=item.get("url", ""),
                                price=item.get("price") or 0.0,
                                currency=item.get("currency") or "EUR",
                                in_stock=item.get("in_stock", True),
                                reliability_score=6.0 if "Amazon" in label else 5.0,
                            )
                            all_offers.append(offer)
                    elif isinstance(offers, list):
                        all_offers.extend(offers)
            except Exception as exc:
                error_msg = f"{label} failed: {exc}"
                logger.warning(error_msg)
                if verbose:
                    errors.append(error_msg)

    elapsed = time.time() - start_time
    merged = _merge_offers(all_offers)
    ranked = rank_offers(merged)

    return SearchResult(
        query=product_name,
        offers=ranked,
        errors=errors,
        search_duration=elapsed,
        sources_searched=sources_searched,
        sources_succeeded=sources_succeeded,
    )


def _safe_search(searcher, query: str, max_results: int):
    try:
        return searcher.search(query, max_results=max_results)
    except Exception as exc:
        logger.warning("Search failed for %s: %s", query, exc)
        return []


def _safe_search_amazon(amazon: AmazonSource, query: str, max_results: int):
    try:
        return amazon.search(query, max_results=max_results)
    except Exception as exc:
        logger.warning("Amazon search failed: %s", exc)
        return []


def _safe_search_aliexpress(aliexpress: AliExpressSource, query: str, max_results: int):
    try:
        return aliexpress.search(query, max_results=max_results)
    except Exception as exc:
        logger.warning("AliExpress search failed: %s", exc)
        return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fortimel-finder",
        description="Search for Fortimel and other medical nutrition products across multiple sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python -m fortimel_finder "Fortimel Compact"
  python -m fortimel_finder "Fortimel" --variant powder_335g --flavor vanilla
  python -m fortimel_finder "Fortimel" --simple
  python -m fortimel_finder "Fortimel" --verbose
        """,
    )
    parser.add_argument("product", help="Product name to search for")
    parser.add_argument(
        "--variant",
        choices=[v.value for v in ProductVariant if v != ProductVariant.UNKNOWN],
        default=DEFAULT_VARIANT.value,
        help="Product variant to search for (default: powder_335g)",
    )
    parser.add_argument(
        "--flavor",
        choices=[f.value for f in Flavor if f != Flavor.UNKNOWN],
        default=None,
        help="Product flavor",
    )
    parser.add_argument(
        "--country",
        default="Algeria",
        help="Target country for shipping (default: Algeria)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=8,
        help="Max results per source (default: 8)",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Simple output format",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output with error details",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    try:
        result = run_search(
            product_name=args.product,
            variant=ProductVariant(args.variant),
            flavor=Flavor(args.flavor) if args.flavor else Flavor.UNKNOWN,
            country=args.country,
            max_results_per_source=args.max_results,
            verbose=args.verbose,
        )
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nSearch cancelled.")
        return 130

    if args.simple:
        print(format_simple(result))
    else:
        print(format_summary(result))

    return 0
