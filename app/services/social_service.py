import logging
from datetime import datetime, timezone
from app.config.database.mongo import (
    users_collection,
    users_connections_collection,
    points_collection,
    user_notifications_collection,
)
from app.utils.notification_manager import notification_manager
from app.utils.methods import (
    convert_iso_date_to_humanize,
    create_exception_response,
    create_success_response,
)
from app.utils.messages import (
    FETCHED_SUCCESS,
    INVALID_DATA,
    ALREADY_EXISTS,
    ACTION_SUCCESS,
    SAVED_SUCCESS,
)
from app.models.schema import User
from pymongo.errors import DuplicateKeyError
from app.services.user_service import get_verified_user, update_user_object

logger = logging.getLogger("uvicorn")


async def fetch_followers_service(login_user_id, user_id, page, limit):
    logger.info("social_service.fetch_followers_service")
    logger.info("Fetching followers for user_id: %s", user_id)
    try:
        saved_user, error = await get_verified_user(login_user_id)
        if error:
            return error
        if user_id:
            saved_user = await users_collection.find_one({"user_id": user_id})
            if not saved_user:
                return create_exception_response(
                    400, INVALID_DATA.format(data="user_id")
                )
        connections = []
        user_followings = {
            f["following_id"]: True
            for f in await users_connections_collection.find(
                {"follower_id": login_user_id}
            ).to_list(None)
        }
        async for result in (
            users_connections_collection.find({"following_id": saved_user["user_id"]})
            .skip((page - 1) * limit)
            .limit(limit)
        ):
            result.pop("_id", None)
            follower_user = await users_collection.find_one(
                {"user_id": result["follower_id"]}
            )
            connections.append(
                {
                    "user_id": follower_user["user_id"],
                    "username": follower_user["username"],
                    "name": follower_user["name"],
                    "avatar": follower_user["avatar"],
                    "total_followers": follower_user.get("total_followers", 0),
                    "is_following": user_followings.get(result["follower_id"], False),
                    "followed_at": result["followed_at"],
                    "followed_at_readable": convert_iso_date_to_humanize(
                        str(result["followed_at"])
                    ),
                }
            )
        total = await users_connections_collection.count_documents(
            {"following_id": saved_user["user_id"]}
        )
        return create_success_response(
            200,
            FETCHED_SUCCESS.format(data="followers"),
            total=total,
            results=connections,
        )
    except Exception as e:
        return create_exception_response(500, f"An unexpected error occurred: {str(e)}")


async def fetch_following_service(login_user_id, user_id, page, limit):
    logger.info("social_service.fetch_following_service")
    logger.info("Fetching following for user_id: %s", user_id)

    try:
        saved_user, error = await get_verified_user(login_user_id)
        if error:
            return error

        if user_id:
            saved_user = await users_collection.find_one({"user_id": user_id})
            if not saved_user:
                return create_exception_response(
                    400, INVALID_DATA.format(data="user_id")
                )

        # users that login_user_id follows
        user_followings = {
            f["following_id"]: True
            for f in await users_connections_collection.find(
                {"follower_id": login_user_id}
            ).to_list(None)
        }

        connections = []

        async for result in (
            users_connections_collection.find({"follower_id": saved_user["user_id"]})
            .skip((page - 1) * limit)
            .limit(limit)
        ):
            result.pop("_id", None)

            following_user = await users_collection.find_one(
                {"user_id": result["following_id"]}
            )

            connections.append(
                {
                    "user_id": following_user["user_id"],
                    "username": following_user["username"],
                    "name": following_user["name"],
                    "avatar": following_user["avatar"],
                    "total_followers": following_user.get("total_followers", 0),

                    # ✅ FIXED
                    "is_following": user_followings.get(
                        following_user["user_id"], False
                    ),

                    "followed_at": result["followed_at"],
                    "followed_at_readable": convert_iso_date_to_humanize(
                        str(result["followed_at"])
                    ),
                }
            )

        total = await users_connections_collection.count_documents(
            {"follower_id": saved_user["user_id"]}
        )

        return create_success_response(
            200,
            FETCHED_SUCCESS.format(data="following"),
            total=total,
            results=connections,
        )

    except Exception as e:
        return create_exception_response(500, f"An unexpected error occurred: {str(e)}")



async def save_follow_service(login_user_id, user_id):
    logger.info("social_service.save_follow_service")
    logger.info("Following user_id: %s", user_id)
    try:
        saved_user, error = await get_verified_user(login_user_id)
        if error:
            return error
        if saved_user["user_id"] == user_id:
            return create_exception_response(400, "you can't follow yourself")

        user: User = await users_collection.find_one({"user_id": user_id})
        if not user:
            return create_exception_response(400, INVALID_DATA.format(data="user_id"))

        existing = await users_connections_collection.find_one(
            {"follower_id": saved_user["user_id"], "following_id": user["user_id"]}
        )
        if existing:
            return create_exception_response(
                400, ALREADY_EXISTS.format(data="following")
            )

        await users_connections_collection.insert_one(
            {
                "follower_id": saved_user["user_id"],
                "following_id": user["user_id"],
                "followed_at": datetime.now(timezone.utc),
            }
        )
        await update_user_object(
            saved_user["_id"],
            {"total_following": saved_user.get("total_following", 0) + 1},
        )
        await update_user_object(
            user["_id"], {"total_followers": user.get("total_followers", 0) + 1}
        )
        # Reward points
        points = 10
        await points_collection.insert_one(
            {
                "user_id": login_user_id,
                "following_id": user["user_id"],
                "type": "earned",
                "icon": "👤",
                "points": points,
                "reason": "Followed user",
                "created_at": datetime.now(timezone.utc),
            }
        )
        await users_collection.update_one(
            {"user_id": login_user_id},
            {"$inc": {"total_points": points}},
        )
        # Add notification
        now = datetime.now(timezone.utc)
        notification_data = {
            "user_id": user["user_id"],
            "actor_id": login_user_id,
            "type": "follow",
            "message": f"{saved_user.get('name', 'Someone')} started following you",
            "is_read": False,
            "created_at": now,
        }
        await user_notifications_collection.insert_one(notification_data)

        # Push notification via WebSocket
        await notification_manager.send_personal_notification(
            user["user_id"],
            {
                "type": "follow",
                "message": notification_data["message"],
                "actor": {
                    "user_id": login_user_id,
                    "name": saved_user.get('name', 'Someone'),
                    "avatar": saved_user.get('avatar', 'https://i.pravatar.cc/300?img=3'),
                },
                "created_at": now.isoformat()
            }
        )

        saved_user: User = await users_collection.find_one({"user_id": login_user_id})
        return create_success_response(
            200,
            ACTION_SUCCESS.format(data=f"{user['username']} follow"),
            result={
                "total_follower": saved_user.get("total_followers", 0),
                "total_following": saved_user.get("total_following", 0),
            },
        )
    except DuplicateKeyError:
        return create_exception_response(400, ALREADY_EXISTS.format(data="following"))
    except Exception as e:
        return create_exception_response(500, f"An unexpected error occurred: {str(e)}")


async def save_unfollow_service(login_user_id, user_id):
    logger.info("social_service.save_unfollow_service")
    logger.info("Unfollowing user_id: %s", user_id)
    try:
        saved_user, error = await get_verified_user(login_user_id)
        if error:
            return error

        if saved_user["user_id"] == user_id:
            return create_exception_response(400, "you can't unfollow yourself")

        user: User = await users_collection.find_one({"user_id": user_id})
        if not user:
            return create_exception_response(400, INVALID_DATA.format(data="user_id"))

        existing = await users_connections_collection.find_one(
            {"follower_id": saved_user["user_id"], "following_id": user["user_id"]}
        )
        if not existing:
            return create_exception_response(400, "You are not following this user")

        await users_connections_collection.find_one_and_delete(
            {"follower_id": saved_user["user_id"], "following_id": user["user_id"]}
        )
        # Update the total followers and following counts
        await update_user_object(
            saved_user["_id"],
            {"total_following": max(0, saved_user.get("total_following", 0) - 1)},
        )
        # This is to ensure that total_followers does not go below 0
        await update_user_object(
            user["_id"], {"total_followers": max(0, user.get("total_followers", 0) - 1)}
        )
        # Deduct points
        points = 10
        await points_collection.delete_one(
            {
                "user_id": login_user_id,
                "following_id": user["user_id"],
                "reason": "Followed user",
            }
        )
        await users_collection.update_one(
            {"user_id": login_user_id},
            [
                {
                    "$set": {
                        "total_points": {
                            "$max": [{"$subtract": ["$total_points", points]}, 0]
                        }
                    }
                }
            ],
        )
        saved_user: User = await users_collection.find_one({"user_id": login_user_id})
        return create_success_response(
            200,
            ACTION_SUCCESS.format(data=f"{user['username']} unfollow"),
            result={
                "total_follower": saved_user.get("total_followers", 0),
                "total_following": saved_user.get("total_following", 0),
            },
        )
    except DuplicateKeyError:
        return create_exception_response(400, ALREADY_EXISTS.format(data="following"))
    except Exception as e:
        return create_exception_response(500, f"An unexpected error occurred: {str(e)}")
