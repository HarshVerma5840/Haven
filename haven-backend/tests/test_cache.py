import json
import pytest
from unittest.mock import patch, MagicMock
import redis
from app.services.cache_service import CacheService

@pytest.fixture
def cache_service():
    with patch("redis.from_url") as mock_redis:
        # Mock redis instance
        instance = MagicMock()
        mock_redis.return_value = instance
        
        service = CacheService("redis://mock")
        # Ensure it acts as connected
        service._is_connected = True
        return service

def test_cache_miss(cache_service):
    cache_service.client.get.return_value = None
    assert cache_service.get("test_key") is None
    cache_service.client.get.assert_called_once_with("test_key")

def test_cache_hit(cache_service):
    data = {"predicted_risk": "Low", "model_version": "1.0"}
    cache_service.client.get.return_value = json.dumps(data)
    
    result = cache_service.get("test_key")
    assert result == data

def test_cache_set(cache_service):
    data = {"predicted_risk": "High"}
    cache_service.set("test_key", data, 3600)
    
    cache_service.client.setex.assert_called_once()
    args = cache_service.client.setex.call_args[0]
    assert args[0] == "test_key"
    assert args[1] == 3600
    assert json.loads(args[2]) == data

def test_cache_sanitize_sensitive_data(cache_service):
    data = {
        "predicted_risk": "Medium",
        "email": "test@test.com",
        "github_username": "hidden",
        "hrms_employee_id": "123",
        "password": "secret_password",
        "token": "secret_token",
        "access_token": "secret",
        "refresh_token": "secret",
        "nested": {
            "email": "nested@test.com",
            "safe": "value"
        }
    }
    
    cache_service.set("test_key", data, 3600)
    args = cache_service.client.setex.call_args[0]
    cached_data = json.loads(args[2])
    
    assert "email" not in cached_data
    assert "github_username" not in cached_data
    assert "hrms_employee_id" not in cached_data
    assert "password" not in cached_data
    assert "token" not in cached_data
    assert "access_token" not in cached_data
    assert "refresh_token" not in cached_data
    
    assert cached_data["predicted_risk"] == "Medium"
    assert "email" not in cached_data["nested"]
    assert cached_data["nested"]["safe"] == "value"

def test_cache_invalidation(cache_service):
    cache_service.client.keys.return_value = ["dashboard:user1", "dashboard:user1:extras"]
    cache_service.invalidate("dashboard:user1*")
    
    cache_service.client.keys.assert_called_once_with("dashboard:user1*")
    cache_service.client.delete.assert_called_once_with("dashboard:user1", "dashboard:user1:extras")

def test_cache_invalidation_no_keys(cache_service):
    cache_service.client.keys.return_value = []
    cache_service.invalidate("nonexistent*")
    
    cache_service.client.keys.assert_called_once_with("nonexistent*")
    cache_service.client.delete.assert_not_called()

def test_redis_failure_get():
    with patch("redis.from_url") as mock_redis:
        instance = MagicMock()
        instance.get.side_effect = redis.RedisError("Connection lost")
        mock_redis.return_value = instance
        
        service = CacheService("redis://mock")
        # Should catch exception and gracefully return None
        assert service.get("test_key") is None

def test_redis_failure_set():
    with patch("redis.from_url") as mock_redis:
        instance = MagicMock()
        instance.setex.side_effect = redis.RedisError("Connection lost")
        mock_redis.return_value = instance
        
        service = CacheService("redis://mock")
        # Should catch exception and gracefully return False
        assert service.set("test_key", {"data": "test"}, 3600) is False

def test_redis_unavailable_fallback():
    # Simulate failed connection on init
    with patch("redis.from_url", side_effect=redis.RedisError("Cannot connect")):
        service = CacheService("redis://mock")
        assert service.is_available() is False
        assert service.get("test_key") is None
        assert service.set("test_key", {"data": "test"}, 3600) is False
        assert service.invalidate("test_key") == 0

def test_malformed_json_fallback(cache_service):
    # If Redis returns non-JSON data somehow
    cache_service.client.get.return_value = "{invalid_json: true"
    
    # Should catch JSONDecodeError and return None
    assert cache_service.get("test_key") is None
