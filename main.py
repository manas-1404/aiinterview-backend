from fastapi import FastAPI
from ai_interviewer_sdk import FoundryClient, UserTokenAuth

from utils.config import settings
from pydantic_schemas.user_pydantic import UserSchema
app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

@app.get("/get-users")
async def get_users():

    auth = UserTokenAuth(token=settings.FOUNDRY_TOKEN)
    client = FoundryClient(auth=auth, hostname=settings.PALANTIR_PROJECT_URL)

    userObjects = client.ontology.objects.User

    print(userObjects.take(5))

    users = [UserSchema(
        uid=user.uid,
        role=user.role,
        email=user.email,
        name=user.name,
        updated_at=user.updated_at,
        created_at=user.created_at
    ) for user in userObjects.take(5)]

    return {"message": "Users fetched successfully", "users": users}

