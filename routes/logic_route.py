from datetime import datetime

import redis
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette import status
from ai_interviewer_sdk.ontology.object_sets import PracticePlanObjectSet, UserObjectSet
from fastapi import APIRouter, Depends, HTTPException, Request
from ai_interviewer_sdk import FoundryClient
from ai_interviewer_sdk.ontology.objects import PracticePlan, User, PracticeTask
from redis.asyncio import Redis
from foundry_sdk_runtime.types import ActionConfig, ActionMode, ReturnEditsMode, SyncApplyActionResponse

from dependency.auth_dependency import create_jwt_token, create_jwt_refresh_token
from db.redisConnection import get_redis_connection
from pydantic_schemas.login_pydantic import LoginSchema
from pydantic_schemas.response_pydantic import ResponseSchema
from pydantic_schemas.signup_pydantic import SignUpSchema
from utils.utils import verify_string, serialize_for_redis, encrypt_string

login_router = APIRouter(
    prefix="/api/auth",
    tags=["Login"]
)

@login_router.post("/login")
def login(request: Request, login_data: LoginSchema, redis_connection: redis.Redis = Depends(get_redis_connection)):

    palantir_client: FoundryClient = request.app.state.foundry_client
    user_object_set: UserObjectSet = palantir_client.ontology.objects.User.where(User.object_type.email == login_data.email.lower())

    user: User = None
    for user_iterator in user_object_set.iterate():
        user = user_iterator
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    #user is not present in the db
    if user is None or not verify_string(plain_string=login_data.password, hashed_string=user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")


    data = {
        "uid": user.uid,
        "role": user.role,
    }
    user_jwt_token = create_jwt_token(data=data)

    user_refresh_token = create_jwt_refresh_token(data=data)

    response: SyncApplyActionResponse = palantir_client.ontology.actions.edit_user(
        action_config=ActionConfig(
            mode=ActionMode.VALIDATE_AND_EXECUTE,
            return_edits=ReturnEditsMode.ALL),
        user=user.uid,
        name=user.name,
        email=user.email,
        password_hash=user.password_hash,
        role=user.role,
        jwt_refresh_token= user_refresh_token,
        created_at=datetime.today(),
        updated_at=datetime.today()
    )

    #cache all the user templates as soon as they login to prevent future database queries for templates
    redis_user_key = f"user:{user.uid}"
    redis_pipeline = redis_connection.pipeline()

    redis_pipeline.hset(redis_user_key, mapping={
        "uid": user.uid,
        "name": user.name,
        "jwt_refresh_token": user_refresh_token,
    })
    redis_pipeline.expire(redis_user_key, 60 * 90)
    redis_pipeline.execute()

    json_response = JSONResponse(
        content= ResponseSchema(
            success=True,
            status_code=200,
            message="Login successful!",
            data={
                "jwt_token": user_jwt_token,
                "user_name": user.name,
            }
        ).model_dump()
    )

    json_response.set_cookie(
        key="refresh_token",
        value=user_refresh_token,
        httponly=True,
        secure=False,  # Set to True in production
        samesite="Strict",
        max_age=60 * 60 * 24 * 7
    )

    return json_response

@login_router.post("/signup")
def sign_up(request: Request, signup_data: SignUpSchema, redis_connection: redis.Redis = Depends(get_redis_connection)):
    """
    Endpoint to sign up a new user.
    """

    palantir_client: FoundryClient = request.app.state.foundry_client
    existing_user_object_set: UserObjectSet = palantir_client.ontology.objects.User.where(User.object_type.email == signup_data.email.lower())

    for existing_user in existing_user_object_set.iterate():
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    new_user_id = palantir_client.ontology.queries.next_user_id_api()

    data = {
        "uid": new_user_id,
        "role": signup_data.role,
    }

    jwt_token = create_jwt_token(data=data)
    refresh_token = create_jwt_refresh_token(data=data)

    response: SyncApplyActionResponse = palantir_client.ontology.actions.create_user(
        action_config=ActionConfig(
            mode=ActionMode.VALIDATE_AND_EXECUTE,
            return_edits=ReturnEditsMode.ALL),
        uid=new_user_id,
        name=signup_data.name,
        email=signup_data.email.lower(),
        password_hash=encrypt_string(plain_string=signup_data.password),
        role=signup_data.role,
        created_at=datetime.today(),
        updated_at=datetime.today(),
        jwt_refresh_token=refresh_token
    )

    return ResponseSchema(
        success=True,
        status_code=201,
        message="User registered successfully",
        data={"jwt_token": jwt_token, "refresh_token": refresh_token}
    )