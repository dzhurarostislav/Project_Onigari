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
        """Извлекает CSRF-токен из куков текущей сессии."""
        token = self._session.cookies.get("csrftoken")
        if not token:
            logger.error("❌ CSRF token not found in cookies!")
            raise ValueError("Missing CSRF token")
        return token

    async def _fetch_more_via_ajax(self, category: str, count: int, csrf_token: str) -> dict:
        """Выполняет POST-запрос для подгрузки новых вакансий."""
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
        """
        Асинхронный ГЕНЕРАТОР.
        Вместо return list[...] мы делаем yield list[...].
        """
        # Шаг 1: Первая страница (всегда отдаем как есть)
        main_url = f"{self.base_url}?category={category}"
        response = await self._session.get(main_url)

        if response.status_code == 200:
            first_batch = self.parser.parse_list(response.text)
            logger.info(f"✨ First page parsed: {len(first_batch)} vacancies")
            yield first_batch  # <--- Отдаем первую пачку сразу
        else:
            return

        # Шаг 2: AJAX цикл
        count = 20
        while True:
            try:
                await self._random_pause()

                # Токен может обновиться, берем свежий
                current_token = self._get_csrf_token()

                # Запрос
                data = await self._fetch_more_via_ajax(category, count, current_token)

                if not data or not data.get("html"):
                    logger.info("💨 Response is empty or no HTML.")
                    break

                # Парсинг
                new_batch = self.parser.parse_list(data.get("html", ""))
                if not new_batch:
                    break

                logger.info(f"✨ Yielding batch of {len(new_batch)} items (offset {count})")
                yield new_batch  # <--- Отдаем следующую пачку

                if data.get("last") is True:
                    logger.info("🏁 Server said: last=true.")
                    break

                # ИСПРАВЛЕНИЕ ЛОГИКИ:
                # Сервер возвращает поле 'num', которое говорит, сколько он отдал.
                # Обычно это 40. Мы должны шагать на это число, чтобы не топтаться на месте.
                step = data.get("num", 40)
                count += step

            except Exception as e:
                logger.warning(f"⚠️ AJAX cycle interrupted: {e}")
                break

    async def fetch_page_html(self, url: str) -> Optional[str]:
        """
        Универсальный метод для скачивания HTML.
        Отвечает только за сеть: заголовки, куки, обход защиты.
        """
        try:
            safe_url = str(url)
            logger.info(f"📡 Hunting for content at: {url}")
            # Мы используем ту же сессию с теми же куками и заголовками
            response = await self._session.get(safe_url)

            if response.status_code == 200:
                return response.text

            logger.error(f"❌ Page fetch failed: {response.status_code} for {url}")
            return None
        except Exception as e:
            logger.error(f"❌ Network error during hunt: {e}")
            return None
