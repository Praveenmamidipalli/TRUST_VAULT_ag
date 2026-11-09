import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_2fa_otp_complete_flow():
    """Verifies end-to-end Two-Factor Authentication (OTP):
    1. Register user
    2. Request 2FA challenge with password
    3. Test invalid OTP rejection
    4. Test valid OTP verification & JWT issuance
    5. Test single-use replay prevention (OTP can only be used once)
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register user
        reg = await client.post("/api/v1/auth/register", json={
            "email": "otp_tester@trustvault.io",
            "username": "otp_tester",
            "full_name": "OTP Tester",
            "password": "Password123!",
            "role": "OWNER"
        })
        assert reg.status_code == 201

        # Step 1: Request 2FA OTP
        req_2fa = await client.post("/api/v1/auth/request-2fa", json={
            "username_or_email": "otp_tester",
            "password": "Password123!"
        })
        assert req_2fa.status_code == 200
        data = req_2fa.json()
        assert data["status"] == "2fa_required"
        assert len(data["demo_otp"]) == 6
        assert data["user_id"] > 0
        otp_code = data["demo_otp"]
        user_id = data["user_id"]

        # Step 2: Try invalid OTP code
        bad_verify = await client.post("/api/v1/auth/verify-2fa", json={
            "user_id": user_id,
            "otp_code": "000000"
        })
        assert bad_verify.status_code == 400
        assert "Invalid verification code" in bad_verify.json()["detail"]

        # Step 3: Verify with real OTP code
        good_verify = await client.post("/api/v1/auth/verify-2fa", json={
            "user_id": user_id,
            "otp_code": otp_code
        })
        assert good_verify.status_code == 200
        verify_data = good_verify.json()
        assert "access_token" in verify_data
        assert verify_data["user"]["username"] == "otp_tester"

        # Step 4: Replay prevention test (same OTP cannot be reused)
        replay = await client.post("/api/v1/auth/verify-2fa", json={
            "user_id": user_id,
            "otp_code": otp_code
        })
        assert replay.status_code == 400
        assert "No active verification code found" in replay.json()["detail"]
