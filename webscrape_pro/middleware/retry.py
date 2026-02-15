"""
Retry middleware with exponential backoff
"""

import time
import random
from typing import Callable, TypeVar, Tuple, Optional
from functools import wraps

import structlog

logger = structlog.get_logger()

T = TypeVar('T')


class RetryManager:
    """Retry logic with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 60.0, exponential_base: float = 2.0,
                 retry_exceptions: Optional[Tuple[type, ...]] = None):
        """
        Initialize retry manager
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff
            retry_exceptions: Tuple of exceptions to retry on
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retry_exceptions = retry_exceptions or (Exception,)
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay with jitter"""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        # Add jitter (±25%)
        jitter = delay * 0.25
        return delay + random.uniform(-jitter, jitter)
    
    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with retry logic
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except self.retry_exceptions as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        "Retry attempt failed",
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        delay=delay,
                        error=str(e)
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "All retry attempts failed",
                        max_retries=self.max_retries,
                        error=str(e)
                    )
        
        raise last_exception


def retry(max_retries: int = 3, delay: float = 1.0, 
          exceptions: Tuple[type, ...] = (Exception,)):
    """
    Decorator for retry logic
    
    Args:
        max_retries: Maximum retry attempts
        delay: Delay between retries
        exceptions: Exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = RetryManager(
                max_retries=max_retries,
                base_delay=delay,
                retry_exceptions=exceptions
            )
            return manager.execute(func, *args, **kwargs)
        return wrapper
    return decorator
