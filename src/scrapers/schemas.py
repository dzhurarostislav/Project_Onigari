from typing import Any, Dict, Optional, List
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator
from utils.hashing import generate_vacancy_identity_hash

# --- Компании ---

class CompanyBaseDTO(BaseModel):
    """Минимум информации из списка вакансий"""
    name: str

class CompanyFullDTO(CompanyBaseDTO):
    """Полная информация из страницы вакансии или профиля компании"""
    dou_url: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

# --- Вакансии ---

class VacancyBaseDTO(BaseModel):
    """Базовая вакансия (Listing)"""
    model_config = ConfigDict(from_attributes=True)

    external_id: str
    title: str
    url: HttpUrl
    # Используем базовую версию компании
    company: CompanyBaseDTO 
    
    # Краткое описание из списка (snippet)
    description: Optional[str] = None
    
    tech_stack: Dict[str, Any] = Field(default_factory=dict)
    salary_from: Optional[float] = None
    salary_to: Optional[float] = None

    identity_hash: Optional[str] = None

    @model_validator(mode="after")
    def generate_hashes(self) -> "VacancyBaseDTO":
        if not self.identity_hash:
            # ИСПРАВЛЕНО: берем имя из вложенного объекта компании
            self.identity_hash = generate_vacancy_identity_hash(
                self.title, 
                self.company.name
            )
        return self

class VacancyDetailDTO(VacancyBaseDTO):
    """Детальная вакансия (Full Page Scan)"""
    # ПЕРЕОПРЕДЕЛЯЕМ поле: здесь нам уже нужна полная компания с тегами
    company: CompanyFullDTO 
    
    full_description: str
    content_hash: str
    
    hr_name: Optional[str] = None
    hr_link: Optional[str] = None