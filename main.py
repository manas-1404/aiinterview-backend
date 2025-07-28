from fastapi import FastAPI
import redis
from utils.config import settings
app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

@app.get("/hit-redis")
async def hit_redis():
    redis_connection = redis.Redis.from_url(settings.REDIS_CLOUD_URL)

    return {"message": redis_connection.ping()}
