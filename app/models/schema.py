from typing import Optional
from pydantic import BaseModel
from app.utils.enums.Gender import Gender
from app.utils.enums.ResponseStatus import ResponseStatus


class MyResponse(BaseModel):
    status: str = ResponseStatus.SUCCESS.name
    status_code: int = 200
    message: str
    query: Optional[any] = None
    total: Optional[int] = None
    result: Optional[any] = None
    results: Optional[any] = None
    model_config = {"arbitrary_types_allowed": True}


class RegisterDeviceRequest(BaseModel):
    platform: str
    device_id: str


class PrefrenceRequest(BaseModel):
    platform: str
    device_id: str
    interests: list[str]


class CommentText(BaseModel):
    text: str


class PostRequest(BaseModel):
    title: Optional[str] = None
    image: Optional[str] = None
    content: str = None
    is_anonymous: bool = False
    is_draft: bool = False
    is_18_plus: bool = False


class SendOTP(BaseModel):
    device_id: str
    email: str


class VerifyOTP(BaseModel):
    device_id: str
    email: str
    otp: int


class UserProfileUpdateRequest(BaseModel):
    avatar: Optional[str] = None
    name: Optional[str] = None
    bio: Optional[str] = None
    username: Optional[str] = None
    gender: Optional[Gender] = None
    interests: Optional[list[str]] = None


class User(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    platform: str
    device_id: str
    gender: Optional[Gender] = None
    interests: list[str]
    total_stories: int = 0
    total_followers: int = 0
    total_following: int = 0


class RegenerateTokenRequest(BaseModel):
    device_id: str
    user_id: str


class RedeemReferralCodeRequest(BaseModel):
    referral_code: str

