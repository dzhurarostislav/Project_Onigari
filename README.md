# Project Onigari (鬼狩り) 👹

<p align="center">
  <img src="鬼狩り.png" width="400" alt="Project Onigari Logo - Demon Hunter tool for job analysis">
</p>

This project is designed to aggregate vacancies from various job platforms and analyze them to distinguish between reputable companies and those with poor practices.

## Core Features
* **Aggregator:** Automatic scraping from Djinni, Dou, and LinkedIn (under development).
* **LLM Analytics:** AI-driven analysis of job descriptions to detect "red flags", toxic requirements, and hidden meanings.
* **Bullshit Detector:** Rating companies on a scale of 1-10 based on transparency and adequacy using **BGE-M3** embeddings.
* **Human-to-Human Translation:** Rewriting HR-speak into honest, plain language.

## Tech Stack
* **Language:** Python 3.11+ (Asynchronous)
* **Orchestration:** Docker & Docker Compose
* **LLM:** Ollama (Local GPU) / OpenAI / LangChain
* **Embedding Model:** BGE-M3 (1024 dimensions)
* **Database:** PostgreSQL + **pgvector** (for semantic search) & Redis

## Project Progress
- [x] Docker infrastructure & GPU passthrough for Ollama
- [x] Database schema & pgvector integration
- [x] Vacancy model with parsing status and HR fields
- [ ] Djinni scraper (In progress: Authentication stage)
- [ ] LLM Scoring engine