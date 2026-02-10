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
* **Embedding Model:** BGE-M3 (1024 dimensions) – planned, DB field already reserved
* **Database:** PostgreSQL + **pgvector** (for semantic search) + JSONB
* **ORM:** SQLAlchemy 2.0 (async) + PostgreSQL `INSERT ... ON CONFLICT`
* **Validation / DTOs:** Pydantic models for `VacancyDTO`
* **HTTP Client:** `curl-cffi` with Chrome impersonation
* **HTML Parsing:** `selectolax` (`LexborHTMLParser`)
* **Config:** `python-dotenv` + environment variables

## Project Structure
```
src/
├── main.py              # Entry point - sets up DB and runs scrapers
├── config.py            # Configuration management (scraper configs)
├── database/
│   ├── models.py        # SQLAlchemy models (Vacancy with pgvector, JSONB, hashing fields)
│   ├── service.py       # VacancyRepository: batch upsert with deduplication
│   └── sessions.py      # Async database engine and session factory
├── scrapers/
│   ├── base.py          # BaseScraper abstract class with session management
│   ├── schemas.py       # Shared Pydantic VacancyDTO for all scrapers
│   ├── dou/             # DOU.ua scraper (fully implemented)
│   │   ├── client.py    # DouScraper - HTTP client + AJAX pagination
│   │   └── parser.py    # DouParser - HTML parsing logic
│   └── djinni/          # Djinni.co scraper (client ready, parser pending)
│       ├── client.py    # DjinniScraper - HTTP client
│       └── parser.py    # Parser implementation pending
├── brain/
│   └── analyzer.py      # LLM analysis engine (planned)
└── utils/
    └── hashing.py       # SHA-256 based vacancy hash generator
```

## Database Schema
The `Vacancy` model includes:
- Basic info: `title`, `company_name`, `description`, `url`
- Tech stack: `tech_stack` (JSONB) with a GIN index for flexible search/filtering
- Salary: `salary_from`, `salary_to` (optional)
- HR info: `hr_name`, `hr_link` (optional)
- Embeddings: `embedding` (1024‑dim vector, reserved for BGE‑M3)
- Hashing & metadata: `external_id`, `identity_hash`, `content_hash` (optional), `is_parsed`, `created_at`

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
- [x] Vacancy model with JSONB tech stack, hashing, parsing status, HR fields, and embedding field
- [x] Base scraper architecture with async session management
- [x] DOU scraper (fully implemented: first page + AJAX pagination, parser, DTOs)
- [x] VacancyRepository with batch upsert & deduplication by `identity_hash`
- [x] Djinni scraper client (parser implementation pending)
- [ ] LLM Scoring engine (`brain/analyzer.py`)
- [ ] BGE-M3 embedding generation and semantic search
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

The bot will:
- Initialize the PostgreSQL database with pgvector extension
- Create database tables
- Run scrapers in a loop (currently fetches DOU vacancies every hour)