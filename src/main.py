import asyncio
import logging
import sys

from sqlalchemy import text

from database.models import Base
from database.service import VacancyRepository
from database.sessions import async_session, engine
from scrapers.dou.client import DouScraper
from scrapers.dou.schemas import VacancyDTO

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


async def run_scrapers() -> list[VacancyDTO]:
    """Fetching our DOU scraper hunt"""
    async with DouScraper() as scraper:
        logger.info("📡 Fetching vacancies from DOU...")
        vacancies = await scraper.fetch_vacancies(category="Python")

        if not vacancies:
            logger.warning("💨 No vacancies found. Check selectors or connection.")
            return []

        for v in vacancies[:5]:  # Выведем первые 5 для теста
            logger.info(f"✅ Found: {v.title} at {v.company_name} | {v.url}")

        logger.info(f"📊 Total fetched: {len(vacancies)}")
        return vacancies


async def save_to_onigari(vacancies: list[VacancyDTO]):
    """Только сохранение. Никакой сети."""
    if not vacancies:
        return

    logger.info(f"💾 Saving {len(vacancies)} units to database...")
    async with async_session() as session:
        repo = VacancyRepository(session)
        added_count = await repo.batch_upsert(vacancies)
        logger.info(f"👹 Onigari report: {added_count} new demons trapped.")


async def main():
    logger.info("Starting Onigari bot...")
    await setup_database()
    logger.info("Bot is running...")

    while True:
        try:
            # 1. Запускаем скраперы.
            raw_data = await run_scrapers()
            logger.info("Scrapers ran successfully")

            # 2. Очистка и сохранение (Чистая функция записи)
            if raw_data:
                await save_to_onigari(raw_data)
                logger.info("Cycle completed successfully")
            else:
                logger.info("Nothing to save this time")

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
