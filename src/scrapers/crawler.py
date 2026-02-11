import asyncio  # Для пауз
import logging
import random

from database.models import VacancyStatus
from scrapers.schemas import VacancyBaseDTO

logger = logging.getLogger(__name__)


class DetailCrawler:
    def __init__(self, repo, scraper, parser) -> None:
        self.repo = repo
        self.scraper = scraper
        self.parser = parser

    async def crawl(self, limit: int = 10):
        logger.info(f"👹 Starting deep crawl for {limit} vacancies...")

        # 1. Получаем список из БД
        pending_vacancies = await self.repo.get_vacancies_by_status(VacancyStatus.NEW, limit)

        for vacancy in pending_vacancies:
            # Оборачиваем КАЖДУЮ итерацию, чтобы одна ошибка не убила всю охоту
            try:
                # 2. Мапим модель в DTO
                vacancy_dto = VacancyBaseDTO.model_validate(vacancy)

                # 3. Качаем HTML (обязательно await!)
                raw_html = await self.scraper.fetch_page_html(vacancy_dto.url)

                if not raw_html:
                    continue

                # 4. Вытаскиваем "мясо"
                vacancy_detail_dto = self.parser.parse_detail(raw_html, vacancy_dto)

                # 5. Сохраняем и меняем статус в базе
                await self.repo.update_vacancy_details(vacancy.id, vacancy_detail_dto)

                logger.info(f"✨ Processed: {vacancy_dto.title}")

                # 6. Даем системе выдохнуть (пауза 2-3 секунды)
                await asyncio.sleep(random.uniform(2, 5))

            except Exception as e:
                logger.error(f"❌ Failed to process vacancy {vacancy.id}: {e}")
                continue  # Идем к следующей вакансии
