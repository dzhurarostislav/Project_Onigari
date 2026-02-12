import logging
import re
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class VacancyVectorizer:
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        # Если есть GPU — используем её, иначе CPU
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"🧠 Loading {model_name} on {self.device}...")
        self.model = SentenceTransformer(
            model_name, 
            device=self.device, 
            model_kwargs={"torch_dtype": torch.float16}
        )

    def _clean_text(self, text: str) -> str:
        """Минимальная чистка: убираем лишние пробелы и мусор"""
        if not text:
            return ""
        # Заменяем любые последовательности пробельных символов на один пробел
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _prepare_input(self, vacancy) -> str:
        """Склеиваем заголовок и описание для лучшего контекста"""
        title = vacancy.title or ""
        company = vacancy.company.name if vacancy.company else ""
        if vacancy.last_snapshot:
            desc = self._clean_text(vacancy.last_snapshot.full_description)
        else:
            desc = self._clean_text(vacancy.description)
        return f"Вакансия: {title}. Компания: {company}. Описание: {desc}"

    async def process_vacancies(self, vacancies):
        """Превращает список моделей SQLAlchemy в векторы"""
        if not vacancies:
            return []

        # 1. Готовим тексты
        texts = [self._prepare_input(v) for v in vacancies]
        
        # 2. Генерируем эмбеддинги
        # BGE-M3 умеет в dense, sparse и multi-vector. Нам нужен dense (обычный вектор).
        embeddings = self.model.encode(
            texts, 
            batch_size=16, 
            show_progress_bar=False,
            convert_to_numpy=True
        )

        # 3. Формируем данные для БД
        return [
            {"b_id": v.id, "b_embedding": emb.tolist()} 
            for v, emb in zip(vacancies, embeddings)
        ]