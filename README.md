# Project Onigari (鬼狩り) 👹

<p align="center">
  <img src="鬼狩り.png" width="400" alt="Project Onigari Logo - Demon Hunter tool for job analysis">
</p>

This project aggregates vacancies from various job platforms and analyzes them to distinguish between reputable companies and those with poor practices.

## Core Features
* **Aggregator:** Automatic scraping from DOU, Djinni, and LinkedIn (planned).
* **LLM Analytics:** Two-stage AI pipeline (Investigator → Demon Hunter) to detect red flags, toxic requirements, and hidden meanings. **Google Gemini** with Pydantic-structured output; see `src/brain/README.md`.
* **Trust Score (1–10):** Onigari verdict per vacancy: trust score, red flags, toxic phrases, and final verdict (Safe/Risky/Avoid). Stored in `VacancyAnalysis`.
* **Human-to-Human Translation:** “Honest summary” — cynical, plain-language translation of HR-speak (part of the brain analysis output).
* **Semantic Search:** **BGE-M3** embeddings (1024d) for similarity search; status flow EXTRACTED → VECTORIZED (planned: pgvector queries).

## Tech Stack
* **Language:** Python 3.11+ (asynchronous)
* **Orchestration:** Docker & Docker Compose
* **LLM:** **Google Gemini** (brain module: abstract provider, Gemini implementation; planned: OpenAI, Anthropic, Ollama)
* **Embedding Model:** BGE-M3 (1024 dimensions) via `sentence-transformers`; GPU (CUDA) when available
* **Database:** PostgreSQL + **pgvector** (for semantic search) + JSONB
* **ORM:** SQLAlchemy 2.0 (async) + PostgreSQL `INSERT ... ON CONFLICT`
* **Validation / DTOs:** Pydantic (scrapers: `VacancyDTO`; brain: `VacancyStructuredData`, `VacancyJudgment`, `VacancyAnalysisResult`)
* **HTTP Client:** `curl-cffi` with Chrome impersonation
* **HTML Parsing:** `selectolax` (`LexborHTMLParser`)
* **Config:** `python-dotenv` + environment variables

## Project Structure
```
src/
├── main.py              # Entry point - orchestrates discovery & deep extraction cycles
├── run_vectorizer.py    # Standalone worker: EXTRACTED → BGE-M3 embeddings → VECTORIZED
├── config.py            # Configuration management (scraper configs, env)
├── database/
│   ├── enums.py         # Shared enums: VacancyStatus, SalaryPeriod, WorkFormat, etc.
│   ├── models.py        # SQLAlchemy models: Vacancy, VacancySnapshot, Company, Tag, SocialSignal, UserInteraction; pgvector, JSONB, statuses, hashing
│   ├── service.py       # VacancyRepository: upsert, deep-extraction, snapshot updates, batch_update_vectors
│   └── sessions.py      # Async database engine and session factory
├── scrapers/
│   ├── base.py          # BaseScraper: shared async HTTP/session logic
│   ├── schemas.py       # Pydantic DTOs: CompanyBase/Full, VacancyBase/Detail
│   ├── crawler.py       # DetailCrawler: deep extraction + VacancyStatus transitions
│   ├── dou/             # DOU.ua scraper (implemented)
│   │   ├── client.py    # DouScraper - async listing fetch + AJAX pagination
│   │   └── parser.py    # DouParser - list & detail parsing (VacancyBaseDTO / VacancyDetailDTO)
│   └── djinni/          # Djinni.co scraper (client ready, parser pending)
│       ├── client.py    # DjinniScraper - HTTP client (listing HTML)
│       └── parser.py    # Parser implementation pending
├── brain/
│   ├── README.md        # Two-stage analysis pipeline docs
│   ├── interfaces.py    # Abstract LLMProvider contract
│   ├── providers.py     # GeminiProvider (planned: OpenAI, Anthropic)
│   ├── exceptions.py    # AnalysisError, ProviderError, ValidationError, RateLimitError, ContentFilterError
│   ├── schemas.py       # Pydantic: VacancyStructuredData, VacancyJudgment, VacancyAnalysisResult
│   ├── prompts.py       # System/user prompts for Stage 1 (Investigator) & Stage 2 (Demon Hunter)
│   ├── few_shots.py     # Few-shot examples for Stage 2
│   ├── analyzer.py      # VacancyAnalyzer: two-stage pipeline (Investigator → Demon Hunter)
│   └── vectorizer.py    # VacancyVectorizer: BGE-M3 embeddings (title + company + description/snapshot)
└── utils/
    └── hashing.py       # SHA-256 based hash helpers (identity/content)
```

## Data Flow

- **Phase 1 – Discovery (list pages)**:  
  `DouScraper.fetch_vacancies()` is an async generator that yields batches of `VacancyBaseDTO`.  
  `VacancyRepository.batch_upsert()` upserts companies and inserts new vacancies with `VacancyStatus.NEW`, using `identity_hash` for deduplication.

- **Phase 2 – Deep extraction (detail pages)**:  
  `DetailCrawler` selects vacancies with status `NEW`, fetches full HTML via `DouScraper`, and uses `DouParser.parse_detail()` to build `VacancyDetailDTO`.  
  `VacancyRepository.update_vacancy_details()` creates a `VacancySnapshot`, updates the main vacancy fields, and switches status to `VacancyStatus.EXTRACTED`.

- **Phase 3 – Vectorization (optional worker)**:  
  `run_vectorizer.py` runs as a separate process: it loads `VacancyVectorizer` (BGE-M3 via `sentence-transformers`), fetches vacancies with status `EXTRACTED`, encodes title + company + full description (from `last_snapshot` or `description`), and calls `VacancyRepository.batch_update_vectors()` to write embeddings and set status to `VacancyStatus.VECTORIZED`.

- **Phase 4 – LLM analysis (optional)**:  
  For vacancies with status `EXTRACTED` or `VECTORIZED`, `VacancyAnalyzer` (see `src/brain/`) runs a two-stage pipeline: **Stage 1 (Investigator)** extracts structured data (tech stack, grade, salary, red-flag keywords); **Stage 2 (Demon Hunter)** produces a trust score (1–10), red flags, toxic phrases, honest summary, and verdict (Safe/Risky/Avoid). Results are stored in `VacancyAnalysis`; vacancy status can be set to `VacancyStatus.ANALYZED` and linked via `last_analysis_id`.

## Database Schema

**`Vacancy`** (current state of a job listing):
- Basic info: `title`, `short_description` (listing snippet), `description` (full text), `source_url`
- Company link: `company_id` → `Company`
- Attributes: `attributes` JSONB (tech stack, grade, seniority, etc.) with a GIN index for flexible search/filtering
- Salary: `salary_from`, `salary_to`, `salary_currency`, `salary_period`, `is_gross`
- Job terms: `work_format`, `employment_type`, `grade`, `languages`, `experience_min`, `requires_own_equipment`
- Location: `location_city`, `location_address`, `geo_lat`, `geo_lon`, `is_relocation_possible`
- HR & contacts: `hr_name`, `contacts` JSONB (email, Telegram, etc.)
- Embeddings: `embedding` (1024‑dim vector for BGE‑M3)
- Hashing & metadata: `external_id`, `identity_hash`, `content_hash` (optional), `status` (`VacancyStatus`: `new` → `extracted` → `vectorized` → `analyzed` / `archived` / `failed`), `created_at`, `updated_at`, `is_active`
- Snapshot link: `last_snapshot_id` → points to the latest `VacancySnapshot`; relationship `last_snapshot` / `snapshots` for history
- Analysis link: `last_analysis_id` → points to the latest `VacancyAnalysis`; relationship `last_analysis` / `analyses` for AI verdict history

**`VacancyAnalysis`** (LLM analysis results):
- Links to `Vacancy` via `vacancy_id`; vacancy has `last_analysis` / `analyses`
- Judgment: `trust_score` (0–10), `red_flags`, `toxic_phrases`, `honest_summary`, `verdict`
- Metadata: `model_name`, `provider`, `analysis_version`, `confidence_score`, `tokens_used`, `error_message`
- Timestamp: `created_at`; `is_current` for latest run per vacancy

**`VacancySnapshot`** (versioned history of a vacancy’s description):
- `vacancy_id` → `Vacancy`
- `full_description`, `content_hash`, `created_at`
- Used to track changes over time; each vacancy can have many snapshots and one current “last” snapshot

**`Company`**:
- Core info: `name`, `slug`, `description`, `website_url`
- Reputation: `overall_rating`, `is_blacklisted`, `is_verified`, `industry`, `size_range`
- Relations: `vacancies` (one-to-many), `tags` (many-to-many via `company_tags`), `signals` (one-to-many `SocialSignal`)

**`Tag`**:
- Core info: `name`, `category`
- Relations: `companies` (many-to-many via `company_tags`)

**`SocialSignal`**:
- Links external reviews/posts to a company (`company_id`, `source`, `source_url`, `content`)
- Analytics: `sentiment_score`, `is_verified`, `embedding` (for semantic search)

**`UserInteraction`**:
- Tracks user actions on vacancies: `status` (`UserInteractionStatus`), `notes`
- Links to `Vacancy` via `vacancy_id`

## Configuration
The project uses environment variables for configuration:
- `DATABASE_URL` - PostgreSQL connection string (or `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DB_HOST`, `DB_PORT` for async URL)
- `DOU_COOKIES` - Browser cookies for DOU.ua scraping
- `DOU_USER_AGENT` - User agent string for DOU requests
- `DJINNI_COOKIES` - Browser cookies for Djinni.co scraping
- `DJINNI_USER_AGENT` - User agent string for Djinni requests
- `DB_ECHO` - Enable SQL echo in logs when set to `"True"`
- **Brain (LLM):** Pass a Google AI API key when creating `GeminiProvider(api_key="...")`; you can use `GOOGLE_AI_API_KEY` from env for local runs.

For local development, these are loaded from `.env` via `python-dotenv`.

## Project Progress
- [x] Docker infrastructure with PostgreSQL + pgvector
- [x] Database schema & pgvector extension setup
- [x] Vacancy model with JSONB attributes, rich job metadata, hashing, statuses, HR fields, embedding field; `VacancySnapshot` for description history; `VacancyAnalysis` and `last_analysis` for LLM results
- [x] Base scraper architecture with async session management
- [x] DOU scraper (fully implemented: first page + AJAX pagination, parser, DTOs)
- [x] VacancyRepository with batch upsert & deduplication by `identity_hash`
- [x] Djinni scraper client (parser implementation pending)
- [x] BGE-M3 embedding pipeline: `brain/vectorizer.py` + `run_vectorizer.py` (EXTRACTED → VECTORIZED), `VacancyRepository.batch_update_vectors`
- [x] LLM analysis pipeline: two-stage brain (Investigator + Demon Hunter), Gemini provider, Pydantic schemas, few-shot learning; trust score, red flags, honest summary, verdict → `VacancyAnalysis`
- [ ] Semantic search (pgvector queries on `embedding`)
- [ ] LinkedIn scraper
- [ ] Optional: OpenAI/Anthropic providers, token usage tracking, retry/backoff

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)

### Setup
1. Clone the repository
2. Create a `.env` file with required environment variables (see Configuration section)
3. Build and run with Docker Compose:
   ```bash
   docker-compose up --build
   ```

The main bot (`main.py`) will:
- Initialize the PostgreSQL database with pgvector extension and create tables
- Run Phase 1 (Discovery) and Phase 2 (Deep extraction) in a loop every hour

To populate embeddings (Phase 3), run the vectorizer worker separately (e.g. on a machine with GPU):

```bash
# From project root, with PYTHONPATH=src and DB reachable (e.g. port 5435 for local Postgres)
python src/run_vectorizer.py
```

It processes vacancies with status `EXTRACTED`, computes BGE-M3 vectors, and sets them to `VECTORIZED`.

To run the LLM analysis pipeline (Phase 4), use `VacancyAnalyzer` from `brain.analyzer` with a `GeminiProvider`; see **`src/brain/README.md`** for usage, schemas, and status flow (e.g. EXTRACTED/VECTORIZED → ANALYZED, results in `VacancyAnalysis`).