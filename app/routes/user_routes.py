from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query
from app.services.user_service import (
    fetch_prefrences_service,
    fetch_user_points_service,
    fetch_user_profile_service,
    register_device_service,
    save_prefrence_service,
    fetch_interests_service,
    update_user_profile_service,
    user_send_otp_service,
    user_verify_otp_service,
    user_logout_service,
    regenerate_token_service,
    fetch_users_service,
)
from app.utils.enums.ResponseStatus import ResponseStatus
from app.config.auth.dependencies import get_current_user
from app.models.schema import (
    MyResponse,
    PrefrenceRequest,
    RegisterDeviceRequest,
    SendOTP,
    UserProfileUpdateRequest,
    VerifyOTP,
    RegenerateTokenRequest,
)

user_router = APIRouter()

# that's how we use dependency injection
current_user_dependency = Annotated[MyResponse, Depends(get_current_user)]


@user_router.get("/v1/interests")
async def fetch_interests():
    return await fetch_interests_service()


@user_router.get("/v1/prefrence", response_model=MyResponse)
async def fetch_prefrences(device_id: str, user_id: Optional[str] = None):
    return await fetch_prefrences_service(device_id, user_id)


@user_router.post("/v1/prefrence", response_model=MyResponse)
async def save_prefrence(request: PrefrenceRequest):
    return await save_prefrence_service(request)


@user_router.post("/v1/register_device", response_model=MyResponse)
async def register_device(request: RegisterDeviceRequest):
    return await register_device_service(request)


@user_router.get("/v1/points")
async def fetch_points(auth_response: current_user_dependency, page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0, le=100)):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await fetch_user_points_service(auth_response.result["user_id"], page, limit)


@user_router.get("/v1/profile")
async def fetch_profile(
    auth_response: current_user_dependency, user_id: Optional[str] = None
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await fetch_user_profile_service(auth_response.result["user_id"], user_id)


@user_router.put("/v1/profile")
async def fetch_profile(
    auth_response: current_user_dependency, request: UserProfileUpdateRequest
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await update_user_profile_service(auth_response.result["user_id"], request)


@user_router.post("/v1/send_otp", response_model=MyResponse)
async def user_send_otp(send_otp: SendOTP):
    return await user_send_otp_service(send_otp)


@user_router.post("/v1/verify_otp", response_model=MyResponse)
async def user_verify_otp(verify_otp: VerifyOTP):
    return await user_verify_otp_service(verify_otp)


@user_router.post("/v1/logout", response_model=MyResponse)
async def user_logout(
    auth_response: current_user_dependency,
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await user_logout_service(auth_response)


@user_router.post("/v1/regenerate_token", response_model=MyResponse)
async def regenerate_token(request: RegenerateTokenRequest):
    return await regenerate_token_service(request)


@user_router.get("/v1/search")
async def fetch_users(
    auth_response: current_user_dependency,
    search: str = Query(..., min_length=0),
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0, le=100),
):
    if auth_response.status == ResponseStatus.FAILURE:
        return auth_response
    return await fetch_users_service(
        search, page, limit, auth_response.result["user_id"]
    )
