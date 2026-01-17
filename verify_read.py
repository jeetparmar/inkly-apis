import asyncio
import os
import sys
from bson import ObjectId

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.config.database.mongo import user_notifications_collection
from app.services.content_service import mark_notification_as_read_service

async def verify():
    print("--- Mark as Read Verification ---")
    
    # 1. Get a notification
    notif = await user_notifications_collection.find_one({"is_read": False})
    if not notif:
        print("No unread notifications found to test.")
        return
    
    notif_id = str(notif["_id"])
    user_id = notif["user_id"]
    print(f"Testing Notification ID: {notif_id} for User: {user_id}")
    
    # 2. Mark as read
    response = await mark_notification_as_read_service(user_id, notif_id)
    print(f"Service Response: {response.status} - {response.message}")
    
    # 3. Verify in DB
    updated_notif = await user_notifications_collection.find_one({"_id": ObjectId(notif_id)})
    if updated_notif and updated_notif.get("is_read") == True:
        print("Verification Successful: Notification is marked as read in database.")
    else:
        print("Verification Failed: Notification is still unread or not found.")

if __name__ == "__main__":
    asyncio.run(verify())
