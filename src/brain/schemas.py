from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from database.enums import EmploymentType, VacancyGrade, WorkFormat

# --- ENUMS FOR STRICT VALIDATION ---
# LLM structured output will enforce these values automatically


class Currency(str, Enum):
    """Supported currency codes."""

    USD = "USD"
    EUR = "EUR"
    UAH = "UAH"  # Ukrainian Hryvnia (гривня)
    PLN = "PLN"  # Polish Zloty
    GBP = "GBP"


# --- STAGE 1: THE AUTOPSY (Structured Data Extraction) ---
# Задача: Вытащить факты. Без эмоций, только данные.


class SalaryData(BaseModel):
    """Parsed salary information from vacancy text."""

    model_config = ConfigDict(from_attributes=True)

    min: Optional[int] = Field(None, description="Minimum salary in specified currency. None if not specified.")
    max: Optional[int] = Field(None, description="Maximum salary in specified currency. None if not specified.")
    currency: Currency = Field(Currency.USD, description="Currency code.")
    is_gross: bool = Field(False, description="True if salary is before taxes.")


class VacancyStructuredData(BaseModel):
    """
    Stage 1 Output: Structured extraction of vacancy facts.
    This is the raw autopsy - just the facts, no judgment.
    """

    model_config = ConfigDict(from_attributes=True)

    tech_stack: List[str] = Field(
        default_factory=list,
        description="List of technologies mentioned (e.g., ['Python', 'Django', 'PostgreSQL']).",
    )
    grade: VacancyGrade = Field(description="Seniority level.")
    work_format: WorkFormat = Field(description="Work format.")
    employment_type: EmploymentType = Field(description="Employment type.")
    experience_min: Optional[float] = Field(None, description="Minimum required experience in years. (float)", ge=0.0)
    location_city: Optional[str] = Field(None, description="City where the job is located. Empty if remote.")
    location_address: Optional[str] = Field(None, description="Address where the job is located. Empty if remote.")
    domain: Optional[str] = Field(None, description="Company domain (FinTech, Crypto, Gamedev, etc.).")

    salary_parse: Optional[SalaryData] = Field(None, description="Parsed salary info if found in text.")

    benefits: List[str] = Field(
        default_factory=list,
        description="List of real perks (insurance, equipment). Exclude vague promises like 'friendly team'.",
    )
    red_flag_keywords: List[str] = Field(
        default_factory=list,
        description="Keywords that might indicate issues (e.g., 'overtime', 'unpaid', 'family', 'stress').",
    )


# --- STAGE 2: THE JUDGMENT (Onigari Analysis) ---
# Задача: Оценить "душу" вакансии. Сарказм, поиск лжи, вердикт.


class VacancyContext(BaseModel):
    """
    RICH Context based on the Vacancy SQLAlchemy model.
    Transfers the Single Source of Truth from DB to LLM.
    """

    model_config = ConfigDict(from_attributes=True)  # Магия: работает с ORM объектами

    id: int
    title: str

    # Company info (Flattened for prompt)
    company_name: str = Field(default="Unknown Company")

    description: Optional[str]

    # MONEY (The most important part)
    salary_from: Optional[float]
    salary_to: Optional[float]
    salary_currency: Optional[str] = "USD"
    is_gross: bool = False

    # Metadata that changes the verdict
    hr_name: Optional[str] = None
    contacts: Dict[str, Any] = Field(default_factory=dict)  # Telegram/Email inside
    work_format: str = "OFFICE"  # Convert Enum to string
    location_city: Optional[str] = None

    url: str = Field(alias="source_url")

    @computed_field
    def financial_summary(self) -> str:
        """Generates a human-readable salary string for the LLM."""
        if not self.salary_from and not self.salary_to:
            return "NOT SPECIFIED (Hidden)"

        currency = self.salary_currency or "USD"
        tax_info = " (Gross)" if self.is_gross else " (Net?)"

        if self.salary_from and self.salary_to:
            return f"{self.salary_from} - {self.salary_to} {currency}{tax_info}"

        if self.salary_from:
            return f"From {self.salary_from} {currency}{tax_info}"

        if self.salary_to:
            return f"Up to {self.salary_to} {currency}{tax_info}"

        return "Error parsing salary"

    @computed_field
    def contact_info(self) -> str:
        """Extracts direct contacts if available."""
        if not self.contacts:
            return "Apply via site"

        details = []
        if self.hr_name:
            details.append(f"HR: {self.hr_name}")

        # Если в контактах есть телеграм - это жирный плюс
        for channel, value in self.contacts.items():
            details.append(f"{channel}: {value}")

        return " | ".join(details)


class VacancyJudgment(BaseModel):
    """
    Stage 2 Output: The Onigari verdict.
    Cynical, sarcastic analysis of what the vacancy REALLY means.
    """

    model_config = ConfigDict(from_attributes=True)

    trust_score: int = Field(
        ge=0,
        le=10,
        description="Company quality score: 0 = Technical failure (analysis error), 1 = Awful/Toxic (run away!), 10 = Perfect/Clean (dream job). Higher = better.",
    )
    red_flags: List[str] = Field(
        default_factory=list,
        description="List of specific concerns detected (e.g., 'Toxic requirements', 'Low salary for Senior').",
    )
    toxic_phrases: List[str] = Field(
        default_factory=list,
        description="Direct quotes from the text that sound toxic or manipulative.",
    )
    honest_summary: str = Field(
        description="A cynical, 'human-to-human' translation of the vacancy. What does it REALLY mean?"
    )
    verdict: str = Field(description="Final verdict: 'Safe', 'Risky', or 'Avoid'. Brief explanation.")


# --- COMBINED RESULT ---
# Объединяет оба этапа для сохранения в БД


class VacancyAnalysisResult(BaseModel):
    """
    Complete analysis result combining both stages.
    Used for database insertion into VacancyAnalysis model.
    """

    model_config = ConfigDict(from_attributes=True)

    # From Stage 1 (Structured Data)
    structured_data: VacancyStructuredData

    # From Stage 2 (Judgment)
    judgment: VacancyJudgment

    # Metadata about the analysis process
    model_name: str = Field(description="Model used for analysis (e.g., 'gemini-1.5-pro')")
    provider: str = Field(description="Provider (e.g., 'google', 'openai')")
    analysis_version: str = Field(default="1.0", description="Version of the analysis prompt/schema")
    tokens_used: Optional[int] = Field(None, description="Total tokens consumed across both stages")
    confidence_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Model's confidence in the analysis (0.0-1.0)"
    )
    error_message: Optional[str] = Field(None, description="Error message if analysis failed")

    @classmethod
    def create_failed(cls, error_msg: str, provider_name: str, model_name: str):
        """Фабричный метод для создания результата-заглушки при сбое."""
        return cls(
            structured_data=VacancyStructuredData(tech_stack=[], grade=VacancyGrade.JUNIOR, red_flag_keywords=[]),
            judgment=VacancyJudgment(
                trust_score=0,
                red_flags=[f"System error: {error_msg}"],
                toxic_phrases=[],
                honest_summary="Analysis failed due to a technical issue.",
                verdict="ERROR",
            ),
            model_name=model_name,
            provider=provider_name,
            analysis_version="1.2",
            tokens_used=0,
            error_message=error_msg,
        )

    def to_db_dict(self) -> dict:
        """
        Convert to dictionary format suitable for VacancyAnalysis database model.
        Maps DTO fields to database columns.
        """
        return {
            "trust_score": self.judgment.trust_score,
            "red_flags": self.judgment.red_flags,
            "toxic_phrases": self.judgment.toxic_phrases,
            "honest_summary": self.judgment.honest_summary,
            "verdict": self.judgment.verdict,
            "model_name": self.model_name,
            "provider": self.provider,
            "analysis_version": self.analysis_version,
            "tokens_used": self.tokens_used,
            "confidence_score": self.confidence_score,
            "error_message": self.error_message,
        }
