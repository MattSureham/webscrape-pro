"""
Caching middleware
"""

import hashlib
import pickle
import time
from typing import Optional, Any
from pathlib import Path

try:
    import diskcache
    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False

from cachetools import TTLCache


class CacheManager:
    """Multi-backend cache manager"""
    
    def __init__(self, backend: str = 'memory', cache_dir: str = '.cache',
                 maxsize: int = 1000, ttl: int = 3600):
        """
        Initialize cache manager
        
        Args:
            backend: 'memory' or 'disk'
            cache_dir: Directory for disk cache
            maxsize: Maximum cache size
            ttl: Time-to-live in seconds
        """
        self.backend = backend
        
        if backend == 'memory':
            self.cache = TTLCache(maxsize=maxsize, ttl=ttl)
        elif backend == 'disk':
            if not DISKCACHE_AVAILABLE:
                raise ImportError("diskcache required for disk backend. "
                                "Install with: pip install diskcache")
            Path(cache_dir).mkdir(parents=True, exist_ok=True)
            self.cache = diskcache.Cache(cache_dir)
        else:
            raise ValueError(f"Unknown backend: {backend}")
    
    def _make_key(self, key: str) -> str:
        """Create safe cache key"""
        return hashlib.md5(key.encode()).hexdigest()
    
    def has(self, key: str) -> bool:
        """Check if key exists in cache"""
        cache_key = self._make_key(key)
        return cache_key in self.cache
    
    def get(self, key: str) -> Any:
        """Get value from cache"""
        cache_key = self._make_key(key)
        if self.backend == 'memory':
            return self.cache.get(cache_key)
        else:
            return self.cache.get(cache_key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        cache_key = self._make_key(key)
        if self.backend == 'memory':
            self.cache[cache_key] = value
        else:
            self.cache.set(cache_key, value, expire=ttl)
    
    def delete(self, key: str):
        """Delete key from cache"""
        cache_key = self._make_key(key)
        if cache_key in self.cache:
            del self.cache[cache_key]
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
    
    def close(self):
        """Close cache (important for disk backend)"""
        if self.backend == 'disk':
            self.cache.close()
