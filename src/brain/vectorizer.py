import logging
import re

import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class VacancyVectorizer:
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        # Use GPU if available, else CPU
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"🧠 Loading {model_name} on {self.device}...")
        self.model = SentenceTransformer(model_name, device=self.device, model_kwargs={"torch_dtype": torch.float16})
        self.model.max_seq_length = 1024
        logger.info(f"📏 Max sequence length set to {self.model.max_seq_length}")

    def _clean_text(self, text: str) -> str:
        """Basic text cleaning: remove redundant whitespace."""
        if not text:
            return ""
        # Replace all whitespace sequences with a single space
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _prepare_input(self, vacancy) -> str:
        """Merge title and description for improved context."""
        title = vacancy.title or ""
        company = vacancy.company.name if vacancy.company else ""
        raw_desc = (
            vacancy.description
            or (vacancy.last_snapshot.full_description if vacancy.last_snapshot else None)
            or vacancy.short_description
            or ""
        )
        desc = self._clean_text(raw_desc)
        return f"Represent this vacancy for retrieval; Title: {title}; Company: {company}; Description: {desc}"

    async def process_vacancies(self, vacancies):
        """Convert SQLAlchemy models to vectors."""
        if not vacancies:
            return []

        # Prepare texts
        texts = [self._prepare_input(v) for v in vacancies]

        # BGE-M3 supports dense, sparse, and multi-vector. Using dense embeddings.
        embeddings = self.model.encode(texts, batch_size=16, show_progress_bar=False, convert_to_numpy=True)

        # Prepare data for DB
        return [{"b_id": v.id, "b_embedding": emb.tolist()} for v, emb in zip(vacancies, embeddings)]
