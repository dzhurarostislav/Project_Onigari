import asyncio
import logging
import os
import signal
import sys

# Hacks for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from brain.analyzer import VacancyAnalyzer
from brain.manager import SmartChainProvider
from brain.providers import GeminiProvider, OpenAIProvider
from brain.schemas import VacancyContext
from config import Config
from database.models import Vacancy, VacancyStatus
from database.service import VacancyRepository
from database.sessions import DATABASE_URL
from services.notifications import TelegramService

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def register_signals(stop_event):
    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: stop_event.set())
    else:
        # For Windows simplified version
        logger.info("Windows detected: use Ctrl+Break for graceful stop if Ctrl+C fails.")


async def process_vacancy(v_id, analyzer, session_factory, semaphore, notifier):
    """Each vacancy works in its own isolated session."""
    async with semaphore:
        # Open YOUR OWN session for this task
        async with session_factory() as session:
            repo = VacancyRepository(session)
            try:
                # Get a fresh vacancy object inside this session
                # (SQLAlchemy objects are tied to the session in which they were created)
                v = await session.get(Vacancy, v_id, options=[selectinload(Vacancy.company)])

                s1_tokens = 0
                s2_tokens = 0

                # --- STAGE 1 ---
                if v.status == VacancyStatus.VECTORIZED:
                    logger.info(f"🔍 Stage 1: Extraction for {v.id}")
                    s1_data, s1_tokens = await analyzer.analyze_stage1(
                        {"id": v.id, "title": v.title, "company_name": v.company.name, "description": v.description}
                    )
                    await repo.save_stage1_result(v.id, s1_data)
                    logger.info(f"✅ Stage 1 finished. Vacancy {v.id} Tokens used: {s1_tokens}")
                else:
                    s1_data = v.to_structured_data()

                # --- STAGE 2 ---
                logger.info(f"👹 Stage 2: Judgment for {v.id}")
                context = VacancyContext.model_validate(v)

                # 2. 🕵️ DEBUG LOG: ЧТО ВИДИТ ОХОТНИК?
                logger.info(
                    f"""
                🔎 [CONTEXT CHECK for ID {v.id}]
                --------------------------------------------------
                💰 Salary (DB): {context.financial_summary}
                🔗 URL:         {context.url}
                🛠 Stack (S1):  {", ".join(s1_data.tech_stack) if s1_data.tech_stack else "Empty"}
                🚩 Flags (S1):  {s1_data.red_flag_keywords}
                --------------------------------------------------
                """
                )

                result, s2_tokens = await analyzer.analyze_stage2(context, s1_data)
                result.tokens_used = s1_tokens + s2_tokens
                await repo.save_stage2_result(v.id, result)
                await notifier.notify_analysis_complete(v, result)
                logger.info(f"✅ Stage 2 finished. Vacancy {v.id} Total tokens used: {s2_tokens}")

            except Exception as e:
                logger.error(f"❌ Crisis at vacancy {v_id}: {e}", exc_info=True)


async def main():
    db_url = DATABASE_URL.replace("@db:5432", "@127.0.0.1:5432")
    engine = create_async_engine(db_url, echo=False)
    local_async_session = async_sessionmaker(engine, expire_on_commit=False)

    Config.validate()
    gemini_provider = GeminiProvider(api_key=Config.GEMINI_API_KEY, model_name="gemini-2.5-flash")
    openai_provider = OpenAIProvider(api_key=Config.OPENAI_API_KEY, model_name="gpt-4o-mini")
    provider = SmartChainProvider([gemini_provider, openai_provider])
    analyzer = VacancyAnalyzer(provider)
    notifier = TelegramService(token=Config.TELEGRAM_BOT_TOKEN, chat_id=Config.TELEGRAM_CHAT_ID)
    semaphore = asyncio.Semaphore(2)
    stop_event = asyncio.Event()

    # NEED TO REGISTER SIGNALS
    register_signals(stop_event)

    logger.info("🎭 The stage is set. The tragedy of vacancies begins.")

    try:
        while not stop_event.is_set():
            async with local_async_session() as session:
                repo = VacancyRepository(session)
                # Get list of vacancies ready for LLM processing
                vacancies = await repo.get_vacancies_for_llm_processing(limit=10)

                vacancy_ids = [v.id for v in vacancies]

            if not vacancy_ids:
                logger.info("💤 No fragments to judge. Waiting 30s...")
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=30)
                except asyncio.TimeoutError:
                    pass
                continue

            # Pass ID and session factory to workers
            for v_id in vacancy_ids:
                if stop_event.is_set():
                    break

                await process_vacancy(v_id, analyzer, local_async_session, semaphore, notifier)

                logger.info("⏳ Waiting for Free Tier limits (30s)...")
                await asyncio.sleep(30)

    finally:
        await engine.dispose()
        logger.info("👋 Judge is going back to the shrine.")


if __name__ == "__main__":
    asyncio.run(main())
