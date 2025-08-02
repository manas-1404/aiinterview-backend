import redis
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette import status

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
def login(login_data: LoginSchema, db_connection: Session = Depends(get_db_session), redis_connection: redis.Redis = Depends(get_redis_connection)):

    user = (db_connection.query(User).options(joinedload(User.templates)).filter(User.email == login_data.email).first())

    #user is not present in the db
    if user is None or not verify_string(plain_string=login_data.password, hashed_string=user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")


    user_jwt_token = create_jwt_token(data=user.uid)

    user_refresh_token = create_jwt_refresh_token(data=user.uid)

    user.jwt_refresh_token = user_refresh_token

    db_connection.commit()

    #cache all the user templates as soon as they login to prevent future database queries for templates
    redis_template_key = f"user:{user.uid}:templates"
    redis_pipeline = redis_connection.pipeline()

    for template in user.templates:
        template_data = TemplateSchema.model_validate(template).model_dump()
        redis_pipeline.hset(redis_template_key, template.template_id, serialize_for_redis(template_data))

    redis_pipeline.hset("user_name", user.uid, user.name)
    redis_pipeline.expire(redis_template_key, 60 * 90)
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
def sign_up(signup_data: SignUpSchema, db_connection: Session = Depends(get_db_session), redis_connection: redis.Redis = Depends(get_redis_connection)):
    """
    Endpoint to sign up a new user.
    """
    existing_user = db_connection.query(User).filter(User.email == signup_data.email.lower()).first()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    new_user = User(
        name=signup_data.name,
        email=signup_data.email,
        password=encrypt_string(plain_string=signup_data.password),
    )

    db_connection.add(new_user)
    db_connection.flush()

    jwt_token = create_jwt_token(data=new_user.uid)
    refresh_token = create_jwt_refresh_token(data=new_user.uid)

    new_user.jwt_refresh_token = refresh_token

    db_connection.commit()

    return ResponseSchema(
        success=True,
        status_code=201,
        message="User registered successfully",
        data={"jwt_token": jwt_token, "refresh_token": refresh_token}
    )