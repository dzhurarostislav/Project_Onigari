import logging

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from database.enums import VacancyStatus
from database.models import Company, Vacancy, VacancySnapshot
from scrapers.schemas import VacancyBaseDTO, VacancyDetailDTO

logger = logging.getLogger(__name__)


class VacancyRepository:
    def __init__(self, session):
        self.session = session

    async def _get_or_create_companies(self, company_names: set[str]) -> dict[str, int]:
        """Bulk create companies and return {name: id} mapping."""
        if not company_names:
            return {}

        # UPSERT companies.
        stmt = (
            insert(Company)
            .values([{"name": name, "description": "", "website_url": ""} for name in company_names])
            .on_conflict_do_update(index_elements=["name"], set_={"name": Company.name})
            .returning(Company.id, Company.name)
        )

        result = await self.session.execute(stmt)
        return {name: c_id for c_id, name in result.all()}

    async def batch_upsert(self, vacancies: list[VacancyBaseDTO]) -> int:
        """Phase 1: List Parsing"""
        if not vacancies:
            return 0

        # 1. Companies
        company_names = {v.company.name for v in vacancies}
        company_map = await self._get_or_create_companies(company_names)

        logger.info(f"🏢 Companies processed: {len(company_map)}")

        # 2. Prepare data
        values = []
        for v in vacancies:
            v_data = v.model_dump(exclude={"company"})

            v_data["company_id"] = company_map[v.company.name]
            v_data["status"] = VacancyStatus.NEW

            # === DESCRIPTION LOGIC ===
            # Data from the list parsing (BaseDTO.short_description) is a snippet.
            # We map it to short_description, keeping the full description empty for now.
            v_data["short_description"] = v.short_description
            v_data["description"] = None

            values.append(v_data)

        # 3. Insert ... ON CONFLICT DO NOTHING
        stmt = insert(Vacancy).values(values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["identity_hash"])

        result = await self.session.execute(stmt)
        await self.session.commit()

        count = result.rowcount
        if count > 0:
            logger.info(f"✅ Successfully inserted {count} new vacancies.")
        else:
            logger.info("ℹ️ No new vacancies added (all duplicates).")

        return count

    async def get_vacancies_by_status(self, status: VacancyStatus, limit: int | None = None) -> list[Vacancy]:
        stmt = select(Vacancy).options(selectinload(Vacancy.company)).where(Vacancy.status == status).limit(limit)
        # Load full description only for vectorization (EXTRACTED status)
        if status == VacancyStatus.EXTRACTED:
            stmt = stmt.options(selectinload(Vacancy.last_snapshot))

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_vacancy_details(self, vacancy_id: int, detail_dto: "VacancyDetailDTO"):
        """Phase 2: Deep Extraction"""

        # 1. Snapshot (History)
        snapshot = VacancySnapshot(
            vacancy_id=vacancy_id, full_description=detail_dto.full_description, content_hash=detail_dto.content_hash
        )
        self.session.add(snapshot)
        await self.session.flush()

        # 2. Update Vacancy
        stmt = (
            update(Vacancy)
            .where(Vacancy.id == vacancy_id)
            .values(
                # === DESCRIPTION LOGIC ===
                # Update the snippet (short_description) if it has changed
                short_description=detail_dto.short_description,
                # Save the FULL description to the main table for vectorization
                description=detail_dto.full_description,
                salary_from=detail_dto.salary_from,
                salary_to=detail_dto.salary_to,
                attributes=detail_dto.attributes,
                grade=detail_dto.grade,
                languages=detail_dto.languages,
                content_hash=detail_dto.content_hash,
                hr_name=detail_dto.hr_name,
                contacts=detail_dto.contacts,
                last_snapshot_id=snapshot.id,
                status=VacancyStatus.EXTRACTED,
            )
        )
        await self.session.execute(stmt)

        # 3. Update Company
        company_dto = detail_dto.company
        if company_dto:
            update_values = {}
            if company_dto.description:
                update_values["description"] = company_dto.description

            # Map dou_url to website_url as per models.py
            if company_dto.dou_url:
                update_values["website_url"] = company_dto.dou_url

            if update_values:
                await self.session.execute(
                    update(Company).where(Company.name == company_dto.name).values(**update_values)
                )

        await self.session.commit()

    async def batch_update_vectors(self, vector_data: list[dict], new_status: VacancyStatus = VacancyStatus.VECTORIZED):
        if not vector_data:
            return

        formatted_data = [{"id": d["b_id"], "embedding": d["b_embedding"], "status": new_status} for d in vector_data]

        await self.session.execute(update(Vacancy), formatted_data)
        await self.session.commit()
