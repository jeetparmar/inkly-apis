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
from app.utils.constants import INTERESTS_DATA
from app.config.database.mongo import (
    create_device_id_index,
    create_post_bookmark_index,
    create_post_heart_index,
    create_post_view_index,
    create_user_id_index,
    interests_collection,
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
    count = await interests_collection.count_documents({})
    if count == 0:
        interests_docs = [
            {"title": interest.get("title"), "icon": interest.get("icon")}
            for interest in INTERESTS_DATA
        ]
        await interests_collection.insert_many(interests_docs)
        print("✅ Interests initialized")
    else:
        print("ℹ️ Interests already exist")

    asyncio.create_task(otp_worker())

    # Create DB indexes
    await create_device_id_index()
    await create_user_id_index()
    await create_post_view_index()
    await create_post_heart_index()
    await create_post_bookmark_index()


# ---------------- Static Files ---------------- #
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------- Routes ---------------- #
@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(os.path.join("static", "index.html"))


@app.get("/api/health", include_in_schema=False)
def check_health():
    return {"health": "ok", "message": "Server is up and running"}
