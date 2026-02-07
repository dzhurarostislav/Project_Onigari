import asyncio
import logging
import sys

from sqlalchemy import text

from database.models import Base
from database.sessions import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_database():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("✅ PGVector extension is ready")

            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database tables created/verified")

            result = await conn.execute(text("SELECT version();"))
            version = result.scalar()
            logger.info(f"Connected to: {version}")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")


async def main():
    logger.info("Starting Onigari bot...")
    await setup_database()
    logger.info("Bot is running...")
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot is shutting down...")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        sys.exit(1)
