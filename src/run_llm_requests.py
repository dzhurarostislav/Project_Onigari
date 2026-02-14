import asyncio
import logging
import os
import sys
import signal
from datetime import datetime

# Хаки для импортов
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import Config
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from brain.providers import GeminiProvider
from brain.analyzer import VacancyAnalyzer
from brain.context import tokens_counter
from database.models import Vacancy
from database.service import VacancyRepository
from database.models import VacancyStatus
from database.sessions import DATABASE_URL

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def register_signals(stop_event):
    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: stop_event.set())
    else:
        # Для Windows упрощенный вариант
        logger.info("Windows detected: use Ctrl+Break for graceful stop if Ctrl+C fails.")


async def process_vacancy(v_id, analyzer, session_factory, semaphore):
    """Каждая вакансия работает в своей изолированной сессии."""
    async with semaphore:
        # Открываем СВОЮ сессию для этого таска
        async with session_factory() as session:
            repo = VacancyRepository(session)
            try:
                tokens_counter.set(0)
                
                # Получаем свежий объект вакансии внутри этой сессии
                # (SQLAlchemy объекты привязаны к сессии, в которой созданы)
                v = await session.get(Vacancy, v_id, options=[selectinload(Vacancy.company)]) 
                
                # --- STAGE 1 ---
                if v.status == VacancyStatus.VECTORIZED:
                    logger.info(f"🔍 Stage 1: Extraction for {v.id}")
                    s1_data = await analyzer.analyze_stage1({
                        "id": v.id, "title": v.title, 
                        "company_name": v.company.name, "description": v.description
                    })
                    await repo.save_stage1_result(v.id, s1_data)
                else:
                    s1_data = v.to_structured_data() 

                # --- STAGE 2 ---
                logger.info(f"👹 Stage 2: Judgment for {v.id}")
                result = await analyzer.analyze_stage2(
                    {"id": v.id, "title": v.title, "description": v.description},
                    s1_data
                )
                
                await repo.save_stage2_result(v.id, result)
                logger.info(f"✅ Vacancy {v.id} finished. Tokens: {result.tokens_used}")

            except Exception as e:
                logger.error(f"❌ Crisis at vacancy {v_id}: {e}", exc_info=True)

async def main():
    db_url = DATABASE_URL.replace("@db:5432", "@127.0.0.1:5432")
    engine = create_async_engine(db_url, echo=False)
    local_async_session = async_sessionmaker(engine, expire_on_commit=False)

    Config.validate()
    provider = GeminiProvider(api_key=Config.GEMINI_API_KEY, model_name="gemini-2.5-flash")
    analyzer = VacancyAnalyzer(provider)
    semaphore = asyncio.Semaphore(2)
    stop_event = asyncio.Event()

    # ОБЯЗАТЕЛЬНО: Регистрируем сигналы
    register_signals(stop_event)
    
    logger.info("🎭 The stage is set. The tragedy of vacancies begins.")

    try:
        while not stop_event.is_set():
            async with local_async_session() as session:
                repo = VacancyRepository(session)
                # Получаем список готовых вакансий
                vacancies = await repo.get_vacancies_for_llm_processing(limit=10)
                
                if not vacancies:
                    logger.info("💤 No fragments to judge. Waiting 30s...")
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=30)
                    except asyncio.TimeoutError:
                        pass
                    continue

                # Передаем ID и ФАБРИКУ сессий в воркеры
                for v in vacancies:
                    if stop_event.is_set():
                        break
                        
                    await process_vacancy(v.id, analyzer, local_async_session, semaphore)
                    
                    # 5 запросов в минуту = 1 запрос в 12 секунд. 
                    # У нас 2 запроса на вакансию, значит ждем ~25 секунд.
                    logger.info("⏳ Ожидание лимитов Free Tier (25s)...")
                    await asyncio.sleep(25)
                
    finally:
        await engine.dispose()
        logger.info("👋 Judge is going back to the shrine.")

if __name__ == "__main__":
    asyncio.run(main())
