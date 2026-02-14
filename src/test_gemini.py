import asyncio
import os
from google import genai
from dotenv import load_dotenv

# Загружаем переменные из твоего .env
load_dotenv()

async def test_connection():
    # 1. Проверяем наличие ключа в окружении
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ ОШИБКА: Ключ GEMINI_API_KEY не найден в .env файле!")
        return

    print(f"📡 Попытка подключения с ключом: {api_key[:5]}...{api_key[-5:]}")
    
    try:
        # 2. Инициализируем клиент (как в твоем провайдере)
        client = genai.Client(api_key=api_key)
        
        # 3. Простейший запрос к Flash-модели
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents="Ответь одним словом: Охота началась?"
        )
        
        if response.text:
            print(f"✅ УСПЕХ! Ответ от модели: {response.text.strip()}")
        else:
            print("⚠️ Странно: Ответ пустой, но ошибки нет.")
            
    except Exception as e:
        print(f"💥 КАТАСТРОФА: Ошибка при запросе!")
        print(f"Текст ошибки: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())