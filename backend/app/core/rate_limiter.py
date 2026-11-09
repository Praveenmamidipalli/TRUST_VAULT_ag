import time
from collections import defaultdict
from threading import Lock
from typing import Tuple


class AuthRateLimiter:
    """Thread-safe in-memory sliding window rate limiter to defend against brute-force
    and credential stuffing attacks on authentication endpoints.
    """
    def __init__(self, max_attempts: int = 5, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts = defaultdict(list)
        self._lock = Lock()

    def is_rate_limited(self, key: str) -> Tuple[bool, int]:
        """Checks if a key (IP or identifier) is rate limited.
        
        Returns:
            (is_limited, retry_after_seconds)
        """
        now = time.time()
        with self._lock:
            # Clean expired timestamps outside the rolling window
            timestamps = [t for t in self._attempts[key] if now - t < self.window_seconds]
            self._attempts[key] = timestamps

            if len(timestamps) >= self.max_attempts:
                oldest = timestamps[0]
                retry_after = max(1, int(self.window_seconds - (now - oldest)))
                return True, retry_after
            return False, 0

    def record_failure(self, key: str):
        """Records a failed authentication attempt."""
        now = time.time()
        with self._lock:
            self._attempts[key].append(now)

    def reset(self, key: str):
        """Clears recorded attempts upon successful authentication."""
        with self._lock:
            self._attempts.pop(key, None)


auth_rate_limiter = AuthRateLimiter(max_attempts=5, window_seconds=60)
