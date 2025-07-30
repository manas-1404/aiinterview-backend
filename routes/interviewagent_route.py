from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request, HTTPException, Body
from fastapi.responses import StreamingResponse
import httpx
from redis.asyncio import Redis
from ai_interviewer_sdk.ontology.objects import User

from db.redisConnection import get_redis_connection
from pydantic_schemas.response_pydantic import ResponseSchema
from dependency.httpclient_dependency import get_http_client
from dependency.auth_dependency import authenticate_request
from utils.config import settings

agent_router = APIRouter(
    prefix="/interviewagent",
    tags=["interviewagent"]
)

@agent_router.get("/create-session")
async def create_agent_session(request: Request, jwt_payload: dict[str] = Depends(authenticate_request) , http_client: httpx.AsyncClient = Depends(get_http_client), redis_connection: Redis = Depends(get_redis_connection)):
    """
    Endpoint to create a new interview agent session.
    """

    user_id = jwt_payload.get("sub")

    palantir_client = request.app.state.foundry_client
    user: User = palantir_client.ontology.objects.User.get(user_id)

    redis_hash_key = f"interview_agent:{user_id}"

    cached_agent_session_id = await redis_connection.hget(redis_hash_key, "agent_session_id")

    if cached_agent_session_id:
        await redis_connection.hset(redis_hash_key, "current_qna_pointer", str(0))
        await redis_connection.expire(redis_hash_key, 3600*2)

        return ResponseSchema(
            success=True,
            status_code=200,
            message="Session already exists",
            data={"session_id": cached_agent_session_id}
        )

    if not user:
        raise HTTPException(status_code=404, detail="User not found in Palantir ontology.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.PALANTIR_API_KEY}"
    }

    payload = {
        "agentVersion": "1.0"
    }

    try:
        response = await http_client.post(
            url=f"{settings.PALANTIR_PROJECT_URL}/api/v2/aipAgents/agents/{settings.INTERVIEWER_AGENT_RID}/sessions?preview=true",
            headers=headers,
            json=payload
        )

        response.raise_for_status()

        data = response.json()

        if "rid" not in data:
            print("Palantir response does not contain 'rid':", data)
            raise HTTPException(status_code=500, detail="Missing 'rid' in Palantir response")

        agent_session_id = data["rid"]

        await redis_connection.hset(redis_hash_key, mapping={
                "agent_session_id": agent_session_id,
                "current_qna_pointer": str(0),
            }
        )
        await redis_connection.expire(redis_hash_key, 3600*2)

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

@agent_router.post("/send-message-streaming")
async def send_message_streaming(
    message: str = Body(..., embed=True),
    jwt_payload: dict[str] = Depends(authenticate_request),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    redis_connection: Redis = Depends(get_redis_connection)
):
    """
    Endpoint to send message to Palantir AIP Agent in streaming mode.
    """

    user_id = jwt_payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found in JWT payload.")

    redis_hash_key = "interview_agent_session_key"
    redis_hash_field = f"user:{user_id}"

    cached_session_rid = await redis_connection.hget(redis_hash_key, redis_hash_field)
    if not cached_session_rid:
        raise HTTPException(status_code=404, detail="No active session found. Please create a session first.")

    url = f"{settings.PALANTIR_PROJECT_URL}/api/v2/aipAgents/agents/{settings.INTERVIEWER_AGENT_RID}/sessions/{cached_session_rid}/streamingContinue?preview=true"
    headers = {
        "Authorization": f"Bearer {settings.PALANTIR_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "userInput": {
            "text": message
        }
    }

    async def event_stream() -> AsyncGenerator[str, None]:
        async with http_client.stream("POST", url, headers=headers, json=payload) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                raise HTTPException(status_code=response.status_code, detail=error_text.decode())

            async for chunk in response.aiter_text():
                if chunk.strip():
                    yield chunk

    return StreamingResponse(event_stream(), media_type="text/event-stream")