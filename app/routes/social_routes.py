from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query
from app.services.social_service import (
    fetch_followers_service,
    fetch_following_service,
    save_follow_service,
    save_unfollow_service,
)
from app.models.schema import MyResponse
from app.utils.enums.ResponseStatus import ResponseStatus
from app.config.auth.dependencies import get_current_user


social_router = APIRouter()
# that's how we use dependency injection
current_user_dependency = Annotated[MyResponse, Depends(get_current_user)]


@social_router.get("/v1/followers", response_model=MyResponse)
async def fetch_followers(
    auth_response: current_user_dependency,
    user_id: Optional[str] = None,
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0, le=100),
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await fetch_followers_service(
        auth_response.result["user_id"], user_id, page, limit
    )


@social_router.get("/v1/following", response_model=MyResponse)
async def fetch_following(
    auth_response: current_user_dependency,
    user_id: Optional[str] = None,
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0, le=100),
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await fetch_following_service(
        auth_response.result["user_id"], user_id, page, limit
    )


@social_router.post("/v1/follow", response_model=MyResponse)
async def save_follow(
    auth_response: current_user_dependency,
    user_id: str,
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await save_follow_service(auth_response.result["user_id"], user_id)


@social_router.post("/v1/unfollow", response_model=MyResponse)
async def save_unfollow(
    auth_response: current_user_dependency,
    user_id: str,
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await save_unfollow_service(auth_response.result["user_id"], user_id)
