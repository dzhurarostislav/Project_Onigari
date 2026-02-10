from sqlalchemy import String, Float, DateTime, Boolean, Text, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from datetime import datetime
from typing import Optional

class Base(DeclarativeBase):
    pass

class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String, index=True)
    
    title: Mapped[str] = mapped_column(String)
    company_name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text)
    
    # Тот самый JSONB для гибкого поиска по техстеку
    tech_stack: Mapped[dict] = mapped_column(JSONB, server_default='{}')

    # Создаем GIN индекс
    __table_args__ = (
        Index(
            "ix_vacancy_tech_stack_gin", # Имя индекса
            "tech_stack",                # Поле
            postgresql_using="gin"       # Магия Postgres
        ),
    )
    
    salary_from: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_to: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    url: Mapped[str] = mapped_column(String, nullable=False)

    hr_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hr_link: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Хеши для дедупликации и отслеживания изменений
    identity_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Вектор для BGE-M3 (1024 измерения)
    embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1024), nullable=True)
    
    is_parsed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())