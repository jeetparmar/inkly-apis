import logging

from app.queue.in_memory import get_otp_task, task_done
from app.utils.methods import send_otp_email

logger = logging.getLogger("uvicorn")


import asyncio
from functools import partial

async def otp_worker():
    loop = asyncio.get_running_loop()
    while True:
        task = await get_otp_task()
        try:
            await loop.run_in_executor(
                None, 
                partial(send_otp_email, task["config"], task["email"], task["otp"])
            )
            logger.info(f"📨 OTP sent to {task['email']}")
        except Exception as e:
            logger.error(f"❌ Failed to send OTP: {e}")
        finally:
            task_done()
