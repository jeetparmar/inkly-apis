from asyncio import Queue

otp_queue = Queue()


async def enqueue_otp_task(task: dict):
    await otp_queue.put(task)


async def get_otp_task():
    return await otp_queue.get()


def task_done():
    otp_queue.task_done()
