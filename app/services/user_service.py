from datetime import datetime, timezone
import logging
import random
import uuid

from bson import ObjectId
from app.queue.in_memory import enqueue_otp_task
from app.config.auth.token import create_access_token
from app.models.schema import (
    PrefrenceRequest,
    RegisterDeviceRequest,
    SendOTP,
    VerifyOTP,
    RegenerateTokenRequest,
)
from app.utils.methods import (
    convert_iso_date_to_humanize,
    create_exception_response,
    create_success_response,
    is_invalid_field,
    is_valid_email,
    serialize_doc,
    token_expired_at,
)
from app.config.cache.in_memory_cache import (
    cached_mongo_call,
)
from pymongo.errors import DuplicateKeyError
from app.config.database.mongo import (
    points_collection,
    users_collection,
    interests_collection,
    user_devices_collection,
    users_connections_collection,
    email_config_collection,
)
from app.utils.constants import (
    MAIL_SMTP_HOST,
    MAIL_SMTP_PASSWORD,
    MAIL_SMTP_PORT,
    MAIL_SMTP_USER,
    OTP_EMAIL_TEMPLATE,
    VALID_PLATFORMS,
)
from app.utils.messages import (
    ALREADY_EXISTS_FIELD,
    ALREADY_LOGOUT,
    CREATED_SUCCESS,
    DEFAULT_USERNAME,
    FETCHED_SUCCESS,
    INVALID_DATA,
    INVALID_TOKEN,
    IS_REQUIRED,
    LOGOUT_SUCCESS,
    NO_PREFERENCE,
    NOT_FOUND,
    OTP_VERIFIED,
    SELECT_REQUIRED,
    SOME_ERROR,
)

logger = logging.getLogger("uvicorn")


async def fetch_interests_service():
    logger.info("user_service.fetch_interests_service")

    interests_cursor = interests_collection.find({}).sort("title", 1)
    interests = [serialize_doc(doc) async for doc in interests_cursor]

    return create_success_response(
        200,
        FETCHED_SUCCESS.format(data="interests"),
        results=interests,
    )


async def fetch_prefrences_service(device_id: str, user_id: str):
    logger.info("user_service.fetch_prefrences_service")
    logger.info(f"Fetching prefrences for device {device_id} and user {user_id}")
    if user_id:
        saved_user = await users_collection.find_one(
            {"user_id": user_id, "devices.device_id": device_id}
        )
        if not saved_user:
            return create_exception_response(400, NO_PREFERENCE)

        devices = saved_user.get("devices", [])
        current_device = next(
            (d for d in devices if d.get("device_id") == device_id), {}
        )

        current_token = current_device.get("access_token", "")
        current_token, token_expiry, regenerated = regenerate_access_token_if_needed(
            user_id, device_id, current_token
        )

        if regenerated:
            await users_collection.update_one(
                {"_id": saved_user["_id"], "devices.device_id": device_id},
                {
                    "$set": {
                        "devices.$.access_token": current_token,
                        "devices.$.token_expire_at": token_expiry,
                        "devices.$.logged_out_at": None,
                    }
                },
            )

        return build_preference_response(
            {**saved_user, **current_device},
            device_id,
            current_token,
            token_expiry,
            user_id,
        )

    # device-only user
    saved_device_user = await user_devices_collection.find_one({"device_id": device_id})
    if not saved_device_user:
        return create_exception_response(400, NO_PREFERENCE)

    current_token = saved_device_user.get("access_token", "")
    current_token, token_expiry, regenerated = regenerate_access_token_if_needed(
        device_id, user_id, current_token
    )

    if regenerated:
        await user_devices_collection.update_one(
            {"_id": saved_device_user["_id"]},
            {
                "$set": {
                    "access_token": current_token,
                    "token_expire_at": token_expiry,
                    "logged_out_at": None,
                }
            },
        )

    return build_preference_response(
        saved_device_user, device_id, current_token, token_expiry
    )


# Response builder
def build_preference_response(doc, device_id, token, token_expiry, user_id=None):
    return create_success_response(
        200,
        FETCHED_SUCCESS.format(data="my preferences"),
        result={
            "saved_preferences": {
                "access_token": token,
                "interests": doc.get("interests", []),
                "created_at": doc.get("created_at"),
                "device_id": device_id,
                "email": doc.get("email") if user_id else None,
                "platform": doc.get("platform", ""),
                "token_type": "bearer",
                "token_expire_at": token_expiry,
                "user_id": user_id,
                "username": doc.get("username", None),
            }
        },
    )


def regenerate_access_token_if_needed(device_id, user_id, token):
    if token_expired_at(token) < datetime.now(timezone.utc):
        new_token = create_access_token(data={"sub": device_id, "user_id": user_id})
        new_expiry = token_expired_at(new_token)
        return new_token, new_expiry, True
    return token, token_expired_at(token), False


async def save_prefrence_service(request: PrefrenceRequest):
    logger.info("user_service.save_prefrence_service")
    logger.info(
        f"Saving preferences for device {request.device_id} with platform: {request.platform}"
    )
    status_code = 400
    if is_invalid_field(request.device_id):
        return create_exception_response(
            status_code, IS_REQUIRED.format(data="device id")
        )
    if request.platform not in VALID_PLATFORMS:
        return create_exception_response(
            status_code,
            INVALID_DATA.format(data="platform, valid value is ios | android | web"),
        )
    if len(request.interests) == 0:
        return create_exception_response(
            status_code, SELECT_REQUIRED.format(data="interests")
        )
    try:
        user_id = str(uuid.uuid4())
        access_token = create_access_token(
            data={"sub": request.device_id, "user_id": user_id}
        )
        username = DEFAULT_USERNAME.format(data=str(random.randint(8**9, 8**10 - 1)))
        await user_devices_collection.insert_one(
            {
                "device_id": request.device_id,
                "platform": request.platform,
                "user_id": user_id,
                "username": username,
                "interests": request.interests,
                "token_type": "bearer",
                "access_token": access_token,
                "token_expire_at": token_expired_at(access_token),
                "created_at": datetime.now(timezone.utc),
            }
        )
        await users_collection.insert_one(
            {
                "email": f"{username}@email.com",
                "user_id": user_id,
                "username": username,
                "created_at": datetime.now(timezone.utc),
                "interests": request.interests,
                "devices": [{"device_id": request.device_id}],
            }
        )
    except DuplicateKeyError as e:
        error_msg = str(e)
        if "device_id" in error_msg:
            data = "device id"
        else:
            data = "a unique field"
        return create_exception_response(409, ALREADY_EXISTS_FIELD.format(data=data))

    return create_success_response(
        201,
        CREATED_SUCCESS.format(data="user preferences"),
        result={
            "saved_user": {
                "access_token": access_token,
                "interests": request.interests,
                "created_at": datetime.now(timezone.utc),
                "device_id": request.device_id,
                "email": "",
                "platform": request.platform,
                "token_type": "bearer",
                "token_expire_at": token_expired_at(access_token),
                "user_id": user_id,
                "username": username,
            },
        },
    )


async def register_device_service(request: RegisterDeviceRequest):
    logger.info("user_service.register_device_service")
    logger.info(
        f"Register device {request.device_id} with platform: {request.platform}"
    )
    status_code = 400
    if is_invalid_field(request.device_id):
        return create_exception_response(
            status_code, IS_REQUIRED.format(data="device id")
        )
    if request.platform not in VALID_PLATFORMS:
        return create_exception_response(
            status_code,
            INVALID_DATA.format(data="platform, valid value is ios | android | web"),
        )
    try:
        user_id = str(uuid.uuid4())
        access_token = create_access_token(
            data={"sub": request.device_id, "user_id": user_id}
        )
        username = DEFAULT_USERNAME.format(data=str(random.randint(8**9, 8**10 - 1)))
        await user_devices_collection.insert_one(
            {
                "device_id": request.device_id,
                "platform": request.platform,
                "user_id": user_id,
                "username": username,
                "token_type": "bearer",
                "access_token": access_token,
                "token_expire_at": token_expired_at(access_token),
                "created_at": datetime.now(timezone.utc),
            }
        )
    except DuplicateKeyError as e:
        error_msg = str(e)
        if "device_id" in error_msg:
            data = "device id"
        else:
            data = "a unique field"
        return create_success_response(200, ALREADY_EXISTS_FIELD.format(data=data))
    return create_success_response(
        201,
        CREATED_SUCCESS.format(data="device registered"),
        result={
            "saved_user": {
                "access_token": access_token,
                "created_at": datetime.now(timezone.utc),
                "device_id": request.device_id,
                "email": "",
                "platform": request.platform,
                "token_type": "bearer",
                "token_expire_at": token_expired_at(access_token),
                "user_id": user_id,
                "username": username,
            },
        },
    )


async def fetch_user_points_service(user_id: str):
    logger.info("user_service.fetch_user_points_service")
    saved_user = await users_collection.find_one({"user_id": user_id})
    if not saved_user:
        return create_exception_response(404, NOT_FOUND.format(data="user"))

    total_points = saved_user.get("total_points", 0)
    results = points_collection.find({"user_id": user_id}).sort("created_at", -1)
    activities = []
    async for result in results:
        activities.append(
            {
                "post_id": (
                    str(result.get("post_id")) if result.get("post_id") else None
                ),
                "type": result.get("type"),
                "reason": result.get("reason"),
                "points": result.get("points"),
                "timeAgo": convert_iso_date_to_humanize(result.get("created_at")),
                "icon": result.get("icon"),
            }
        )
    return create_success_response(
        200,
        FETCHED_SUCCESS.format(data="user points"),
        result={"total_points": total_points},
        results=activities,
    )


async def fetch_user_profile_service(login_user_id: str, user_id: str):
    logger.info("user_service.fetch_user_profile_service")

    target_user_id = user_id or login_user_id
    profile_type = "self" if target_user_id == login_user_id else "other"
    logger.info(f"Fetching {profile_type} profile for user_id: {target_user_id}")

    saved_user = await users_collection.find_one({"user_id": target_user_id})
    if not saved_user:
        return create_exception_response(
            400, INVALID_DATA.format(data="username")
        )

    interest_ids = saved_user.get("interests") or []

    is_following = False
    if login_user_id != target_user_id:
        is_following = await users_connections_collection.count_documents(
            {
                "follower_id": login_user_id,
                "following_id": target_user_id,
            }
        ) > 0

    result = {
        "user_id": saved_user.get("user_id"),
        "name": saved_user.get("name", ""),
        "avatar": saved_user.get("avatar", ""),
        "username": saved_user.get("username"),
        "bio": saved_user.get("bio", ""),
        "email": saved_user.get("email"),
        "gender": saved_user.get("gender"),
        "interests": interest_ids,
        "total_stories": saved_user.get("total_stories", 0),
        "total_jokes": saved_user.get("total_jokes", 0),
        "total_poems": saved_user.get("total_poems", 0),
        "total_quotes": saved_user.get("total_quotes", 0),
        "total_points": saved_user.get("total_points", 0),
        "total_followers": saved_user.get("total_followers", 0),
        "total_following": saved_user.get("total_following", 0),
        "is_following": is_following,
    }

    return create_success_response(
        200,
        FETCHED_SUCCESS.format(data="user"),
        result=result,
    )


async def update_user_profile_service(user_id: str, request):
    logger.info(f"Updating profile for user with user_id: {user_id}")
    saved_user = await users_collection.find_one({"user_id": user_id})
    if not saved_user:
        return create_exception_response(404, NOT_FOUND.format(data="user"))
    update_fields = {}
    if request.name is not None:
        update_fields["name"] = request.name.strip()
    if request.avatar is not None:
        update_fields["avatar"] = request.avatar.strip()
    if request.bio is not None:
        update_fields["bio"] = request.bio.strip()
    if request.username is not None:
        update_fields["username"] = request.username.strip()
    if request.interests is not None:
        update_fields["interests"] = request.interests
    if request.gender is not None:
        update_fields["gender"] = request.gender.strip()
    if update_fields:
        await users_collection.update_one(
            {"_id": saved_user.get("_id")},
            {"$set": update_fields},
        )
    return create_success_response(
        200,
        FETCHED_SUCCESS.format(data="user profile updated"),
    )


async def user_send_otp_service(send_otp: SendOTP):
    logger.info("user_service.user_send_otp_service")
    logger.info(
        f"Sending OTP for device {send_otp.device_id} with email: {send_otp.email}"
    )
    email = send_otp.email.strip().lower()
    if not is_valid_email(email):
        return create_exception_response(400, INVALID_DATA.format(data="email"))

    saved_device_user = await user_devices_collection.find_one(
        {"device_id": send_otp.device_id}
    )
    if saved_device_user is None:
        return create_exception_response(400, INVALID_DATA.format(data="device id"))

    saved_user = await users_collection.find_one(
        {"devices.device_id": send_otp.device_id, "email": email}
    )
    if saved_user is None:
        # may be same email is trying to login with different device
        saved_user = await users_collection.find_one({"email": email})
        if saved_user is not None:
            await users_collection.update_one(
                {"_id": saved_user.get("_id")},
                {"$addToSet": {"devices": {"device_id": send_otp.device_id}}},
            )

        # means first time otp sending
        if saved_user is None:
            saved_user = await users_collection.find_one(
                {
                    "devices.device_id": send_otp.device_id,
                    "email": {"$regex": r"^vurse_", "$options": "i"},
                }
            )

    otp = random.randint(1000, 9999)

    if saved_user is not None:
        user_id = saved_user.get("user_id")
        device_user_id = saved_device_user.get("user_id")
        if user_id == device_user_id:
            user_id = str(uuid.uuid4())
        await users_collection.update_one(
            {"_id": saved_user.get("_id"), "devices.device_id": send_otp.device_id},
            {
                "$set": {
                    "email": email,
                    "devices.$.otp": otp,
                    "devices.$.otp_verified": False,
                    "user_id": user_id,
                    "username": f"{email.split('@')[0]}_{random.randint(100, 999)}",
                }
            },
        )
    else:
        await users_collection.insert_one(
            {
                "email": email,
                "user_id": str(uuid.uuid4()),
                "username": f"{email.split('@')[0]}_{random.randint(100, 999)}",
                "created_at": datetime.now(timezone.utc),
                "interests": saved_device_user.get("interests"),
                "devices": [
                    {
                        "device_id": send_otp.device_id,
                        "otp": otp,
                        "otp_verified": False,
                    }
                ],
            }
        )

    saved_email_config = await email_config_collection.find_one({})
    if not saved_email_config:
        saved_email_config = {
            "mail_smtp_host": MAIL_SMTP_HOST,
            "mail_smtp_port": MAIL_SMTP_PORT,
            "mail_smtp_user": MAIL_SMTP_USER,
            "mail_smtp_password": MAIL_SMTP_PASSWORD,
            "use_tls": True,
            "otp_email_template": OTP_EMAIL_TEMPLATE,
        }
    await enqueue_otp_task({"email": email, "otp": otp, "config": saved_email_config})
    logger.info(f"✅ OTP task enqueued for {email}")
    return create_success_response(200, f"OTP is being sent to {email}")


async def user_verify_otp_service(verify_otp: VerifyOTP):
    logger.info("user_service.user_verify_otp_service")
    logger.info(
        f"Verifying OTP for device {verify_otp.device_id} with email: {verify_otp.email}"
    )
    email = verify_otp.email
    if not is_valid_email(email):
        return create_exception_response(400, INVALID_DATA.format(data="email"))

    saved_device_user = await user_devices_collection.find_one(
        {"device_id": verify_otp.device_id}
    )
    if saved_device_user is None:
        return create_exception_response(400, INVALID_DATA.format(data="device id"))

    saved_user = await users_collection.find_one(
        {"devices.device_id": verify_otp.device_id, "email": verify_otp.email}
    )
    if not saved_user:
        return create_exception_response(400, INVALID_DATA.format(data="device id"))

    device = next(
        (
            d
            for d in saved_user.get("devices", [])
            if d.get("device_id") == verify_otp.device_id
        ),
        None,
    )

    if not device or device.get("otp") != verify_otp.otp:
        return create_exception_response(400, INVALID_DATA.format(data="otp"))

    access_token = create_access_token(
        data={
            "sub": verify_otp.device_id,
            "user_id": saved_user.get("user_id"),
        }
    )
    await users_collection.update_one(
        {"_id": saved_user.get("_id"), "devices.device_id": verify_otp.device_id},
        {
            "$set": {
                "devices.$.otp": "",
                "devices.$.otp_verified": True,
                "devices.$.access_token": access_token,
                "devices.$.token_expire_at": token_expired_at(access_token),
                "devices.$.logged_in_at": datetime.now(timezone.utc),
                "devices.$.logged_out_at": None,
            }
        },
    )
    return create_success_response(
        200,
        OTP_VERIFIED,
        result={
            "saved_user": {
                "access_token": access_token,
                "interests": saved_device_user.get("interests", []),
                "device_id": verify_otp.device_id,
                "email": email,
                "platform": saved_device_user.get("platform", ""),
                "token_expire_at": token_expired_at(access_token),
                "username": saved_user.get("username"),
                "user_id": saved_user.get("user_id"),
            },
        },
    )


async def regenerate_token_service(request: RegenerateTokenRequest):
    logger.info("user_service.regenerate_token_service")
    logger.info(
        f"Regenerating token for device {request.device_id} and user {request.user_id}"
    )

    # Check if user exists with this device
    saved_user = await users_collection.find_one(
        {"user_id": request.user_id, "devices.device_id": request.device_id}
    )

    if not saved_user:
        # Check if it's a device-only user
        saved_device_user = await user_devices_collection.find_one(
            {"device_id": request.device_id, "user_id": request.user_id}
        )
        if not saved_device_user:
            return create_exception_response(
                400, NOT_FOUND.format(data="user/device record")
            )

        doc = saved_device_user
        collection = user_devices_collection
        query = {"_id": doc["_id"]}
        update_query = {
            "$set": {
                "access_token": None,
                "token_expire_at": None,
            }
        }  # Placeholder, will update below
    else:
        doc = saved_user
        collection = users_collection
        query = {"_id": doc["_id"], "devices.device_id": request.device_id}

    # Generate new token
    access_token = create_access_token(
        data={"sub": request.device_id, "user_id": request.user_id}
    )
    expiry = token_expired_at(access_token)

    # Update token in database
    if saved_user:
        await collection.update_one(
            query,
            {
                "$set": {
                    "devices.$.access_token": access_token,
                    "devices.$.token_expire_at": expiry,
                    "devices.$.logged_out_at": None,
                }
            },
        )
    else:
        await collection.update_one(
            query,
            {
                "$set": {
                    "access_token": access_token,
                    "token_expire_at": expiry,
                    "logged_out_at": None,
                }
            },
        )

    return create_success_response(
        200,
        FETCHED_SUCCESS.format(data="token regenerated"),
        result={
            "access_token": access_token,
            "token_expire_at": expiry,
            "token_type": "bearer",
        },
    )


async def user_logout_service(auth_response):
    logger.info("user_service.user_logout_service")
    logger.info(f"Logging out user with device_id: {auth_response.result['device_id']}")
    device_id = auth_response.result["device_id"]
    user_id = auth_response.result.get("user_id")
    saved_user = await users_collection.find_one(
        {"devices.device_id": device_id, "user_id": user_id}
    )
    if saved_user:
        devices = saved_user.get("devices", [])
        current_device = next(
            (d for d in devices if d.get("device_id") == device_id), None
        )

        if current_device.get("access_token") is None:
            return create_exception_response(400, INVALID_TOKEN)
        if not current_device.get("otp_verified", True):
            return create_exception_response(400, ALREADY_LOGOUT)
        await users_collection.update_one(
            {
                "_id": saved_user.get("_id"),
                "devices.device_id": device_id,
            },
            {
                "$set": {
                    "devices.$.otp_verified": False,
                    "devices.$.logged_in_at": None,
                    "devices.$.access_token": None,
                    "devices.$.token_expire_at": None,
                    "devices.$.logged_out_at": datetime.now(timezone.utc),
                }
            },
        )
        saved_device_user = await user_devices_collection.find_one(
            {"device_id": device_id}
        )
        access_token = create_access_token(
            data={
                "sub": device_id,
                "user_id": saved_device_user.get("user_id", user_id),
            }
        )
        token_expire_at = token_expired_at(access_token)

        await user_devices_collection.update_one(
            {"_id": ObjectId(saved_device_user.get("_id"))},
            {
                "$set": {
                    "access_token": access_token,
                    "token_expire_at": token_expire_at,
                }
            },
        )

        return create_success_response(
            200,
            LOGOUT_SUCCESS,
            result={
                "access_token": access_token,
                "token_expire_at": token_expire_at,
                "token_type": "bearer",
            },
        )
    return create_exception_response(404, NOT_FOUND.format(data="user"))


async def get_verified_user(user_id: str):
    user = await users_collection.find_one({"user_id": user_id})
    if not user:
        return None, create_exception_response(400, SOME_ERROR)
    return user, None


async def update_user_object(id, set):
    await users_collection.update_one(
        {"_id": id},
        {"$set": set},
    )
