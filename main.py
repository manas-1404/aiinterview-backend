import httpx
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import logging

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
    app.state.client = httpx.AsyncClient()

@app.on_event("shutdown")
async def shutdown_event():
    await app.state.client.aclose()