from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, String, Table, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from database.enums import (
    EmploymentType,
    SalaryPeriod,
    SignalSource,
    UserInteractionStatus,
    VacancyGrade,
    VacancyStatus,
    WorkFormat,
)

# --- BASE ---


class Base(DeclarativeBase):
    pass


company_tags = Table(
    "company_tags",
    Base.metadata,
    Column("company_id", ForeignKey("companies.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)

# --- MODELS ---


class Vacancy(Base):
    __tablename__ = "vacancies"

    # Identifiers
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String, index=True)  # ID on source (dou_123, etc)
    source_url: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships (Snapshots)
    last_snapshot_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("vacancy_snapshots.id", use_alter=True, name="fk_last_snapshot")
    )
    last_snapshot: Mapped[Optional["VacancySnapshot"]] = relationship(
        "VacancySnapshot",
        foreign_keys=[last_snapshot_id],
        back_populates="current_for_vacancy",
    )
    snapshots: Mapped[List["VacancySnapshot"]] = relationship(
        "VacancySnapshot",
        foreign_keys="[VacancySnapshot.vacancy_id]",
        back_populates="vacancy",
        cascade="all, delete-orphan",
    )

    # Relationships (Company)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    company: Mapped["Company"] = relationship("Company", back_populates="vacancies")

    # Content
    title: Mapped[str] = mapped_column(String, index=True)
    short_description: Mapped[str] = mapped_column(Text)  # Snippet from listing
    description: Mapped[Optional[str]] = mapped_column(Text)  # Full description for vectorization

    # Universal Attributes (JSONB)
    # e.g., { "languages": ["Python"], "frameworks": ["Django"], "grade": "Senior" }
    attributes: Mapped[dict] = mapped_column(JSONB, server_default="{}")

    # Salary
    salary_from: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_to: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(3), default="USD")
    salary_period: Mapped[SalaryPeriod] = mapped_column(
        SQLEnum(SalaryPeriod), default=SalaryPeriod.MONTH, nullable=True
    )
    is_gross: Mapped[bool] = mapped_column(Boolean, default=False)  # Before taxes?

    # Job Terms
    work_format: Mapped[WorkFormat] = mapped_column(SQLEnum(WorkFormat), default=WorkFormat.OFFICE, index=True)
    employment_type: Mapped[EmploymentType] = mapped_column(SQLEnum(EmploymentType), default=EmploymentType.FULL_TIME)
    grade: Mapped[Optional[VacancyGrade]] = mapped_column(SQLEnum(VacancyGrade), nullable=True, index=True)
    languages: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    experience_min: Mapped[Optional[float]] = mapped_column(Float)  # In years
    requires_own_equipment: Mapped[bool] = mapped_column(Boolean, default=False)  # Own car/laptop

    # Location
    location_city: Mapped[Optional[str]] = mapped_column(String, index=True)
    location_address: Mapped[Optional[str]] = mapped_column(String)
    geo_lat: Mapped[Optional[float]] = mapped_column(Float)  # Latitude
    geo_lon: Mapped[Optional[float]] = mapped_column(Float)  # Longitude
    is_relocation_possible: Mapped[bool] = mapped_column(Boolean, default=False)

    # HR Info
    hr_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    contacts: Mapped[dict] = mapped_column(JSONB, server_default="{}")  # {"email": "...", "telegram": "..."}

    # Metadata & AI
    identity_hash: Mapped[str] = mapped_column(String, unique=True, index=True)  # SHA256(url + external_id)
    content_hash: Mapped[Optional[str]] = mapped_column(String, index=True)  # SHA256(description + title)

    embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1024), nullable=True)  # BGE-M3

    status: Mapped[VacancyStatus] = mapped_column(
        SQLEnum(VacancyStatus), default=VacancyStatus.NEW, nullable=False, index=True
    )

    # Reputation metrics
    trust_score: Mapped[Optional[float]] = mapped_column(Float)  # 1.0 - 10.0
    red_flags: Mapped[Optional[list]] = mapped_column(JSONB)  # Identified issues

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    __table_args__ = (Index("ix_vacancy_attributes_gin", "attributes", postgresql_using="gin"),)


class VacancySnapshot(Base):
    __tablename__ = "vacancy_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"))

    vacancy: Mapped["Vacancy"] = relationship("Vacancy", foreign_keys=[vacancy_id], back_populates="snapshots")
    current_for_vacancy: Mapped["Vacancy"] = relationship(
        "Vacancy", foreign_keys="[Vacancy.last_snapshot_id]", back_populates="last_snapshot"
    )

    full_description: Mapped[str] = mapped_column(Text)
    raw_json: Mapped[Optional[dict]] = mapped_column(JSONB)  # Raw API/HTML response

    content_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    slug: Mapped[Optional[str]] = mapped_column(String, index=True)  # For SEO URL

    description: Mapped[str] = mapped_column(Text, default="")
    website_url: Mapped[Optional[str]] = mapped_column(String)

    # Reputation
    overall_rating: Mapped[float] = mapped_column(Float, default=0.0)  # Internal Onigari rating
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # Verified by us

    industry: Mapped[Optional[str]] = mapped_column(String)  # IT, Logistics, Retail
    size_range: Mapped[Optional[str]] = mapped_column(String)  # 10-50, 1000+

    vacancies: Mapped[List[Vacancy]] = relationship("Vacancy", back_populates="company")
    tags: Mapped[List["Tag"]] = relationship("Tag", secondary=company_tags, back_populates="companies")
    signals: Mapped[List["SocialSignal"]] = relationship("SocialSignal", back_populates="company")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    category: Mapped[Optional[str]] = mapped_column(String)  # Tech, Benefit, Warning
    companies: Mapped[List["Company"]] = relationship("Company", secondary=company_tags, back_populates="tags")


class SocialSignal(Base):
    __tablename__ = "social_signals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)

    company: Mapped["Company"] = relationship("Company", back_populates="signals")

    source: Mapped[SignalSource] = mapped_column(SQLEnum(SignalSource), index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String)  # URL to comment/post

    content: Mapped[str] = mapped_column(Text)  # Review or identified compromise text

    # Signal analytics
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)  # From -1.0 (bad) to 1.0 (excellent)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # Verified author

    # Vector for search
    embedding: Mapped[Optional[Vector]] = mapped_column(Vector(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"), index=True)
    vacancy: Mapped["Vacancy"] = relationship("Vacancy")

    status: Mapped[UserInteractionStatus] = mapped_column(
        SQLEnum(UserInteractionStatus), default=UserInteractionStatus.VIEWED, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
