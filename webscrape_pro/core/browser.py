"""
Selenium-based browser scraper for JavaScript-heavy sites
"""

import time
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import structlog

logger = structlog.get_logger()


@dataclass
class SeleniumConfig:
    """Configuration for Selenium scraper"""
    browser: str = 'chrome'  # chrome, firefox
    headless: bool = True
    window_size: tuple = (1920, 1080)
    page_load_timeout: int = 30
    implicit_wait: int = 10
    user_data_dir: Optional[str] = None
    extensions: List[str] = None
    proxy: Optional[str] = None


class SeleniumScraper:
    """
    Selenium-based scraper for JavaScript-rendered content
    """
    
    def __init__(self, config: Optional[SeleniumConfig] = None):
        self.config = config or SeleniumConfig()
        self.driver: Optional[webdriver.Remote] = None
    
    def _create_driver(self) -> webdriver.Remote:
        """Create and configure webdriver"""
        if self.config.browser == 'chrome':
            return self._create_chrome_driver()
        elif self.config.browser == 'firefox':
            return self._create_firefox_driver()
        else:
            raise ValueError(f"Unsupported browser: {self.config.browser}")
    
    def _create_chrome_driver(self) -> webdriver.Chrome:
        """Create Chrome driver"""
        options = ChromeOptions()
        
        if self.config.headless:
            options.add_argument('--headless')
        
        options.add_argument(f'--window-size={self.config.window_size[0]},{self.config.window_size[1]}')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        if self.config.user_data_dir:
            options.add_argument(f'--user-data-dir={self.config.user_data_dir}')
        
        if self.config.proxy:
            options.add_argument(f'--proxy-server={self.config.proxy}')
        
        if self.config.extensions:
            for ext in self.config.extensions:
                options.add_extension(ext)
        
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(self.config.page_load_timeout)
        driver.implicitly_wait(self.config.implicit_wait)
        
        # Remove webdriver property to avoid detection
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        
        return driver
    
    def _create_firefox_driver(self) -> webdriver.Firefox:
        """Create Firefox driver"""
        options = FirefoxOptions()
        
        if self.config.headless:
            options.add_argument('--headless')
        
        options.add_argument(f'--width={self.config.window_size[0]}')
        options.add_argument(f'--height={self.config.window_size[1]}')
        
        if self.config.proxy:
            proxy_parts = self.config.proxy.replace('http://', '').replace('https://', '').split(':')
            if len(proxy_parts) == 2:
                options.set_preference('network.proxy.type', 1)
                options.set_preference('network.proxy.http', proxy_parts[0])
                options.set_preference('network.proxy.http_port', int(proxy_parts[1]))
        
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)
        driver.set_page_load_timeout(self.config.page_load_timeout)
        driver.implicitly_wait(self.config.implicit_wait)
        
        return driver
    
    def start(self):
        """Initialize the browser"""
        if not self.driver:
            self.driver = self._create_driver()
            logger.info(f"Started {self.config.browser} browser")
    
    def close(self):
        """Close browser and cleanup"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("Browser closed")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def get(self, url: str) -> None:
        """Navigate to URL"""
        self.driver.get(url)
        logger.info("Navigated to", url=url)
    
    def get_page_source(self) -> str:
        """Get current page HTML"""
        return self.driver.page_source
    
    def find_element(self, by: By, value: str, timeout: Optional[int] = None):
        """Find single element with wait"""
        wait = WebDriverWait(self.driver, timeout or self.config.implicit_wait)
        return wait.until(EC.presence_of_element_located((by, value)))
    
    def find_elements(self, by: By, value: str, timeout: Optional[int] = None):
        """Find multiple elements with wait"""
        wait = WebDriverWait(self.driver, timeout or self.config.implicit_wait)
        return wait.until(EC.presence_of_all_elements_located((by, value)))
    
    def click(self, by: By, value: str, timeout: Optional[int] = None):
        """Click element"""
        element = self.find_element(by, value, timeout)
        element.click()
    
    def type_text(self, by: By, value: str, text: str, clear: bool = True, 
                  timeout: Optional[int] = None):
        """Type text into input field"""
        element = self.find_element(by, value, timeout)
        if clear:
            element.clear()
        element.send_keys(text)
    
    def select_dropdown(self, by: By, value: str, option_text: str, 
                        timeout: Optional[int] = None):
        """Select dropdown option by visible text"""
        from selenium.webdriver.support.ui import Select
        element = self.find_element(by, value, timeout)
        select = Select(element)
        select.select_by_visible_text(option_text)
    
    def scroll_to_bottom(self):
        """Scroll to page bottom"""
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    def scroll_to_element(self, element):
        """Scroll element into view"""
        self.driver.execute_script("arguments[0].scrollIntoView();", element)
    
    def infinite_scroll(self, scroll_pause: float = 2.0, max_scrolls: int = 10):
        """
        Handle infinite scroll pages
        
        Args:
            scroll_pause: Seconds to wait between scrolls
            max_scrolls: Maximum scroll attempts
        """
        last_height = self.driver.execute_script(
            "return document.body.scrollHeight"
        )
        
        for _ in range(max_scrolls):
            self.scroll_to_bottom()
            time.sleep(scroll_pause)
            
            new_height = self.driver.execute_script(
                "return document.body.scrollHeight"
            )
            
            if new_height == last_height:
                break
            
            last_height = new_height
    
    def wait_for_element(self, by: By, value: str, timeout: int = 10):
        """Explicit wait for element"""
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_element_located((by, value)))
    
    def wait_for_clickable(self, by: By, value: str, timeout: int = 10):
        """Wait for element to be clickable"""
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.element_to_be_clickable((by, value)))
    
    def wait_for_invisible(self, by: By, value: str, timeout: int = 10):
        """Wait for element to become invisible"""
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.invisibility_of_element_located((by, value)))
    
    def execute_script(self, script: str, *args):
        """Execute JavaScript"""
        return self.driver.execute_script(script, *args)
    
    def screenshot(self, filepath: str, full_page: bool = False):
        """Take screenshot"""
        if full_page:
            original_size = self.driver.get_window_size()
            total_height = self.driver.execute_script(
                "return document.body.parentNode.scrollHeight"
            )
            self.driver.set_window_size(original_size['width'], total_height)
            self.driver.find_element(By.TAG_NAME, 'body').screenshot(filepath)
            self.driver.set_window_size(original_size['width'], original_size['height'])
        else:
            self.driver.save_screenshot(filepath)
        
        logger.info("Screenshot saved", filepath=filepath)
        return filepath
    
    def get_cookies(self) -> List[Dict]:
        """Get all cookies"""
        return self.driver.get_cookies()
    
    def add_cookie(self, cookie: Dict):
        """Add cookie"""
        self.driver.add_cookie(cookie)
    
    def clear_cookies(self):
        """Clear all cookies"""
        self.driver.delete_all_cookies()
    
    def switch_to_frame(self, frame_reference):
        """Switch to iframe"""
        self.driver.switch_to.frame(frame_reference)
    
    def switch_to_default_content(self):
        """Switch back to main content"""
        self.driver.switch_to.default_content()
    
    def handle_alert(self, accept: bool = True):
        """Handle JavaScript alert"""
        alert = self.driver.switch_to.alert
        if accept:
            alert.accept()
        else:
            alert.dismiss()
    
    def scrape(self, url: str, wait_for: Optional[tuple] = None) -> str:
        """
        Scrape page content
        
        Args:
            url: Target URL
            wait_for: Tuple of (By, value) to wait for
            
        Returns:
            Page source HTML
        """
        self.get(url)
        
        if wait_for:
            self.wait_for_element(*wait_for)
        
        return self.get_page_source()
