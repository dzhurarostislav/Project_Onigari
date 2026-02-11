import logging

from sqlalchemy.dialects.postgresql import insert

from database.models import Company, Vacancy, VacancyStatus
from scrapers.schemas import VacancyBaseDTO

logger = logging.getLogger(__name__)


class VacancyRepository:
    def __init__(self, session):
        self.session = session

    async def _get_or_create_companies(self, company_names: set[str]) -> dict[str, int]:
        """
        Магия массового создания компаний.
        Возвращает маппинг { "имя_компании": id_в_базе }
        """
        if not company_names:
            return {}

        # 1. Пытаемся вставить компании, если их нет (upsert)
        # Мы ничего не обновляем (DO UPDATE SET name=EXCLUDED.name — технический трюк,
        # чтобы RETURNING вернул ID даже для существующих записей)
        stmt = (
            insert(Company)
            .values([{"name": name, "description": "", "dou_url": ""} for name in company_names])
            .on_conflict_do_update(
                index_elements=["name"], set_={"name": Company.name}  # Ничего не меняем, просто пинаем базу
            )
            .returning(Company.id, Company.name)
        )

        result = await self.session.execute(stmt)
        # Собираем словарь { name: id }
        return {name: c_id for c_id, name in result.all()}

    async def batch_upsert(self, vacancies: list[VacancyBaseDTO]) -> int:
        if not vacancies:
            return 0

        # 1. Собираем все уникальные имена компаний из пачки DTO
        company_names = {v.company.name for v in vacancies}

        # 2. Получаем актуальные ID для этих компаний
        company_map = await self._get_or_create_companies(company_names)

        logger.info(f"🏢 Companies processed: {len(company_map)} (Total unique in batch)")

        # 3. Готовим данные вакансий для вставки
        values = []
        for v in vacancies:
            # Превращаем DTO в словарь, готовый для БД
            v_data = v.model_dump(exclude={"company"})  # Выкидываем вложенный объект

            # Подставляем правильный Foreign Key и конвертируем типы
            v_data["company_id"] = company_map[v.company.name]
            v_data["url"] = str(v.url)
            v_data["status"] = VacancyStatus.NEW  # Явно задаем статус для новых

            # Убеждаемся, что хеш на месте (он генерится валидатором в DTO)
            v_data["identity_hash"] = v.identity_hash

            values.append(v_data)

        # 4. Выполняем массовый INSERT для вакансий
        stmt = insert(Vacancy).values(values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["identity_hash"])

        result = await self.session.execute(stmt)
        await self.session.commit()

        count = result.rowcount
        if count > 0:
            logger.info(f"✅ Successfully inserted {count} new vacancies.")
        else:
            logger.info("ℹ️ No new vacancies added (all duplicates).")

        return result.rowcount
