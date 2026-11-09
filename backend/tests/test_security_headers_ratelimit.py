import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.rate_limiter import auth_rate_limiter


@pytest.mark.asyncio
async def test_security_headers_present():
    """Verifies that all OWASP security headers are returned on API responses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert "max-age=31536000" in resp.headers.get("strict-transport-security", "")
        assert resp.headers.get("x-xss-protection") == "1; mode=block"


@pytest.mark.asyncio
async def test_auth_rate_limiting_blocks_brute_force():
    """Verifies that 5 rapid failed login attempts trigger HTTP 429 Too Many Requests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Reset limiter for test key
        auth_rate_limiter.reset("127.0.0.1:brute_test_user")

        # 5 failed attempts
        for _ in range(5):
            r = await client.post("/api/v1/auth/login", json={
                "username_or_email": "brute_test_user",
                "password": "WrongPassword123!"
            })
            assert r.status_code in (401, 429)

        # 6th attempt MUST be blocked by rate limiter with 429
        blocked_resp = await client.post("/api/v1/auth/login", json={
            "username_or_email": "brute_test_user",
            "password": "WrongPassword123!"
        })
        assert blocked_resp.status_code == 429
        assert "Rate limit exceeded" in blocked_resp.json()["detail"]
        assert "retry-after" in blocked_resp.headers

        # Cleanup
        auth_rate_limiter.reset("127.0.0.1:brute_test_user")
