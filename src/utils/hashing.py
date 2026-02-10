import hashlib


def generate_vacancy_hash(title: str, company: str) -> str:
    """
    Create unique hashname based on title and company name
    title: name of position
    company: company name
    return: unique hashcode
    """
    # Нормализуем: нижний регистр, убираем лишние пробелы
    raw_data = f"{title.lower().strip()}|{company.lower().strip()}"
    return hashlib.sha256(raw_data.encode()).hexdigest()
