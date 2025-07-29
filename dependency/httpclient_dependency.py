import httpx
from fastapi import Request

async def get_http_client(request: Request) -> httpx.AsyncClient:
    """
    Dependency function to get the HTTP client from the FastAPI application state.
    :param request:
    :return:
    """
    return request.app.state.client