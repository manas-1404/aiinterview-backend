from fastapi import APIRouter, Depends, Request, HTTPException
import httpx
from redis.asyncio import Redis

from db.redisConnection import get_redis_connection
from pydantic_schemas.response_pydantic import ResponseSchema
from dependency.httpclient_dependency import get_http_client
from utils.config import settings

agent_router = APIRouter(
    prefix="/interviewagent",
    tags=["interviewagent"]
)

# client: httpx.AsyncClient = None

@agent_router.get("/create-session")
async def create_agent_session(http_client: httpx.AsyncClient = Depends(get_http_client), redis_connection: Redis = Depends(get_redis_connection)):
    """
    Endpoint to create a new interview agent session.
    """

    # TODO: get the userid from auth jwt tokens
    user_id = 100

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.PALANTIR_API_KEY}"
    }

    payload = {
        "agentVersion": "1.0"
    }

    redis_hash_key = "interview_agent_session_key"
    redis_hash_field = f"user:{user_id}"

    cached_agent_session_id = await redis_connection.hget(redis_hash_key, redis_hash_field)

    if cached_agent_session_id:
        return ResponseSchema(
            success=True,
            status_code=200,
            message="Session already exists",
            data={"session_id": cached_agent_session_id}
        )

    try:
        response = await http_client.post(
            url=f"{settings.PALANTIR_PROJECT_URL}/api/v2/aipAgents/agents/{settings.INTERVIEWER_AGENT_RID}/sessions?preview=true",
            headers=headers,
            json=payload
        )

        data = response.json()

        agent_session_id = data["rid"]

        if "rid" not in data:
            print("Palantir response does not contain 'rid':", data)
            raise HTTPException(status_code=500, detail="Missing 'rid' in Palantir response")

        redis_hash_value = agent_session_id

        await redis_connection.hset(redis_hash_key, redis_hash_field, redis_hash_value)
        await redis_connection.expire(redis_hash_key, 3600*24*2)

        return ResponseSchema(
            success=True,
            status_code=200,
            message="Session created successfully",
            data={"session_id": agent_session_id}
        )

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
