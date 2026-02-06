# Project Onigari (鬼狩り)

![Logo](<p align="center">
  <img src="鬼狩り.png" width="400" alt="Onigari Logo">
</p>)

## Description
This project is designed to aggregate vacancies from various job platforms and analyze them to distinguish between reputable companies and those with poor practices.

## Core Features
* **Aggregator**: Automatic scraping from Djinni, Dou, and LinkedIn.
* **LLM Analytics**: AI-driven analysis of job descriptions to detect "red flags", toxic requirements, and hidden meanings.
* **Bullshit Detector**: Rating companies on a scale of 1-10 based on transparency and adequacy.
* **Human-to-Human Translation**: Rewriting HR-speak into honest, plain language.

## Tech Stack
* **Language**: Python 3.11+
* **Orchestration**: Docker & Docker Compose
* **LLM**: LangChain / OpenAI / Ollama
* **Database**: PostgreSQL & Redis
