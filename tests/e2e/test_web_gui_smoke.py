"""E2E Tests - Web GUI Smoke (no browser)

These tests verify that the web container serves the SPA and that API proxy works.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_web_serves_index_html():
    async with AsyncClient(base_url="http://web") as client:
        r = await client.get("/")
        assert r.status_code == 200
        assert "System B+R" in r.text
        assert "static/js/app.js" in r.text


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_web_serves_static_js():
    async with AsyncClient(base_url="http://web") as client:
        r = await client.get("/static/js/app.js")
        assert r.status_code == 200
        assert "function navigateTo" in r.text


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_web_proxies_api_health():
    async with AsyncClient(base_url="http://web") as client:
        r = await client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "healthy"
