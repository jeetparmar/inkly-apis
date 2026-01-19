import asyncio
import os
import time
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.utils.settings import settings
from fastapi.middleware.cors import CORSMiddleware

from app.routes.user_routes import user_router
from app.routes.content_routes import content_router
from app.routes.social_routes import social_router

from app.workers.otp_worker import otp_worker
from app.utils.constants import INTERESTS_DATA, CONTENT_CONFIGS_DATA
from app.config.database.mongo import (
    create_device_id_index,
    create_post_bookmark_index,
    create_post_heart_index,
    create_post_view_index,
    create_user_id_index,
    interests_collection,
    content_configs_collection, 
)

# ---------------- FastAPI App ---------------- #
app = FastAPI(
    title=settings.app_name, version=settings.api_version, docs_url=settings.docs_url
)

# ---------------- Middleware ---------------- #
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Routers ---------------- #
app.include_router(content_router, prefix="/api/content", tags=["Content"])
app.include_router(social_router, prefix="/api/social", tags=["Social"])
app.include_router(user_router, prefix="/api/user", tags=["User"])


@app.middleware("http")
async def add_execution_time_header(request: Request, call_next):
    start_time = time.time()
    response: Response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time, 4))
    if process_time > 1.0:
        print(f"Slow request: {request.url} took {process_time:.2f}s")
    else:
        print(f"Response status: {response.status_code}")
    return response


@app.on_event("startup")
async def startup_event():
    # Sync interests from constants
    try:
        await interests_collection.delete_many({})
        await interests_collection.insert_many(INTERESTS_DATA)
        print("✅ Interests synchronized")

        await content_configs_collection.delete_many({})
        await content_configs_collection.insert_many(CONTENT_CONFIGS_DATA)
        print("✅ Content configs synchronized")    
    except Exception as e:
        print(f"❌ Failed to sync interests: {e}")

    asyncio.create_task(otp_worker())

    # Create DB indexes
    print("🏗️ Building database indexes...")
    index_tasks = [
        ("Device ID", create_device_id_index),
        ("User ID", create_user_id_index),
        ("Post View", create_post_view_index),
        ("Post Heart", create_post_heart_index),
        ("Post Bookmark", create_post_bookmark_index),
    ]

    for name, func in index_tasks:
        try:
            await func()
            print(f"   ✅ {name} index created/verified")
        except Exception as e:
            print(f"   ⚠️ Failed to create {name} index: {e}")
    
    print("🚀 Startup process complete")


# ---------------- Static Files ---------------- #
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------- Routes ---------------- #
@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(os.path.join("static", "index.html"))


@app.get("/api/health", include_in_schema=False)
def check_health():
    return {"health": "ok", "message": "Server is up and running"}
