import logging
import re

from selectolax.lexbor import LexborHTMLParser

from scrapers.schemas import VacancyDTO

logger = logging.getLogger("OnigariScraper")


class DouParser:
    def parse_list(self, html_content: str) -> list[VacancyDTO]:
        """
        parse raw html from dou using selectolax
        and generate dataclass VacancyDTO with bd structure
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

            salary_from, salary_to = self._parse_dou_salary(
                salary_node.text(strip=True) if salary_node else None
            )

            vacancies.append(
                VacancyDTO(
                    external_id=external_id,
                    title=title_node.text(strip=True),
                    company_name=company_node.text(strip=True)
                    if company_node
                    else "Unknown",
                    description=item.css_first(".sh-info").text(strip=True),
                    salary_from=salary_from,
                    salary_to=salary_to,
                    url=url,
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
