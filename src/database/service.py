import logging

from sqlalchemy import cast, func, or_, select, update
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.orm import selectinload

from brain.schemas import VacancyAnalysisResult, VacancyStructuredData
from database.enums import VacancyStatus
from database.models import Company, Vacancy, VacancyAnalysis, VacancySnapshot
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

    async def save_stage1_result(self, vacancy_id: int, data: VacancyStructuredData):
        """
        Save Stage 1 analysis (Structured Data).
        Updates vacancy attributes and sets status to STRUCTURED.
        Uses Atomic UPDATE.
        """
        # Prepare update dict from Pydantic model
        attributes_update = {
            "tech_stack": data.tech_stack,
            "benefits": data.benefits,
            "red_flag_keywords": data.red_flag_keywords,
            "domain": data.domain,
        }

        update_values = {
            "grade": data.grade,  # Enum compatible
            "status": VacancyStatus.STRUCTURED,
            "work_format": data.work_format,
            "employment_type": data.employment_type,
            "experience_min": data.experience_min,
            "location_city": data.location_city,
            "location_address": data.location_address,
            # Use SQL concatenation for attributes (current || new), handling NULLs with coalesce
            "attributes": func.coalesce(Vacancy.attributes, cast({}, JSONB)).concat(cast(attributes_update, JSONB)),
        }

        # Map Salary if present
        if data.salary_parse:
            update_values.update(
                {
                    "salary_from": data.salary_parse.min,
                    "salary_to": data.salary_parse.max,
                    "salary_currency": data.salary_parse.currency,
                    "is_gross": data.salary_parse.is_gross,
                }
            )

        stmt = update(Vacancy).where(Vacancy.id == vacancy_id).values(**update_values)
        await self.session.execute(stmt)
        await self.session.commit()

    async def save_stage2_result(self, vacancy_id: int, result: VacancyAnalysisResult):
        """
        Save Stage 2 analysis (Judgment).
        Creates VacancyAnalysis record and updates Vacancy status.
        Uses Atomic Transaction.
        """
        async with self.session.begin_nested():
            # 1. Reset is_current for all old analyses
            await self.session.execute(
                update(VacancyAnalysis).where(VacancyAnalysis.vacancy_id == vacancy_id).values(is_current=False)
            )

            # 2. Save Analysis (marked as current)
            analysis = VacancyAnalysis(vacancy_id=vacancy_id, is_current=True, **result.to_db_dict())
            self.session.add(analysis)
            await self.session.flush()  # Get ID

            # 3. Update Vacancy
            await self.session.execute(
                update(Vacancy)
                .where(Vacancy.id == vacancy_id)
                .values(status=VacancyStatus.ANALYZED, last_analysis_id=analysis.id)
            )
        await self.session.commit()

    async def get_vacancies_for_llm_processing(self, limit: int | None = None) -> list[Vacancy]:
        stmt = (
            select(Vacancy)
            .where(or_(Vacancy.status == VacancyStatus.VECTORIZED, Vacancy.status == VacancyStatus.STRUCTURED))
            .limit(limit)
        )

        # Eager load company to avoid N+1
        stmt = stmt.options(selectinload(Vacancy.company))

        stmt = stmt.with_for_update(skip_locked=True)

        result = await self.session.execute(stmt)
        return result.scalars().all()
