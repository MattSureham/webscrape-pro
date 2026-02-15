"""
WebScrape Pro - Main Package
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from .core.scraper import SmartScraper, AsyncScraper
from .core.browser import SeleniumScraper, PlaywrightScraper
from .exporters.base import JSONExporter, CSVExporter, ExcelExporter
from .utils.parsers import HTMLParser, URLParser

__all__ = [
    "SmartScraper",
    "AsyncScraper",
    "SeleniumScraper",
    "PlaywrightScraper",
    "JSONExporter",
    "CSVExporter",
    "ExcelExporter",
    "HTMLParser",
    "URLParser",
]
