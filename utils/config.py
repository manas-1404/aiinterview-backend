import os
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PALANTIR_API_KEY: str
    INTERVIEWER_AGENT_RID: str
    ONTOLOGY_RID: str

    PALANTIR_PROJECT_URL: str
    FOUNDRY_TOKEN: str

    ALLOWED_ORIGINS: List[str]

    AGENT_RUN_API_NAME: str = "AgentRun"
    COMBINED_RESULT_API_NAME: str = "CombinedResult"
    INTERVIEW_SESSION_API_NAME: str = "InterviewSession"
    JOB_DESCRIPTION_API_NAME: str = "JobDescription"
    PRACTICE_PLAN_API_NAME: str = "PracticePlan"
    PRACTICE_TASK_API_NAME: str = "PracticeTask"
    RESUME_API_NAME: str = "Resume"
    TURN_API_NAME: str = "Turn"
    USER_API_NAME: str = "User"

    REDIS_CLOUD_URL: str

    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str

    OAUTHLIB_INSECURE_TRANSPORT: int

    JWT_AUTH_ALGORITHM: str
    JWT_SIGNATURE_SECRET_KEY: str
    JWT_TOKEN_EXPIRATION_MINUTES: int
    JWT_REFRESH_TOKEN_EXPIRATION_DAYS: int

    class Config:
        env_file = ".env"

settings = Settings()

if settings.OAUTHLIB_INSECURE_TRANSPORT:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = str(settings.OAUTHLIB_INSECURE_TRANSPORT)