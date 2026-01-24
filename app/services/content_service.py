import asyncio
from datetime import datetime, timezone, timedelta
import logging
import re
import json
from bson import ObjectId
from bson import errors as bson_errors
import httpx
from pymongo import ReturnDocument
from app.models.schema import PostRequest, PostFilterParams
from app.utils.enums.PostType import PostType
from app.utils.enums.PostFilters import PostDuration, PostSortBy, PostFilter
from app.utils.gemini import ask_from_gemini
from app.utils.openai import ask_from_openai
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
from app.utils.constants import CONTENT_CONFIGS_DATA
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
    user_notifications_collection,
    content_configs_collection,
)
from app.utils.settings import settings
from app.utils.notification_manager import notification_manager
# Removal of CONTENT_CONFIG import

logger = logging.getLogger("uvicorn")


async def get_content_config(post_type: PostType):
    """Utility to fetch config for a specific post type"""
    config = await content_configs_collection.find_one({"type": post_type.value})
    if not config:
        # Fallback to some defaults if not found, though seeding should prevent this
        return {"points": 40, "icon": "", "stats_field": ""}
    return config


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
    model: str = "gemini",
):
    logger.info("content_service.generate_content_from_llm_service")

    # Verify user
    saved_user, error = await get_verified_user(login_user_id)
    if error:
        return error
    
    try:
        # Route to appropriate AI model
        if model.lower() == "openai":
            output = ask_from_openai(ai_key, type, prompt, size, language, theme)
        else:  # Default to Gemini
            output = ask_from_gemini(ai_key, type, prompt, size, language, theme)
        
        if not output:
            return create_exception_response(500, "LLM returned empty output")

        title = output.get("title", "")
        content = output.get("content", "")

    except ValueError as e:
        # Handle errors from AI utilities (rate limits, auth errors, etc.)
        logger.error(f"AI model error: {e}")
        return create_exception_response(400, str(e))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return create_exception_response(500, "Invalid JSON returned from LLM")
    except Exception as e:
        logger.error(f"Unexpected error in content generation: {e}")
        return create_exception_response(500, f"Failed to generate content: {str(e)}")

    return create_success_response(
        200,
        FETCHED_SUCCESS.format(data="generated content"),
        query={"type": type, "prompt": prompt, "theme": theme, "size": size, "model": model},
        result={"title": title, "content": content},
    )

async def fetch_post_service(login_user_id: str, post_id: str):
    logger.info("content_service.fetch_post_service")

    # Verify user
    saved_user, error = await get_verified_user(login_user_id)
    if error:
        return error

    try:
        post_oid = ObjectId(post_id)
    except Exception:
        return create_exception_response(400, "Invalid post_id")
    # Fetch post
    post = await posts_collection.find_one({"_id": post_oid})
    if not post:
        return create_exception_response(404, NOT_FOUND.format(data="post"))

    return create_success_response(
        200,
        FETCHED_SUCCESS.format(data="post"),
        result=await _format_post_data(post, saved_user),
    )

async def _format_post_data(post: dict, user: dict):
    is_following = await users_connections_collection.find_one({"following_id": user.get("user_id"), 
        "follower_id": post.get("author").get("user_id")})
    is_following = True if is_following else False

    query = {"user_id": user.get("user_id"), "post_id": post.get("_id")}

    is_hearted = await posts_hearts_collection.find_one(query)
    is_hearted = True if is_hearted else False

    is_commented = await posts_comments_collection.find_one(query) 
    is_commented = True if is_commented else False

    is_bookmarked = await posts_bookmarks_collection.find_one(query)
    is_bookmarked = True if is_bookmarked else False
    
    return {
        "id": str(post.get("_id")),
        "type": post.get("type", ""),
        "title": post.get("title", ""),
        "image": post.get("image", ""),
        "content": post.get("content", ""),
        "theme": post.get("theme", ""),
        "author": {
            "user_id": user.get("user_id", ""),
            "name": user.get("name", ""),
            "username": user.get("username", ""),
            "avatar": user.get("avatar", ""),
            "is_following": is_following,
            "is_verified": False,
        },
        "is_hearted": is_hearted,
        "is_commented": is_commented,
        "is_bookmarked": is_bookmarked,
        "is_18_plus": post.get("is_18_plus", False),
        "is_anonymous": post.get("is_anonymous", False),
        "is_for_kids": post.get("is_for_kids", False),
        "stats": post.get("stats", {}),
        "created_at_readable": convert_iso_date_to_humanize(
            post.get("created_at")
        ),
    }

# ---------------- Posts Service ----------------
async def fetch_posts_service(
    login_user_id: str,
    params: PostFilterParams,
):
    logger.info("content_service.fetch_posts_service")

    # ---------------- Verify User ----------------
    saved_user, error = await get_verified_user(login_user_id)
    if error:
        return error

    # ---------------- Validation ----------------
    if params.theme:
        # If types are provided, only check themes for those types
        applicable_configs = [
            conf for conf in CONTENT_CONFIGS_DATA 
            if not params.types or conf["type"] in [t.value for t in params.types]
        ]
        
        valid_themes = set()
        for conf in applicable_configs:
            for t in conf.get("themes", []):
                valid_themes.add(t["id"])
        
        if params.theme in valid_themes:
            pass # Valid
        else:
            # Check if it exists in ANY config to give better error message
            all_themes = {t["id"] for conf in CONTENT_CONFIGS_DATA for t in conf.get("themes", [])}
            if params.theme in all_themes:
                return create_exception_response(400, f"Theme '{params.theme}' is not applicable for the selected post types.")
            return create_exception_response(400, f"Invalid theme: '{params.theme}'.")

    page = max(params.page, 1)
    limit = max(params.limit, 1)
    # ---------------- Query Stories ----------------
    query = {"is_draft": False, "is_18_plus": params.is_18_plus}
    
    if params.is_anonymous is not None:
        query["is_anonymous"] = params.is_anonymous
        
    if params.is_for_kids is not None:
        query["is_for_kids"] = params.is_for_kids
    if params.types:
        query["type"] = {"$in": params.types}
    
    if params.theme:
        query["theme"] = params.theme
        
    if params.tags:
        query["tags"] = {"$all": params.tags}
    
    if params.search:
        query["$or"] = [
            {"title": {"$regex": params.search, "$options": "i"}},
            {"content": {"$regex": params.search, "$options": "i"}},
        ]

    # ---------------- Filter by Duration ----------------
    if params.duration and params.duration != PostDuration.ALL_TIME:
        now = datetime.now(timezone.utc)
        if params.duration == PostDuration.LAST_24H:
            query["created_at"] = {"$gte": now - timedelta(days=1)}
        elif params.duration == PostDuration.LAST_7D:
            query["created_at"] = {"$gte": now - timedelta(days=7)}
        elif params.duration == PostDuration.LAST_30D:
            query["created_at"] = {"$gte": now - timedelta(days=30)}

    # ---------------- Filter by Source ----------------
    if params.filter == PostFilter.FOLLOWING:
        followings = await users_connections_collection.find(
            {"follower_id": login_user_id}
        ).to_list(None)
        following_ids = [f["following_id"] for f in followings]
        query["author.user_id"] = {"$in": following_ids}
    elif params.filter == PostFilter.FOLLOWERS:
        followers = await users_connections_collection.find(
            {"following_id": login_user_id}
        ).to_list(None)
        follower_ids = [f["follower_id"] for f in followers]
        query["author.user_id"] = {"$in": follower_ids}
    elif params.user_id:
        query["author.user_id"] = params.user_id

    # ---------------- Sorting ----------------
    sort_field = "created_at"
    if params.sort_by == PostSortBy.MOST_VIEWED:
        sort_field = "stats.views"
    elif params.sort_by == PostSortBy.MOST_HEARTED:
        sort_field = "stats.hearts"
    elif params.sort_by == PostSortBy.MOST_COMMENTED:
        sort_field = "stats.comments"

    # ---------------- Aggregation Pipeline ----------------
    # 1. Match filters
    # 2. Sort by created_at DESC (to get latest for each user)
    # 3. Group by author.user_id, taking the $first (latest)
    # 4. Replace root to the latest post
    # 5. Sort by requested sort_field
    # 6. Pagination (skip/limit)

    pipeline = [
        {"$match": query},
        {"$sort": {"created_at": -1}},
        {"$group": {"_id": "$author.user_id", "latest_post": {"$first": "$$ROOT"}}},
        {"$replaceRoot": {"newRoot": "$latest_post"}},
        {"$sort": {sort_field: -1}},
        {"$skip": (page - 1) * limit},
        {"$limit": limit}
    ]

    # Calculate total unique authors matching query
    total_pipeline = [
        {"$match": query},
        {"$group": {"_id": "$author.user_id"}},
        {"$count": "total"}
    ]
    
    total_result = await posts_collection.aggregate(total_pipeline).to_list(None)
    total = total_result[0]["total"] if total_result else 0

    cursor = posts_collection.aggregate(pipeline)
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
        if post.get("is_anonymous"):
            user_id = ""
            name = "Anonymous"
            username = "anonymous"
            avatar = "https://cdn-icons-png.flaticon.com/512/149/149071.png"
            is_following = False
        else:
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
            is_following = user_followings.get(post_user_id, False)

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
                    "is_following": is_following,
                    "is_verified": False,
                },
                "is_hearted": user_hearts.get(post_id, False),
                "is_commented": user_comments.get(post_id, False),
                "is_bookmarked": user_bookmarks.get(post_id, False),
                "is_18_plus": post.get("is_18_plus", False),
                "is_anonymous": post.get("is_anonymous", False),
                "is_for_kids": post.get("is_for_kids", False),
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
    if types and is_draft == False:
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

        if post.get("is_anonymous"):
            post["author"].update(
                {
                    "user_id": "",
                    "name": "Anonymous",
                    "username": "anonymous",
                    "avatar": "https://cdn-icons-png.flaticon.com/512/149/149071.png",
                    "is_verified": False,
                    "is_following": False,
                }
            )
        else:
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

    async def handle_publish_stats(p_id, p_type, is_transition=False):
        config = await get_content_config(p_type)
        points = config.get("points", 40)
        icon = config.get("icon", "")
        field = config.get("stats_field", "")

        inc_data = {"total_points": points}
        if field:
            inc_data[field] = 1
        if is_transition:
            inc_data["total_drafts"] = -1

        await users_collection.update_one(
            {"user_id": login_user_id},
            {"$inc": inc_data},
        )
        await points_collection.insert_one(
            {
                "user_id": login_user_id,
                "post_id": p_id,
                "type": "earned",
                "icon": icon,
                "points": points,
                "reason": f"Published {p_type.value} from draft"
                if is_transition
                else f"Posted {p_type.value}",
                "created_at": now,
            }
        )
        return points

    try:
        if post_id:
            # Validate ObjectId
            try:
                obj_id = ObjectId(post_id)
            except Exception:
                return create_exception_response(400, "Invalid post_id")

            # Fetch existing post to check current state
            existing_post = await posts_collection.find_one(
                {"_id": obj_id, "author.user_id": login_user_id}
            )

            if not existing_post:
                return create_exception_response(
                    404, "post id not found or unauthorized"
                )

            # Check if transitioning from draft to published
            is_transitioning_to_publish = (
                existing_post.get("is_draft") and not request.is_draft
            )

            # Only update non-stat fields
            update_fields = {
                "title": request.title,
                "image": request.image,
                "content": request.content,
                "theme": request.theme,
                "tags": request.tags,
                "is_anonymous": request.is_anonymous,
                "is_18_plus": request.is_18_plus,
                "is_for_kids": request.is_for_kids,
                "is_draft": request.is_draft,
                "updated_at": now,
            }

            await posts_collection.update_one(
                {"_id": obj_id, "author.user_id": login_user_id},
                {"$set": update_fields},
                upsert=False,
            )

            if is_transitioning_to_publish:
                points = await handle_publish_stats(obj_id, type, is_transition=True)
                message = f"{type.value} published from draft successfully and earned {points} points"
            else:
                message = f"{type.value.capitalize()} updated successfully"

            status = 200
        else:
            # New post creation
            content_data = {
                "type": type,
                "author": {"user_id": login_user_id},
                "title": request.title,
                "image": request.image,
                "content": request.content,
                "theme": request.theme,
                "tags": request.tags,
                "is_anonymous": request.is_anonymous,
                "is_18_plus": request.is_18_plus,
                "is_for_kids": request.is_for_kids,
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

            if request.is_draft:
                message = f"{type.value.capitalize()} saved as draft"
                status = 200
                # Increment user draft count
                await users_collection.update_one(
                    {"user_id": login_user_id},
                    {"$inc": {"total_drafts": 1}},
                )
            else:
                points = await handle_publish_stats(result.inserted_id, type)
                message = (
                    f"{type.value.capitalize()} created successfully and earned {points} points"
                )
                status = 201
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

    if post.get("is_draft"):
        await users_collection.update_one(
            {"user_id": login_user_id},
            {"$inc": {"total_drafts": -1}},
        )
    else:
        post_type_val = post.get("type")
        # Find PostType enum member from value
        post_type = None
        for pt in PostType:
            if pt.value == post_type_val:
                post_type = pt
                break
        
        if not post_type:
            post_type = PostType.story # Default

        config = await get_content_config(post_type)
        count_field = config.get("stats_field")

        if count_field:
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
                # Push notification via WebSocket
                await notification_manager.send_personal_notification(
                    post_owner_id, 
                    {
                        "type": "heart",
                        "message": notification_data["message"],
                        "actor": {
                            "user_id": login_user_id,
                            "name": saved_user.get('name', 'Someone'),
                            "avatar": saved_user.get('avatar', 'https://i.pravatar.cc/300?img=3'),
                        },
                        "post_id": str(post_oid),
                        "created_at": now.isoformat()
                    }
                )
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
            # Push notification via WebSocket
            await notification_manager.send_personal_notification(
                post_owner_id,
                {
                    "type": "comment",
                    "message": notification_data["message"],
                    "actor": {
                        "user_id": login_user_id,
                        "name": saved_user.get('name', 'Someone'),
                        "avatar": saved_user.get('avatar', 'https://i.pravatar.cc/300?img=3'),
                    },
                    "post_id": str(post_oid),
                    "comment_id": str(comment_data["_id"]),
                    "created_at": now.isoformat()
                }
            )

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


async def fetch_content_config_service(login_user_id: str):
    logger.info("content_service.fetch_content_config_service")

    # Verify user
    saved_user, error = await get_verified_user(login_user_id)
    if error:
        return error

    # Fetch all configs from DB
    configs_cursor = content_configs_collection.find({})
    configs = await configs_cursor.to_list(length=None)

    # Reconstruct the expected response format
    # {
    #     "post_types": { type: {emoji, label} },
    #     "size_config": { type: [sizes] },
    #     "themes": { type: [themes] },
    #     "placeholders": { type: string },
    #     ...
    # }
    
    post_types = {}
    size_config = {}
    themes = {}
    placeholders = {}
    prompt_placeholders = {}
    labels = {}
    buttons = {}

    for cfg in configs:
        ctype = cfg["type"]
        post_types[ctype] = {"emoji": cfg["emoji"], "label": cfg["label"]}
        size_config[ctype] = cfg["sizes"]
        themes[ctype] = cfg["themes"]
        placeholders[ctype] = cfg["placeholder"]
        prompt_placeholders[ctype] = cfg["prompt_placeholder"]
        labels[ctype] = cfg["field_label"]
        buttons[ctype] = cfg["button_text"]

    content_config = {
        "post_types": post_types,
        "size_config": size_config,
        "themes": themes,
        "placeholders": placeholders,
        "prompt_placeholders": prompt_placeholders,
        "labels": labels,
        "buttons": buttons,
    }

    return create_success_response(
        200,
        FETCHED_SUCCESS.format(data="content configuration"),
        result=content_config,
    )
