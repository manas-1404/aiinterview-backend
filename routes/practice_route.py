from datetime import datetime, time
from typing import List, Iterator

from ai_interviewer_sdk.ontology.object_sets import PracticePlanObjectSet
from fastapi import APIRouter, Depends, HTTPException, Request
from ai_interviewer_sdk import FoundryClient
from ai_interviewer_sdk.ontology.objects import PracticePlan, User, PracticeTask
from redis.asyncio import Redis
from foundry_sdk_runtime.types import ActionConfig, ActionMode, ReturnEditsMode, SyncApplyActionResponse

from db.redisConnection import get_redis_connection
from dependency.auth_dependency import authenticate_request
from permissions.user_permissions import user_can
from pydantic_schemas.interviewsession_pydantic import InterviewSessionSchema
from pydantic_schemas.practiceplan_pydantic import PracticePlanSchema
from pydantic_schemas.practicetask_pydantic import PracticeTaskSchema
from pydantic_schemas.response_pydantic import ResponseSchema
from utils.utils import encode_for_cache, decode_from_cache

practice_router = APIRouter(
    prefix="/api/practice",
    tags=["Practice Plan"]
)

@practice_router.get("/get-practice-details")
async def get_practice_plan(request: Request, interview_session_detail: InterviewSessionSchema , jwt_payload: dict = Depends(authenticate_request)):
    """
    Endpoint to retrieve the practice plan for the user.
    """
    user_id = jwt_payload.get("sub")

    palantir_client: FoundryClient = request.app.state.foundry_client

    user: User = palantir_client.ontology.objects.User.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    practice_plan_object_sets: PracticePlanObjectSet = (
            palantir_client.ontology.objects.PracticePlan.
            where((PracticePlan.iid == interview_session_detail.iid) & (PracticePlan.uid == user_id))
        )

    practice_plan_list: List[PracticePlanSchema] = []
    practice_task_list: List[PracticeTaskSchema] = []

    for each_practice_plan in practice_plan_object_sets.iterate():

        practice_plan_schema = PracticePlanSchema(
            iid=each_practice_plan.iid,
            uid=each_practice_plan.uid,
            ppid= each_practice_plan.ppid,
            overall_goal= each_practice_plan.overall_goal,
            approved_at= each_practice_plan.approved_at,
            approved_by= each_practice_plan.approved_by,
            created_at= each_practice_plan.created_at,
            created_by= each_practice_plan.created_by,
            decline_reason= each_practice_plan.decline_reason,
            motivation_note= each_practice_plan.motivation_note,
            next_session_suggested_days= each_practice_plan.next_session_suggestion_days,
            plan_version= each_practice_plan.plan_version,
            reading_list= each_practice_plan.reading_list,
            status= each_practice_plan.status,
            updated_at= each_practice_plan.updated_at
        )

        each_practice_task: PracticeTask = each_practice_plan.practice_task()

        practice_task_schema = PracticeTaskSchema(
            ptid= each_practice_task.ptid,
            competency= each_practice_task.competency,
            actions= each_practice_task.actions,
            completed_at= each_practice_task.completed_at,
            created_at= each_practice_task.created_at,
            description= each_practice_task.description,
            due_date=datetime.combine(each_practice_task.due_date, time(23, 59)),
            est_minutes= each_practice_task.est_minutes,
            ppid= each_practice_task.ppid,
            priority= each_practice_task.priority,
            status= each_practice_task.status,
            success_criteria= each_practice_task.success_criteria,
            uid= user_id,
            updated_at= each_practice_task.updated_at
        )

        practice_plan_list.append(practice_plan_schema)
        practice_task_list.append(practice_task_schema)

    if not practice_plan_list or not practice_task_list:
        raise HTTPException(
            status_code=404,
            detail="Practice plan or tasks not found for the user."
        )

    return ResponseSchema(
        success=True,
        status_code=200,
        message="Practice plan retrieved successfully.",
        data={"practice_plan": practice_plan_list, "practice_tasks": practice_task_list}
    )


@practice_router.get("/get-all-practice-details")
async def get_all_practice_details(request: Request,
                                   jwt_payload: dict = Depends(authenticate_request),
                                   redis_connection: Redis = Depends(get_redis_connection)):
    """
    Endpoint to retrieve the practice plan for the user.
    """
    user_id = jwt_payload.get("sub")
    role = jwt_payload.get("role")

    palantir_client: FoundryClient = request.app.state.foundry_client

    user: User = palantir_client.ontology.objects.User.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    redis_cache_key = f"all_practice_details_cache:{user_id}"

    cached_data = await redis_connection.hgetall(redis_cache_key)

    if cached_data:
        practice_plan_list = decode_from_cache(cached_data.get("practice_plan"))
        practice_task_list = decode_from_cache(cached_data.get("practice_tasks"))

        return ResponseSchema(
            success=True,
            status_code=200,
            message="Practice plan retrieved successfully from cache.",
            data={"practice_plan": practice_plan_list, "practice_tasks": practice_task_list}
        )

    if user_can(role, "all_view_practice_plans") and user_can(role, "all_view_practice_tasks"):

        practice_plan_iterator: Iterator[PracticePlan] = palantir_client.ontology.objects.PracticePlan.iterate()
        practice_task_iterator: Iterator[PracticeTask] = palantir_client.ontology.objects.PracticeTask.iterate()

        practice_plan_list: List[PracticePlanSchema] = list(practice_plan_iterator)
        practice_task_list: List[PracticeTaskSchema] = list(practice_task_iterator)

    else:
        practice_plan_object_sets: PracticePlanObjectSet = (
                palantir_client.ontology.objects.PracticePlan.
                where(PracticePlan.uid == user_id)
            )

        practice_plan_list: List[PracticePlanSchema] = []
        practice_task_list: List[PracticeTaskSchema] = []

        for each_practice_plan in practice_plan_object_sets.iterate():

            practice_plan_schema = PracticePlanSchema(
                iid=each_practice_plan.iid,
                uid=each_practice_plan.uid,
                ppid= each_practice_plan.ppid,
                overall_goal= each_practice_plan.overall_goal,
                approved_at= each_practice_plan.approved_at,
                approved_by= each_practice_plan.approved_by,
                created_at= each_practice_plan.created_at,
                created_by= each_practice_plan.created_by,
                decline_reason= each_practice_plan.decline_reason,
                motivation_note= each_practice_plan.motivation_note,
                next_session_suggested_days= each_practice_plan.next_session_suggestion_days,
                plan_version= each_practice_plan.plan_version,
                reading_list= each_practice_plan.reading_list,
                status= each_practice_plan.status,
                updated_at= each_practice_plan.updated_at
            )

            each_practice_task: PracticeTask = each_practice_plan.practice_task()

            practice_task_schema = PracticeTaskSchema(
                ptid= each_practice_task.ptid,
                competency= each_practice_task.competency,
                actions= each_practice_task.actions,
                completed_at= each_practice_task.completed_at,
                created_at= each_practice_task.created_at,
                description= each_practice_task.description,
                due_date=datetime.combine(each_practice_task.due_date, time(23, 59)),
                est_minutes= each_practice_task.est_minutes,
                ppid= each_practice_task.ppid,
                priority= each_practice_task.priority,
                status= each_practice_task.status,
                success_criteria= each_practice_task.success_criteria,
                uid= each_practice_plan.uid,
                updated_at= each_practice_task.updated_at
            )

            practice_plan_list.append(practice_plan_schema)
            practice_task_list.append(practice_task_schema)

    if not practice_plan_list or not practice_task_list:
        raise HTTPException(
            status_code=404,
            detail="Practice plan or tasks not found for the user."
        )

    await redis_connection.hset(redis_cache_key, mapping={
        "practice_plan": encode_for_cache(practice_plan_list),
        "practice_tasks": encode_for_cache(practice_task_list)
    })

    await redis_connection.expire(redis_cache_key, 3600)

    return ResponseSchema(
        success=True,
        status_code=200,
        message="Practice plan retrieved successfully.",
        data={"practice_plan": practice_plan_list, "practice_tasks": practice_task_list}
    )

@practice_router.post("/review-practice-plan")
async def review_practice_plan(
    request: Request,
    practice_plan_details: PracticePlanSchema,
    practice_task_details: PracticeTaskSchema,
    jwt_payload: dict = Depends(authenticate_request),
):
    """
    Endpoint for coaches to approve or decline a practice plan.
    """
    user_id = jwt_payload.get("sub")
    role = jwt_payload.get("role")

    if not user_can(role, "approve_practice_plans"):
        raise HTTPException(status_code=403, detail="You are not authorized to perform this action.")

    palantir_client: FoundryClient = request.app.state.foundry_client

    if practice_plan_details.status not in ["approved", "declined"]:
        raise HTTPException(status_code=400, detail="Status must be approved or declined.")

    status = practice_plan_details.status
    approved_at = None
    approved_by = None
    decline_reason = None

    if status == "approved":
        approved_at = datetime.utcnow()
        approved_by = float(user_id)
    else:
        if not practice_plan_details.decline_reason:
            raise HTTPException(status_code=400, detail="Decline reason required for declined plans.")
        decline_reason = practice_plan_details.decline_reason

    response: SyncApplyActionResponse = palantir_client.ontology.actions.edit_practice_plan(
        action_config=ActionConfig(
            mode=ActionMode.VALIDATE_AND_EXECUTE,
            return_edits=ReturnEditsMode.ALL
        ),
        practice_plan=practice_plan_details.ppid,
        iid=practice_plan_details.iid,
        uid=practice_plan_details.uid,
        status=status,
        plan_version=practice_plan_details.plan_version,
        overall_goal=practice_plan_details.overall_goal,
        reading_list=practice_plan_details.reading_list,
        next_session_suggestion_days=practice_plan_details.next_session_suggested_days,
        motivation_note=practice_plan_details.motivation_note,
        created_by=practice_plan_details.created_by,
        approved_by=approved_by,
        approved_at=approved_at,
        decline_reason=decline_reason,
        created_at=practice_plan_details.created_at,
        updated_at=datetime.utcnow()
    )

    if response.validation.result != "VALID":
        raise HTTPException(status_code=400, detail="Practice plan update failed validation.")

    return ResponseSchema(
        success=True,
        status_code=200,
        message=f"Practice plan successfully {status}.",
        data={"practice_plan_id": practice_plan_details.ppid}
    )