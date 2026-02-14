import logging
import os
from typing import Optional

from scrapers.base import BaseScraper
from scrapers.dou.parser import DouParser

logger = logging.getLogger(__name__)


class DouScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            base_url="https://jobs.dou.ua/vacancies/",
            user_agent=os.getenv(
                "DOU_USER_AGENT",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            ),
            cookies_str=os.getenv("DOU_COOKIES", ""),
        )
        self.parser = DouParser()

    def _get_csrf_token(self) -> str:
        """Extract CSRF token from current session cookies."""
        token = self._session.cookies.get("csrftoken")
        if not token:
            logger.error("❌ CSRF token not found in cookies!")
            raise ValueError("Missing CSRF token")
        return token

    async def _fetch_more_via_ajax(self, category: str, count: int, csrf_token: str) -> dict:
        """POST request to load more vacancies via AJAX."""
        url = f"{self.base_url}xhr-load/?category={category}"
        payload = {"csrfmiddlewaretoken": csrf_token, "count": count}

        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}?category={category}",
            "Origin": "https://jobs.dou.ua",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }

        try:
            logger.info(f"👹 Onigari sending AJAX request with count={count}...")
            res = await self._session.post(url, data=payload, headers=headers)

            if res.status_code == 403:
                logger.error("❌ 403 Forbidden: DOU rejected the request.")
                return {}

            return res.json() if res.status_code == 200 else {}
        except Exception as e:
            logger.error(f"Error during AJAX load: {e}")
            return {}

    async def fetch_vacancies(self, category: str = "Python", **kwargs):
        """Async generator for vacancy batches."""
        # Phase 1: Initial page
        main_url = f"{self.base_url}?category={category}"
        response = await self._session.get(main_url)

        if response.status_code == 200:
            first_batch = self.parser.parse_list(response.text)
            logger.info(f"✨ First page parsed: {len(first_batch)} vacancies")
            yield first_batch
        else:
            return

        # Phase 2: AJAX loop
        count = 20
        while True:
            try:
                await self._random_pause()

                # CSRF token can be refreshed
                current_token = self._get_csrf_token()

                data = await self._fetch_more_via_ajax(category, count, current_token)

                if not data or not data.get("html"):
                    logger.info("💨 Response is empty or no HTML.")
                    break

                new_batch = self.parser.parse_list(data.get("html", ""))
                if not new_batch:
                    break

                logger.info(f"✨ Yielding batch of {len(new_batch)} items (offset {count})")
                yield new_batch

                if data.get("last") is True:
                    logger.info("🏁 Server said: last=true.")
                    break

                # Server returns 'num' field indicating how many items were sent (usually 40).
                # Use it as offset step to avoid duplicates.
                step = data.get("num", 40)
                count += step

            except Exception as e:
                logger.warning(f"⚠️ AJAX cycle interrupted: {e}")
                break

    async def fetch_page_html(self, url: str) -> Optional[str]:
        """Generic HTML fetch method handling headers and cookies."""
        try:
            safe_url = str(url)
            logger.info(f"📡 Hunting for content at: {url}")
            response = await self._session.get(safe_url)

            if response.status_code == 200:
                return response.text

            logger.error(f"❌ Page fetch failed: {response.status_code} for {url}")
            return None
        except Exception as e:
            logger.error(f"❌ Network error during hunt: {e}")
            return None
