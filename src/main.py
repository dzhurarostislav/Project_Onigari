import asyncio
import logging
import sys

from sqlalchemy import text

from database.models import Base
from database.service import VacancyRepository
from database.sessions import async_session, engine
from scrapers.crawler import DetailCrawler
from scrapers.dou.client import DouScraper
from scrapers.dou.parser import DouParser


# Centralized logging configuration
def setup_logging(level=logging.INFO):
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=level, format=log_format, handlers=[logging.StreamHandler(sys.stdout)])
    # Quiet mode for noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("curl_cffi").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


async def setup_database():
    """Initialize database: extensions and tables."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("✅ PGVector extension is ready")

            # NOTE: Alembic is preferred for production, but this is fine for initial setup
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database tables verified")
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        raise


async def run_scrapers():
    """Cycle for gathering data from external sources."""
    async with async_session() as session:
        repository = VacancyRepository(session)

        async with DouScraper() as scraper:
            logger.info("📡 Scanning DOU for new opportunities...")
            # TODO: Add category list from config
            async for batch in scraper.fetch_vacancies(category="Python"):
                if not batch:
                    continue

                added_count = await repository.batch_upsert(batch)
                if added_count > 0:
                    logger.info(f"👹 Trapped {added_count} new demons in the database.")


async def run_deep_extraction():
    """Phase 2: Deep extraction (Full Page Scan)"""
    async with async_session() as session:
        repository = VacancyRepository(session)
        async with DouScraper() as scraper:
            parser = DouParser()

            crawler = DetailCrawler(repository, scraper, parser)

            logger.info("🔪 Starting deep extraction of vacancy details...")
            await crawler.crawl(20)


async def main():
    setup_logging()
    logger.info("👹 Project Onigari (鬼狩り) is waking up...")

    await setup_database()

    while True:
        try:
            logger.info("🚀 Phase 1: Discovery started...")
            await run_scrapers()
            logger.info("🚀 Phase 2: Deep Extraction started...")
            await run_deep_extraction()
            logger.info("🏁 Full hunting cycle completed successfully.")
        except Exception as e:
            logger.error(f"⚠️ Scraper cycle failed: {e}", exc_info=True)

        logger.info("💤 Sleeping for 1 hour before next hunt...")
        await asyncio.sleep(60 * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Onigari is going to sleep (KeyboardInterrupt)")
    except Exception as e:
        logger.critical(f"💥 Fatal crash: {e}")
        sys.exit(1)
