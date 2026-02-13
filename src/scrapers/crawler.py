import asyncio  # For delays
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

        pending_vacancies = await self.repo.get_vacancies_by_status(VacancyStatus.NEW, limit)

        for vacancy in pending_vacancies:
            # Wrap each iteration to prevent one error from stopping the crawl
            try:
                vacancy_dto = VacancyBaseDTO.model_validate(vacancy)

                # Fetch HTML
                raw_html = await self.scraper.fetch_page_html(vacancy_dto.source_url)

                if not raw_html:
                    continue

                # Extract vacancy details
                vacancy_detail_dto = self.parser.parse_detail(raw_html, vacancy_dto)

                # Save details and update status
                await self.repo.update_vacancy_details(vacancy.id, vacancy_detail_dto)

                logger.info(f"✨ Processed: {vacancy_dto.title}")

                # Random delay
                await asyncio.sleep(random.uniform(2, 5))

            except Exception as e:
                continue
