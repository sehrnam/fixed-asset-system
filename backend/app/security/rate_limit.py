import time
from collections import defaultdict
from threading import Lock

from app.config import settings


class _RateLimiter:
    """Simple in-memory sliding-window limiter. Adequate for a local MVP.

    Note: this is process-local. Under a multi-worker deployment it would need
    to be replaced with a shared store (e.g. Redis). Documented in README.
    """

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max = max_attempts
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            bucket = self._hits[key]
            bucket[:] = [t for t in bucket if now - t < self.window]
            if len(bucket) >= self.max:
                return False
            bucket.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


login_limiter = _RateLimiter(
    max_attempts=settings.login_rate_limit_attempts,
    window_seconds=settings.login_rate_limit_window_seconds,
)