from datetime import datetime

from pgvector.sqlalchemy import Vector  # Для нашего BGE-M3
from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Vacancy(Base):
    __tablename__ = "vacancies"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    is_parsed: Mapped[bool] = mapped_column(default=False)

    # Основная информация
    title: Mapped[str] = mapped_column(String(255))
    company_name: Mapped[str] = mapped_column(String(255))

    # Текст вакансии — используем Text, так как он не имеет лимита по длине
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

    # Время добавления в систему
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
