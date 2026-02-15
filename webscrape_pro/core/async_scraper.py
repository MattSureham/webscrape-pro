"""
Async Scraping Engine - aiohttp implementation for high-performance scraping
"""

import asyncio
import aiohttp
import structlog
from typing import List, Dict, Optional, Callable, Any, Union
from dataclasses import dataclass
from bs4 import BeautifulSoup
import random

from ..utils.validators import URLValidator

logger = structlog.get_logger()


@dataclass
class AsyncScrapingConfig:
    """Configuration for async scraper"""
    max_concurrent: int = 10
    delay_range: tuple = (0.5, 1.5)
    timeout: int = 30
    max_retries: int = 3
    rotate_user_agents: bool = True
    proxy_list: List[str] = None


class AsyncScraper:
    """
    High-performance async web scraper
    """
    
    def __init__(self, config: Optional[AsyncScrapingConfig] = None):
        self.config = config or AsyncScrapingConfig()
        self.validator = URLValidator()
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._user_agents = self._load_user_agents()
    
    def _load_user_agents(self) -> List[str]:
        """Load common user agents"""
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101',
        ]
    
    def _get_headers(self) -> Dict[str, str]:
        """Generate headers"""
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
        }
        if self.config.rotate_user_agents:
            headers['User-Agent'] = random.choice(self._user_agents)
        return headers
    
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(limit=self.config.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self._get_headers()
        )
        return self
    
    async def __aexit__(self, *args):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _apply_delay(self):
        """Apply random delay"""
        delay = random.uniform(*self.config.delay_range)
        await asyncio.sleep(delay)
    
    async def fetch(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """
        Fetch URL with concurrency control
        
        Args:
            url: Target URL
            **kwargs: Additional aiohttp parameters
            
        Returns:
            ClientResponse object
        """
        self.validator.validate(url)
        
        async with self.semaphore:
            await self._apply_delay()
            
            proxy = random.choice(self.config.proxy_list) if self.config.proxy_list else None
            
            for attempt in range(self.config.max_retries):
                try:
                    async with self.session.get(url, proxy=proxy, **kwargs) as response:
                        response.raise_for_status()
                        # Read content to avoid connection issues
                        await response.read()
                        logger.info("Fetched URL", url=url, status=response.status)
                        return response
                except Exception as e:
                    if attempt == self.config.max_retries - 1:
                        raise
                    logger.warning("Retrying fetch", url=url, attempt=attempt + 1)
                    await asyncio.sleep(2 ** attempt)
    
    async def fetch_many(self, urls: List[str], **kwargs) -> List[aiohttp.ClientResponse]:
        """Fetch multiple URLs concurrently"""
        tasks = [self.fetch(url, **kwargs) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                logger.error("Fetch failed", url=url, error=str(result))
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def scrape(self, url: str, parser: str = 'html.parser', **kwargs) -> BeautifulSoup:
        """Fetch and parse HTML"""
        response = await self.fetch(url, **kwargs)
        content = await response.text()
        return BeautifulSoup(content, parser)
    
    async def scrape_many(self, urls: List[str], parser: str = 'html.parser', 
                          **kwargs) -> List[BeautifulSoup]:
        """Scrape multiple URLs concurrently"""
        tasks = [self.scrape(url, parser, **kwargs) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        soups = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                logger.error("Scrape failed", url=url, error=str(result))
            else:
                soups.append(result)
        
        return soups
    
    async def post(self, url: str, data: Optional[Dict] = None, 
                   json_data: Optional[Dict] = None, **kwargs) -> aiohttp.ClientResponse:
        """POST request"""
        self.validator.validate(url)
        
        async with self.semaphore:
            await self._apply_delay()
            
            proxy = random.choice(self.config.proxy_list) if self.config.proxy_list else None
            
            async with self.session.post(url, data=data, json=json_data, 
                                         proxy=proxy, **kwargs) as response:
                response.raise_for_status()
                return response
    
    async def download(self, url: str, filepath: str, chunk_size: int = 8192, 
                       **kwargs) -> str:
        """Download file"""
        response = await self.fetch(url, **kwargs)
        
        with open(filepath, 'wb') as f:
            while True:
                chunk = await response.content.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
        
        logger.info("Downloaded file", url=url, filepath=filepath)
        return filepath
    
    async def download_many(self, downloads: List[tuple], **kwargs) -> List[str]:
        """
        Download multiple files
        
        Args:
            downloads: List of (url, filepath) tuples
            **kwargs: Additional parameters
            
        Returns:
            List of downloaded file paths
        """
        tasks = [self.download(url, path, **kwargs) for url, path in downloads]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        paths = []
        for (url, _), result in zip(downloads, results):
            if isinstance(result, Exception):
                logger.error("Download failed", url=url, error=str(result))
            else:
                paths.append(result)
        
        return paths
