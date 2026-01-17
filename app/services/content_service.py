import asyncio
from datetime import datetime, timezone, timedelta
import logging
import re
import json
from bson import ObjectId
from bson import errors as bson_errors
import httpx
from pymongo import ReturnDocument
from app.models.schema import PostRequest
from app.utils.enums.PostType import PostType
from app.utils.enums.PostFilters import PostDuration, PostSortBy, PostFilter
from app.utils.gemini import ask_from_gemini
from app.utils.methods import (
    convert_iso_date_to_humanize,
    create_success_response,
    create_exception_response,
)
from app.utils.messages import (
    ACTION_SUCCESS,
    FETCHED_SUCCESS,
    INVALID_DATA,
    NOT_FOUND,
)
from app.services.user_service import get_verified_user
from app.config.database.mongo import (
    posts_collection,
    users_collection,
    points_collection,
    posts_views_collection,
    posts_hearts_collection,
    posts_comments_collection,
    posts_bookmarks_collection,
    users_connections_collection,
    user_notifications_collection
)
from app.utils.settings import settings

logger = logging.getLogger("uvicorn")


async def fetch_related_images_service(login_user_id: str, title: str):
    logger.info("content_service.fetch_related_images")

    # Verify user
    saved_user, error = await get_verified_user(login_user_id)
    if error:
        return error

    params = {
        "query": title.replace(" ", ",").lower(),
        "client_id": settings.client_id,
        "per_page": 15,
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(settings.unsplash_url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as e:
            create_exception_response(500, f"Error fetching Unsplash API: {str(e)}")
    data = response.json()
    # Extract only the small image URLs
    small_image_urls = [
        item["urls"]["small"]
        for item in data.get("results", [])
        if "urls" in item and "small" in item["urls"]
    ]
    return create_success_response(
        200,
        FETCHED_SUCCESS.format(data="related images"),
        results=small_image_urls,
    )


async def generate_content_from_llm_service(
    login_user_id: str,
    ai_key: str,
    type: PostType = None,
    prompt: str = "a little boy",
    theme: str = None,
    size: int = 50,
    language: str = "English",
):
    logger.info("content_service.generate_content_from_llm_service")

    # Verify user
    saved_user, error = await get_verified_user(login_user_id)
    if error:
        return error
    # Call LLM
    output = ask_from_gemini(ai_key, type, prompt, size, language, theme)
    if not output:
        return create_exception_response(500, "LLM returned empty output")

    try:
        title = output.get("title", "")
        content = output.get("content", "")

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return create_exception_response(500, "Invalid JSON returned from LLM")

    return create_success_response(
        200,
        FETCHED_SUCCESS.format(data="generated content"),
        query={"type": type, "prompt": prompt, "theme": theme, "size": size},
        result={"title": title, "content": content},
    )


# ---------------- Posts Service ----------------
async def fetch_posts_service(
    login_user_id: str,
    types: list[PostType],
    search: str,
    filter: PostFilter = PostFilter.NONE,
    user_id: str = None,
    duration: PostDuration = PostDuration.ALL_TIME,
    sort_by: PostSortBy = PostSortBy.NEWEST,
    page: int = 1,
    limit: int = 10,
):
    logger.info("content_service.fetch_posts_service")

    # ---------------- Verify User ----------------
    saved_user, error = await get_verified_user(login_user_id)
    if error:
        return error

    page = max(page, 1)
    limit = max(limit, 1)
    # ---------------- Query Stories ----------------
    query = {"is_draft": False}
    if types:
        query["type"] = {"$in": types}
    
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"content": {"$regex": search, "$options": "i"}},
        ]

    # ---------------- Filter by Duration ----------------
    if duration and duration != PostDuration.ALL_TIME:
        now = datetime.now(timezone.utc)
        if duration == PostDuration.LAST_24H:
            query["created_at"] = {"$gte": now - timedelta(days=1)}
        elif duration == PostDuration.LAST_7D:
            query["created_at"] = {"$gte": now - timedelta(days=7)}
        elif duration == PostDuration.LAST_30D:
            query["created_at"] = {"$gte": now - timedelta(days=30)}

    # ---------------- Filter by Source ----------------
    if filter == PostFilter.FOLLOWING:
        followings = await users_connections_collection.find(
            {"follower_id": login_user_id}
        ).to_list(None)
        following_ids = [f["following_id"] for f in followings]
        query["author.user_id"] = {"$in": following_ids}
    elif filter == PostFilter.FOLLOWERS:
        followers = await users_connections_collection.find(
            {"following_id": login_user_id}
        ).to_list(None)
        follower_ids = [f["follower_id"] for f in followers]
        query["author.user_id"] = {"$in": follower_ids}
    elif user_id:
        query["author.user_id"] = user_id

    # ---------------- Sorting ----------------
    sort_field = "created_at"
    if sort_by == PostSortBy.MOST_VIEWED:
        sort_field = "stats.views"
    elif sort_by == PostSortBy.MOST_HEARTED:
        sort_field = "stats.hearts"
    elif sort_by == PostSortBy.MOST_COMMENTED:
        sort_field = "stats.comments"

    total = await posts_collection.count_documents(query)

    cursor = (
        posts_collection.find(query)
        .sort(sort_field, -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )

    raw_posts = await cursor.to_list(length=limit)

    # ---------------- Fetch Related Data ----------------
    response = create_success_response(
        200,
        FETCHED_SUCCESS.format(data="posts"),
        results=await _format_posts_data(login_user_id, saved_user, raw_posts),
        total=total,
        page=page,
        limit=limit,
    )
    return response


async def _format_posts_data(login_user_id: str, saved_user: dict, raw_posts: list):
    # ---------------- Fetch Related Data ----------------
    post_ids = [s["_id"] for s in raw_posts]

    user_hearts = {
        h["post_id"]: True
        for h in await posts_hearts_collection.find(
            {"user_id": login_user_id, "post_id": {"$in": post_ids}}
        ).to_list(None)
    }

    user_bookmarks = {
        h["post_id"]: True
        for h in await posts_bookmarks_collection.find(
            {"user_id": login_user_id, "post_id": {"$in": post_ids}}
        ).to_list(None)
    }

    user_comments = {
        c["post_id"]: True
        for c in await posts_comments_collection.find(
            {"user_id": login_user_id, "post_id": {"$in": post_ids}}
        ).to_list(None)
    }

    post_user_ids = [s["author"]["user_id"] for s in raw_posts]

    user_followings = {
        f["following_id"]: True
        for f in await users_connections_collection.find(
            {"follower_id": login_user_id, "following_id": {"$in": post_user_ids}}
        ).to_list(None)
    }

    # ---------------- Format Response ----------------
    posts = []
    for post in raw_posts:
        post_id = post["_id"]
        post_user_id = post.get("author", {}).get("user_id", "")
        if post_user_id != saved_user.get("user_id", ""):
            user_id = post_user_id
            post_author = await users_collection.find_one({"user_id": user_id})
            name = post_author.get("name", "Unknown")
            username = post_author.get("username", "unknown")
            avatar = post_author.get("avatar", "https://i.pravatar.cc/300?img=3")
        else:
            user_id = saved_user.get("user_id", "")
            name = saved_user.get("name", "Unknown")
            username = saved_user.get("username", "unknown")
            avatar = saved_user.get("avatar", "https://i.pravatar.cc/300?img=3")

        posts.append(
            {
                "id": str(post_id),
                "type": post.get("type", ""),
                "title": post.get("title", ""),
                "image": post.get("image", ""),
                "content": post.get("content", ""),
                "author": {
                    "user_id": user_id,
                    "name": name,
                    "username": username,
                    "avatar": avatar,
                    "is_following": user_followings.get(post_user_id, False),
                    "is_verified": False,
                },
                "is_hearted": user_hearts.get(post_id, False),
                "is_commented": user_comments.get(post_id, False),
                "is_bookmarked": user_bookmarks.get(post_id, False),
                "stats": post.get("stats", {}),
                "created_at_readable": convert_iso_date_to_humanize(
                    post.get("created_at")
                ),
            }
        )
    return posts


async def fetch_bookmarks_service(
    login_user_id: str,
    page: int = 1,
    limit: int = 10,
):
    logger.info("content_service.fetch_bookmarks_service")

    # ---------------- Verify User ----------------
    saved_user, error = await get_verified_user(login_user_id)
    if error:
        return error

    page = max(page, 1)
    limit = max(limit, 1)

    # ---------------- Query Bookmarks ----------------
    total = await posts_bookmarks_collection.count_documents({"user_id": login_user_id})

    cursor = (
        posts_bookmarks_collection.find({"user_id": login_user_id})
        .sort("bookmarked_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )

    bookmarks = await cursor.to_list(length=limit)
    post_ids = [b["post_id"] for b in bookmarks]

    if not post_ids:
        return create_success_response(
            200,
            FETCHED_SUCCESS.format(data="bookmarks"),
            results=[],
            total=total,
            page=page,
            limit=limit,
        )

    # Fetch posts
    raw_posts = await posts_collection.find({"_id": {"$in": post_ids}}).to_list(None)

    # We need to maintain the order of bookmarks
    posts_map = {p["_id"]: p for p in raw_posts}
    ordered_raw_posts = [posts_map[pid] for pid in post_ids if pid in posts_map]

    response = create_success_response(
        200,
        FETCHED_SUCCESS.format(data="bookmarks"),
        results=await _format_posts_data(login_user_id, saved_user, ordered_raw_posts),
        total=total,
        page=page,
        limit=limit,
    )
    return response


# ---------------- User Posts Service ----------------
async def fetch_user_posts_service(
    login_user_id: str,
    user_id: str = None,
    is_draft: bool = False,
    types: PostType = None,
    search: str = None,
    page: int = 1,
    limit: int = 10,
):
    logger.info("content_service.fetch_user_stories_service")

    # ---------------- Verify User ----------------
    saved_user, error = await get_verified_user(login_user_id)
    if error:
        return error

    # Determine whose stories we are fetching
    if user_id:
        is_draft = False  # Only public stories for other users
        other_user = await users_collection.find_one({"user_id": user_id})
        if not other_user:
            return create_exception_response(400, INVALID_DATA.format(data="user_id"))
    else:
        user_id = login_user_id

    page = max(page, 1)
    limit = max(limit, 1)

    # ---------------- Query Stories ----------------
    query = {"author.user_id": user_id, "is_draft": is_draft}
    if type:
        query["type"] = types

    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"content": {"$regex": search, "$options": "i"}},
        ]
    total = await posts_collection.count_documents(query)

    cursor = (
        posts_collection.find(query)
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )

    posts = []
    async for post in cursor:
        post["id"] = str(post.pop("_id"))

        author_id = post["author"]["user_id"]
        author_user = await users_collection.find_one({"user_id": author_id}) or {}
        post["author"].update(
            {
                "name": author_user.get("username", "Unknown"),
                "avatar": author_user.get("avatar", "https://i.pravatar.cc/300?img=3"),
                "is_verified": author_user.get("is_verified", False),
                "is_following": False,
            }
        )
        posts.append(post)

    # ---------------- Build Response ----------------
    response = create_success_response(
        200,
        FETCHED_SUCCESS.format(data="user stories"),
        results=posts,
        total=total,
        page=page,
        limit=limit,
    )
    return response


async def save_post_service(
    login_user_id: str,
    request: PostRequest,
    type: PostType,
    post_id: str = None,
):
    logger.info(f"User {login_user_id} saving {type} {post_id or 'new'}")

    # Verify user
    saved_user, error = await get_verified_user(login_user_id)
    if error:
        return create_exception_response(400, error)

    now = datetime.now(timezone.utc)

    try:
        if post_id:
            # Validate ObjectId
            try:
                obj_id = ObjectId(post_id)
            except Exception:
                return create_exception_response(400, "Invalid post_id")

            # Only update non-stat fields
            update_fields = {
                "title": request.title,
                "image": request.image,
                "content": request.content,
                "is_anonymous": request.is_anonymous,
                "is_18_plus": request.is_18_plus,
                "is_draft": request.is_draft,
                "updated_at": now,
            }

            result = await posts_collection.update_one(
                {"_id": obj_id, "author.user_id": login_user_id},
                {"$set": update_fields},
                upsert=False,
            )

            if result.matched_count == 0:
                return create_exception_response(
                    404, "post id not found or unauthorized"
                )

            message = f"{type.value} updated successfully"
            status = 200
        else:
            # New post creation
            content_data = {
                "type": type,
                "author": {"user_id": login_user_id},
                "title": request.title,
                "image": request.image,
                "content": request.content,
                "is_anonymous": request.is_anonymous,
                "is_18_plus": request.is_18_plus,
                "is_draft": request.is_draft,
                "stats": {
                    "bookmarks": 0,
                    "comments": 0,
                    "hearts": 0,
                    "shares": 0,
                    "views": 0,
                },
                "created_at": now,
                "updated_at": now,
            }

            result = await posts_collection.insert_one(content_data)
            if type == PostType.story:
                points = 50
                icon = "📚"
                inc_request = {"total_stories": 1}
            elif type == PostType.joke:
                points = 40
                icon = "😂"
                inc_request = {"total_jokes": 1}
            elif type == PostType.poem:
                points = 40
                icon = "🎭"
                inc_request = {"total_poems": 1}
            elif type == PostType.quote:
                points = 40
                icon = "💭"
                inc_request = {"total_quotes": 1}
            elif type == PostType.fact:
                points = 40
                icon = "🧠"
                inc_request = {"total_facts": 1}
            elif type == PostType.riddle:
                points = 40
                icon = "🧩"
                inc_request = {"total_riddles": 1}
            elif type == PostType.article:
                points = 40
                icon = "📰"
                inc_request = {"total_articles": 1}
            message = f"{type.value} created successfully and earned {points} points"
            status = 201
            # Increment user post count
            await users_collection.update_one(
                {"user_id": login_user_id},
                {
                    "$inc": {
                        **inc_request,
                        "total_points": points,
                    }
                },
            )
            points_collection.insert_one(
                {
                    "user_id": login_user_id,
                    "post_id": result.inserted_id if not post_id else obj_id,
                    "type": "earned",
                    "icon": icon,
                    "points": points,
                    "reason": f"Posted {type.value}",
                    "created_at": now,
                }
            )
        return create_success_response(status, message, data={"post_id": post_id})
    except Exception as e:
        logger.error(f"Error saving post: {e}", exc_info=True)
        return create_exception_response(500, "Failed to save post. Please try again.")


async def delete_post_service(login_user_id: str, post_id: str):
    logger.info(f"User {login_user_id} deleting post {post_id}")

    # Verify user
    saved_user, error = await get_verified_user(login_user_id)
    if error:
        return create_exception_response(400, error)

    # Validate ObjectId
    try:
        post_obj_id = ObjectId(post_id)
    except bson_errors.InvalidId:
        return create_exception_response(400, "Invalid post_id")

    # Fetch the post + verify ownership in one query
    post = await posts_collection.find_one(
        {"_id": post_obj_id, "author.user_id": login_user_id}
    )

    if not post:
        return create_exception_response(404, "Post not found or unauthorized")

    # Delete the post
    await posts_collection.delete_one({"_id": post_obj_id})

    # Map post types to user count fields
    POST_TYPE_COUNT_FIELD = {
        "story": "total_stories",
        "joke": "total_jokes",
        "poem": "total_poems",
        "quote": "total_quotes",
        "fact": "total_facts",
        "riddle": "total_riddles",
        "article": "total_articles",
    }

    post_type = post.get("type", "story")
    count_field = POST_TYPE_COUNT_FIELD.get(post_type)

    if count_field:
        # Decrement only if current count > 0
        await users_collection.update_one(
            {"user_id": saved_user["user_id"], count_field: {"$gt": 0}},
            {"$inc": {count_field: -1}},
        )

    points_cursor = points_collection.find(
        {"post_id": post_obj_id, "user_id": login_user_id}
    )
    total_points = 0
    async for point_record in points_cursor:
        total_points += point_record.get("points", 0)
    if total_points > 0:
        await users_collection.update_one(
            {"user_id": saved_user["user_id"]},
            {"$inc": {"total_points": -total_points}},
        )

    # Clean up related data
    delete_tasks = [
        posts_views_collection.delete_many({"post_id": post_obj_id}),
        posts_hearts_collection.delete_many({"post_id": post_obj_id}),
        posts_comments_collection.delete_many({"post_id": post_obj_id}),
        posts_bookmarks_collection.delete_many({"post_id": post_obj_id}),
        points_collection.delete_many({"post_id": post_obj_id}),
    ]
    await asyncio.gather(*delete_tasks)

    return create_success_response(200, "Post deleted successfully")


async def save_view_count_service(login_user_id: str, post_id: str):
    logger.info("content_service.save_view_count_service")

    # Verify user
    saved_user, error = await get_verified_user(login_user_id)
    if error:
        return error

    # Validate ObjectId
    try:
        post_oid = ObjectId(post_id)
    except Exception:
        return create_exception_response(400, "Invalid post_id")

    # Track whether user already viewed
    insert_result = await posts_views_collection.update_one(
        {"user_id": login_user_id, "post_id": post_oid},
        {"$setOnInsert": {"viewed_at": datetime.now(timezone.utc)}},
        upsert=True,
    )

    if insert_result.upserted_id:
        # First-time view → increment count
        result = await posts_collection.find_one_and_update(
            {"_id": post_oid},
            {"$inc": {"stats.views": 1}},  # removed $setOnInsert
            return_document=ReturnDocument.AFTER,
        )
    else:
        # Already viewed → fetch existing
        result = await posts_collection.find_one(
            {"_id": post_oid}, {"stats.views": 1}  # projection to optimize
        )

    if not result:
        return create_exception_response(404, NOT_FOUND.format(data="Post"))

    total_views = result.get("stats", {}).get("views", 0)
    return create_success_response(
        200,
        ACTION_SUCCESS.format(data="view count updated"),
        total=total_views,
    )


async def toggle_bookmark_service(login_user_id: str, post_id: str):
    try:
        saved_user, error = await get_verified_user(login_user_id)
        if error:
            return error

        try:
            post_oid = ObjectId(post_id)
        except Exception:
            return create_exception_response(400, "Invalid post_id")

        # Try to insert bookmark first
        insert_result = await posts_bookmarks_collection.update_one(
            {"user_id": login_user_id, "post_id": post_oid},
            {"$setOnInsert": {"bookmarked_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

        if insert_result.upserted_id:
            # Bookmark added
            result = await posts_collection.find_one_and_update(
                {"_id": post_oid},
                {"$inc": {"stats.bookmarks": 1}},
                return_document=ReturnDocument.AFTER,
            )
            # Increment user's total_bookmarks
            await users_collection.update_one(
                {"user_id": login_user_id},
                {"$inc": {"total_bookmarks": 1}}
            )
            action = "added"
        else:
            # Already exists, remove
            delete_result = await posts_bookmarks_collection.delete_one(
                {"user_id": login_user_id, "post_id": post_oid}
            )
            if delete_result.deleted_count:
                # Decrement safely using aggregation pipeline
                result = await posts_collection.find_one_and_update(
                    {"_id": post_oid},
                    [
                        {
                            "$set": {
                                "stats.bookmarks": {
                                    "$max": [{"$subtract": ["$stats.bookmarks", 1]}, 0]
                                }
                            }
                        }
                    ],
                    return_document=ReturnDocument.AFTER,
                )
                # Decrement user's total_bookmarks
                await users_collection.update_one(
                    {"user_id": login_user_id},
                    [
                        {
                            "$set": {
                                "total_bookmarks": {
                                    "$max": [{"$subtract": ["$total_bookmarks", 1]}, 0]
                                }
                            }
                        }
                    ]
                )
                action = "removed"
            else:
                # Something went wrong
                return create_exception_response(500, "Failed to toggle bookmark")

        total_bookmarks = result.get("stats", {}).get("bookmarks", 0)
        return create_success_response(
            200,
            ACTION_SUCCESS.format(data=f"Bookmark {action}"),
            total=total_bookmarks,
        )

    except Exception as e:
        logger.exception("Error in toggle_bookmark_service")
        return create_exception_response(500, f"An unexpected error occurred: {str(e)}")


async def toggle_heart_service(login_user_id: str, post_id: str):
    logger.info("content_service.toggle_heart_service")

    try:
        # Verify user
        saved_user, error = await get_verified_user(login_user_id)
        if error:
            return error

        # Validate ObjectId
        try:
            post_oid = ObjectId(post_id)
        except Exception:
            return create_exception_response(400, "Invalid post_id")

        # Try to add heart atomically
        insert_result = await posts_hearts_collection.update_one(
            {"user_id": login_user_id, "post_id": post_oid},
            {"$setOnInsert": {"hearted_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

        if insert_result.upserted_id:
            # Heart added
            result = await posts_collection.find_one_and_update(
                {"_id": post_oid},
                {"$inc": {"stats.hearts": 1}},
                return_document=ReturnDocument.AFTER,
            )
            # Reward points
            points = 5
            now = datetime.now(timezone.utc)
            await points_collection.insert_one(
                {
                    "user_id": login_user_id,
                    "post_id": post_oid,
                    "type": "earned",
                    "icon": "❤️",
                    "points": points,
                    "reason": "Hearted post",
                    "created_at": now,
                }
            )
            await users_collection.update_one(
                {"user_id": login_user_id},
                {"$inc": {"total_points": points}},
            )
            # Add notification
            post_owner_id = result.get("author", {}).get("user_id")
            if post_owner_id and post_owner_id != login_user_id:
                notification_data = {
                    "user_id": post_owner_id,
                    "actor_id": login_user_id,
                    "post_id": post_oid,
                    "type": "heart",
                    "message": f"{saved_user.get('name', 'Someone')} hearted your post",
                    "is_read": False,
                    "created_at": now,
                }
                await user_notifications_collection.insert_one(notification_data)
            action = "added"
        else:
            # Already exists, remove heart
            delete_result = await posts_hearts_collection.delete_one(
                {"user_id": login_user_id, "post_id": post_oid}
            )
            if delete_result.deleted_count:
                # Decrement safely using aggregation pipeline
                result = await posts_collection.find_one_and_update(
                    {"_id": post_oid},
                    [
                        {
                            "$set": {
                                "stats.hearts": {
                                    "$max": [{"$subtract": ["$stats.hearts", 1]}, 0]
                                }
                            }
                        }
                    ],
                    return_document=ReturnDocument.AFTER,
                )
                # Deduct points
                points = 5
                await points_collection.delete_one(
                    {
                        "user_id": login_user_id,
                        "post_id": post_oid,
                        "reason": "Hearted post",
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
                action = "removed"
            else:
                return create_exception_response(500, "Failed to toggle heart")

        if not result:
            logger.warning(f"Post not found: {post_id}")
            return create_exception_response(404, NOT_FOUND.format(data="Post"))

        total_hearts = result.get("stats", {}).get("hearts", 0)

        return create_success_response(
            200,
            ACTION_SUCCESS.format(data=f"Heart {action}"),
            total=total_hearts,
        )

    except Exception as e:
        logger.exception("Error in toggle_heart_service")
        return create_exception_response(500, f"An unexpected error occurred: {str(e)}")


async def fetch_heart_service(
    login_user_id: str, post_id: str, page: int = 1, limit: int = 10
):
    logger.info("content_service.fetch_heart_service")
    try:
        saved_user, error = await get_verified_user(login_user_id)
        if error:
            return error

        try:
            post_oid = ObjectId(post_id)
        except Exception:
            return create_exception_response(400, "Invalid post_id")

        # Check if post exists
        post = await posts_collection.find_one({"_id": post_oid})
        if not post:
            return create_exception_response(404, NOT_FOUND.format(data="Post"))

        # Count total hearts
        total_hearts = await posts_hearts_collection.count_documents(
            {"post_id": post_oid}
        )

        # Fetch hearts
        cursor = (
            posts_hearts_collection.find({"post_id": post_oid})
            .sort("hearted_at", -1)
            .skip((page - 1) * limit)
            .limit(limit)
        )

        raw_hearts = await cursor.to_list(length=limit)

        post_user_ids = [s["user_id"] for s in raw_hearts]

        # Batch fetch followers
        user_followings = {
            f["following_id"]: True
            for f in await users_connections_collection.find(
                {"follower_id": login_user_id, "following_id": {"$in": post_user_ids}}
            ).to_list(None)
        }

        # Batch fetch users
        users_cursor = users_collection.find({"user_id": {"$in": post_user_ids}})
        users_map = {u["user_id"]: u async for u in users_cursor}

        hearts = []
        for heart in raw_hearts:
            uid = heart["user_id"]
            hearted_user = users_map.get(uid, {})

            heart_item = {
                "heart_id": str(heart.get("_id")),
                "user_id": uid,
                "username": hearted_user.get("username", "unknown"),
                "name": hearted_user.get("name", "Unknown"),
                "user_avatar": hearted_user.get(
                    "avatar", "https://i.pravatar.cc/300?img=3"
                ),
                "is_following": user_followings.get(uid, False),
                "hearted_at_readable": convert_iso_date_to_humanize(
                    heart.get("hearted_at")
                ),
            }
            hearts.append(heart_item)

        return create_success_response(
            200,
            ACTION_SUCCESS.format(data="Hearts fetched successfully"),
            results=hearts,
            total=total_hearts,
            page=page,
            limit=limit,
        )
    except Exception as e:
        logger.exception("Error in fetch_heart_service")
        return create_exception_response(500, f"An unexpected error occurred: {str(e)}")

async def fetch_comments_service(
    login_user_id: str, post_id: str, page: int = 1, limit: int = 10
):
    logger.info("content_service.fetch_comments_service")
    try:
        saved_user, error = await get_verified_user(login_user_id)
        if error:
            return error
        # Validate pagination
        page = max(page, 1)
        limit = max(limit, 1)

        post_oid = ObjectId(post_id)

        # Check if post exists
        post = await posts_collection.find_one({"_id": post_oid})
        if not post:
            return create_exception_response(404, NOT_FOUND.format(data="Post"))

        # Count total comments
        total_comments = await posts_comments_collection.count_documents(
            {"post_id": post_oid}
        )

        # Fetch paginated comments
        cursor = (
            posts_comments_collection.find({"post_id": post_oid})
            .sort("created_at", -1)
            .skip((page - 1) * limit)
            .limit(limit)
        )

        raw_comments = await cursor.to_list(length=limit)
        comment_user_ids = [c["user_id"] for c in raw_comments]

        # Batch fetch users
        users_cursor = users_collection.find({"user_id": {"$in": comment_user_ids}})
        users_map = {u["user_id"]: u async for u in users_cursor}

        comments = []
        for comment in raw_comments:
            uid = comment["user_id"]
            comment_user = users_map.get(uid, {})

            comment_item = {
                "comment_id": str(comment.get("_id")),
                "user_id": uid,
                "comment_text": comment.get("comment_text"),
                "username": comment_user.get("username", "unknown"),
                "name": comment_user.get("name", "Unknown"),
                "user_avatar": comment_user.get(
                    "avatar", "https://i.pravatar.cc/300?img=3"
                ),
                "post_id": str(comment["post_id"]),
                "created_at_readable": convert_iso_date_to_humanize(
                    comment.get("created_at")
                ),
            }
            comments.append(comment_item)

        return create_success_response(
            200,
            FETCHED_SUCCESS.format(data="comments"),
            results=comments,
            total=total_comments,
            page=page,
            limit=limit,
        )

    except Exception as e:
        logger.exception("Error in fetch_comments_service")
        return create_exception_response(500, f"An unexpected error occurred: {str(e)}")


async def save_comment_service(login_user_id: str, post_id: str, comment_text: str):
    logger.info("content_service.save_comment_service")

    try:
        # Verify user
        saved_user, error = await get_verified_user(login_user_id)
        if error:
            return error

        post_oid = ObjectId(post_id)

        # Check if post exists
        post = await posts_collection.find_one({"_id": post_oid})
        if not post:
            return create_exception_response(404, NOT_FOUND.format(data="Post"))
        now = datetime.now(timezone.utc)
        # Insert comment
        comment_data = {
            "post_id": post_oid,
            "user_id": login_user_id,
            "comment_text": comment_text,
            "created_at": now,
        }
        result = await posts_comments_collection.insert_one(comment_data)

        # Attach generated _id
        comment_data["_id"] = result.inserted_id

        # Increment comments count in post (nested inside stats)
        result = await posts_collection.find_one_and_update(
            {"_id": post_oid},
            {"$inc": {"stats.comments": 1}},  # 👈 update nested field
            return_document=ReturnDocument.AFTER,
        )
        points = 10
        points_collection.insert_one(
            {
                "user_id": login_user_id,
                "post_id": post_oid,
                "source_id": comment_data["_id"],
                "type": "earned",
                "icon": "💬",
                "points": points,
                "reason": f"Posted comment",
                "created_at": now,
            }
        )
        await users_collection.update_one(
            {"user_id": login_user_id},
            {"$inc": {"total_points": points}},
        )
        # Add notification
        post_owner_id = post.get("author", {}).get("user_id")
        if post_owner_id and post_owner_id != login_user_id:
            notification_data = {
                "user_id": post_owner_id,
                "actor_id": login_user_id,
                "post_id": post_oid,
                "comment_id": comment_data["_id"],
                "type": "comment",
                "message": f"{saved_user.get('name', 'Someone')} commented on your post",
                "is_read": False,
                "created_at": now,
            }
            await user_notifications_collection.insert_one(notification_data)
        return create_success_response(
            200,
            ACTION_SUCCESS.format(data="Comment added"),
            total=result.get("stats", {}).get("comments", 0),  # 👈 nested access
            result={
                "comment_id": str(comment_data["_id"]),
                "user_id": comment_data["user_id"],
                "comment_text": comment_data["comment_text"],
                "created_at": comment_data["created_at"].isoformat(),
                "created_at_readable": convert_iso_date_to_humanize(
                    comment_data["created_at"]
                ),
            },
        )

    except Exception as e:
        logger.exception("Error in save_comment_service")
        return create_exception_response(500, f"An unexpected error occurred: {str(e)}")


async def delete_comment_service(login_user_id: str, comment_id: str):
    logger.info("social_service.delete_comment_service")

    try:
        # Verify user
        saved_user, error = await get_verified_user(login_user_id)
        if error:
            return error

        comment_oid = ObjectId(comment_id)

        # Fetch the comment to verify ownership and get post_id
        comment = await posts_comments_collection.find_one({"_id": comment_oid})
        if not comment:
            return create_exception_response(404, NOT_FOUND.format(data="Comment"))

        if comment["user_id"] != login_user_id:
            return create_exception_response(
                403, "You can only delete your own comment."
            )

        post_oid = comment["post_id"]

        # Delete the comment
        await posts_comments_collection.delete_one({"_id": comment_oid})

        # Decrement comments count in the post
        result = await posts_collection.find_one_and_update(
            {"_id": post_oid},
            [
                {
                    "$set": {
                        "stats.comments": {
                            "$max": [{"$subtract": ["$stats.comments", 1]}, 0]
                        }
                    }
                }
            ],
            return_document=ReturnDocument.AFTER,
        )

        # Deduct points from user
        points = 10
        await points_collection.delete_one(
            {
                "user_id": login_user_id,
                "post_id": post_oid,
                "source_id": comment_oid,
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

        return create_success_response(
            200,
            ACTION_SUCCESS.format(data="Comment deleted"),
            total=result.get("stats", {}).get("comments", 0),
        )

    except Exception as e:
        logger.exception("Error in delete_comment_service")
        return create_exception_response(500, f"An unexpected error occurred: {str(e)}")


async def fetch_user_notifications_service(
    login_user_id: str,
    page: int = 1,
    limit: int = 10,
):
    logger.info("content_service.fetch_user_notifications_service")
    try:
        saved_user, error = await get_verified_user(login_user_id)
        if error:
            return error

        page = max(page, 1)
        limit = max(limit, 1)

        query = {"user_id": login_user_id}
        total = await user_notifications_collection.count_documents(query)

        cursor = (
            user_notifications_collection.find(query)
            .sort("created_at", -1)
            .skip((page - 1) * limit)
            .limit(limit)
        )

        raw_notifications = await cursor.to_list(length=limit)

        actor_ids = list(set(doc.get("actor_id") for doc in raw_notifications if doc.get("actor_id")))
        post_ids = list(set(doc.get("post_id") for doc in raw_notifications if doc.get("post_id")))

        actors = {u["user_id"]: u async for u in users_collection.find({"user_id": {"$in": actor_ids}})}
        posts = {p["_id"]: p async for p in posts_collection.find({"_id": {"$in": post_ids}})}

        results = []
        for doc in raw_notifications:
            actor_id = doc.get("actor_id")
            actor = actors.get(actor_id)
            
            post_id = doc.get("post_id")
            post = posts.get(post_id)
            
            results.append({
                "id": str(doc["_id"]),
                "type": doc.get("type"),
                "message": doc.get("message"),
                "is_read": doc.get("is_read", False),
                "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
                "created_at_readable": convert_iso_date_to_humanize(doc.get("created_at")),
                "actor": {
                    "user_id": actor_id,
                    "name": actor.get("name") if actor else "Unknown",
                    "avatar": actor.get("avatar") if actor else "https://i.pravatar.cc/300?img=3",
                },
                "post": {
                    "id": str(post_id),
                    "title": post.get("title") if post else "",
                    "type": post.get("type") if post else "",
                }
            })

        return create_success_response(
            200,
            FETCHED_SUCCESS.format(data="notifications"),
            results=results,
            total=total,
            page=page,
            limit=limit,
        )
    except Exception as e:
        logger.exception("Error in fetch_user_notifications_service")
        return create_exception_response(500, f"An unexpected error occurred: {str(e)}")


async def mark_notification_as_read_service(login_user_id: str, notification_id: str):
    logger.info(f"content_service.mark_notification_as_read_service: {notification_id}")
    try:
        # Verify user
        saved_user, error = await get_verified_user(login_user_id)
        if error:
            return error

        try:
            notif_oid = ObjectId(notification_id)
        except Exception:
            return create_exception_response(400, "Invalid notification_id")

        result = await user_notifications_collection.update_one(
            {"_id": notif_oid, "user_id": login_user_id},
            {"$set": {"is_read": True}}
        )

        if result.matched_count == 0:
            return create_exception_response(404, "Notification not found or unauthorized")

        return create_success_response(200, ACTION_SUCCESS.format(data="Notification marked as read"))
    except Exception as e:
        logger.exception("Error in mark_notification_as_read_service")
        return create_exception_response(500, f"An unexpected error occurred: {str(e)}")
