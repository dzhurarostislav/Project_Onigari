import abc
import asyncio
import logging
import random
from typing import Optional

from curl_cffi.requests import AsyncSession

# Настраиваем логи (потом вынесем в отдельный конфиг)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("OnigariScraper")


class BaseScraper(abc.ABC):
    """
    Абстрактный фундамент. Он не знает о Djinni или Dou,
    он знает только о логике сетевого взаимодействия.
    """

    def __init__(self, base_url: str, user_agent: str, cookies_str: str):
        self.base_url = base_url
        self.user_agent = user_agent
        self.raw_cookies = cookies_str
        self._session: Optional[AsyncSession] = None

    async def _random_pause(self, min_sec: int = 2, max_sec: int = 7):
        """Simulate human-like behavior with random delays."""
        pause = random.uniform(min_sec, max_sec)
        logger.info(f"Sleeping for {pause:.2f} seconds...")
        await asyncio.sleep(pause)

    def _get_cookie_dict(self) -> dict:
        """Превращает строку кук из браузера в словарь для сессии."""
        if not self.raw_cookies:
            return {}
        return {
            res.split("=", 1)[0]: res.split("=", 1)[1]
            for res in self.raw_cookies.split("; ")
            if "=" in res
        }

    async def __aenter__(self):
        """Открываем сессию при входе в блок async with"""
        logger.info(f"Initiating session for {self.base_url}...")
        self._session = AsyncSession(impersonate="chrome")
        self._session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            }
        )
        self._session.cookies.update(self._get_cookie_dict())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрываем сессию при выходе"""
        if self._session:
            await self._session.close()
            logger.info(f"Session for {self.base_url} closed.")
        if exc_type:
            logger.error(f"An error occurred: {exc_val}")

    @abc.abstractmethod
    async def fetch_vacancies(self, page: int):
        """Каждый скрапер должен реализовать свой метод получения данных."""
        pass
