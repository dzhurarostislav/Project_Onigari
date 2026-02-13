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

# В config.py
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("DB_HOST", "db") # Внутри докера это всегда 'db'
DB_PORT = os.getenv("DB_PORT", "5432") # Внутри докера это всегда '5432'

# Добавь проверку, что все переменные долетели
if not all([DB_USER, DB_PASSWORD, DB_NAME]):
    raise ValueError(f"❌ MISSING ENV: user={DB_USER}, pass={'***' if DB_PASSWORD else 'NONE'}, db={DB_NAME}")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# Debug: print connection string with masked password if DB_ECHO is on
if os.getenv("DB_ECHO", "False").lower() == "true":
    print(f"🔌 DB Connection: postgresql+asyncpg://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    