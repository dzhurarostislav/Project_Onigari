import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ScraperConfig:
    cookies: str
    user_agent: str


# Собираем настройки для Djinni
DJINNI_CONFIG = ScraperConfig(
    cookies=os.getenv("DJINNI_COOKIES", ""),
    user_agent=os.getenv("DJINNI_USER_AGENT", ""),
)
