import secrets
import time
from typing import Dict, Tuple


class OTPService:
    """Manages secure 6-digit Time-based One-Time Passwords (OTP) for 
    Two-Factor Authentication (2FA) with expiration and attempt limiting.
    """
    def __init__(self, expiry_seconds: int = 300):
        self.expiry_seconds = expiry_seconds
        # user_id -> {"otp": str, "expires_at": float, "attempts": int}
        self._store: Dict[int, Dict] = {}

    def generate_otp(self, user_id: int) -> str:
        """Generates a cryptographically secure 6-digit OTP code valid for 5 minutes."""
        code = f"{secrets.randbelow(900000) + 100000}"
        self._store[user_id] = {
            "otp": code,
            "expires_at": time.time() + self.expiry_seconds,
            "attempts": 0
        }
        return code

    def verify_otp(self, user_id: int, code: str) -> Tuple[bool, str]:
        """Verifies an OTP code for a user.
        
        Returns:
            (is_valid, error_message)
        """
        record = self._store.get(user_id)
        if not record:
            return False, "No active verification code found. Please request a new code."

        if time.time() > record["expires_at"]:
            self._store.pop(user_id, None)
            return False, "Verification code has expired (5-minute limit). Please request a new one."

        if record["attempts"] >= 3:
            self._store.pop(user_id, None)
            return False, "Too many failed attempts. This code has been invalidated for security."

        if record["otp"] != code.strip():
            record["attempts"] += 1
            remaining = 3 - record["attempts"]
            return False, f"Invalid verification code. {remaining} attempt(s) remaining."

        # Valid: remove OTP so it cannot be replayed (Strict One-Time Property)
        self._store.pop(user_id, None)
        return True, ""


otp_service = OTPService(expiry_seconds=300)
