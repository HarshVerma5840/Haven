import json
import redis
import structlog
from typing import Any, Optional, Dict
from app.config import get_settings

logger = structlog.get_logger(__name__)

class CacheService:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        try:
            self.client = redis.from_url(
                redis_url, 
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2
            )
            self._is_connected = True
        except Exception as e:
            logger.warning(f"Failed to initialize Redis client: {e}")
            self.client = None
            self._is_connected = False

    def is_available(self) -> bool:
        if not self._is_connected or not self.client:
            return False
        try:
            return self.client.ping()
        except redis.RedisError:
            return False

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve and deserialize JSON from cache."""
        if not self.is_available():
            return None
        
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except redis.RedisError as e:
            logger.warning(f"Redis get error for {key}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to deserialize cache for {key}: {e}")
            return None

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: int) -> bool:
        """Serialize and store JSON in cache."""
        if not self.is_available():
            return False
        
        # Ensure no raw identity data or tokens are cached
        safe_value = self._sanitize(value)
        
        try:
            json_data = json.dumps(safe_value)
            self.client.setex(key, ttl_seconds, json_data)
            return True
        except redis.RedisError as e:
            logger.warning(f"Redis set error for {key}: {e}")
            return False
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize cache for {key}: {e}")
            return False

    def invalidate(self, pattern: str) -> int:
        """Invalidate keys matching a pattern."""
        if not self.is_available():
            return 0
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except redis.RedisError as e:
            logger.warning(f"Redis invalidate error for {pattern}: {e}")
            return 0

    def _sanitize(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """Strip sensitive fields before caching."""
        if not isinstance(value, dict):
            return value
        
        # Copy to avoid mutating original
        clean_value = value.copy()
        
        # Strip tokens, passwords, raw identities
        sensitive_keys = {"password", "token", "access_token", "refresh_token", 
                          "email", "github_username", "hrms_employee_id"}
                          
        # Note: employee_hash is pseudo-anonymous and acts as the vault key, so it's generally 
        # safe in the cache namespace/values, but raw HRMS IDs are NOT.
        
        for k in list(clean_value.keys()):
            if k.lower() in sensitive_keys:
                clean_value.pop(k, None)
            elif isinstance(clean_value[k], dict):
                clean_value[k] = self._sanitize(clean_value[k])
                
        return clean_value

# Singleton instance
_cache_service_instance = None

def get_cache_service() -> CacheService:
    global _cache_service_instance
    if _cache_service_instance is None:
        settings = get_settings()
        _cache_service_instance = CacheService(settings.redis_url)
    return _cache_service_instance
