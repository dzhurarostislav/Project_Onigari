import hashlib


def generate_vacancy_hash(title: str, company: str) -> str:
    """
    Создает уникальный хеш вакансии на основе названия и компании.
    """
    # Нормализуем: нижний регистр, убираем лишние пробелы
    raw_data = f"{title.lower().strip()}|{company.lower().strip()}"
    return hashlib.sha256(raw_data.encode()).hexdigest()
