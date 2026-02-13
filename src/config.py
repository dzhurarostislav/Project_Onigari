import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class ScraperConfig:
    cookies: str
    user_agent: str

# 1. Scraper Configs
DJINNI_CONFIG = ScraperConfig(
    cookies=os.getenv("DJINNI_COOKIES", ""),
    user_agent=os.getenv("DJINNI_USER_AGENT", ""),
)

# 2. Database Config
DB_USER = os.getenv("POSTGRES_USER", "ryugue")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB", "onigari_db")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5435")

# Защита от дурака: если забыл пароль в .env, падаем сразу
if not DB_PASSWORD:
    raise ValueError("❌ CRITICAL: POSTGRES_PASSWORD is missing in .env")

# Собираем строку подключения для SQLAlchemy
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Для отладки (вывод в консоль только если включен ECHO, пароль скрываем)
if os.getenv("DB_ECHO", "False").lower() == "true":
    print(f"🔌 DB Connection: postgresql+asyncpg://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}")