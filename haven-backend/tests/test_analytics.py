import pytest
import json
from unittest.mock import patch, MagicMock
from app.services.cache_service import CacheService
from app.api.analytics import _hash_filters

from app.main import app as fastapi_app
from app.security.dependencies import require_hr_admin
from app.services.cache_service import get_cache_service

def mock_require_admin():
    from app.database.models import RoleEnum
    from unittest.mock import MagicMock
    user = MagicMock()
    user.id = 1
    user.role = RoleEnum.HR_ADMIN
    return user

def test_hash_filters():
    # Same JSON, different spacing
    filter1 = '{"dept": "Engineering", "role": "Senior"}'
    filter2 = '{\n  "dept": "Engineering",\n  "role": "Senior"\n}'
    
    assert _hash_filters(filter1) == _hash_filters(filter2)
    
    # Different filter
    filter3 = '{"dept": "Sales"}'
    assert _hash_filters(filter1) != _hash_filters(filter3)

def test_dashboard_cache_hit_and_miss(client):
    mock_cache = MagicMock(spec=CacheService)
    mock_cache.get.return_value = None
    
    fastapi_app.dependency_overrides[require_hr_admin] = mock_require_admin
    fastapi_app.dependency_overrides[get_cache_service] = lambda: mock_cache
    
    response = client.get("/api/v1/analytics/dashboard?department=Engineering")
    assert response.status_code == 200
    
    # Assert cache GET was called
    assert mock_cache.get.called
    
    # Assert cache SET was called
    assert mock_cache.set.called
    
    # Simulate a cache hit for a repeated request
    mock_cache.reset_mock()
    mock_cache.get.return_value = {"department": "Engineering", "cached": True}
    
    response = client.get("/api/v1/analytics/dashboard?department=Engineering")
    assert response.status_code == 200
    assert response.json()["cached"] is True
    
    # Assert cache SET was NOT called
    assert not mock_cache.set.called
    
    fastapi_app.dependency_overrides.clear()

def test_graph_cache_different_filters(client):
    mock_cache = MagicMock(spec=CacheService)
    mock_cache.get.return_value = None
    
    fastapi_app.dependency_overrides[require_hr_admin] = mock_require_admin
    fastapi_app.dependency_overrides[get_cache_service] = lambda: mock_cache
    
    # Request 1
    client.get("/api/v1/analytics/network?graph_type=collab&filters={\"k\":\"v1\"}")
    key1 = mock_cache.get.call_args[0][0]
    
    # Request 2 (different filter)
    client.get("/api/v1/analytics/network?graph_type=collab&filters={\"k\":\"v2\"}")
    key2 = mock_cache.get.call_args[0][0]
    
    # Request 3 (same filter as 1 but different spacing)
    client.get("/api/v1/analytics/network", params={"graph_type": "collab", "filters": "{\n  \"k\": \"v1\"\n}"})
    key3 = mock_cache.get.call_args[0][0]
    
    assert key1 != key2
    assert key1 == key3
    
    fastapi_app.dependency_overrides.clear()

def test_analytics_redis_downtime(client):
    mock_cache = MagicMock(spec=CacheService)
    mock_cache.get.return_value = None
    
    fastapi_app.dependency_overrides[require_hr_admin] = mock_require_admin
    fastapi_app.dependency_overrides[get_cache_service] = lambda: mock_cache
    
    response = client.get("/api/v1/analytics/dashboard?department=Engineering")
    assert response.status_code == 200
    assert response.json()["department"] == "Engineering"
    
    # Even if cache fails, the API gracefully serves the response
    response_network = client.get("/api/v1/analytics/network?graph_type=collab")
    assert response_network.status_code == 200
    assert "nodes" in response_network.json()
    
    fastapi_app.dependency_overrides.clear()
