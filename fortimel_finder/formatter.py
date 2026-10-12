from __future__ import annotations

import shutil
import sys
from datetime import datetime

from .models import Flavor, Offer, ProductVariant, SearchResult

COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "white": "\033[97m",
}

USE_COLOR = True


def _supports_color() -> bool:
    if not USE_COLOR:
        return False
    if sys.platform == "win32":
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def color(name: str) -> str:
    return COLORS.get(name, "") if _supports_color() else ""


def _format_price(offer: Offer) -> str:
    if offer.price_local:
        return f"{offer.price_local:,.0f} DZD"
    if offer.price:
        return f"{offer.price:.2f} {offer.currency}"
    return "Price N/A"


def _format_total(offer: Offer) -> str:
    total = offer.total_cost_local or offer.total_cost_eur
    if total is None:
        return "N/A"
    if offer.price_local:
        return f"{total:,.0f} DZD"
    return f"{total:.2f} {offer.currency}"


def _variant_label(variant: ProductVariant) -> str:
    labels = {
        ProductVariant.POWDER_335G: "Powder 335g",
        ProductVariant.POWDER_400G: "Powder 400g",
        ProductVariant.POWDER_800G: "Powder 800g",
        ProductVariant.RTD_200ML: "Ready-to-Drink 200ml",
        ProductVariant.RTD_400ML: "Ready-to-Drink 400ml",
        ProductVariant.COMPACT_125ML: "Compact 125ml",
        ProductVariant.COMPACT_PROTEIN: "Compact Protein",
        ProductVariant.UNKNOWN: "Unknown variant",
    }
    return labels.get(variant, variant.value)


def _flavor_label(flavor: Flavor) -> str:
    labels = {
        Flavor.VANILLA: "Vanilla",
        Flavor.CHOCOLATE: "Chocolate",
        Flavor.STRAWBERRY: "Strawberry",
        Flavor.BANANA: "Banana",
        Flavor.COFFEE: "Coffee",
        Flavor.CAPPUCCINO: "Cappuccino",
        Flavor.FRUITS: "Fruits",
        Flavor.NEUTRAL: "Neutral",
        Flavor.UNKNOWN: "Unknown",
    }
    return labels.get(flavor, flavor.value)


def _wrap_text(text: str, width: int, indent: int = 0) -> list[str]:
    if not text:
        return []
    words = text.split()
    lines: list[str] = []
    current = " " * indent
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current.rstrip())
            current = " " * indent + word + " "
        else:
            current += word + " "
    if current.strip():
        lines.append(current.rstrip())
    return lines


def format_offer(offer: Offer, index: int, terminal_width: int) -> str:
    reset = color("reset")
    bold = color("bold")
    green = color("green")
    yellow = color("yellow")
    cyan = color("cyan")
    blue = color("blue")

    medal = ""
    if index == 0:
        medal = f"{color('yellow')}[#1 BEST]{reset} "
    elif index == 1:
        medal = f"{color('cyan')}[#2]{reset} "
    elif index == 2:
        medal = f"{color('blue')}[#3]{reset} "

    score = "N/A"
    for note in offer.notes:
        if note.startswith("Score:"):
            score = note.split(":")[1].strip()
            break

    stock = f"{green}In Stock{reset}" if offer.in_stock else f"{yellow}Out of Stock{reset}"
    shipping = "Unknown"
    if offer.shipping_available is True:
        shipping = f"{green}Ships to DZ{reset}"
    elif offer.shipping_available is False:
        shipping = f"{color('red')}No intl. shipping{reset}"

    lines = [
        f"{medal}{bold}{offer.product.name[:terminal_width-10]}{reset}",
        f"   {_variant_label(offer.product.variant)} | {_flavor_label(offer.product.flavor)}",
        f"   Price: {_format_price(offer)}  |  Total: {_format_total(offer)}  |  {stock}",
        f"   Source: {cyan}{offer.source_name}{reset}  |  {shipping}  |  Score: {score}",
    ]
    if offer.shipping_days:
        lines.append(f"   Shipping time: {offer.shipping_days}")
    if offer.seller_rating:
        lines.append(f"   Seller rating: {offer.seller_rating}/5 ({offer.review_count} reviews)")
    if offer.notes:
        extra_notes = [n for n in offer.notes if not n.startswith("Score:")]
        if extra_notes:
            lines.append(f"   Notes: {', '.join(extra_notes)}")
    lines.append(f"   URL: {offer.source_url}")
    return "\n".join(lines)


def format_summary(result: SearchResult) -> str:
    reset = color("reset")
    bold = color("bold")
    green = color("green")
    red = color("red")
    yellow = color("yellow")
    cyan = color("cyan")
    magenta = color("magenta")
    dim = color("dim")

    term_width = shutil.get_terminal_size((100, 24)).columns
    term_width = min(term_width, 120)

    lines: list[str] = []
    lines.append("")
    lines.append(f"{bold}{cyan}{'=' * term_width}{reset}")
    lines.append(f"{bold}{cyan}  FORTIMEL FINDER — Search Results{reset}")
    lines.append(f"{bold}{cyan}{'=' * term_width}{reset}")
    lines.append(f"  Query: {bold}{result.query}{reset}")
    lines.append(f"  Date:  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"  Sources searched: {result.sources_searched} | Succeeded: {result.sources_succeeded}")
    lines.append(f"  Offers found: {bold}{len(result.offers)}{reset}")
    if result.search_duration:
        lines.append(f"  Search time: {result.search_duration:.1f}s")
    lines.append("")

    if result.errors:
        lines.append(f"{yellow}  WARNINGS:{reset}")
        for error in result.errors:
            for wrapped in _wrap_text(error, term_width - 4, indent=4):
                lines.append(wrapped)
        lines.append("")

    if not result.offers:
        lines.append(f"{red}  No offers found. Try a different query or check your internet connection.{reset}")
        lines.append("")
        return "\n".join(lines)

    ranked = result.offers

    lines.append(f"{bold}{magenta}  TOP OFFERS (ranked by price + reliability + shipping):{reset}")
    lines.append("")
    for i, offer in enumerate(ranked[:10]):
        lines.append(format_offer(offer, i, term_width))
        lines.append("")

    variants = {}
    for offer in ranked:
        v = offer.product.variant
        if v not in variants:
            variants[v] = offer
    if len(variants) > 1:
        lines.append(f"{bold}{magenta}  BEST PER VARIANT:{reset}")
        for variant, offer in variants.items():
            lines.append(f"   {bold}{_variant_label(variant)}{reset}: {_format_price(offer)} — {cyan}{offer.source_name}{reset} (Score: {offer.notes[0].split(':')[1].strip() if offer.notes and offer.notes[0].startswith('Score:') else 'N/A'})")
        lines.append("")

    in_stock = [o for o in ranked if o.in_stock]
    if in_stock:
        cheapest = min(in_stock, key=lambda o: o.total_cost_eur or o.price or 9999)
        lines.append(f"{bold}{green}  CHEAPEST IN-STOCK:{reset} {cheapest.product.name}")
        lines.append(f"   {_format_total(cheapest)} total — {cyan}{cheapest.source_name}{reset}")
        lines.append("")

    ships_dz = [o for o in ranked if o.ships_to_algeria]
    if ships_dz:
        lines.append(f"{bold}{green}  SHIPS TO ALGERIA:{reset} {len(ships_dz)} offer(s)")
        for offer in ships_dz[:3]:
            lines.append(f"   - {offer.product.name[:50]} via {cyan}{offer.source_name}{reset} — {_format_total(offer)}")
        lines.append("")

    lines.append(f"{dim}{'─' * term_width}{reset}")
    lines.append(f"{dim}  Note: Prices are indicative and may change. Always verify on the seller's site.{reset}")
    lines.append(f"{dim}  Generated by fortimel-finder{reset}")
    lines.append("")
    return "\n".join(lines)


def format_simple(result: SearchResult) -> str:
    lines: list[str] = []
    lines.append(f"\nSearch: {result.query}")
    lines.append(f"Found {len(result.offers)} offers from {result.sources_succeeded}/{result.sources_searched} sources\n")
    for i, offer in enumerate(result.offers[:5]):
        price = _format_total(offer)
        stock = "In Stock" if offer.in_stock else "Out of Stock"
        lines.append(f"  {i+1}. {offer.product.name[:60]}")
        lines.append(f"     {offer.product.variant.value} | {offer.product.flavor.value} | {price} | {stock}")
        lines.append(f"     {offer.source_name}: {offer.source_url}")
        lines.append("")
    return "\n".join(lines)
