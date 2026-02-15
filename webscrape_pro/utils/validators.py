"""
Validation utilities
"""

import re
from urllib.parse import urlparse
from typing import Optional

import validators
import structlog

logger = structlog.get_logger()


class URLValidator:
    """URL validation utilities"""
    
    def __init__(self, allowed_schemes: Optional[list] = None):
        self.allowed_schemes = allowed_schemes or ['http', 'https']
    
    def validate(self, url: str) -> bool:
        """
        Validate URL format and scheme
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If URL is invalid
        """
        if not url or not isinstance(url, str):
            raise ValueError("URL must be a non-empty string")
        
        if not validators.url(url):
            raise ValueError(f"Invalid URL format: {url}")
        
        parsed = urlparse(url)
        
        if parsed.scheme not in self.allowed_schemes:
            raise ValueError(f"URL scheme must be one of {self.allowed_schemes}")
        
        if not parsed.netloc:
            raise ValueError("URL must have a domain")
        
        return True
    
    def is_valid(self, url: str) -> bool:
        """Check if URL is valid without raising"""
        try:
            return self.validate(url)
        except ValueError:
            return False
    
    def is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are on the same domain"""
        return urlparse(url1).netloc == urlparse(url2).netloc
    
    def is_internal_link(self, base_url: str, link: str) -> bool:
        """Check if link is internal to base URL"""
        link_full = urlparse(link)
        if link_full.netloc:
            return self.is_same_domain(base_url, link)
        return True  # Relative links are internal


class DataValidator:
    """Data validation utilities"""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email address"""
        return validators.email(email) is True
    
    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """Validate phone number (basic)"""
        # Remove common separators
        cleaned = re.sub(r'[\s\-\.\(\)]', '', phone)
        # Check if remaining is digits and reasonable length
        return cleaned.isdigit() and 7 <= len(cleaned) <= 15
    
    @staticmethod
    def extract_emails(text: str) -> list:
        """Extract email addresses from text"""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(pattern, text)
    
    @staticmethod
    def extract_phones(text: str) -> list:
        """Extract phone numbers from text"""
        pattern = r'[\+]?[1-9]?[0-9]{7,15}'
        matches = re.findall(pattern, text)
        return [m for m in matches if len(re.sub(r'\D', '', m)) >= 7]
