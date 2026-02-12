import logging

from sqlalchemy import select, update, bindparam
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload


from database.models import Company, Vacancy, VacancySnapshot, VacancyStatus
from scrapers.schemas import VacancyBaseDTO, VacancyDetailDTO

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

    async def get_vacancies_by_status(self, status: VacancyStatus, limit: int = 10) -> list[Vacancy]:
        """
        Возвращает список вакансий с заданным статусом.
        Используем selectinload для компании. Снапшот грузим только если он нужен.
        """
        stmt = (
            select(Vacancy)
            .options(selectinload(Vacancy.company))  # Компании нужны почти всегда
            .where(Vacancy.status == status)
            .limit(limit)
        )

        # Подгружаем полный текст только для векторизации (статус EXTRACTED)
        if status == VacancyStatus.EXTRACTED:
            stmt = stmt.options(selectinload(Vacancy.last_snapshot))

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_vacancy_details(self, vacancy_id: int, detail_dto: "VacancyDetailDTO"):
        """
        Переводит вакансию из NEW в EXTRACTED, сохраняя полное описание и снапшот.
        """
        # 1. Создаем снапшот (историю)
        snapshot = VacancySnapshot(
            vacancy_id=vacancy_id, full_description=detail_dto.full_description, content_hash=detail_dto.content_hash
        )
        self.session.add(snapshot)

        # Нам нужно, чтобы база присвоила ID снапшоту, прежде чем мы привяжем его к вакансии
        await self.session.flush()

        # 2. Обновляем основную запись вакансии
        stmt = (
            update(Vacancy)
            .where(Vacancy.id == vacancy_id)
            .values(
                description=detail_dto.description,  # Краткое можно обновить, если оно стало лучше
                content_hash=detail_dto.content_hash,
                hr_name=detail_dto.hr_name,
                hr_link=detail_dto.hr_link,
                last_snapshot_id=snapshot.id,  # Привязываем актуальный снимок
                status=VacancyStatus.EXTRACTED,  # Метка: "Данные собраны"
            )
        )

        await self.session.execute(stmt)
        await self.session.commit()

    async def batch_update_vectors(self, vector_data: list[dict], new_status: VacancyStatus = VacancyStatus.VECTORIZED):
        """
        vector_data: list of dicts like [{"b_id": 1, "b_embedding": [0.1, 0.2, ...]}, ...]
        """
        if not vector_data:
            return

        # 1. Приводим данные к формату, который SQLAlchemy 2.0 понимает автоматически.
        # Ключи в словаре должны СОВПАДАТЬ с именами атрибутов в модели Vacancy.
        # 'id' обязателен — по нему SQLAlchemy поймет, какую строку обновлять (WHERE id = ...).
        formatted_data = [
            {
                "id": d["b_id"],
                "embedding": d["b_embedding"],
                "status": new_status # Передаем сам объект Enum
            }
            for d in vector_data
        ]

        # 2. В SQLAlchemy 2.0 вызов execute(update(Model), list_of_dicts) 
        # — это официальный способ массового обновления по первичному ключу.
        await self.session.execute(
            update(Vacancy),
            formatted_data
        )
        await self.session.commit()
