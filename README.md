# Fortimel Finder

A Python CLI tool that searches multiple online sources for Fortimel (Nutricia) and other hard-to-find medical nutrition products, compares prices and shipping options, and ranks the best options — especially useful for Algeria and regions where these products are difficult to source.

## Features

- **Multi-source search**: DuckDuckGo, Amazon (FR/ES/IT/DE/UK/AE), AliExpress
- **Smart parsing**: Automatically detects product variant (powder 335g/400g/800g, RTD 200ml/400ml, Compact 125ml/Compact Protein) and flavor
- **Price comparison**: Shows price, total cost (with shipping), and local currency estimate
- **Reliability ranking**: Scores each offer based on price (40%), reliability (30%), shipping availability (20%), and stock status (10%)
- **Clean terminal output**: Color-coded, formatted summary with top picks, best per variant, and Algeria-specific shipping info
- **Robust error handling**: If a source fails, the search continues with the rest
- **Simple CLI**: Just type a product name and get results

## Installation

```bash
git clone https://github.com/yourusername/fortimel-finder.git
cd fortimel-finder
pip install -r requirements.txt
```

Or install directly:

```bash
pip install requests beautifulsoup4
```

## Usage

### Basic search
```bash
python -m fortimel_finder "Fortimel Compact"
```

### Search with variant and flavor
```bash
python -m fortimel_finder "Fortimel" --variant powder_335g --flavor vanilla
```

### Simple output (compact list)
```bash
python -m fortimel_finder "Fortimel" --simple
```

### Verbose mode (shows errors)
```bash
python -m fortimel_finder "Fortimel" --verbose
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `product` | Product name to search | (required) |
| `--variant` | Product variant | `powder_335g` |
| `--flavor` | Flavor | (auto-detect) |
| `--country` | Target country for shipping | `Algeria` |
| `--max-results` | Max results per source | `8` |
| `--simple` | Simple output format | `False` |
| `--verbose` | Show detailed errors | `False` |

### Available variants
- `powder_335g` — Powder 335g tin
- `powder_400g` — Powder 400g tin
- `powder_800g` — Powder 800g tin
- `rtd_200ml` — Ready-to-drink 200ml bottle
- `rtd_400ml` — Ready-to-drink 400ml bottle
- `compact_125ml` — Compact 125ml bottle
- `compact_protein` — Compact Protein

### Available flavors
- `vanilla`, `chocolate`, `strawberry`, `banana`, `coffee`, `cappuccino`, `fruits`, `neutral`

## How it works

1. **Search queries** are generated based on product name, variant, flavor, and target country
2. **Multiple sources** are searched in parallel using DuckDuckGo (general web), Amazon, and AliExpress
3. **Results are parsed** to extract price, URL, stock status, and shipping info
4. **Offers are deduplicated** and ranked using a weighted scoring algorithm
5. **Summary is displayed** with top picks, best per variant, and Algeria-specific recommendations

## Scoring Algorithm

| Factor | Weight | Description |
|--------|--------|-------------|
| Price | 40% | Total cost (product + shipping) vs. reference price (80 EUR) |
| Reliability | 30% | Source trustworthiness (Amazon > DuckDuckGo > AliExpress) |
| Shipping | 20% | Whether the source ships to Algeria |
| Stock | 10% | In-stock bonus |

## Project Structure

```
fortimel-finder/
├── fortimel_finder/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # CLI entry point
│   ├── models.py           # Data models (Product, Offer, SearchResult)
│   ├── analyzer.py         # Ranking and scoring logic
│   ├── formatter.py        # Terminal output formatting
│   └── search/
│       ├── __init__.py
│       ├── base.py         # Base searcher class
│       └── duckduckgo.py   # DuckDuckGo web search
│   └── sources/
│       ├── __init__.py
│       ├── base.py         # Base marketplace source
│       ├── amazon.py       # Amazon scraper
│       └── aliexpress.py   # AliExpress scraper
├── requirements.txt
├── main.py                 # Convenience entry point
└── README.md
```

## Notes

- Prices are indicative and scraped from public pages; always verify on the seller's website before purchasing.
- Some sources may block automated searches — the tool handles failures gracefully and continues with available sources.
- The tool is designed for personal research purposes.

## License

MIT
