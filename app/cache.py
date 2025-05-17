import os
import json
import time
import hashlib
import threading
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

class Cache:
    """File-based cache for processed URLs with thread-safe operations."""
    
    def __init__(self, cache_dir: str = None, ttl_hours: int = 24):
        """
        Initialize the cache.
        
        Args:
            cache_dir: Directory to store cache files (defaults to app/cache)
            ttl_hours: Time-to-live for cache entries in hours (default: 24)
        """
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), 'cache')
        self.ttl_seconds = ttl_hours * 3600
        self._lock = threading.Lock()
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def _get_cache_key(self, url: str) -> str:
        """Generate a cache key from a URL."""
        return hashlib.sha256(url.encode()).hexdigest()
        
    def _get_cache_path(self, url: str) -> str:
        """Get the full path for a cache file."""
        return os.path.join(self.cache_dir, f"{self._get_cache_key(url)}.json")
        
    def get(self, url: str, encode_base64: bool = True) -> Optional[Dict]:
        """
        Get a cached result for a URL.
        
        Args:
            url: The URL to look up
            encode_base64: Whether to include base64-encoded video data in the response
            
        Returns:
            Cached result if found and not expired, None otherwise
        """
        cache_path = self._get_cache_path(url)
        
        with self._lock:
            try:
                if not os.path.exists(cache_path):
                    return None
                    
                # Check if cache is expired
                if time.time() - os.path.getmtime(cache_path) > self.ttl_seconds:
                    os.remove(cache_path)
                    return None
                    
                # Load and return cached data
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    
                # If encode_base64 is False, only remove video base64 data
                if not encode_base64 and 'videos' in data:
                    for video in data['videos']:
                        for scene in video.get('scenes', []):
                            scene.pop('video', None)
                            
                return data
                
            except Exception as e:
                print(f"Cache error for {url}: {e}")
                return None
                
    def set(self, url: str, data: Dict) -> None:
        """
        Cache a result for a URL.
        
        Args:
            url: The URL to cache
            data: The data to cache
        """
        cache_path = self._get_cache_path(url)
        
        with self._lock:
            try:
                # Add cache metadata
                cache_data = {
                    'url': url,
                    'cached_at': datetime.utcnow().isoformat(),
                    'data': data
                }
                
                # Write to cache file
                with open(cache_path, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                    
            except Exception as e:
                print(f"Cache write error for {url}: {e}")
                
    def clear(self, older_than_hours: Optional[int] = None) -> None:
        """
        Clear the cache.
        
        Args:
            older_than_hours: If provided, only clear entries older than this many hours
        """
        with self._lock:
            try:
                now = time.time()
                for cache_file in Path(self.cache_dir).glob('*.json'):
                    if older_than_hours is None or (now - cache_file.stat().st_mtime) > (older_than_hours * 3600):
                        cache_file.unlink()
            except Exception as e:
                print(f"Cache clear error: {e}")
                
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            try:
                cache_files = list(Path(self.cache_dir).glob('*.json'))
                total_size = sum(f.stat().st_size for f in cache_files)
                oldest = min((f.stat().st_mtime for f in cache_files), default=0)
                newest = max((f.stat().st_mtime for f in cache_files), default=0)
                
                return {
                    'total_entries': len(cache_files),
                    'total_size_bytes': total_size,
                    'oldest_entry': datetime.fromtimestamp(oldest).isoformat() if oldest else None,
                    'newest_entry': datetime.fromtimestamp(newest).isoformat() if newest else None,
                    'ttl_hours': self.ttl_seconds / 3600
                }
            except Exception as e:
                print(f"Cache stats error: {e}")
                return {} 