import asyncio
import logging
import os
import signal
import sys

# Hack to allow imports from src/
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from brain.vectorizer import VacancyVectorizer
from database.models import VacancyStatus
from database.service import VacancyRepository
from database.sessions import DATABASE_URL

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OnigariBrain")


async def main():
    # 1. LOCAL HOST OVERRIDE
    # If running on host but config points to 'db', change to localhost
    db_url = DATABASE_URL.replace("@db:5432", "@127.0.0.1:5432")

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(db_url, echo=False)
    local_async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Graceful shutdown flag
    stop_event = asyncio.Event()

    # Termination signals (Linux/macOS)
    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: stop_event.set())

    logger.info(f"🧠 Brain module starting. GPU available: {torch.cuda.is_available()}")

    # Load model into VRAM once
    vectorizer = VacancyVectorizer()

    logger.info("🚀 Main loop started. Press Ctrl+C to stop safely.")

    try:
        while not stop_event.is_set():
            try:
                async with local_async_session() as session:
                    repo = VacancyRepository(session)

                    # Process EXTRACTED vacancies -> VECTORIZED
                    vacancies = await repo.get_vacancies_by_status(VacancyStatus.EXTRACTED, limit=16)

                    if not vacancies:
                        logger.info("💤 No extracted vacancies found. Sleeping...")
                        # Wait 60s or until stop signal
                        try:
                            await asyncio.wait_for(stop_event.wait(), timeout=60)
                        except asyncio.TimeoutError:
                            pass
                        continue

                    logger.info(f"🧬 Vectorizing batch of {len(vacancies)}...")
                    vectors_data = await vectorizer.process_vacancies(vacancies)

                    # Commit results to DB
                    await repo.batch_update_vectors(vectors_data, new_status=VacancyStatus.VECTORIZED)

                    logger.info("✅ Batch finished.")

            except Exception as e:
                logger.error(f"Error in vectorizer loop: {e}")
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=10)
                except asyncio.TimeoutError:
                    pass
    except KeyboardInterrupt:
        logger.info("🛑 KeyboardInterrupt received.")
    finally:
        logger.info("🧹 Cleaning up resources...")
        stop_event.set()
        await engine.dispose()
        logger.info("👋 Gracefully shut down.")


if __name__ == "__main__":
    import torch  # Lazy import for heavy libraries

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # asyncio.run already raised the exception, suppress duplicate output
