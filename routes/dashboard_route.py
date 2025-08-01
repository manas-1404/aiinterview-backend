import pickle
from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Iterator, Optional, List
from ai_interviewer_sdk.ontology.object_sets import UserObjectSet, InterviewSessionObjectSet, PracticePlanObjectSet
from ai_interviewer_sdk import FoundryClient
from redis.asyncio import Redis

from utils.utils import encode_for_cache, decode_from_cache
from db.redisConnection import get_redis_connection
from dependency.auth_dependency import authenticate_request
from pydantic_schemas.combinedresults_pydantic import CombinedResultSchema
from pydantic_schemas.interviewsession_pydantic import InterviewSessionSchema
from pydantic_schemas.practiceplan_pydantic import PracticePlanSchema
from pydantic_schemas.practicetask_pydantic import PracticeTaskSchema
from pydantic_schemas.response_pydantic import ResponseSchema
from ai_interviewer_sdk.ontology.objects import User, InterviewSession, CombinedResult, PracticePlan, PracticeTask

dashboard_router = APIRouter(
    prefix="/api/dashboard",
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

@dashboard_router.get("/get-dashboard-data")
async def get_dashboard_data(request: Request, jwt_payload: dict = Depends(authenticate_request), redis_connection: Redis = Depends(get_redis_connection)):
    """
    Endpoint to get dashboard data.
    """
    user_id = jwt_payload.get("sub")

    palantir_client: FoundryClient = request.app.state.foundry_client

    user: User = palantir_client.ontology.objects.User.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    cached_data = await redis_connection.hgetall(f"dashboard_cache:{user_id}")

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
            await redis_connection.delete(f"dashboard_cache:{user_id}")

    try:
        interview_session_list: List[InterviewSession] = list(get_linked_interview_sessions_from_object(source=user))

        interview_session: InterviewSession = max(interview_session_list, key=lambda x: x.created_at, default=None)

        if interview_session is None:
            return ResponseSchema(
                success=True,
                status_code=200,
                message="No interview sessions found. Take new interview to get started.",
                data={}
            )

        combined_result: CombinedResult = interview_session.combined_result()

        if combined_result is None:
            return ResponseSchema(
                success=True,
                status_code=200,
                message="Processing the results. Please wait or try again later.",
            )

        practice_plan_iterator: Iterator[PracticePlan] = get_linked_practice_plans_from_object(source=interview_session)

        practice_plan_list: List[PracticePlan] = []
        practice_task_list: List[PracticeTask] = []

        for practice_plan in practice_plan_iterator:

            if practice_plan.iid == interview_session.iid:
                practice_plan_list.append(practice_plan)
                practice_task_list.append(practice_plan.practice_task())

        combined_result_data = CombinedResultSchema(
            rid=int(combined_result.rid),
            total_score_25=combined_result.total_score25,
            clarity_avg=combined_result.clarity_avg,
            created_at=combined_result.created_at,
            eval_confidence=combined_result.eval_confidence,
            filler_avg=combined_result.filler_avg,
            gaps=combined_result.gaps,
            iid=combined_result.iid,
            per_metric_weights=combined_result.per_metric_weights,
            recommendation=combined_result.recommendation,
            relevance_avg=combined_result.relevance_avg,
            rubric_version=combined_result.rubric_version,
            star_avg=combined_result.star_avg,
            strengths=combined_result.strengths,
            technical_depth_avg=combined_result.technical_depth_avg,
            turn_indices_used=combined_result.turn_indices_used,
            uid=combined_result.uid,
            updated_at=combined_result.updated_at,
            weaknesses=combined_result.weaknesses,
        )

        practice_plan_list_data = [
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

        practice_task_list_data = [
            PracticeTaskSchema(
                ptid=task.ptid,
                competency=task.competency,
                actions=task.actions,
                completed_at=task.completed_at,
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

        interview_session_data = InterviewSessionSchema(
            iid=interview_session.iid,
            uid=interview_session.uid,
            jid=interview_session.jid,
            created_at=interview_session.created_at,
            updated_at=interview_session.updated_at,
            status=interview_session.status,
            started_at=interview_session.started_at,
            ended_at=interview_session.ended_at
        )

        await redis_connection.hset(
            f"dashboard_cache:{user_id}",
            mapping={
                "combined_result": encode_for_cache(combined_result_data),
                "interview_session": encode_for_cache(interview_session_data),
                "practice_plans": encode_for_cache(practice_plan_list_data),
                "practice_tasks": encode_for_cache(practice_task_list_data),
            }
        )

        await redis_connection.expire(f"dashboard_cache:{user_id}", 3600)

        return ResponseSchema(
            success=True,
            status_code=200,
            message="Dashboard data retrieved successfully.",
            data={"CombinedResult": combined_result_data,
                  "InterviewSession": interview_session_data,
                  "PracticePlans": practice_plan_list_data,
                  "PracticeTasks": practice_task_list_data
                  }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))






