import hashlib


def generate_vacancy_identity_hash(title: str, company: str) -> str:
    """
    Create unique hashcode based on title and company name
    title: name of position
    company: company name
    return: unique hashcode
    """
    # Normalize: lowercase and strip whitespace
    raw_data = f"{title.lower().strip()}|{company.lower().strip()}"
    return hashlib.sha256(raw_data.encode()).hexdigest()


def generate_vacancy_content_hash(description: str) -> str:
    """
    Create unique hashcode based on description of vacancy
    description: descrtiption of vacancy
    return: unique hashcode
    """
    return hashlib.sha256(description.encode()).hexdigest()
