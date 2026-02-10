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
    Absctact class contain main logic of for any parser
    abcstractmethod -> fetch_vacancies.
    """

    def __init__(self, base_url: str, user_agent: str, cookies_str: str):
        self.base_url = base_url
        self.user_agent = user_agent
        self.raw_cookies = cookies_str
        self._session: Optional[AsyncSession] = None

    async def _random_pause(self, min_sec: int = 2, max_sec: int = 7):
        """
        simulate human-like behavior with random delays.
        """
        pause = random.uniform(min_sec, max_sec)
        logger.info(f"Sleeping for {pause:.2f} seconds...")
        await asyncio.sleep(pause)

    def _get_cookie_dict(self) -> dict:
        """
        transform cookie string from browser into dict
        """
        if not self.raw_cookies:
            return {}
        return {
            res.split("=", 1)[0]: res.split("=", 1)[1]
            for res in self.raw_cookies.split("; ")
            if "=" in res
        }

    async def __aenter__(self):
        """
        magic method, create async session when entering async with
        """
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
        """
        close session after program left async with
        """
        if self._session:
            await self._session.close()
            logger.info(f"Session for {self.base_url} closed.")
        if exc_type:
            logger.error(f"An error occurred: {exc_val}")

    @abc.abstractmethod
    async def fetch_vacancies(self, category: str, **kwargs):
        """
        Every scraper must create his own method of fetching data
        """
        pass
