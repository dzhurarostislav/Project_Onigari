from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector  # Для нашего BGE-M3
from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Vacancy(Base):
    __tablename__ = "vacancies"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    internal_hash: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_parsed: Mapped[bool] = mapped_column(default=False)

    # Основная информация
    title: Mapped[str] = mapped_column(String(255))
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text)

    # Зарплатная вилка (может быть пустой, поэтому Float | None)
    salary_from: Mapped[float | None] = mapped_column(Float)
    salary_to: Mapped[float | None] = mapped_column(Float)

    hr_name: Mapped[str | None] = mapped_column(String(255))
    hr_link: Mapped[str | None] = mapped_column(String(500))

    # Наш "Детектор булшита" (от 1.0 до 10.0)
    cheating_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Поле для вектора BGE-M3 (размерность 1024)
    embedding: Mapped[Vector] = mapped_column(Vector(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
