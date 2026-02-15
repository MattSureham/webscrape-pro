# WebScrape Pro 🕸️

A comprehensive, production-ready web scraping toolkit with multiple engines, advanced features, and extensible architecture.

## Features

- **Multiple Scraping Engines**: Requests + BeautifulSoup, Selenium, Playwright, aiohttp (async)
- **Advanced Features**: Auto-retry, rate limiting, proxy rotation, caching, session management
- **Data Exporters**: JSON, CSV, Excel, SQLite, Parquet, MongoDB
- **Utilities**: URL parsing, form handling, pagination helpers, data validators
- **CLI Interface**: Command-line tool for quick scraping tasks
- **Docker Support**: Ready-to-use containerized environment
- **Extensible**: Plugin architecture for custom scrapers

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Basic usage
python -m webscrape_pro https://example.com --output data.json

# Using the library
from webscrape_pro import SmartScraper

scraper = SmartScraper()
data = scraper.scrape('https://example.com')
```

## Repository Structure

```
webscrape-pro/
├── webscrape_pro/          # Main package
│   ├── core/               # Core scraping engines
│   ├── utils/              # Utility functions
│   ├── exporters/          # Data export modules
│   ├── middleware/         # Middleware (caching, retries)
│   └── cli.py              # Command line interface
├── examples/               # Usage examples
├── tests/                  # Test suite
├── docker/                 # Docker configuration
└── docs/                   # Documentation
```

## License

MIT License
