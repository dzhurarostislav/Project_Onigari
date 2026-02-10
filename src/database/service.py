from sqlalchemy.dialects.postgresql import insert

from database.models import Vacancy
from scrapers.schemas import VacancyDTO


class VacancyRepository:
    def __init__(self, session):
        self.session = session

    async def batch_upsert(self, vacancies: list[VacancyDTO]) -> int:
        """
        Сохраняет список вакансий, игнорируя дубликаты по identity_hash.
        """
        if not vacancies:
            return 0

        # 1. Превращаем DTO в список словарей, готовых для JSON/SQL
        # mode='json' критичен для сериализации HttpUrl в строку
        values = []
        for v in vacancies:
            v_data = v.model_dump()
            v_data["url"] = str(v_data["url"])
            values.append(v_data)

        # 2. Формируем INSERT
        stmt = insert(Vacancy).values(values)

        # 3. Обработка конфликтов по нашему новому полю identity_hash
        # Пока оставляем do_nothing, как ты и хотел
        stmt = stmt.on_conflict_do_nothing(index_elements=["identity_hash"])

        # 4. Выполнение
        result = await self.session.execute(stmt)
        await self.session.commit()

        # result.rowcount вернет количество реально вставленных строк
        return result.rowcount
