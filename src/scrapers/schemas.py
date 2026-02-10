from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from utils.hashing import generate_vacancy_identity_hash


class VacancyDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    company_name: str
    description: str

    # JSONB структура: {"python": {"importance": "core", ...}}
    tech_stack: Dict[str, Any] = Field(default_factory=dict)

    salary_from: Optional[float] = None
    salary_to: Optional[float] = None

    url: HttpUrl

    hr_name: Optional[str] = None
    hr_link: Optional[str] = None

    identity_hash: Optional[str] = None
    content_hash: Optional[str] = None

    external_id: str

    @model_validator(mode="after")
    def generate_hashes(self) -> "VacancyDTO":
        if not self.identity_hash:
            self.identity_hash = generate_vacancy_identity_hash(self.title, self.company_name)

        # content_hash пока опционален, так как описание может чиститься позже
        return self
