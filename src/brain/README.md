# Brain Module - Vacancy Analysis Pipeline

This module implements the two-stage Chain-of-Thought (CoT) analysis pipeline for vacancy trust analysis.

## Architecture

```
Vacancy → Stage 1: Investigator → Stage 2: Demon Hunter → VacancyAnalysis (DB)
```

### Stage 1: The Investigator (Structured Extraction)
**Goal:** Extract facts without judgment

**Input:** Raw vacancy text  
**Output:** `VacancyStructuredData`
- Tech stack (normalized)
- Grade/seniority
- Domain
- Parsed salary
- Real benefits
- Red flag keywords

**Model:** Fast, cheap model (e.g., Gemini 1.5 Flash)

### Stage 2: The Demon Hunter (Onigari Verdict)
**Goal:** Analyze trust and toxicity using few-shot learning

**Input:** Original text + Stage 1 structured data + User role + Few-shot examples  
**Output:** `VacancyJudgment`
- Trust score (1-10, where 1=toxic, 10=perfect)
- Specific red flags
- Toxic phrases (direct quotes)
- Honest summary (cynical translation)
- Final verdict (Safe/Risky/Avoid)

**Model:** More capable model (e.g., Gemini 1.5 Pro, GPT-4)

## Files

- **`interfaces.py`** - Abstract LLM provider contract
- **`providers.py`** - LLM provider implementations (Gemini, future: OpenAI, Anthropic)
- **`exceptions.py`** - Custom exception hierarchy for error handling
- **`schemas.py`** - Pydantic DTOs for all stages
- **`prompts.py`** - System and user prompts for LLM calls
- **`few_shots.py`** - Few-shot examples for Stage 2 (The Demon Hunter)
- **`analyzer.py`** - Analysis orchestration logic
- **`vectorizer.py`** - Embedding generation for semantic search

## Usage Example

### Basic Usage

```python
from brain.analyzer import VacancyAnalyzer
from brain.providers import GeminiProvider
from brain.schemas import VacancyAnalysisResult
from database.models import VacancyAnalysis

# Initialize provider
provider = GeminiProvider(
    api_key="your-google-ai-api-key",
    model_name="gemini-1.5-flash"  # or "gemini-1.5-pro" for better quality
)

# Initialize analyzer
analyzer = VacancyAnalyzer(provider)

# Run full two-stage analysis
result: VacancyAnalysisResult = await analyzer.analyze_vacancy(
    vacancy_dict={
        "id": 123,
        "title": "Senior Python Developer",
        "company_name": "TechCorp",
        "description": "..."
    },
    user_role="Python/LLM Engineer"  # Dynamic user context
)

# Access results
print(f"Trust Score: {result.judgment.trust_score}/10")
print(f"Verdict: {result.judgment.verdict}")
print(f"Red Flags: {result.judgment.red_flags}")
print(f"Tech Stack: {result.structured_data.tech_stack}")

# Convert to DB format
db_data = result.to_db_dict()

# Save to database
analysis = VacancyAnalysis(vacancy_id=vacancy_dict["id"], **db_data)
session.add(analysis)
```

### Processing Pipeline Integration

```python
from database.enums import VacancyStatus
from database.models import Vacancy, VacancyAnalysis

# Only analyze vacancies with EXTRACTED or VECTORIZED status
vacancies = session.query(Vacancy).filter(
    Vacancy.status.in_([VacancyStatus.EXTRACTED, VacancyStatus.VECTORIZED])
).all()

for vacancy in vacancies:
    try:
        result = await analyzer.analyze_vacancy(
            vacancy_dict={
                "id": vacancy.id,
                "title": vacancy.title,
                "company_name": vacancy.company.name,
                "description": vacancy.description
            }
        )
        
        # Save analysis
        analysis = VacancyAnalysis(vacancy_id=vacancy.id, **result.to_db_dict())
        session.add(analysis)
        
        # Update vacancy status
        vacancy.status = VacancyStatus.ANALYZED
        vacancy.last_analysis = analysis
        
        session.commit()
        
    except Exception as e:
        logger.error(f"Failed to analyze vacancy {vacancy.id}: {e}")
        vacancy.status = VacancyStatus.FAILED
        session.commit()
```

## Trust Score Semantics

**0:** Technical failure - Analysis error (see `error_message`); not a company rating  
**1-3:** Toxic/Dangerous - Major red flags, avoid  
**4-5:** Concerning - Multiple warnings, high risk  
**6-7:** Standard corporate - Proceed with caution  
**8-9:** Decent - Minor concerns, generally acceptable  
**10:** Perfect - Transparent, honest, excellent offer

**Higher score = Better company**

## Why Two Stages?

1. **Better Prompts** - Each stage has a focused task
2. **Cost Optimization** - Use cheap model for extraction, expensive for judgment
3. **Debugging** - See intermediate results
4. **Flexibility** - Can skip/retry stages independently
5. **Model Selection** - Different models for different tasks
6. **Few-Shot Learning** - Stage 2 uses golden examples to improve judgment quality

## Provider Architecture

The system uses an abstract `LLMProvider` interface, making it easy to swap providers:

```python
# Current: Google Gemini
provider = GeminiProvider(api_key="...")

# Future: OpenAI
provider = OpenAIProvider(api_key="...")

# Future: Anthropic
provider = AnthropicProvider(api_key="...")

# Same analyzer code works with any provider
analyzer = VacancyAnalyzer(provider)
```

## Few-Shot Learning

Stage 2 (The Demon Hunter) uses few-shot examples from `few_shots.py` to teach the model:
- How to detect legacy code traps
- How to identify burnout factories
- How to recognize good companies
- How to translate corporate speak to reality

Update `few_shots.py` as you discover new toxic patterns.

## Error Handling

The system provides granular exception handling:
- `ProviderError` - API failures (including safety filter blocks; see below)
- `ValidationError` - Schema validation failures
- `RateLimitError` - API rate limiting
- `ContentFilterError` - Reserved for safety filter blocks (Gemini currently raises `ProviderError` for blocked content)

On analysis failure, `analyze_vacancy` does not raise: it returns a `VacancyAnalysisResult` with `error_message` set, `trust_score=0`, and `verdict="Analysis Failed"`. Use `result.error_message` to detect failures.

## Implementation Status

✅ **Complete**
- Abstract provider interface
- Gemini provider implementation
- Two-stage analysis pipeline
- Few-shot learning system
- Error handling and logging
- Pydantic schemas
- System prompts

🔄 **Future Enhancements**
- OpenAI provider
- Anthropic provider
- Token usage tracking
- Retry logic with exponential backoff
- A/B testing for few-shot examples
- Confidence score calculation

