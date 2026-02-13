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

    async def analyze_vacancy(
        self, 
        vacancy_dict: dict, 
        user_role: str = "Python/LLM Engineer"
    ) -> VacancyAnalysisResult:
        """
        Run the full two-stage analysis pipeline.
        
        Args:
            vacancy_dict: Dictionary containing:
                - title: Job title
                - company_name: Company name
                - description: Full job description
                - id (optional): Vacancy ID for logging
            user_role: Context for the Demon Hunter (who is this analysis for?)
            
        Returns:
            VacancyAnalysisResult with structured data, judgment, and metadata
            
        Raises:
            AnalysisError: If analysis fails at any stage
        """
        start_time = datetime.now()
        vacancy_id = vacancy_dict.get("id", "unknown")
        
        try:
            # --- STAGE 1: THE INVESTIGATOR ---
            # Extract raw facts without emotion
            logger.info(f"👹 Stage 1: Extracting structured data for vacancy {vacancy_id}")
            stage1_start = datetime.now()
            
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
            
            stage1_ms = int((datetime.now() - stage1_start).total_seconds() * 1000)
            logger.info(
                f"✅ Stage 1 complete ({stage1_ms}ms): "
                f"Grade={structured_data.grade}, "
                f"Tech={len(structured_data.tech_stack)} items, "
                f"Red flags={len(structured_data.red_flag_keywords)}"
            )

            # --- STAGE 2: THE DEMON HUNTER ---
            # Apply judgment using the extracted facts + few-shots
            logger.info(f"👹 Stage 2: Applying Demon Hunter judgment for vacancy {vacancy_id}")
            stage2_start = datetime.now()
            
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
            
            stage2_ms = int((datetime.now() - stage2_start).total_seconds() * 1000)
            logger.info(
                f"✅ Stage 2 complete ({stage2_ms}ms): "
                f"Trust Score={judgment.trust_score}/10, "
                f"Verdict={judgment.verdict[:20]}..."
            )

            # --- ASSEMBLY ---
            end_time = datetime.now()
            processing_ms = int((end_time - start_time).total_seconds() * 1000)
            
            logger.info(
                f"🎯 Analysis complete for vacancy {vacancy_id} in {processing_ms}ms "
                f"(Stage1: {stage1_ms}ms, Stage2: {stage2_ms}ms)"
            )

            return VacancyAnalysisResult(
                structured_data=structured_data,
                judgment=judgment,
                model_name=self.provider.model_name,
                provider=self.provider.provider_name,
                analysis_version="1.1",
                tokens_used=0,  # Gemini async doesn't easily expose token count, can be improved
                confidence_score=0.9,  # Placeholder, can implement logprobs if available
                error_message=None
            )

        except Exception as e:
            logger.error(f"❌ Analysis failed for vacancy {vacancy_id}: {e}", exc_info=True)
            
            # Return a failed result with error message
            # This allows graceful degradation instead of crashing
            # NOTE: trust_score=0 indicates technical failure, not a toxic company
            return VacancyAnalysisResult(
                structured_data=VacancyStructuredData(
                    tech_stack=[],
                    grade="Junior",  # Default fallback
                    domain=None,
                    salary_parse=None,
                    benefits=[],
                    red_flag_keywords=[]
                ),
                judgment=VacancyJudgment(
                    trust_score=0,  # 0 = technical failure, not toxic company
                    red_flags=["Analysis failed - see error message"],
                    toxic_phrases=[],
                    honest_summary="Analysis failed due to technical error.",
                    verdict="Analysis Failed"
                ),
                model_name=self.provider.model_name,
                provider=self.provider.provider_name,
                analysis_version="1.1",
                tokens_used=0,
                confidence_score=0.0,
                error_message=str(e)
            )
