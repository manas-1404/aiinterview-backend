from redis.asyncio import Redis

from utils.config import settings

redis_client: Redis = Redis.from_url(settings.REDIS_CLOUD_URL, decode_responses=True)

async def get_redis_connection() -> Redis:
    """
    Dependency to get a Redis connection.
    This function can be used in FastAPI routes to get a Redis connection for caching.
    """
    return redis_client