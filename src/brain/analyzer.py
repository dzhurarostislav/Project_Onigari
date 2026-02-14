"""
Vacancy analysis orchestrator.

The brain of the Onigari Project. Conducts a two-stage analysis:
1. The Investigator (Stage 1): Extract structured data
2. The Demon Hunter (Stage 2): Apply cynical judgment with few-shot learning
"""

import logging
from datetime import datetime

from brain.exceptions import AnalysisError
from brain.few_shots import STAGE2_FEW_SHOTS
from brain.interfaces import LLMProvider
from brain.prompts import (
    STAGE1_SYSTEM_PROMPT,
    STAGE2_SYSTEM_PROMPT,
    format_stage1_prompt,
    format_stage2_prompt,
)
from brain.schemas import VacancyAnalysisResult, VacancyJudgment, VacancyStructuredData
from brain.context import tokens_counter
from database.enums import VacancyGrade

logger = logging.getLogger(__name__)


class VacancyAnalyzer:
    """
    The Orchestrator of the Onigari Project.
    
    Conducts a two-stage analysis:
    1. The Investigator (Extraction) - Extract facts without emotion
    2. The Demon Hunter (Judgment) - Apply cynical analysis with few-shots
    
    Usage:
        provider = GeminiProvider(api_key="...")
        analyzer = VacancyAnalyzer(provider)
        result = await analyzer.analyze_vacancy(vacancy_dict)
    """

    def __init__(self, provider: LLMProvider):
        """
        Initialize the analyzer with an LLM provider.
        
        Args:
            provider: Any LLM provider implementing the LLMProvider interface
        """
        self.provider = provider
        logger.info(f"Initialized VacancyAnalyzer with provider: {provider.__class__.__name__}")

    async def analyze_stage1(self, vacancy_dict: dict) -> VacancyStructuredData:
        """
        Stage 1: The Investigator (Facts Extraction).
        Extracts structured data without judgment.
        """
        tokens_counter.set(0)
        vacancy_id = vacancy_dict.get("id", "unknown")
        logger.info(f"👹 Stage 1: Extracting structured data for vacancy {vacancy_id}")
        
        start_time = datetime.now()
        
        s1_prompt = format_stage1_prompt(
            title=vacancy_dict.get("title", "Unknown"),
            company_name=vacancy_dict.get("company_name", "Unknown"),
            description=vacancy_dict.get("description", "")
        )
        
        structured_data = await self.provider.analyze(
            user_prompt=s1_prompt,
            system_instruction=STAGE1_SYSTEM_PROMPT,
            schema=VacancyStructuredData
        )
        
        ms = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.info(
            f"✅ Stage 1 complete ({ms}ms): "
            f"Grade={structured_data.grade}, "
            f"Tech={len(structured_data.tech_stack)} items, "
            f"Red flags={len(structured_data.red_flag_keywords)}"
        )
        return structured_data

    async def analyze_stage2(
        self, 
        vacancy_dict: dict, 
        structured_data: VacancyStructuredData,
        user_role: str = "Python/LLM Engineer"
    ) -> VacancyAnalysisResult:
        """
        Stage 2: The Demon Hunter (Judgment).
        Applies cynical judgment using facts from Stage 1.
        """
        vacancy_id = vacancy_dict.get("id", "unknown")
        logger.info(f"👹 Stage 2: Applying Demon Hunter judgment for vacancy {vacancy_id}")
        
        start_time = datetime.now()
        
        s2_prompt = format_stage2_prompt(
            title=vacancy_dict.get("title", "Unknown"),
            company_name=vacancy_dict.get("company_name", "Unknown"),
            description=vacancy_dict.get("description", ""),
            structured_data=structured_data,
            user_role=user_role
        )
        
        # Enrich system instruction with few-shot examples
        enriched_system_prompt = f"{STAGE2_SYSTEM_PROMPT}\n\n{STAGE2_FEW_SHOTS}"

        judgment = await self.provider.analyze(
            user_prompt=s2_prompt,
            system_instruction=enriched_system_prompt,
            schema=VacancyJudgment
        )
        
        ms = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.info(
            f"✅ Stage 2 complete ({ms}ms): "
            f"Trust Score={judgment.trust_score}/10, "
            f"Verdict={judgment.verdict[:20]}..."
        )

        return VacancyAnalysisResult(
            structured_data=structured_data,
            judgment=judgment,
            model_name=self.provider.model_name,
            provider=self.provider.provider_name,
            analysis_version="1.1",
            confidence_score=0.9,
            error_message=None
        )

    async def analyze_vacancy(
        self, 
        vacancy_dict: dict, 
        user_role: str = "Python/LLM Engineer"
    ) -> VacancyAnalysisResult:
        """
        Run the full two-stage analysis pipeline (Legacy wrapper).
        """
        vacancy_id = vacancy_dict.get("id", "unknown")
        start_time = datetime.now()
        
        try:
            # Stage 1
            structured_data = await self.analyze_stage1(vacancy_dict)
            
            # Stage 2
            result = await self.analyze_stage2(vacancy_dict, structured_data, user_role)
            
            total_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.info(f"🎯 Full analysis complete for vacancy {vacancy_id} in {total_ms}ms")
            result.tokens_used = tokens_counter.get()
            
            return result

        except Exception as e:
            logger.error(f"❌ Analysis failed for vacancy {vacancy_id}: {e}", exc_info=True)
            
            # Return a failed result with error message
            return VacancyAnalysisResult(
                structured_data=VacancyStructuredData(
                    tech_stack=[],
                    grade=VacancyGrade.JUNIOR,
                    domain=None,
                    salary_parse=None,
                    benefits=[],
                    red_flag_keywords=[]
                ),
                judgment=VacancyJudgment(
                    trust_score=0,
                    red_flags=["Analysis failed - see error message"],
                    toxic_phrases=[],
                    honest_summary="Analysis failed due to technical error.",
                    verdict="Analysis Failed"
                ),
                model_name=self.provider.model_name,
                provider=self.provider.provider_name,
                analysis_version="1.1",
                tokens_used=tokens_counter.get(),
                confidence_score=0.0,
                error_message=str(e)
            )
