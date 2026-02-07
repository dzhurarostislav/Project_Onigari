import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# В Docker Compose имя сервиса БД — 'db'
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://ryugue:onigari_pass@db:5432/onigari_db"
)

# Создаем движок (engine)
engine = create_async_engine(DATABASE_URL, echo=True)

# Фабрика сессий
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
