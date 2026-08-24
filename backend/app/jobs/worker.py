import asyncio
import logging
import signal
import sys

from app.jobs.queue import start_worker, stop_worker
from app.database.session import init_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


async def main():
    init_db()
    logger.info("Starting VexPanel worker...")
    
    await start_worker()
    
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        asyncio.create_task(shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass


async def shutdown():
    logger.info("Stopping worker...")
    await stop_worker()
    logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())