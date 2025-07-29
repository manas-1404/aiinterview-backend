import redis
from utils.config import settings

def get_redis_connection():
    """
    Dependency to get a Redis connection.
    This function can be used in FastAPI routes to get a Redis connection for caching.
    """
    redis_client = redis.Redis.from_url(settings.REDIS_CLOUD_URL)

    try:
        yield redis_client
    finally:
        pass