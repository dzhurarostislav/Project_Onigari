from ...config import DJINNI_CONFIG  # Поднимаемся на 2 уровня выше
from ..base import BaseScraper


class DjinniScraper(BaseScraper):
    def __init__(self):
        # Теперь мы просто берем готовый конфиг
        super().__init__(
            base_url="https://djinni.co",
            user_agent=DJINNI_CONFIG.user_agent,
            cookies_str=DJINNI_CONFIG.cookies,
        )

    async def fetch_vacancies(self, page: int = 1):
        if not self._session:
            raise RuntimeError("Ау-ау! Сначала используй 'async with'!")

        url = f"{self.base_url}/jobs/?page={page}"

        # Делаем запрос через нашу магическую сессию
        response = await self._session.get(url)

        if response.status_code == 200:
            return response.text
        else:
            print(f"Ошибка {response.status_code} на странице {page}")
            return None
