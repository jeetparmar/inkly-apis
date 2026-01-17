import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger("uvicorn")

class NotificationManager:
    def __init__(self):
        # Dictionary mapping user_id to a list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected for user: {user_id}. Active connections: {len(self.active_connections[user_id])}")

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                logger.info(f"WebSocket disconnected for user: {user_id}")

    async def send_personal_notification(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            connections = self.active_connections[user_id]
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending WebSocket message to user {user_id}: {e}")
                    # Optionally handle disconnection here if needed

# Global instance of the manager
notification_manager = NotificationManager()
