import logging
import re

from selectolax.lexbor import LexborHTMLParser

from scrapers.schemas import CompanyBaseDTO, CompanyFullDTO, VacancyBaseDTO, VacancyDetailDTO
from utils.hashing import generate_vacancy_content_hash

logger = logging.getLogger(__name__)


class DouParser:
    def parse_list(self, html_content: str) -> list[VacancyBaseDTO]:
        """
        parse raw html from dou using selectolax
        and generate dataclass VacancyBaseDTO with bd structure
        html_content: raw html content of site
        return: list containing structured vacancy info
        """
        parser = LexborHTMLParser(html_content)
        items = parser.css("li.l-vacancy")

        if not items:
            logger.warning("No li.l-vacancy found. Trying alternative selector...")
            items = parser.css(".vacancy")

        logger.info(f"Found {len(items)} potential vacancy nodes.")

        vacancies = []
        for item in items:
            title_node = item.css_first("a.vt")
            if not title_node:
                continue

            url = title_node.attributes.get("href")
            # Safe Regex for ID
            match = re.search(r"vacancies/(\d+)/", url)
            external_id = match.group(1) if match else "unknown"

            company_node = item.css_first("a.company")
            salary_node = item.css_first("span.salary")
            desc_node = item.css_first(".sh-info")

            salary_from, salary_to = self._parse_dou_salary(salary_node.text(strip=True) if salary_node else None)

            vacancies.append(
                VacancyBaseDTO(
                    external_id=external_id,
                    title=title_node.text(strip=True),
                    company=CompanyBaseDTO(name=company_node.text(strip=True) if company_node else "Unknown"),
                    short_description=desc_node.text(strip=True) if desc_node else None,
                    salary_from=salary_from,
                    salary_to=salary_to,
                    source_url=url,
                )
            )
        return vacancies

    def _parse_dou_salary(self, salary_str: str | None):
        """
        Parse string into min and max salary
        salary_str: string containing salary
        """
        if not salary_str:
            return None, None
        clean_str = salary_str.replace("$", "").replace("\xa0", "").replace(" ", "")
        nums = re.findall(r"\d+", clean_str)
        if len(nums) == 2:
            return float(nums[0]), float(nums[1])
        if len(nums) == 1:
            return float(nums[0]), None
        return None, None

    def parse_detail(self, html_content: str, base_dto: VacancyBaseDTO) -> VacancyDetailDTO:
        """Extract full vacancy content via Selectolax."""
        parser = LexborHTMLParser(html_content)

        # Vacancy text usually in .vacancy-section or .b-typo
        desc_node = parser.css_first(".vacancy-section") or parser.css_first(".b-typo")
        full_description = desc_node.text(strip=True) if desc_node else ""

        # Generate content hash to track changes
        content_hash = generate_vacancy_content_hash(full_description)

        # Extract HR info
        hr_name = None
        hr_link = None
        hr_node = parser.css_first(".sh-info")

        if hr_node:
            name_node = hr_node.css_first(".name")
            if name_node:
                hr_name = name_node.text(strip=True)

            # Look for profile link
            link_node = hr_node.css_first("a")
            if link_node:
                hr_link = link_node.attributes.get("href")

        # Prepare contacts
        contacts = {}
        if hr_link:
             contacts["profile_url"] = hr_link

        # Build detailed DTO by spreading base fields and adding/overriding specific ones
        return VacancyDetailDTO(
            **base_dto.model_dump(exclude={"company"}),
            company=CompanyFullDTO(name=base_dto.company.name),
            full_description=full_description,
            content_hash=content_hash,
            hr_name=hr_name,
            contacts=contacts,
        )
