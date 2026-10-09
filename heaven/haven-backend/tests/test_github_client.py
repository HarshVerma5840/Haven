import pytest
import httpx
import asyncio
from app.services.github_client import (
    GitHubClient,
    GitHubUnauthorizedError,
    GitHubForbiddenError,
    GitHubNetworkTimeoutError,
    GitHubExhaustedRetriesError,
    GitHubUnexpectedAPIResponseError
)
from app.config import get_settings

class MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, handler):
        self.handler = handler
        self.calls = []
        
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        return await self.handler(request)

@pytest.fixture
def mock_client_factory():
    def _make_client(handler):
        transport = MockTransport(handler)
        client = GitHubClient(transport=transport)
        return client, transport
    return _make_client

@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

@pytest.mark.anyio
async def test_authentication_headers(mock_client_factory, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test_secret_token")
    
    async def handler(request):
        return httpx.Response(200, json={"message": "ok"})
        
    client, transport = mock_client_factory(handler)
    assert client.client.headers.get("authorization") == "Bearer test_secret_token"
    
    await client.get("/user")
    assert len(transport.calls) == 1
    assert transport.calls[0].headers.get("authorization") == "Bearer test_secret_token"

@pytest.mark.anyio
async def test_pagination(mock_client_factory):
    call_count = 0
    async def handler(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            headers = {"Link": '<https://api.github.com/repos?page=2>; rel="next"'}
            return httpx.Response(200, json=[{"id": 1}], headers=headers)
        elif call_count == 2:
            return httpx.Response(200, json=[{"id": 2}])
            
    client, transport = mock_client_factory(handler)
    results = await client.get_paginated("/repos")
    
    assert len(transport.calls) == 2
    assert len(results) == 2
    assert results[0]["id"] == 1
    assert results[1]["id"] == 2

@pytest.mark.anyio
async def test_timeout(mock_client_factory):
    async def handler(request):
        raise httpx.TimeoutException("Timeout")
        
    client, transport = mock_client_factory(handler)
    with pytest.raises(GitHubNetworkTimeoutError):
        await client.get("/user")
    
    # Should have retried up to max_retries
    assert len(transport.calls) == client.max_retries + 1

@pytest.mark.anyio
async def test_unauthorized_response(mock_client_factory):
    async def handler(request):
        return httpx.Response(401, json={"message": "Bad credentials"})
        
    client, transport = mock_client_factory(handler)
    with pytest.raises(GitHubUnauthorizedError):
        await client.get("/user")
    
    assert len(transport.calls) == 1

@pytest.mark.anyio
async def test_rate_limit_response(mock_client_factory):
    async def handler(request):
        headers = {"x-ratelimit-remaining": "0"}
        return httpx.Response(403, json={"message": "Rate limit exceeded"}, headers=headers)
        
    client, transport = mock_client_factory(handler)
    with pytest.raises(GitHubForbiddenError) as exc:
        await client.get("/user")
    
    assert "Rate limit exceeded" in str(exc.value)

@pytest.mark.anyio
async def test_server_error_and_retry(mock_client_factory):
    call_count = 0
    async def handler(request):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return httpx.Response(500, json={"message": "Internal error"})
        return httpx.Response(200, json={"message": "success"})
        
    client, transport = mock_client_factory(handler)
    result = await client.get("/user")
    
    assert result == {"message": "success"}
    assert len(transport.calls) == 3

@pytest.mark.anyio
async def test_server_error_exhausted(mock_client_factory):
    async def handler(request):
        return httpx.Response(500, json={"message": "Internal error"})
        
    client, transport = mock_client_factory(handler)
    with pytest.raises(GitHubExhaustedRetriesError):
        await client.get("/user")
        
    assert len(transport.calls) == client.max_retries + 1

@pytest.mark.anyio
async def test_malformed_json(mock_client_factory):
    async def handler(request):
        return httpx.Response(200, content=b"invalid json")
        
    client, transport = mock_client_factory(handler)
    with pytest.raises(GitHubUnexpectedAPIResponseError) as exc:
        await client.get("/user")
        
    assert "Malformed JSON response" in str(exc.value)

@pytest.mark.anyio
async def test_empty_result_pages(mock_client_factory):
    async def handler(request):
        return httpx.Response(200, json=[])
        
    client, transport = mock_client_factory(handler)
    results = await client.get_paginated("/repos")
    
    assert results == []
    assert len(transport.calls) == 1
