import httpx
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import logging
from ai_interviewer_sdk import FoundryClient, UserTokenAuth

from pydantic_schemas.response_pydantic import ResponseSchema
from utils.config import settings

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