FROM python:3.11-slim

# Не даем Python писать .pyc файлы и буферизировать вывод (важно для логов в Docker)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Ставим системные зависимости для парсинга (если понадобятся)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Кэшируем установку библиотек
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app/src

CMD ["python", "src/main.py"]
