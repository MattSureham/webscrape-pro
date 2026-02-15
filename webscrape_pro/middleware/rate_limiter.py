"""
Rate limiting and throttling
"""

import time
import threading
from typing import Optional
from collections import deque
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_second: float = 1.0
    requests_per_minute: Optional[int] = None
    burst_size: int = 5


class TokenBucket:
    """Token bucket rate limiter"""
    
    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket
        
        Args:
            rate: Tokens added per second
            capacity: Maximum tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = threading.Lock()
    
    def _add_tokens(self):
        """Add tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.rate
        )
        self.last_update = now
    
    def acquire(self, tokens: int = 1, blocking: bool = True) -> bool:
        """
        Acquire tokens from bucket
        
        Args:
            tokens: Number of tokens to acquire
            blocking: Whether to wait for tokens
            
        Returns:
            True if tokens acquired
        """
        with self._lock:
            self._add_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            if not blocking:
                return False
            
            # Calculate wait time
            deficit = tokens - self.tokens
            wait_time = deficit / self.rate
            
        time.sleep(wait_time)
        
        with self._lock:
            self._add_tokens()
            self.tokens -= tokens
        
        return True


class SlidingWindowRateLimiter:
    """Sliding window rate limiter"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize sliding window limiter
        
        Args:
            max_requests: Maximum requests in window
            window_seconds: Window size in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self._lock = threading.Lock()
    
    def _clean_old_requests(self):
        """Remove requests outside the window"""
        cutoff = time.time() - self.window_seconds
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
    
    def acquire(self, blocking: bool = True) -> bool:
        """
        Try to acquire a request slot
        
        Args:
            blocking: Whether to wait for slot
            
        Returns:
            True if slot acquired
        """
        while True:
            with self._lock:
                self._clean_old_requests()
                
                if len(self.requests) < self.max_requests:
                    self.requests.append(time.time())
                    return True
                
                if not blocking:
                    return False
                
                # Calculate wait time
                wait_time = self.requests[0] + self.window_seconds - time.time()
            
            if wait_time > 0:
                time.sleep(wait_time)


class AdaptiveRateLimiter:
    """Rate limiter that adapts based on response codes"""
    
    def __init__(self, initial_rps: float = 2.0, min_rps: float = 0.1,
                 max_rps: float = 10.0):
        self.current_rps = initial_rps
        self.min_rps = min_rps
        self.max_rps = max_rps
        self.bucket = TokenBucket(initial_rps, int(initial_rps * 2))
    
    def report_response(self, status_code: int):
        """Adjust rate based on response"""
        if status_code == 429:  # Too Many Requests
            self.current_rps = max(self.min_rps, self.current_rps * 0.5)
            self.bucket = TokenBucket(self.current_rps, int(self.current_rps * 2))
            logger.warning("Rate limited, reducing speed", new_rps=self.current_rps)
        elif status_code < 400:
            # Gradually increase rate on success
            self.current_rps = min(self.max_rps, self.current_rps * 1.1)
            self.bucket = TokenBucket(self.current_rps, int(self.current_rps * 2))
    
    def acquire(self):
        """Acquire permission to make request"""
        return self.bucket.acquire()
