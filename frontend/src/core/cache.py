# ==============================================
# CACHE MANAGER
# ==============================================

import time
import json
import hashlib
from typing import Any, Optional
import asyncio
from collections import OrderedDict

class CacheManager:
    """Client-side caching for API responses."""
    
    def __init__(self, max_size: int = 100, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl  # Time to live in seconds
        self.cache = OrderedDict()
        self.lock = asyncio.Lock()
    
    def _make_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = {
            "args": args,
            "kwargs": kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        async with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                
                if time.time() - timestamp < self.ttl:
                    # Move to end (LRU)
                    self.cache.move_to_end(key)
                    return value
                else:
                    # Expired
                    del self.cache[key]
            
            return None
    
    async def set(self, key: str, value: Any):
        """Set value in cache."""
        async with self.lock:
            # Remove oldest if at capacity
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
            
            self.cache[key] = (value, time.time())
    
    async def clear(self):
        """Clear all cache entries."""
        async with self.lock:
            self.cache.clear()
    
    async def remove(self, key: str):
        """Remove specific key from cache."""
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def cache_decorator(self, ttl: Optional[int] = None):
        """Decorator for caching async function results."""
        cache_ttl = ttl or self.ttl
        
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._make_key(func.__name__, *args, **kwargs)
                
                # Try to get from cache
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                await self.set(cache_key, result)
                
                return result
            
            return wrapper
        
        return decorator
