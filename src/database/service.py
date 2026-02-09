from dataclasses import asdict

from sqlalchemy.dialects.postgresql import insert

from database.models import Vacancy
from utils.hashing import generate_vacancy_hash


class VacancyRepository:
    def __init__(self, session):
        self.session = session

    async def batch_upsert(self, vacancies: list) -> int:
        if not vacancies:
            return 0

        values = []
        for v in vacancies:
            # Превращаем dataclass в dict
            v_dict = asdict(v)
            # Генерируем хэш и добавляем в словарь
            v_dict["internal_hash"] = generate_vacancy_hash(v.title, v.company_name)
            values.append(v_dict)

        stmt = insert(Vacancy).values(values)
        # Указываем, что делать при конфликте хэшей
        stmt = stmt.on_conflict_do_nothing(index_elements=["internal_hash"])

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount
