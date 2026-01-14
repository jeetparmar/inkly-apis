import asyncio
import os
import sys
from datetime import datetime, timezone
from bson import ObjectId

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mocking dependencies that might fail imports
from unittest.mock import MagicMock
if "google.generativeai" not in sys.modules:
    sys.modules["google.generativeai"] = MagicMock()

from app.services.content_service import fetch_heart_service, fetch_comments_service, toggle_heart_service, save_comment_service
from app.config.database.mongo import users_collection, posts_collection, posts_hearts_collection, posts_comments_collection, points_collection

async def verify_optimized_services():
    print("🧪 Verifying optimized heart and comment services...")
    
    test_user_id = "verifier_user_123"
    target_user_id = "target_user_456"
    
    # 1. Setup - Users
    await users_collection.update_one(
        {"user_id": test_user_id},
        {"$set": {"username": "verifier", "name": "Verifier", "total_points": 0}},
        upsert=True
    )
    await users_collection.update_one(
        {"user_id": target_user_id},
        {"$set": {"username": "target", "name": "Target", "total_points": 0}},
        upsert=True
    )
    
    # 2. Setup - Post
    post_item = {
        "title": "Verification Post",
        "author": {"user_id": target_user_id},
        "stats": {"hearts": 0, "comments": 0}
    }
    insert_result = await posts_collection.insert_one(post_item)
    post_id = str(insert_result.inserted_id)
    
    try:
        # 3. Add heart and comment
        print("   - Adding heart and comment...")
        await toggle_heart_service(test_user_id, post_id)
        await save_comment_service(test_user_id, post_id, "Verified comment")
        
        # 4. Verify fetch_heart_service
        print("   - Testing fetch_heart_service...")
        heart_response = await fetch_heart_service(test_user_id, post_id)
        if heart_response.status == "SUCCESS":
            results = heart_response.results
            print(f"     ✅ Found {len(results)} hearts.")
            if len(results) > 0:
                h = results[0]
                print(f"     ✅ Heart user: {h.get('username')}, name: {h.get('name')}")
                if h.get('username') == "verifier":
                    print("     ✅ Correct user data returned.")
        else:
            print(f"     ❌ fetch_heart_service failed: {heart_response.message}")

        # 5. Verify fetch_comments_service
        print("   - Testing fetch_comments_service...")
        comment_response = await fetch_comments_service(test_user_id, post_id)
        if comment_response.status == "SUCCESS":
            results = comment_response.results
            print(f"     ✅ Found {len(results)} comments.")
            if len(results) > 0:
                c = results[0]
                print(f"     ✅ Comment user: {c.get('username')}, text: {c.get('comment_text')}")
                if c.get('username') == "verifier":
                    print("     ✅ Correct user data returned.")
        else:
            print(f"     ❌ fetch_comments_service failed: {comment_response.message}")

    finally:
        # 6. Cleanup
        print("   - Cleaning up...")
        await users_collection.delete_one({"user_id": test_user_id})
        await users_collection.delete_one({"user_id": target_user_id})
        await posts_collection.delete_one({"_id": ObjectId(post_id)})
        await posts_hearts_collection.delete_many({"post_id": ObjectId(post_id)})
        await posts_comments_collection.delete_many({"post_id": ObjectId(post_id)})
        await points_collection.delete_many({"user_id": test_user_id})
        print("   ✅ Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(verify_optimized_services())
