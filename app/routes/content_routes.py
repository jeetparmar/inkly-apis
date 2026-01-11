from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query
from app.services.content_service import (
    delete_post_service,
    generate_content_from_llm_service,
    fetch_related_images_service,
    fetch_posts_service,
    fetch_user_posts_service,
    save_post_service,
    save_view_count_service,
    delete_comment_service,
    toggle_bookmark_service,
    toggle_heart_service,
    save_comment_service,
    fetch_comments_service,
)
from app.models.schema import CommentText, MyResponse, PostRequest
from app.utils.enums.PostType import PostType
from app.utils.enums.ResponseStatus import ResponseStatus
from app.config.auth.dependencies import get_current_user

content_router = APIRouter()

# that's how we use dependency injection
current_user_dependency = Annotated[MyResponse, Depends(get_current_user)]


@content_router.get("/v1/images", response_model=MyResponse)
async def fetch_related_images(auth_response: current_user_dependency, title: str):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await fetch_related_images_service(auth_response.result["user_id"], title)


@content_router.get("/v1/generate", response_model=MyResponse)
async def generate_content_from_llm(
    auth_response: current_user_dependency,
    type: PostType,
    prompt: str,
    size: int,
    theme: Optional[str] = "inspiring",
    language: Optional[str] = "English",
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response

    return await generate_content_from_llm_service(
        auth_response.result["user_id"],
        type,
        prompt,
        theme,
        size,
        language,
    )


@content_router.get("/v1/posts", response_model=MyResponse)
async def fetch_posts(
    auth_response: current_user_dependency,
    type: Optional[PostType] = None,
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0, le=100),
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await fetch_posts_service(auth_response.result["user_id"], type, page, limit)


@content_router.get("/v1/user_posts", response_model=MyResponse)
async def fetch_user_posts(
    auth_response: current_user_dependency,
    type: PostType,
    user_id: Optional[str] = None,
    is_draft: bool = False,
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0, le=100),
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await fetch_user_posts_service(
        auth_response.result["user_id"], user_id, is_draft, type, page, limit
    )


@content_router.post("/v1/post", response_model=MyResponse)
async def save_post(
    auth_response: current_user_dependency,
    request: PostRequest,
    type: PostType,
    post_id: Optional[str] = None,
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await save_post_service(
        auth_response.result["user_id"], request, type, post_id
    )


@content_router.delete("/v1/post/{post_id}", response_model=MyResponse)
async def delete_post(
    auth_response: current_user_dependency,
    post_id: str,
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await delete_post_service(auth_response.result["user_id"], post_id)


@content_router.post("/v1/view/{post_id}", response_model=MyResponse)
async def save_post_view_count(auth_response: current_user_dependency, post_id: str):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await save_view_count_service(auth_response.result["user_id"], post_id)


@content_router.post("/v1/bookmark/{post_id}")
async def save_bookmark(auth_response: current_user_dependency, post_id: str):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await toggle_bookmark_service(auth_response.result["user_id"], post_id)


@content_router.post("/v1/heart/{post_id}")
async def save_heart(auth_response: current_user_dependency, post_id: str):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await toggle_heart_service(auth_response.result["user_id"], post_id)


@content_router.get("/v1/comments/{post_id}")
async def fetch_comments(
    auth_response: current_user_dependency,
    post_id: str,
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0, le=100),
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await fetch_comments_service(
        auth_response.result["user_id"], post_id, page, limit
    )


@content_router.post("/v1/comment/{post_id}")
async def save_comment(
    auth_response: current_user_dependency, post_id: str, text: CommentText
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await save_comment_service(
        auth_response.result["user_id"], post_id, text.text
    )


@content_router.delete("/v1/comment/{comment_id}")
async def delete_comment(auth_response: current_user_dependency, comment_id: str):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await delete_comment_service(auth_response.result["user_id"], comment_id)
