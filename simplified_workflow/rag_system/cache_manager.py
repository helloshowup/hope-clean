#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple Cache Manager for RAG system.

Provides a two-tier (memory + disk) caching system optimized for local usage.
"""

import os
import json
import hashlib
import time
import logging
from functools import lru_cache
from typing import Dict, Any, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)


class SimpleCacheManager:
    """Two-tier cache focused on essentials with better error handling"""
    
    def __init__(self, cache_dir: str = "./cache", memory_size: int = 100):
        """Initialize the cache manager
        
        Args:
            cache_dir: Directory to store cache files
            memory_size: Maximum number of items to keep in memory cache
        """
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            logger.info(f"Created cache directory: {cache_dir}")
        
        # Create a memory cache with the lru_cache decorator
        self._get_from_disk = lru_cache(maxsize=memory_size)(self._load_from_disk)
        
        # Simple stats tracking
        self.hits = 0
        self.misses = 0
        
        logger.info(f"Initialized cache manager with memory size {memory_size}")
    
    def get_cache_key(self, content_type: str, params: Union[Dict, str]) -> str:
        """Generate cache key based on content type and parameters
        
        Args:
            content_type: Type of content being cached (e.g., 'generation', 'embedding')
            params: Parameters that uniquely identify the cached content
            
        Returns:
            MD5 hash to use as cache key
        """
        # Convert params to a stable string format
        if isinstance(params, dict):
            # Sort keys to ensure consistent hashing
            key_content = json.dumps(params, sort_keys=True)
        else:
            key_content = str(params)
        
        # Combine content type and params for the full key
        full_key = f"{content_type}:{key_content}"
        return hashlib.md5(full_key.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> str:
        """Get file path for a cache key"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def _load_from_disk(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load cache entry from disk - wrapped by lru_cache decorator
        
        Args:
            cache_key: Cache key to load
            
        Returns:
            Cache data or None if not found/invalid
        """
        cache_path = self._get_cache_path(cache_key)
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.exception(f"Invalid JSON in cache file: {cache_path}")
                # Remove corrupt cache file
                try:
                    os.remove(cache_path)
                    logger.info(f"Removed corrupt cache file: {cache_path}")
                except Exception as e:
                    logger.error(f"Failed to remove corrupt cache file: {e}")
            except Exception as e:
                logger.exception(f"Failed to load cache from {cache_path}: {e}")
        
        return None
    
    def get(self, cache_key: str, max_age: int = 86400) -> Optional[Any]:
        """Get cached value, respecting max age
        
        Args:
            cache_key: Cache key to retrieve
            max_age: Maximum age in seconds for valid cache
            
        Returns:
            Cached data or None if not found/expired
        """
        # Check memory and disk cache
        cache_data = self._get_from_disk(cache_key)
        
        if cache_data:
            # Check if cache is expired
            timestamp = cache_data.get('timestamp', 0)
            if time.time() - timestamp <= max_age:
                self.hits += 1
                logger.debug(f"Cache hit for key: {cache_key}")
                return cache_data.get('data')
            else:
                logger.debug(f"Cache expired for key: {cache_key}")
        
        self.misses += 1
        logger.debug(f"Cache miss for key: {cache_key}")
        return None
    
    def set(self, cache_key: str, data: Any) -> bool:
        """Set cache value in both memory and disk
        
        Args:
            cache_key: Cache key to store under
            data: Data to cache
            
        Returns:
            True if successful, False otherwise
        """
        cache_data = {
            'timestamp': time.time(),
            'data': data
        }
        
        # Save to disk
        cache_path = self._get_cache_path(cache_key)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False)
                
            # Invalidate memory cache to ensure fresh data is loaded next time
            self._get_from_disk.cache_clear()
            logger.debug(f"Cache set for key: {cache_key}")
            
            return True
        except Exception as e:
            logger.exception(f"Failed to save cache to {cache_path}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get basic cache statistics
        
        Returns:
            Dict with hits, misses, and hit rate
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / max(1, total)) * 100
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'cache_entries': len(os.listdir(self.cache_dir))
        }
    
    def clear_expired(self, max_age: int = 86400) -> int:
        """Clear expired entries from disk cache
        
        Args:
            max_age: Maximum age in seconds for valid cache
            
        Returns:
            Number of entries cleared
        """
        cleared = 0
        now = time.time()
        
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.json'):
                continue
                
            cache_path = os.path.join(self.cache_dir, filename)
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                timestamp = cache_data.get('timestamp', 0)
                if now - timestamp > max_age:
                    os.remove(cache_path)
                    cleared += 1
                    logger.debug(f"Cleared expired cache: {filename}")
            except Exception as e:
                # Skip files with errors but log them
                logger.exception(f"Error checking cache file {filename}: {e}")
        
        # Clear memory cache after clearing disk entries
        self._get_from_disk.cache_clear()
        
        if cleared > 0:
            logger.info(f"Cleared {cleared} expired cache entries")
        
        return cleared


# Create a singleton instance for easy import
cache = SimpleCacheManager()


if __name__ == "__main__":
    # Simple self-test
    logging.basicConfig(level=logging.INFO)
    
    # Test cache operations
    test_cache = SimpleCacheManager(cache_dir="./test_cache")
    
    # Test setting and getting
    key1 = test_cache.get_cache_key("test", {"param1": "value1", "param2": 123})
    test_cache.set(key1, {"result": "This is a test result"})
    
    # Get the value back
    result = test_cache.get(key1)
    print(f"Retrieved from cache: {result}")
    
    # Check stats
    stats = test_cache.get_stats()
    print(f"Cache stats: {stats}")
