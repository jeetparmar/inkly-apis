from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
from app.utils.settings import settings

client = AsyncIOMotorClient(settings.mongo_details)
database = client.get_database()

users_collection = database.get_collection("users")
interests_collection = database.get_collection("interests")
posts_collection = database.get_collection("posts")
posts_hearts_collection = database.get_collection("posts_hearts")
posts_views_collection = database.get_collection("posts_views")
posts_comments_collection = database.get_collection("posts_comments")
posts_bookmarks_collection = database.get_collection("posts_bookmarks")
user_devices_collection = database.get_collection("user_devices")
email_config_collection = database.get_collection("email_config")
users_connections_collection = database.get_collection("users_connections")
points_collection = database.get_collection("points")


async def create_device_id_index():
    await user_devices_collection.create_index([("device_id", 1)], unique=True)


async def create_user_id_index():
    await users_collection.create_index([("user_id", 1)], unique=True)


async def create_user_email_index():
    await users_collection.create_index([("email", 1)])


async def create_user_device_id_index():
    await users_collection.create_index([("devices.device_id", 1)])


async def create_post_view_index():
    await posts_views_collection.create_index(
        [("user_id", 1), ("post_id", 1)], unique=True
    )


async def create_post_heart_index():
    await posts_hearts_collection.create_index(
        [("user_id", 1), ("post_id", 1)], unique=True
    )


async def create_post_bookmark_index():
    await posts_bookmarks_collection.create_index(
        [("user_id", 1), ("post_id", 1)], unique=True
    )


user_notifications_collection = database.get_collection("user_notifications")
content_configs_collection = database.get_collection("content_configs")


async def create_user_notifications_index():
    await user_notifications_collection.create_index(
        [("user_id", 1), ("created_at", -1)]
    )
