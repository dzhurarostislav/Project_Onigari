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

    async def fetch_vacancies(self, page: int = 1) -> str|None:
        """
        Fetch vacancies from djinni
        page: page for pagination
        return: raw html code from site
        """
        if not self._session:
            raise RuntimeError("first use 'async with'!")

        url = f"{self.base_url}/jobs/?page={page}"

        # Делаем запрос через нашу магическую сессию
        response = await self._session.get(url)

        if response.status_code == 200:
            return response.text
        else:
            print(f"Error {response.status_code} on page {page}")
            return None
