"""Fixed-window rate limiter. Redis when FV_REDIS_URL is set (shared between workers), otherwise in-process memory."""
import threading
import time
from collections import defaultdict

from app.core.config import get_settings
from app.core.errors import AppError

_lock = threading.Lock()
_mem: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
_redis = None


def _client():
    global _redis
    url = get_settings().redis_url
    if not url:
        return None
    if _redis is None:
        import redis
        _redis = redis.Redis.from_url(url, socket_timeout=0.5)
    return _redis


def hit(key: str, limit: int, window: int = 60) -> tuple[bool, int]:
    """Returns (allowed, retry_after_seconds)."""
    bucket = int(time.time() // window)
    r = _client()
    if r is not None:
        try:
            k = f"rl:{key}:{bucket}"
            n = r.incr(k)
            if n == 1:
                r.expire(k, window + 1)
            return n <= limit, window - int(time.time() % window)
        except Exception:  # noqa: BLE001, S110  Redis down: fall back to the in-memory limiter rather than blocking everyone
            pass
    with _lock:
        b, n = _mem[key]
        n = n + 1 if b == bucket else 1
        _mem[key] = (bucket, n)
        if len(_mem) > 50_000:
            _mem.clear()
        return n <= limit, window - int(time.time() % window)


def enforce(key: str, limit: int, window: int = 60) -> None:
    ok, retry = hit(key, limit, window)
    if not ok:
        raise AppError(429, "rate_limited", "Too many requests. Please slow down.", headers={"Retry-After": str(retry)})


def reset_memory() -> None:
    with _lock:
        _mem.clear()
