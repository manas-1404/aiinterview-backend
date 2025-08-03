import pickle
from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Iterator, Optional, List
from ai_interviewer_sdk.ontology.object_sets import UserObjectSet, InterviewSessionObjectSet, TurnObjectSet
from ai_interviewer_sdk import FoundryClient
from redis.asyncio import Redis

from pydantic_schemas.turn_pydantic import TurnSchema
from utils.utils import encode_for_cache, decode_from_cache
from permissions.user_permissions import user_can
from db.redisConnection import get_redis_connection
from dependency.auth_dependency import authenticate_request
from pydantic_schemas.combinedresults_pydantic import CombinedResultSchema
from pydantic_schemas.interviewsession_pydantic import InterviewSessionSchema
from pydantic_schemas.practiceplan_pydantic import PracticePlanSchema
from pydantic_schemas.practicetask_pydantic import PracticeTaskSchema
from pydantic_schemas.response_pydantic import ResponseSchema
from ai_interviewer_sdk.ontology.objects import User, Turn, InterviewSession, CombinedResult, PracticePlan, PracticeTask

all_qna_router = APIRouter(
    prefix="/api/qna",
    tags=["All QnA"]
)


@all_qna_router.get("/get-qna-by-iid")
async def get_qna_by_iid(
        request: Request,
        query_iid: int,
        jwt_payload: dict = Depends(authenticate_request),
        redis_connection: Redis = Depends(get_redis_connection)):

    """
    Endpoint to get all QnA for a specific interview session by its ID.
    :param request:
    :param jwt_payload:
    :param redis_connection:
    :return:
    """

    user_id = jwt_payload.get("sub").get("uid")

    palantir_client: FoundryClient = request.app.state.foundry_client

    user: User = palantir_client.ontology.objects.User.get(user_id)

    print("Fetching QnA for user ID: ", user_id, " and interview session ID: ", query_iid)

    if not user:
        print("User not found for ID: ", user_id)
        raise HTTPException(status_code=404, detail="User not found.")

    cached_qna = await redis_connection.get(f"allqna_cache:{user_id}")

    if cached_qna:
        return ResponseSchema(
            success=True,
            status_code=200,
            message="QnA retrieved from cache.",
            data={
                "OnA": decode_from_cache(cached_qna)
            }
        )


    Turn_object_set: TurnObjectSet = (
        palantir_client.ontology.objects.Turn
        .where(Turn.object_type.iid == query_iid)
    )

    turns_list: List[TurnSchema] = []

    for turn in Turn_object_set.iterate():
        turns_list.append(TurnSchema(
            qaid=turn.qaid,
            question=turn.question,
            answer=turn.answer,
            blocked=turn.blocked,
            clarity= turn.clarity,
            composite_star=turn.composite_star,
            filler=turn.filler,
            iid=turn.iid,
            issues=turn.issues,
            justification= turn.justification,
            relevance= turn.relevance,
            repair_attempts= turn.repair_attempts,
            safety_flags= turn.safety_flags,
            star_a= turn.star_a,
            star_r= turn.star_r,
            star_s= turn.star_s,
            star_t= turn.star_t,
            target_competency= turn.target_competency,
            technical_depth= turn.technical_depth,
            transcript_text=turn.transcript_text,
            turn_index= turn.turn_index,
            uid= user_id,
            created_at= turn.created_at if turn.created_at else datetime.now(),
            updated_at= turn.updated_at if turn.updated_at else datetime.now()
        ))

    if not turns_list:
        print("No qna for iid: ", query_iid)
        raise HTTPException(status_code=404, detail="No QnA found for the given interview session ID.")

    await redis_connection.set(f"allqna_cache:{user_id}", encode_for_cache(turns_list), ex=60*10)

    return ResponseSchema(
        success=True,
        status_code=200,
        message="QnA retrieved successfully.",
        data={
            "OnA": turns_list
        }
    )
