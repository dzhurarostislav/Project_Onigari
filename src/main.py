import asyncio
import logging
import sys

from sqlalchemy import text

from database.models import Base
from database.service import VacancyRepository
from database.sessions import async_session, engine
from scrapers.dou.client import DouScraper
from scrapers.schemas import VacancyDTO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_database():
    """
    create/confirm db tables, also create pgvector extension
    """
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


async def run_scrapers():
    """Оркестратор: получает пачки и сразу отправляет их в ловушку."""
    # 1. Открываем сессию, чтобы создать репозиторий
    async with async_session() as session:
        repository = VacancyRepository(session)
        
        async with DouScraper() as scraper:
            logger.info("📡 Onigari is hunting on DOU...")
            
            # 2. Итерируемся по генератору
            async for batch in scraper.fetch_vacancies(category="Python"):
                if not batch:
                    continue
                
                # 3. Сохраняем сразу же!
                added_count = await repository.batch_upsert(batch)
                logger.info(f"👹 Trapped {added_count} new demons.")


async def main():
    logger.info("Starting Onigari bot...")
    await setup_database()
    logger.info("Bot is running...")

    while True:
        try:
            # Просто вызываем. Вся логика сохранения теперь внутри run_scrapers
            await run_scrapers()
            logger.info("Cycle completed successfully")

        except Exception as e:
            logger.error(f"❌ Scrapers crashed: {e}", exc_info=True)
            
        logger.info("Sleeping for 1 hour...")
        await asyncio.sleep(60 * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot is shutting down...")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        sys.exit(1)
