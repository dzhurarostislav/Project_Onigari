import asyncio
import logging
import sys

from sqlalchemy import text

from database.models import Base
from database.service import VacancyRepository
from database.sessions import async_session, engine
from scrapers.dou.client import DouScraper


# 1. Централизованная настройка логов
def setup_logging(level=logging.INFO):
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=level, format=log_format, handlers=[logging.StreamHandler(sys.stdout)])
    # Тихий режим для шумных библиотек
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("curl_cffi").setLevel(logging.WARNING)


logger = logging.getLogger("onigari.main")


async def setup_database():
    """Инициализация базы: расширения и таблицы"""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("✅ PGVector extension is ready")

            # ВНИМАНИЕ: в продакшене лучше использовать Alembic, но для старта — ок
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database tables verified")
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        raise


async def run_scrapers():
    """Цикл сбора данных из внешних источников"""
    async with async_session() as session:
        repository = VacancyRepository(session)

        async with DouScraper() as scraper:
            logger.info("📡 Scanning DOU for new opportunities...")
            # Можно будет добавить список категорий из конфига
            async for batch in scraper.fetch_vacancies(category="Python"):
                if not batch:
                    continue

                added_count = await repository.batch_upsert(batch)
                if added_count > 0:
                    logger.info(f"👹 Trapped {added_count} new demons in the database.")


async def main():
    setup_logging()  # Вызываем настройку логов первым делом
    logger.info("👹 Project Onigari (鬼狩り) is waking up...")

    await setup_database()

    while True:
        try:
            logger.info("🚀 Starting new scraping cycle...")
            await run_scrapers()
            logger.info("🏁 Cycle completed successfully.")
        except Exception as e:
            # exc_info=True выведет весь traceback ошибки
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
