import os

from ..base import BaseScraper
from .parser import DouParser


class DouScraper(BaseScraper):
    def __init__(self):
        # Наследуем сетевую логику (сессии, куки, прокси)
        super().__init__(
            base_url="https://jobs.dou.ua/vacancies/",
            user_agent=os.getenv(
                "DOU_USER_AGENT",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ),
            cookies_str=os.getenv("DOU_COOKIES", ""),
        )
        self.parser = DouParser()

    async def fetch_vacancies(self, category: str = "Python"):
        # Используем self._session, который создается в BaseScraper.__aenter__
        url = f"{self.base_url}?category={category}"
        response = await self._session.get(url)

        if response.status_code == 200:
            return self.parser.parse_list(response.text)
        return []
