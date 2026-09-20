from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.redis import get_redis


class RateLimiter:
    def __init__(self, times: int = 120, seconds: int = 60) -> None:
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request) -> None:
        if not settings.rate_limit_enabled or settings.is_test:
            return
        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        key = f"rl:{ip}:{request.url.path}"
        try:
            client = await get_redis()
            current = await client.incr(key)
            if current == 1:
                await client.expire(key, self.seconds)
            if current > self.times:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests",
                )
        except HTTPException:
            raise
        except Exception:
            return
