"""
Playwright-based scraper for modern browser automation
"""

import asyncio
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from playwright.sync_api import sync_playwright
import structlog

logger = structlog.get_logger()


@dataclass
class PlaywrightConfig:
    """Configuration for Playwright scraper"""
    browser: str = 'chromium'  # chromium, firefox, webkit
    headless: bool = True
    window_size: tuple = (1920, 1080)
    user_agent: Optional[str] = None
    proxy: Optional[Dict[str, str]] = None
    viewport: Optional[Dict] = None
    locale: str = 'en-US'
    timezone: str = 'America/New_York'


class PlaywrightScraper:
    """
    Playwright-based scraper with stealth capabilities
    """
    
    def __init__(self, config: Optional[PlaywrightConfig] = None):
        self.config = config or PlaywrightConfig()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def start_async(self):
        """Initialize async browser"""
        self.playwright = await async_playwright().start()
        
        browser_type = getattr(self.playwright, self.config.browser)
        
        args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ]
        
        self.browser = await browser_type.launch(
            headless=self.config.headless,
            args=args
        )
        
        context_options = {
            'viewport': self.config.viewport or {
                'width': self.config.window_size[0],
                'height': self.config.window_size[1]
            },
            'locale': self.config.locale,
            'timezone_id': self.config.timezone,
        }
        
        if self.config.user_agent:
            context_options['user_agent'] = self.config.user_agent
        
        if self.config.proxy:
            context_options['proxy'] = self.config.proxy
        
        self.context = await self.browser.new_context(**context_options)
        
        # Add stealth scripts
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            window.chrome = { runtime: {} };
        """)
        
        self.page = await self.context.new_page()
        logger.info(f"Started {self.config.browser} browser with Playwright")
    
    def start_sync(self):
        """Initialize sync browser"""
        self.playwright = sync_playwright().start()
        
        browser_type = getattr(self.playwright, self.config.browser)
        
        self.browser = browser_type.launch(headless=self.config.headless)
        
        context_options = {
            'viewport': self.config.viewport or {
                'width': self.config.window_size[0],
                'height': self.config.window_size[1]
            },
            'locale': self.config.locale,
            'timezone_id': self.config.timezone,
        }
        
        if self.config.user_agent:
            context_options['user_agent'] = self.config.user_agent
        
        if self.config.proxy:
            context_options['proxy'] = self.config.proxy
        
        self.context = self.browser.new_context(**context_options)
        self.page = self.context.new_page()
    
    async def close_async(self):
        """Close async browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")
    
    def close_sync(self):
        """Close sync browser"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    async def goto(self, url: str, wait_until: str = 'networkidle'):
        """Navigate to URL"""
        await self.page.goto(url, wait_until=wait_until)
        logger.info("Navigated to", url=url)
    
    async def get_content(self) -> str:
        """Get page content"""
        return await self.page.content()
    
    async def click(self, selector: str):
        """Click element"""
        await self.page.click(selector)
    
    async def type_text(self, selector: str, text: str, clear: bool = True):
        """Type text into input"""
        if clear:
            await self.page.fill(selector, text)
        else:
            await self.page.type(selector, text)
    
    async def select_option(self, selector: str, value: Optional[str] = None, 
                          label: Optional[str] = None, index: Optional[int] = None):
        """Select dropdown option"""
        if value:
            await self.page.select_option(selector, value=value)
        elif label:
            await self.page.select_option(selector, label=label)
        elif index is not None:
            await self.page.select_option(selector, index=index)
    
    async def scroll_to_bottom(self):
        """Scroll to page bottom"""
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    
    async def infinite_scroll(self, scroll_pause: float = 2.0, max_scrolls: int = 10):
        """Handle infinite scroll"""
        for _ in range(max_scrolls):
            previous_height = await self.page.evaluate(
                "document.body.scrollHeight"
            )
            await self.scroll_to_bottom()
            await asyncio.sleep(scroll_pause)
            
            new_height = await self.page.evaluate("document.body.scrollHeight")
            if new_height == previous_height:
                break
    
    async def wait_for_selector(self, selector: str, timeout: int = 30000):
        """Wait for element"""
        await self.page.wait_for_selector(selector, timeout=timeout)
    
    async def wait_for_load_state(self, state: str = 'networkidle'):
        """Wait for page load state"""
        await self.page.wait_for_load_state(state)
    
    async def screenshot(self, path: str, full_page: bool = False):
        """Take screenshot"""
        await self.page.screenshot(path=path, full_page=full_page)
        logger.info("Screenshot saved", path=path)
    
    async def pdf(self, path: str):
        """Save page as PDF"""
        await self.page.pdf(path=path)
    
    async def evaluate(self, expression: str) -> Any:
        """Execute JavaScript"""
        return await self.page.evaluate(expression)
    
    async def route_intercept(self, url_pattern: str, handler: Callable):
        """Intercept network requests"""
        await self.page.route(url_pattern, handler)
    
    async def get_cookies(self) -> List[Dict]:
        """Get cookies"""
        return await self.context.cookies()
    
    async def add_cookies(self, cookies: List[Dict]):
        """Add cookies"""
        await self.context.add_cookies(cookies)
    
    async def clear_cookies(self):
        """Clear cookies"""
        await self.context.clear_cookies()
    
    async def scrape(self, url: str, wait_for: Optional[str] = None) -> str:
        """
        Scrape page content
        
        Args:
            url: Target URL
            wait_for: CSS selector to wait for
            
        Returns:
            Page HTML content
        """
        await self.goto(url)
        
        if wait_for:
            await self.wait_for_selector(wait_for)
        
        return await self.get_content()
