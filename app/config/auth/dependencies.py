from fastapi import Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.utils.methods import (
    create_exception_response,
    create_success_response,
)
from app.utils.messages import INVALID_TOKEN, USER_FOUND
from .token import verify_token

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    result = verify_token(token)
    if not isinstance(result, tuple):
        return result
    device_id, user_id = result
    if not device_id:
        return create_exception_response(status.HTTP_401_UNAUTHORIZED, INVALID_TOKEN)
    return create_success_response(
        200, USER_FOUND, result={"device_id": device_id, "user_id": user_id}
    )


def get_current_user_ws(token: str):
    device_id, user_id = verify_token(token)
    if not device_id:
        return create_exception_response(status.HTTP_401_UNAUTHORIZED, INVALID_TOKEN)
    return create_success_response(
        200, USER_FOUND, result={"device_id": device_id, "user_id": user_id}
    )
