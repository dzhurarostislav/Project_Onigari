from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String, index=True)
    last_snapshot_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("vacancy_snapshots.id", use_alter=True, name="fk_last_snapshot")
    )

    # 2. МАГИЯ: Ссылка на ОБЪЕКТ последнего снимка
    # Мы явно говорим: "Используй ключ last_snapshot_id для этой связи"
    last_snapshot: Mapped[Optional["VacancySnapshot"]] = relationship(
        "VacancySnapshot",
        foreign_keys=[last_snapshot_id],  # Указываем, какой FK использовать
        back_populates="current_for_vacancy",
    )

    # 3. МАГИЯ: Список ВСЕХ снимков (История)
    # Здесь мы говорим: "Ищи все снимки, где vacancy_id равен моему id"
    snapshots: Mapped[list["VacancySnapshot"]] = relationship(
        "VacancySnapshot",
        foreign_keys="[VacancySnapshot.vacancy_id]",  # Указываем FK в другой таблице
        back_populates="vacancy",
    )

    title: Mapped[str] = mapped_column(String)
    company_name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text)

    # Тот самый JSONB для гибкого поиска по техстеку
    tech_stack: Mapped[dict] = mapped_column(JSONB, server_default="{}")

    # Создаем GIN индекс
    __table_args__ = (
        Index(
            "ix_vacancy_tech_stack_gin", "tech_stack", postgresql_using="gin"  # Имя индекса  # Поле  # Магия Postgres
        ),
    )

    salary_from: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_to: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    url: Mapped[str] = mapped_column(String, nullable=False)

    hr_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hr_link: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Хеш для дедупликации и отслеживания изменений
    identity_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)

    # Вектор для BGE-M3 (1024 измерения)
    embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1024), nullable=True)

    is_parsed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class VacancySnapshot(Base):
    __tablename__ = "vacancy_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id"))

    # 2. МАГИЯ: Обратная ссылка к истории
    vacancy: Mapped["Vacancy"] = relationship("Vacancy", foreign_keys=[vacancy_id], back_populates="snapshots")

    # 3. МАГИЯ: Обратная ссылка к "актуалочке"
    current_for_vacancy: Mapped["Vacancy"] = relationship(
        "Vacancy", foreign_keys="[Vacancy.last_snapshot_id]", back_populates="last_snapshot"
    )

    full_description: Mapped[str] = mapped_column(Text)

    content_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
