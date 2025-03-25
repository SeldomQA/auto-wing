import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Any, Optional


class CacheManager:
    """
    Manages caching of AI responses to improve performance.
    """

    def __init__(self, cache_dir: str = ".auto-wing/cache", ttl_days: int = 7):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_days: Number of days to keep cache entries
        """
        self.cache_dir = cache_dir
        self.ttl_days = ttl_days
        os.makedirs(cache_dir, exist_ok=True)

    def _generate_cache_key(self, prompt: str, context: dict) -> str:
        """Generate a unique cache key based on prompt and context."""
        # Create a string combining prompt and relevant context
        cache_str = f"{prompt}:{json.dumps(context, sort_keys=True)}"
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> str:
        """Get the file path for a cache entry."""
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def get(self, prompt: str, context: dict) -> Optional[Any]:
        """
        Get a cached response if available and not expired.
        """
        cache_key = self._generate_cache_key(prompt, context)
        cache_path = self._get_cache_path(cache_key)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Check if cache has expired
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cached_time > timedelta(days=self.ttl_days):
                os.remove(cache_path)
                return None

            return cache_data['response']
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def set(self, prompt: str, context: dict, response: Any) -> None:
        """
        Cache a response.
        """
        cache_key = self._generate_cache_key(prompt, context)
        cache_path = self._get_cache_path(cache_key)

        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt,
            'context': context,
            'response': response
        }

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

    def clear(self, days: Optional[int] = None) -> None:
        """
        Clear expired cache entries.
        
        Args:
            days: Optional number of days, defaults to ttl_days
        """
        if days is None:
            days = self.ttl_days

        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.json'):
                continue

            filepath = os.path.join(self.cache_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                cached_time = datetime.fromisoformat(cache_data['timestamp'])
                if datetime.now() - cached_time > timedelta(days=days):
                    os.remove(filepath)
            except (json.JSONDecodeError, KeyError, ValueError):
                # Remove invalid cache files
                os.remove(filepath)
