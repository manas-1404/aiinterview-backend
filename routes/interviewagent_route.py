import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request, HTTPException, Body
from fastapi.responses import StreamingResponse
import httpx
from redis.asyncio import Redis
from ai_interviewer_sdk.ontology.objects import User
from foundry_sdk_runtime.types import BatchActionConfig, ReturnEditsMode, ActionConfig, ActionMode, SyncApplyActionResponse
from ai_interviewer_sdk.ontology.action_types import CreateTurnBatchRequest
from datetime import datetime
from ai_interviewer_sdk import FoundryClient, UserTokenAuth

from db.redisConnection import get_redis_connection
from pydantic_schemas.response_pydantic import ResponseSchema
from pydantic_schemas.jobdescription_pydantic import JobDescriptionSchema
from dependency.httpclient_dependency import get_http_client
from dependency.auth_dependency import authenticate_request
from utils.config import settings

agent_router = APIRouter(
    prefix="/interviewagent",
    tags=["interviewagent"]
)

@agent_router.post("/create-session")
async def create_agent_session(request: Request, job_details: JobDescriptionSchema, jwt_payload: dict[str] = Depends(authenticate_request) , http_client: httpx.AsyncClient = Depends(get_http_client), redis_connection: Redis = Depends(get_redis_connection)):
    """
    Endpoint to create a new interview agent session.
    """

    user_id = jwt_payload.get("sub")

    palantir_client: FoundryClient = request.app.state.foundry_client
    user: User = palantir_client.ontology.objects.User.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found in Palantir ontology.")

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

        # get the next jid & iid primary key from Palantir ontology
        new_jid = palantir_client.ontology.queries.next_job_description_id_api()
        new_iid = palantir_client.ontology.queries.next_interview_session_id_api()

        # creating the job description in Palantir ontology
        new_job_description: SyncApplyActionResponse = palantir_client.ontology.actions.create_job_description(
            action_config=ActionConfig(
                mode=ActionMode.VALIDATE_AND_EXECUTE,
                return_edits=ReturnEditsMode.ALL),
            jid=new_jid,
            role=job_details.role,
            company=job_details.company,
            minimum_qualification=job_details.min_qualifications,
            preferred_qualification=job_details.preferred_qualifications,
            jd_summary=job_details.jd_summary,
            created_at=datetime.today(),
            updated_at=datetime.today()
        )

        new_interview_session: SyncApplyActionResponse = palantir_client.ontology.actions.create_interview_session(
            action_config=ActionConfig(
                mode=ActionMode.VALIDATE_AND_EXECUTE,
                return_edits=ReturnEditsMode.ALL),
            iid=new_iid,
            uid=user_id,
            jid=new_jid,
            started_at=datetime.today(),
            status="started",
            rubric_version="v1",
            phase_log=json.dumps({"phase1": 3, "phase2": 3, "phase3": 3}),
            created_at=datetime.today(),
            updated_at=datetime.today()
        )

        if new_job_description.validation.result != "VALID":
            raise HTTPException(status_code=400, detail="Job Description creation failed")

        if new_interview_session.validation.result != "VALID":
            raise HTTPException(status_code=400, detail="Interview Session creation failed")

        await redis_connection.hset(redis_hash_key, mapping={
                "agent_session_id": agent_session_id,
                "current_qna_pointer": str(0),
                "jid": str(new_jid),
                "iid": str(new_iid),
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
    request: Request,
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

    redis_hash_key = f"interview_agent:{user_id}"

    fields = ["agent_session_id", "current_qna_pointer"]
    cached_session_rid, question_counter = await redis_connection.hmget(redis_hash_key, fields)
    if not cached_session_rid:
        raise HTTPException(status_code=404, detail="No active session found. Please create a session first.")

    palantir_client = request.app.state.foundry_client

    url = f"{settings.PALANTIR_PROJECT_URL}/api/v2/aipAgents/agents/{settings.INTERVIEWER_AGENT_RID}/sessions/{cached_session_rid}/streamingContinue?preview=true"
    headers = {
        "Authorization": f"Bearer {settings.PALANTIR_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "userInput": {
            "text": message if message != "<start>" else "Start the interview and ask the 1st question"
        }
    }

    redis_pipe = redis_connection.pipeline()
    buffer = []

    async def event_stream():

        # if the questions cross 9, then its the end of the interview
        if question_counter >= 9:
            yield "##END_INTERVIEW##"
        else:
            async with http_client.stream("POST", url, headers=headers, json=payload) as response:
                async for chunk in response.aiter_text():
                    chunk = chunk.strip()
                    if chunk:
                        buffer.append(chunk)
                        yield chunk

    async def finalize():

        if message != "<start>":
            await redis_pipe.rpush(f"interview_agent:{user_id}:answers", message)

        if question_counter >= 9:
            await finalize_interview_logic(user_id, redis_connection, palantir_client)
        else:
            await redis_pipe.rpush(f"interview_agent:{user_id}:questions", " ".join(buffer))
            await redis_pipe.hset(f"interview_agent:{user_id}", "current_qna_pointer", str(int(question_counter) + 1))
            await redis_pipe.execute()

    stream_response = StreamingResponse(event_stream(), media_type="text/event-stream")
    stream_response.background = finalize
    return stream_response


async def finalize_interview_logic(user_id: int, redis_connection: Redis, palantir_client: FoundryClient):
    redis_hash_key = f"interview_agent:{user_id}"

    questions = await redis_connection.lrange(f"{redis_hash_key}:questions", 0, -1)
    answers = await redis_connection.lrange(f"{redis_hash_key}:answers", 0, -1)

    if not questions or not answers or len(questions) != len(answers):
        raise ValueError("Invalid interview data in Redis")

    interview_fields = ["qaid", "iid"]
    cached_qaid, cached_iid = await redis_connection.hmget(redis_hash_key, interview_fields)

    #convert the str to int after retrieving from redis or palantir
    new_qaid = int(cached_qaid) if cached_qaid else palantir_client.ontology.queries.next_turn_id_api()
    cached_iid = int(cached_iid)

    batch_requests = []
    for idx, (q, a) in enumerate(zip(questions, answers)):
        batch_requests.append(
            CreateTurnBatchRequest(
                qaid=new_qaid, iid=cached_iid, uid=user_id,
                turn_index=idx,
                question=q, answer=a,
                target_competency="default",
                audio_url="", transcript_text=a,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        )

        new_qaid += 1


    response = palantir_client.ontology.batch_actions.create_turn(
        batch_action_config=BatchActionConfig(return_edits=ReturnEditsMode.ALL),
        requests=batch_requests
    )

    edit_interview_session: SyncApplyActionResponse = palantir_client.ontology.actions.edit_interview_session(
        action_config=ActionConfig(
            mode=ActionMode.VALIDATE_AND_EXECUTE,
            return_edits=ReturnEditsMode.ALL),
        interview_session=cached_iid,
        ended_at=datetime.today(),
        status="completed",
        updated_at=datetime.today()
    )

    if edit_interview_session.validation.result != "VALID":
        raise HTTPException(status_code=400, detail="Failed to mark interview session as completed")

    await redis_connection.delete(
        redis_hash_key,
        f"{redis_hash_key}:questions",
        f"{redis_hash_key}:answers",
        f"interview_agent:{user_id}:qaid",
        f"interview_agent:{user_id}:iid"
    )

    return response
