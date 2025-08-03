import pickle
from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Iterator, Optional, List
from ai_interviewer_sdk.ontology.object_sets import UserObjectSet, InterviewSessionObjectSet, PracticePlanObjectSet
from ai_interviewer_sdk import FoundryClient
from redis.asyncio import Redis

from utils.utils import encode_for_cache, decode_from_cache
from permissions.user_permissions import user_can
from db.redisConnection import get_redis_connection
from dependency.auth_dependency import authenticate_request
from pydantic_schemas.combinedresults_pydantic import CombinedResultSchema
from pydantic_schemas.interviewsession_pydantic import InterviewSessionSchema
from pydantic_schemas.practiceplan_pydantic import PracticePlanSchema
from pydantic_schemas.practicetask_pydantic import PracticeTaskSchema
from pydantic_schemas.response_pydantic import ResponseSchema
from ai_interviewer_sdk.ontology.objects import User, InterviewSession, CombinedResult, PracticePlan, PracticeTask

allinterview_router = APIRouter(
        prefix="/api/interview-runs",
    tags=["Dashboard"]
)


def get_linked_interview_sessions_from_object(
    source: User
) -> Iterator[InterviewSession]:
    linked_object_set: InterviewSessionObjectSet = source.interview_sessions()
    return linked_object_set.iterate()

def get_linked_practice_plans_from_object(
    source: InterviewSession
) -> Iterator[PracticePlan]:
    linked_object_set: PracticePlanObjectSet = source.practice_plans()
    return linked_object_set.iterate()

@allinterview_router.get("/get-all-interview-sessions")
async def get_all_interview_runs(request: Request, jwt_payload: dict = Depends(authenticate_request), redis_connection: Redis = Depends(get_redis_connection)):
    """
    Endpoint to get dashboard data.
    """
    user_id = jwt_payload.get("sub").get("uid")
    role = jwt_payload.get("sub").get("role")

    palantir_client: FoundryClient = request.app.state.foundry_client

    user: User = palantir_client.ontology.objects.User.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    cached_data = await redis_connection.hgetall(f"allinterview_cache:{user_id}")

    if cached_data and all(k in cached_data for k in ["combined_result", "practice_plans", "interview_session", "practice_tasks"]):

        try:
            #i am decoding and encoding the redis cache because the data is stored as stringifiable bytes, so i need to use base64 decoding and encoding to avoid data corruption
            combined_result = decode_from_cache(cached_data["combined_result"])
            practice_plans = decode_from_cache(cached_data["practice_plans"])
            interview_session = decode_from_cache(cached_data["interview_session"])
            practice_tasks = decode_from_cache(cached_data["practice_tasks"])

            return ResponseSchema(
                success=True,
                status_code=200,
                message="Dashboard data retrieved successfully from cache.",
                data={
                    "CombinedResult": combined_result,
                    "InterviewSession": interview_session,
                    "PracticePlans": practice_plans,
                    "PracticeTasks": practice_tasks
                }
            )

        #something went wrong while decoding the cache, so we are deleting the cache and instead fetch the data again
        except Exception:
            await redis_connection.delete(f"allinterview_cache:{user_id}")

    try:

        interview_session_list: List[InterviewSession] = list((
            palantir_client.ontology.objects.InterviewSession.where(InterviewSession.object_type.uid == user_id)
        ).iterate())

        # interview_session: List[InterviewSession] = [session for session in interview_session_list]

        if not interview_session_list:
            return ResponseSchema(
                success=True,
                status_code=200,
                message="No interview sessions found. Take new interview to get started.",
                data={}
            )

        combined_result: List[CombinedResult] = [each_combined_results.combined_result() for each_combined_results in interview_session_list]

        if not combined_result:
            return ResponseSchema(
                success=True,
                status_code=200,
                message="Processing the results. Please wait or try again later.",
            )

        practice_plan_iterator: List[Iterator[PracticePlan]] = [get_linked_practice_plans_from_object(source=each_interview_session) for each_interview_session in interview_session_list]

        practice_plan_list: List[PracticePlan] = []
        practice_task_list: List[PracticeTask] = []

        for iterator in practice_plan_iterator:
            for practice_plan in iterator:
                    practice_plan_list.append(practice_plan)
                    practice_task_list.append(practice_plan.practice_task())

        combined_result_data = [CombinedResultSchema(
            rid=int(each_combined_results.rid if isinstance(each_combined_results.rid, int) else 0),
            total_score_25=each_combined_results.total_score25,
            clarity_avg=each_combined_results.clarity_avg,
            created_at=each_combined_results.created_at,
            eval_confidence=each_combined_results.eval_confidence,
            filler_avg=each_combined_results.filler_avg,
            gaps=each_combined_results.gaps,
            iid=each_combined_results.iid,
            per_metric_weights=each_combined_results.per_metric_weights,
            recommendation=each_combined_results.recommendation,
            relevance_avg=each_combined_results.relevance_avg,
            rubric_version=each_combined_results.rubric_version,
            star_avg=each_combined_results.star_avg,
            strengths=each_combined_results.strengths,
            technical_depth_avg=each_combined_results.technical_depth_avg,
            turn_indices_used=each_combined_results.turn_indices_used,
            uid=each_combined_results.uid,
            updated_at=each_combined_results.updated_at,
            weaknesses=each_combined_results.weaknesses,
        )
            for each_combined_results in combined_result
        ]

        practice_plan_list_data: List[PracticePlanSchema] = [
            PracticePlanSchema(
                ppid=plan.ppid,
                overall_goal=plan.overall_goal,
                approved_at=plan.approved_at,
                approved_by=plan.approved_by,
                created_at=plan.created_at,
                created_by=plan.created_by,
                decline_reason=plan.decline_reason,
                iid=plan.iid,
                motivation_note=plan.motivation_note,
                next_session_suggested_days=plan.next_session_suggestion_days,
                plan_version=plan.plan_version,
                reading_list=plan.reading_list,
                status=plan.status,
                uid=plan.uid,
                updated_at=plan.updated_at,
            )
            for plan in practice_plan_list
        ]

        # TODO: chekc palantir ontology for PracticeTask completed_at because its returning '' for some reason
        practice_task_list_data: List[PracticeTaskSchema] = [
            PracticeTaskSchema(
                ptid=task.ptid,
                competency=task.competency,
                actions=task.actions,
                completed_at=task.completed_at if task.completed_at not in ("", None) else datetime.today(),
                created_at=task.created_at,
                description=task.description,
                due_date=datetime.combine(task.due_date, time(23, 59)),
                est_minutes=task.est_minutes,
                ppid=task.ppid,
                priority=task.priority,
                status=task.status,
                success_criteria=task.success_criteria,
                uid=task.uid,
                updated_at=task.updated_at,
            )
            for task in practice_task_list
        ]

        interview_session_data: List[InterviewSessionSchema] = [InterviewSessionSchema(
            iid=each_interview_session.iid,
            uid=each_interview_session.uid,
            jid=each_interview_session.jid,
            created_at=each_interview_session.created_at,
            updated_at=each_interview_session.updated_at,
            status=each_interview_session.status,
            started_at=each_interview_session.started_at,
            ended_at=each_interview_session.ended_at
        )
            for each_interview_session in interview_session_list
        ]
        await redis_connection.hset(
            f"allinterview_cache:{user_id}",
            mapping={
                "combined_result": encode_for_cache(combined_result_data),
                "interview_session": encode_for_cache(interview_session_data),
                "practice_plans": encode_for_cache(practice_plan_list_data),
                "practice_tasks": encode_for_cache(practice_task_list_data),
            }
        )

        await redis_connection.expire(f"allinterview_cache:{user_id}", 60*10)

        return ResponseSchema(
            success=True,
            status_code=200,
            message="Dashboard data retrieved successfully.",
            data={"CombinedResult": combined_result_data,
                  "InterviewSession": interview_session_data,
                  "PracticePlans": practice_plan_list_data,
                  "PracticeTasks": practice_task_list_data,
                  "role": role
                  }
        )

    except Exception as e:
        print(f"Error retrieving dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))






