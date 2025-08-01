from typing import Iterator, List

from ai_interviewer_sdk import FoundryClient
from fastapi import APIRouter, Depends, HTTPException, Request
from redis.asyncio import Redis
from ai_interviewer_sdk.ontology.objects import User, Turn, InterviewSession
from ai_interviewer_sdk.ontology.object_sets import TurnObjectSet

from db.redisConnection import get_redis_connection
from dependency.auth_dependency import authenticate_request
from pydantic_schemas.interviewsession_pydantic import InterviewSessionSchema
from pydantic_schemas.response_pydantic import ResponseSchema
from pydantic_schemas.turn_pydantic import TurnSchema
from utils.utils import encode_for_cache, decode_from_cache

turn_route = APIRouter(
    prefix="/api/turn",
    tags=["Turn"]
)

@turn_route.post("/get-turn-by-iid")
async def get_turn_by_iid(request: Request,
                           interview_session_details: InterviewSessionSchema,
                           jwt_payload: dict = Depends(authenticate_request),
                           redis_connection: Redis = Depends(get_redis_connection)):
    """
    Endpoint to retrieve the current turn for the user.
    """
    user_id = jwt_payload.get("sub")

    palantir_client: FoundryClient = request.app.state.foundry_client

    user: User = palantir_client.ontology.objects.User.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    redis_cache_key = f"turns_cache:{user_id}:{interview_session_details.iid}"
    cached_turns = await redis_connection.get(redis_cache_key)

    if cached_turns:
        return ResponseSchema(
            success=True,
            status_code=200,
            message="Current turn retrieved successfully from cache.",
            data={"turn": decode_from_cache(cached_turns)}
        )

    turn_object_set: TurnObjectSet = (
        palantir_client.ontology.objects.Turn
        .where(Turn.iid == interview_session_details.iid)
        .where(Turn.uid == user_id)
    )

    turns_list: List[TurnSchema] = []

    for turn in turn_object_set.iterate():
        turn_schema = TurnSchema(
            qaid=turn.qaid,
            question=turn.question,
            answer=turn.answer,
            blocked=turn.blocked,
            clarity=turn.clarity,
            composite_star= turn.composite_star,
            filler= turn.filler,
            iid=interview_session_details.iid,
            issues= turn.issues,
            justification= turn.justification,
            relevance= turn.relevance,
            repair_attempts= turn.repair_attempts,
            safety_flags= turn.safety_flags,
            star_a=turn.star_a,
            star_r= turn.star_r,
            star_s= turn.star_s,
            star_t= turn.star_t,
            target_competency= turn.target_competency,
            technical_depth= turn.technical_depth,
            transcript_text=turn.transcript_text,
            turn_index= turn.turn_index,
            uid=user_id,
            created_at= turn.created_at,
            updated_at= turn.updated_at
        )

        turns_list.append(turn_schema)

    await redis_connection.set(redis_cache_key, encode_for_cache(turns_list), ex=3600)

    return ResponseSchema(
        success=True,
        status_code=200,
        message="Current turn retrieved successfully.",
        data={"turn": turns_list}
    )

@turn_route.get("/get-all-turns")
async def get_all_turns(request: Request,
                           jwt_payload: dict = Depends(authenticate_request),
                           redis_connection: Redis = Depends(get_redis_connection)):
    """
    Endpoint to retrieve the current turn for the user.
    """
    user_id = jwt_payload.get("sub")

    palantir_client: FoundryClient = request.app.state.foundry_client

    user: User = palantir_client.ontology.objects.User.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    redis_cache_key = f"all_turns_cache:{user_id}"
    cached_turns = await redis_connection.get(redis_cache_key)

    if cached_turns:
        return ResponseSchema(
            success=True,
            status_code=200,
            message="Current turn retrieved successfully from cache.",
            data={"turn": decode_from_cache(cached_turns)}
        )

    turn_object_set: TurnObjectSet = (
        palantir_client.ontology.objects.Turn.where(Turn.uid == user_id)
    )

    turns_list: List[TurnSchema] = []

    for turn in turn_object_set.iterate():
        turn_schema = TurnSchema(
            qaid=turn.qaid,
            question=turn.question,
            answer=turn.answer,
            blocked=turn.blocked,
            clarity=turn.clarity,
            composite_star=turn.composite_star,
            filler=turn.filler,
            iid=turn.iid,
            issues=turn.issues,
            justification=turn.justification,
            relevance=turn.relevance,
            repair_attempts=turn.repair_attempts,
            safety_flags=turn.safety_flags,
            star_a=turn.star_a,
            star_r=turn.star_r,
            star_s=turn.star_s,
            star_t=turn.star_t,
            target_competency=turn.target_competency,
            technical_depth=turn.technical_depth,
            transcript_text=turn.transcript_text,
            turn_index=turn.turn_index,
            uid=user_id,
            created_at=turn.created_at,
            updated_at=turn.updated_at
        )

        turns_list.append(turn_schema)

    await redis_connection.set(redis_cache_key, encode_for_cache(turns_list), ex=3600)

    return ResponseSchema(
        success=True,
        status_code=200,
        message="Current turn retrieved successfully.",
        data={"turn": turns_list}
    )
