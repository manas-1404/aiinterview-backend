from datetime import datetime, time
from typing import List

from ai_interviewer_sdk.ontology.object_sets import PracticePlanObjectSet
from fastapi import APIRouter, Depends, HTTPException, Request

from ai_interviewer_sdk import FoundryClient
from ai_interviewer_sdk.ontology.objects import PracticePlan, User, PracticeTask

from dependency.auth_dependency import authenticate_request
from pydantic_schemas.interviewsession_pydantic import InterviewSessionSchema
from pydantic_schemas.practiceplan_pydantic import PracticePlanSchema
from pydantic_schemas.practicetask_pydantic import PracticeTaskSchema
from pydantic_schemas.response_pydantic import ResponseSchema

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
            where(PracticePlan.iid == interview_session_detail.iid & PracticePlan.uid == user_id)
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
