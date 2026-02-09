import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# В Docker Compose имя сервиса БД — 'db'
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://ryugue:onigari_pass@db:5432/onigari_db"
)

engine = create_async_engine(DATABASE_URL, echo=os.getenv("DB_ECHO", "False") == "True")

async_session = async_sessionmaker(engine, expire_on_commit=False)
