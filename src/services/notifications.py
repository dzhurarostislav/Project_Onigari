import html  # <--- Обязательно
import logging

import httpx

from brain.schemas import VacancyAnalysisResult
from database.models import Vacancy

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        # Используем POST endpoint
        self.api_url = f"https://api.telegram.org/bot{token}/sendMessage"

    def _format_report(self, vacancy: Vacancy, result: VacancyAnalysisResult) -> str:
        """Format a stylish dossier for the vacancy with HTML escaping."""
        score = result.judgment.trust_score

        # Эмодзи статуса
        if score >= 8:
            icon = "💎"  # Gem
        elif score >= 6:
            icon = "🟢"  # Safe
        elif score >= 4:
            icon = "🟡"  # Risky
        else:
            icon = "🔴"  # Avoid

        # 🛡️ ЭКРАНИРОВАНИЕ (Самое важное!)
        # Мы должны обезвредить любые спецсимволы в данных
        safe_title = html.escape(vacancy.title)
        safe_company = "Unknown Company"
        safe_verdict = html.escape(result.judgment.verdict)
        safe_summary = html.escape(result.judgment.honest_summary)

        # Обработка списков
        tech_list = result.structured_data.tech_stack
        safe_tech = html.escape(", ".join(tech_list)) if tech_list else "Не указан"

        # Флаги тоже экранируем
        raw_flags = result.judgment.red_flags
        if raw_flags:
            # Экранируем каждый флаг отдельно
            safe_flags = "\n".join([f"• {html.escape(f)}" for f in raw_flags])
        else:
            safe_flags = "Чисто."

        # Собираем сообщение
        return (
            f"🕵️ <b>Onigari Analysis</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>{safe_title}</b>\n"
            f"🏢 <code>{safe_company}</code>\n"
            f"📊 <b>Score:</b> {score}/10 {icon}\n\n"
            f"⚖️ <b>Verdict:</b> {safe_verdict}\n\n"
            f"🛠 <b>Stack:</b> <code>{safe_tech}</code>\n"
            f"🚩 <b>Flags:</b>\n<i>{safe_flags}</i>\n\n"
            f"📝 <b>Summary:</b>\n{safe_summary}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <a href='{vacancy.source_url}'>Открыть вакансию</a>"
        )

    async def notify_analysis_complete(self, vacancy: Vacancy, result: VacancyAnalysisResult):
        """Send Telegram notification if the vacancy is interesting."""

        # 🔥 ФИЛЬТР: Отправляем только хорошие (>=7) ИЛИ очень плохие (<=3) ради смеха?
        # Сейчас стоит только хорошие.
        if result.judgment.trust_score < 7:
            return

        if not self.token or not self.chat_id:
            logger.warning("Telegram credentials missing, skipping notification.")
            return

        text = self._format_report(vacancy, result)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,  # Лучше True, чтобы не засорять чат превьюшками сайтов
                    },
                )

                # Логируем ответ, если что-то пошло не так
                if response.status_code != 200:
                    logger.error(f"🚀 Telegram Error {response.status_code}: {response.text}")

        except Exception as e:
            logger.error(f"🚀 Telegram Notification failed: {e}")
