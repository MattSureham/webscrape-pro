# WebScrape Pro 🕸️

A comprehensive, production-ready web scraping toolkit with multiple engines, advanced features, and extensible architecture.

## ✨ Features

### Scraping Engines
- **SmartScraper** - Requests + BeautifulSoup with caching, retries, proxies
- **AsyncScraper** - aiohttp for high-performance concurrent scraping
- **SeleniumScraper** - Chrome/Firefox automation for JavaScript-heavy sites
- **PlaywrightScraper** - Modern browser automation with stealth capabilities

### Data Exporters
- JSON / JSONL
- CSV / TSV
- Excel (multi-sheet support)
- SQLite
- Apache Parquet
- MongoDB

### Middleware
- **Caching** - Memory and disk-based caching
- **Retry Logic** - Exponential backoff with jitter
- **Rate Limiting** - Token bucket and sliding window algorithms

### Utilities
- HTML parsing (tables, forms, links, metadata extraction)
- URL manipulation and validation
- Email/phone extraction and validation

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/MattSureham/webscrape-pro.git
cd webscrape-pro

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```python
from webscrape_pro import SmartScraper

# Simple scraping
scraper = SmartScraper()
soup = scraper.scrape('https://example.com')
print(soup.title.text)

# With configuration
from webscrape_pro.core.scraper import ScrapingConfig

config = ScrapingConfig(
    delay_range=(2, 5),
    use_cache=True,
    rotate_user_agents=True
)
scraper = SmartScraper(config)
```

### Async Scraping

```python
import asyncio
from webscrape_pro import AsyncScraper

async def main():
    async with AsyncScraper() as scraper:
        urls = ['https://example.com/page1', 'https://example.com/page2']
        soups = await scraper.scrape_many(urls)
        return soups

asyncio.run(main())
```

### Browser Automation

```python
from webscrape_pro import SeleniumScraper

with SeleniumScraper() as scraper:
    scraper.get('https://example.com')
    scraper.type_text('input#search', 'python')
    scraper.click('button#submit')
    html = scraper.get_page_source()
```

### Exporting Data

```python
from webscrape_pro.exporters.base import JSONExporter, CSVExporter

data = [
    {'name': 'Product A', 'price': 29.99},
    {'name': 'Product B', 'price': 39.99}
]

# Export to JSON
JSONExporter('output.json').export(data)

# Export to CSV
CSVExporter('output.csv').export(data)
```

## 📁 Repository Structure

```
webscrape-pro/
├── webscrape_pro/              # Main package
│   ├── __init__.py
│   ├── core/                   # Core scraping engines
│   │   ├── scraper.py          # SmartScraper (requests/bs4)
│   │   ├── async_scraper.py    # AsyncScraper (aiohttp)
│   │   ├── browser.py          # SeleniumScraper
│   │   └── playwright_scraper.py # PlaywrightScraper
│   ├── exporters/              # Data export modules
│   │   ├── __init__.py
│   │   └── base.py             # JSON, CSV, Excel, SQLite, Parquet, MongoDB
│   ├── middleware/             # Middleware components
│   │   ├── __init__.py
│   │   ├── cache.py            # Caching (memory/disk)
│   │   ├── retry.py            # Retry logic with backoff
│   │   └── rate_limiter.py     # Rate limiting algorithms
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       ├── parsers.py          # HTMLParser, URLParser
│       └── validators.py       # URL, email, phone validators
├── README.md
├── requirements.txt
└── setup.py
```

## 📦 Requirements

- Python 3.8+
- requests
- beautifulsoup4
- aiohttp (for async)
- selenium (optional, for browser automation)
- playwright (optional, for modern browser automation)
- pandas (for data export)
- pymongo (optional, for MongoDB export)

## 🔧 Advanced Configuration

### Using Proxies

```python
config = ScrapingConfig(
    proxy_list=['http://proxy1:8080', 'http://proxy2:8080'],
    rotate_user_agents=True
)
scraper = SmartScraper(config)
```

### Custom Rate Limiting

```python
from webscrape_pro.middleware.rate_limiter import TokenBucket

bucket = TokenBucket(rate=2.0, capacity=5)  # 2 requests/sec, burst of 5
bucket.acquire()  # Wait for token
```

### Caching

```python
from webscrape_pro.middleware.cache import CacheManager

cache = CacheManager(backend='disk', cache_dir='.cache')
cache.set('key', value, ttl=3600)
value = cache.get('key')
```

## 🧪 Running Tests

```bash
pytest tests/
```

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Contributing

Contributions welcome! Please feel free to submit a Pull Request.
