# Project Onigari (鬼狩り) 👹

<p align="center">
  <img src="鬼狩り.png" width="400" alt="Project Onigari Logo - Demon Hunter tool for job analysis">
</p>

This project aggregates vacancies from various job platforms and analyzes them to distinguish between reputable companies and those with poor practices.

## Core Features
* **Aggregator:** Automatic scraping from DOU, Djinni, and LinkedIn (planned).
* **LLM Analytics:** AI-driven analysis of job descriptions to detect "red flags", toxic requirements, and hidden meanings (planned).
* **Bullshit Detector:** Rating companies on a scale of 1-10 based on transparency and adequacy using **BGE-M3** embeddings (planned).
* **Human-to-Human Translation:** Rewriting HR-speak into honest, plain language (planned).

## Tech Stack
* **Language:** Python 3.11+ (asynchronous)
* **Orchestration:** Docker & Docker Compose
* **LLM:** LangChain / OpenAI (planned: Ollama with local GPU)
* **Embedding Model:** BGE-M3 (1024 dimensions) via `sentence-transformers`; GPU (CUDA) when available
* **Database:** PostgreSQL + **pgvector** (for semantic search) + JSONB
* **ORM:** SQLAlchemy 2.0 (async) + PostgreSQL `INSERT ... ON CONFLICT`
* **Validation / DTOs:** Pydantic models for `VacancyDTO`
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
│   ├── vectorizer.py    # VacancyVectorizer: BGE-M3 embeddings (title + company + description/snapshot)
│   └── analyzer.py      # LLM analysis engine (planned)
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
- `DATABASE_URL` - PostgreSQL connection string
- `DOU_COOKIES` - Browser cookies for DOU.ua scraping
- `DOU_USER_AGENT` - User agent string for DOU requests
- `DJINNI_COOKIES` - Browser cookies for Djinni.co scraping
- `DJINNI_USER_AGENT` - User agent string for Djinni requests
- `DB_ECHO` - Enable SQL echo in logs when set to `"True"`

For local development, these are loaded from `.env` via `python-dotenv`.

## Project Progress
- [x] Docker infrastructure with PostgreSQL + pgvector
- [x] Database schema & pgvector extension setup
- [x] Vacancy model with JSONB attributes, rich job metadata, hashing, statuses, HR fields, embedding field; `VacancySnapshot` for description history
- [x] Base scraper architecture with async session management
- [x] DOU scraper (fully implemented: first page + AJAX pagination, parser, DTOs)
- [x] VacancyRepository with batch upsert & deduplication by `identity_hash`
- [x] Djinni scraper client (parser implementation pending)
- [x] BGE-M3 embedding pipeline: `brain/vectorizer.py` + `run_vectorizer.py` (EXTRACTED → VECTORIZED), `VacancyRepository.batch_update_vectors`
- [ ] LLM Scoring engine (`brain/analyzer.py`)
- [ ] Semantic search (pgvector queries on `embedding`)
- [ ] LinkedIn scraper
- [ ] Human-to-Human translation feature

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