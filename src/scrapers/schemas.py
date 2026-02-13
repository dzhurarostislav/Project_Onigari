from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from utils.hashing import generate_vacancy_identity_hash

from database.enums import VacancyGrade

# --- Companies ---


class CompanyBaseDTO(BaseModel):
    """Basic company info from listings."""

    model_config = ConfigDict(from_attributes=True)
    name: str


class CompanyFullDTO(CompanyBaseDTO):
    """Detailed company info from profile pages."""

    model_config = ConfigDict(from_attributes=True)
    dou_url: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


# --- Vacancies ---


class VacancyBaseDTO(BaseModel):
    """Basic vacancy info from listings."""

    model_config = ConfigDict(from_attributes=True)

    external_id: str
    title: str
    source_url: str = Field(..., description="Original URL of the vacancy")
    # Use base version of the company
    company: CompanyBaseDTO

    # Short description from listing
    short_description: Optional[str] = None

    attributes: Dict[str, Any] = Field(default_factory=dict) # Formerly tech_stack
    grade: Optional[VacancyGrade] = None
    languages: Dict[str, str] = Field(default_factory=dict)
    
    salary_from: Optional[float] = None
    salary_to: Optional[float] = None

    identity_hash: Optional[str] = None

    @model_validator(mode="after")
    def generate_hashes(self) -> "VacancyBaseDTO":
        if not self.identity_hash:
            # Fixed: using company name from nested object
            self.identity_hash = generate_vacancy_identity_hash(self.title, self.company.name)
        return self


class VacancyDetailDTO(VacancyBaseDTO):
    """Detailed vacancy info from full page scan."""

    model_config = ConfigDict(from_attributes=True)
    # Detailed company info with tags
    company: CompanyFullDTO

    full_description: str
    content_hash: str

    hr_name: Optional[str] = None
    contacts: Dict[str, str] = Field(default_factory=dict)
