"""
HTML parsing utilities
"""

import re
from typing import List, Dict, Optional, Any, Callable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag
import structlog

logger = structlog.get_logger()


class HTMLParser:
    """Advanced HTML parsing utilities"""
    
    def __init__(self, html: str, parser: str = 'html.parser'):
        self.soup = BeautifulSoup(html, parser)
    
    @classmethod
    def from_response(cls, response, parser: str = 'html.parser'):
        """Create parser from requests response"""
        return cls(response.content, parser)
    
    def find_text(self, selector: str, strip: bool = True) -> Optional[str]:
        """Find text by CSS selector"""
        element = self.soup.select_one(selector)
        if element:
            text = element.get_text(strip=strip)
            return text
        return None
    
    def find_all_text(self, selector: str, strip: bool = True) -> List[str]:
        """Find all text by CSS selector"""
        elements = self.soup.select(selector)
        return [el.get_text(strip=strip) for el in elements]
    
    def find_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """Find attribute by CSS selector"""
        element = self.soup.select_one(selector)
        if element:
            return element.get(attribute)
        return None
    
    def find_all_attributes(self, selector: str, attribute: str) -> List[str]:
        """Find all attributes by CSS selector"""
        elements = self.soup.select(selector)
        return [el.get(attribute) for el in elements if el.get(attribute)]
    
    def extract_table(self, selector: str, headers: Optional[List[str]] = None) -> List[Dict]:
        """
        Extract data from HTML table
        
        Args:
            selector: CSS selector for the table
            headers: Optional header names (auto-detected if not provided)
            
        Returns:
            List of dictionaries representing table rows
        """
        table = self.soup.select_one(selector)
        if not table:
            return []
        
        rows = []
        
        # Get headers
        if headers is None:
            header_cells = table.find_all('th')
            headers = [th.get_text(strip=True) for th in header_cells]
        
        # Get data rows
        data_rows = table.find_all('tr')[1:] if table.find_all('th') else table.find_all('tr')
        
        for row in data_rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) == len(headers):
                row_data = {}
                for header, cell in zip(headers, cells):
                    row_data[header] = cell.get_text(strip=True)
                rows.append(row_data)
        
        return rows
    
    def extract_links(self, base_url: Optional[str] = None, 
                     pattern: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Extract all links from page
        
        Args:
            base_url: Base URL for resolving relative links
            pattern: Regex pattern to filter URLs
            
        Returns:
            List of dicts with 'text', 'url', 'title' keys
        """
        links = []
        
        for link in self.soup.find_all('a', href=True):
            href = link['href']
            
            # Resolve relative URLs
            if base_url:
                href = urljoin(base_url, href)
            
            # Filter by pattern
            if pattern and not re.search(pattern, href):
                continue
            
            links.append({
                'text': link.get_text(strip=True),
                'url': href,
                'title': link.get('title', ''),
            })
        
        return links
    
    def extract_images(self, base_url: Optional[str] = None) -> List[Dict[str, str]]:
        """Extract all images from page"""
        images = []
        
        for img in self.soup.find_all('img'):
            src = img.get('src', '')
            if base_url and src:
                src = urljoin(base_url, src)
            
            images.append({
                'src': src,
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
                'width': img.get('width', ''),
                'height': img.get('height', ''),
            })
        
        return images
    
    def extract_forms(self) -> List[Dict[str, Any]]:
        """Extract all forms from page with their fields"""
        forms = []
        
        for form in self.soup.find_all('form'):
            form_data = {
                'action': form.get('action', ''),
                'method': form.get('method', 'get').upper(),
                'name': form.get('name', ''),
                'id': form.get('id', ''),
                'fields': []
            }
            
            for field in form.find_all(['input', 'textarea', 'select']):
                field_data = {
                    'name': field.get('name', ''),
                    'type': field.get('type', field.name),
                    'id': field.get('id', ''),
                    'required': field.get('required') is not None,
                    'value': field.get('value', ''),
                    'placeholder': field.get('placeholder', ''),
                }
                
                # Handle select options
                if field.name == 'select':
                    field_data['options'] = [
                        {'value': opt.get('value', ''), 
                         'text': opt.get_text(strip=True)}
                        for opt in field.find_all('option')
                    ]
                
                form_data['fields'].append(field_data)
            
            forms.append(form_data)
        
        return forms
    
    def extract_metadata(self) -> Dict[str, str]:
        """Extract page metadata (title, description, OG tags, etc.)"""
        metadata = {}
        
        # Title
        title_tag = self.soup.find('title')
        metadata['title'] = title_tag.get_text(strip=True) if title_tag else ''
        
        # Meta tags
        for meta in self.soup.find_all('meta'):
            name = meta.get('name', meta.get('property', ''))
            content = meta.get('content', '')
            if name and content:
                metadata[name] = content
        
        # Canonical URL
        canonical = self.soup.find('link', rel='canonical')
        if canonical:
            metadata['canonical'] = canonical.get('href', '')
        
        return metadata
    
    def remove_elements(self, selectors: List[str]):
        """Remove elements matching selectors"""
        for selector in selectors:
            for element in self.soup.select(selector):
                element.decompose()
        return self
    
    def clean_text(self) -> str:
        """Extract clean text content"""
        # Remove script and style elements
        for element in self.soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
        
        # Get text and clean up whitespace
        text = self.soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def extract_structured_data(self) -> List[Dict]:
        """Extract JSON-LD structured data"""
        structured_data = []
        
        for script in self.soup.find_all('script', type='application/ld+json'):
            try:
                import json
                data = json.loads(script.string)
                structured_data.append(data)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return structured_data


class URLParser:
    """URL parsing and manipulation utilities"""
    
    @staticmethod
    def parse(url: str) -> Dict[str, str]:
        """Parse URL into components"""
        parsed = urlparse(url)
        return {
            'scheme': parsed.scheme,
            'netloc': parsed.netloc,
            'path': parsed.path,
            'params': parsed.params,
            'query': parsed.query,
            'fragment': parsed.fragment,
            'hostname': parsed.hostname,
            'port': parsed.port,
        }
    
    @staticmethod
    def join(base: str, url: str) -> str:
        """Join base URL with relative URL"""
        return urljoin(base, url)
    
    @staticmethod
    def get_domain(url: str) -> str:
        """Extract domain from URL"""
        return urlparse(url).netloc
    
    @staticmethod
    def get_path(url: str) -> str:
        """Extract path from URL"""
        return urlparse(url).path
    
    @staticmethod
    def add_params(url: str, params: Dict[str, str]) -> str:
        """Add query parameters to URL"""
        from urllib.parse import urlencode, parse_qs, urlunparse
        
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        query.update(params)
        new_query = urlencode(query, doseq=True)
        
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
    
    @staticmethod
    def normalize(url: str) -> str:
        """Normalize URL"""
        parsed = urlparse(url)
        
        # Convert to lowercase domain
        netloc = parsed.netloc.lower()
        
        # Remove default ports
        if ':80' in netloc and parsed.scheme == 'http':
            netloc = netloc.replace(':80', '')
        if ':443' in netloc and parsed.scheme == 'https':
            netloc = netloc.replace(':443', '')
        
        # Remove trailing slash from path
        path = parsed.path.rstrip('/') if parsed.path != '/' else parsed.path
        
        from urllib.parse import urlunparse
        return urlunparse((
            parsed.scheme.lower(),
            netloc,
            path,
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
