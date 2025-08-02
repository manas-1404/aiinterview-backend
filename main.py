import httpx
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import logging
from ai_interviewer_sdk import FoundryClient, UserTokenAuth

from pydantic_schemas.response_pydantic import ResponseSchema
from utils.config import settings
from routes.logic_route import login_router
from routes.turn_route import turn_route
from routes.dashboard_route import dashboard_router
from routes.uploadfile_route import upload_router
from routes.interviewagent_route import agent_router
from routes.practice_route import practice_router
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.include_router(login_router)
app.include_router(turn_route)
app.include_router(dashboard_router)
app.include_router(upload_router)
app.include_router(agent_router)
app.include_router(practice_router)


@app.on_event("startup")
async def startup_event():
    """
    Startup event to initialize the Palantir Foundry client and HTTP client.
    :return:
    """
    auth = UserTokenAuth(token=settings.FOUNDRY_TOKEN)
    app.state.foundry_client = FoundryClient(auth=auth, hostname=settings.PALANTIR_PROJECT_URL)
    app.state.client = httpx.AsyncClient()

@app.on_event("shutdown")
async def shutdown_event():
    """
    Shutdown event to close the HTTP client connection.
    :return:
    """
    await app.state.client.aclose()