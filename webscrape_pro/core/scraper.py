"""
Core Scraping Engine - Requests + BeautifulSoup implementation
"""

import time
import random
import hashlib
import json
from typing import Dict, List, Optional, Union, Callable, Any
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import structlog

from ..middleware.cache import CacheManager
from ..middleware.retry import RetryManager
from ..utils.validators import URLValidator

logger = structlog.get_logger()


@dataclass
class ScrapingConfig:
    """Configuration for scraper behavior"""
    delay_range: tuple = (1, 3)
    timeout: int = 30
    max_retries: int = 3
    follow_redirects: bool = True
    verify_ssl: bool = True
    use_cache: bool = False
    cache_ttl: int = 3600
    rotate_user_agents: bool = True
    proxy_list: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)


class SmartScraper:
    """
    Intelligent web scraper with built-in retries, caching, and rate limiting
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        self.config = config or ScrapingConfig()
        self.session = requests.Session()
        self.ua = UserAgent() if self.config.rotate_user_agents else None
        self.cache = CacheManager() if self.config.use_cache else None
        self.retry_manager = RetryManager(max_retries=self.config.max_retries)
        self.validator = URLValidator()
        
        self._setup_session()
    
    def _setup_session(self):
        """Configure session with headers and settings"""
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        })
        if self.config.headers:
            self.session.headers.update(self.config.headers)
        if self.config.cookies:
            self.session.cookies.update(self.config.cookies)
    
    def _get_headers(self) -> Dict[str, str]:
        """Generate request headers with optional user agent rotation"""
        headers = {}
        if self.config.rotate_user_agents and self.ua:
            headers['User-Agent'] = self.ua.random
        return headers
    
    def _get_proxy(self) -> Optional[Dict[str, str]]:
        """Select random proxy from list"""
        if self.config.proxy_list:
            proxy = random.choice(self.config.proxy_list)
            return {
                'http': proxy,
                'https': proxy
            }
        return None
    
    def _apply_delay(self):
        """Apply random delay between requests"""
        delay = random.uniform(*self.config.delay_range)
        time.sleep(delay)
    
    def fetch(self, url: str, **kwargs) -> requests.Response:
        """
        Fetch URL with caching, retries, and rate limiting
        
        Args:
            url: Target URL
            **kwargs: Additional requests parameters
            
        Returns:
            Response object
        """
        self.validator.validate(url)
        
        # Check cache
        cache_key = hashlib.md5(url.encode()).hexdigest()
        if self.cache and self.cache.has(cache_key):
            logger.info("Cache hit", url=url)
            return self.cache.get(cache_key)
        
        # Apply delay
        self._apply_delay()
        
        # Prepare request
        headers = {**self._get_headers(), **kwargs.pop('headers', {})}
        proxies = self._get_proxy()
        
        def _do_request():
            return self.session.get(
                url,
                headers=headers,
                proxies=proxies,
                timeout=self.config.timeout,
                allow_redirects=self.config.follow_redirects,
                verify=self.config.verify_ssl,
                **kwargs
            )
        
        # Execute with retry
        response = self.retry_manager.execute(_do_request)
        response.raise_for_status()
        
        # Cache response
        if self.cache:
            self.cache.set(cache_key, response, ttl=self.config.cache_ttl)
        
        logger.info("Fetched URL", url=url, status=response.status_code)
        return response
    
    def fetch_many(self, urls: List[str], **kwargs) -> List[requests.Response]:
        """Fetch multiple URLs sequentially"""
        results = []
        for url in urls:
            try:
                response = self.fetch(url, **kwargs)
                results.append(response)
            except Exception as e:
                logger.error("Fetch failed", url=url, error=str(e))
                results.append(None)
        return results
    
    def scrape(self, url: str, parser: str = 'html.parser', **kwargs) -> BeautifulSoup:
        """
        Fetch and parse HTML content
        
        Args:
            url: Target URL
            parser: HTML parser to use
            **kwargs: Additional fetch parameters
            
        Returns:
            BeautifulSoup object
        """
        response = self.fetch(url, **kwargs)
        return BeautifulSoup(response.content, parser)
    
    def scrape_json(self, url: str, **kwargs) -> Union[Dict, List]:
        """Fetch and parse JSON response"""
        response = self.fetch(url, **kwargs)
        return response.json()
    
    def post(self, url: str, data: Optional[Dict] = None, 
             json_data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """POST request with retry logic"""
        self.validator.validate(url)
        self._apply_delay()
        
        headers = {**self._get_headers(), **kwargs.pop('headers', {})}
        proxies = self._get_proxy()
        
        def _do_request():
            return self.session.post(
                url,
                data=data,
                json=json_data,
                headers=headers,
                proxies=proxies,
                timeout=self.config.timeout,
                **kwargs
            )
        
        return self.retry_manager.execute(_do_request)
    
    def download(self, url: str, filepath: str, chunk_size: int = 8192, **kwargs) -> str:
        """
        Download file from URL
        
        Args:
            url: File URL
            filepath: Local save path
            chunk_size: Download chunk size
            **kwargs: Additional fetch parameters
            
        Returns:
            Path to downloaded file
        """
        response = self.fetch(url, stream=True, **kwargs)
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
        
        logger.info("Downloaded file", url=url, filepath=filepath)
        return filepath
    
    def crawl(self, start_url: str, max_pages: int = 10, 
              same_domain: bool = True,
              link_filter: Optional[Callable[[str], bool]] = None) -> List[BeautifulSoup]:
        """
        Basic crawler that follows links
        
        Args:
            start_url: Starting URL
            max_pages: Maximum pages to crawl
            same_domain: Only follow same-domain links
            link_filter: Optional function to filter links
            
        Returns:
            List of BeautifulSoup objects
        """
        visited = set()
        to_visit = [start_url]
        results = []
        
        base_domain = urlparse(start_url).netloc
        
        while to_visit and len(visited) < max_pages:
            url = to_visit.pop(0)
            
            if url in visited:
                continue
            
            try:
                soup = self.scrape(url)
                visited.add(url)
                results.append(soup)
                
                # Extract links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    full_url = urljoin(url, href)
                    
                    if same_domain and urlparse(full_url).netloc != base_domain:
                        continue
                    
                    if link_filter and not link_filter(full_url):
                        continue
                    
                    if full_url not in visited:
                        to_visit.append(full_url)
                        
            except Exception as e:
                logger.error("Crawl error", url=url, error=str(e))
        
        return results
    
    def close(self):
        """Close session and cleanup"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
