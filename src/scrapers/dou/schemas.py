from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class VacancyDTO:
    external_id: str  # maps to external_id in DB
    title: str
    company_name: str
    description: str
    salary_from: Optional[float] = None
    salary_to: Optional[float] = None
    url: Optional[str] = None
    hr_name: Optional[str] = None
    hr_link: Optional[str] = None
