from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from config import DATABASE_URL, os

engine = create_async_engine(
    DATABASE_URL, 
    echo=os.getenv("DB_ECHO", "False").lower() == "true"
)

async_session = async_sessionmaker(engine, expire_on_commit=False)
