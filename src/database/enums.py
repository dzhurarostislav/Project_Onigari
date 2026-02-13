import enum

class VacancyStatus(enum.Enum):
    NEW = "new"
    EXTRACTED = "extracted"
    ANALYZED = "analyzed"
    VECTORIZED = "vectorized"
    ARCHIVED = "archived"
    FAILED = "failed"

class SalaryPeriod(enum.Enum):
    HOUR = "hour"
    MONTH = "month"
    YEAR = "year"
    PROJECT = "project"         # Per project
    SHIFT = "shift"             # Per shift

class WorkFormat(enum.Enum):
    OFFICE = "office"
    REMOTE = "remote"
    HYBRID = "hybrid"
    ROAMING = "roaming"         # For drivers/couriers/agents

class EmploymentType(enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"       # B2B / Contract
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"     # Seasonal / Project

class SignalSource(enum.Enum):
    DOU = "dou"
    GLASSDOOR = "glassdoor"
    LINKEDIN = "linkedin"
    TELEGRAM = "telegram"
    INTERNAL_AI = "internal_ai" # If LLM found a red flag

class VacancyGrade(enum.Enum):
    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"
    INTERN = "intern"

class UserInteractionStatus(enum.Enum):
    VIEWED = "viewed"
    FAVORITE = "favorite"
    APPLIED = "applied"
    HIDDEN = "hidden"
    REJECTED = "rejected"
    OFFER = "offer"
