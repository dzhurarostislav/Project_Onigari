"""
LLM provider implementations.

Currently supports Google Gemini with native JSON schema validation.
Future providers: OpenAI, Anthropic, local models.
"""

import asyncio
import logging
import time
from functools import wraps
from typing import Type, TypeVar

import openai
from google import genai
from google.genai import errors, types
from openai import AsyncOpenAI
from pydantic import BaseModel

from brain.exceptions import ProviderError, RateLimitError, ValidationError
from brain.interfaces import LLMProvider

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def retry_on_rate_limit(retries: int = 3, base_delay: float = 60.0, catch_exceptions: tuple = (Exception,)):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except catch_exceptions as e:
                    # Проверяем, действительно ли это ошибка лимитов (429)
                    err_msg = str(e).lower()
                    if "429" in err_msg or "quota" in err_msg or "rate_limit" in err_msg:
                        wait_time = base_delay * (attempt + 1)
                        logging.warning(f"⏳ Rate Limit detected. Waiting {wait_time}s... (Attempt {attempt + 1})")
                        await asyncio.sleep(wait_time)
                        continue
                    # Если это другая ошибка из пойманных — пробрасываем дальше
                    raise e
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class BaseProvider:
    """Общая логика 'здоровья' для всех ИИ-движков."""

    def __init__(self, cooldown: int = 60):
        self._last_failure_time = 0.0
        self._cooldown_period = cooldown

    def mark_failed(self) -> None:
        self._last_failure_time = time.time()
        logger.warning(f"⚠️ {self.provider_name} захлебнулся. Остываем {self._cooldown_period}с.")

    def is_healthy(self) -> bool:
        return (time.time() - self._last_failure_time) > self._cooldown_period


class GeminiProvider(BaseProvider, LLMProvider):
    """
    Google Gemini implementation with native JSON schema support.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        """
        Initialize Gemini provider.

        Args:
            api_key: Google AI API key
            model_name: Model to use (default: gemini-1.5-flash for speed/cost)
        """
        super().__init__(cooldown=60)
        self.client = genai.Client(api_key=api_key)
        self._model_name = model_name
        logger.info(f"Initialized GeminiProvider with model: {model_name}")

    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return self._model_name

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "google"

    @retry_on_rate_limit(retries=3, base_delay=60.0, catch_exceptions=(errors.ClientError, errors.APIError))
    async def analyze(self, user_prompt: str, system_instruction: str, schema: Type[T]) -> tuple[T, int]:
        """
        Analyze text using Gemini with strict JSON schema validation.

        Returns:
            Validated Pydantic object and tokens used

        Raises:
            ProviderError: If API call fails
            ValidationError: If response doesn't match schema
            RateLimitError: If rate limit exceeded
        """
        try:
            # Initialize model with task-specific persona
            # We create a new model instance for each call because
            # system_instruction changes between stages (Investigator vs Demon Hunter)
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=schema,
                safety_settings=[
                    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                ],
            )

            logger.debug(f"Calling Gemini API with schema: {schema.__name__}")

            # Generate content asynchronously
            response = await self.client.aio.models.generate_content(
                model=self._model_name, contents=user_prompt, config=config
            )

            usage = response.usage_metadata
            total_tokens = usage.total_token_count if usage else 0
            logger.info(
                f"📊 Расход: Prompt={usage.prompt_token_count}, "
                f"Candidates={usage.candidates_token_count}, "
                f"Total={usage.total_token_count}"
            )

            # Validate and return Pydantic object
            # Gemini usually returns valid JSON, but we validate just in case
            result = schema.model_validate_json(response.text)

            logger.debug(f"Successfully validated response as {schema.__name__}")
            return result, total_tokens

        except errors.ClientError as e:
            # Ловит 4xx ошибки (включая 429 Rate Limit)
            err_msg = str(e).lower()
            if "429" in err_msg or "quota" in err_msg:
                self.mark_failed()
                raise RateLimitError(f"Gemini Rate Limit: {e}")
            raise ProviderError(f"Gemini Client Error: {e}")

        except errors.APIError as e:
            # Ловит 5xx ошибки сервера
            raise ProviderError(f"Gemini Server Failure: {e}")

        except Exception as e:
            if "validation" in str(e).lower():
                raise ValidationError(f"Schema mismatch: {e}")
            raise ProviderError(f"Unexpected failure: {e}")


class OpenAIProvider(BaseProvider, LLMProvider):
    """
    OpenAI implementation using Structured Outputs (beta.chat.completions.parse).
    """

    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model_name: Model to use (default: gpt-4o-mini for efficiency)
        """
        super().__init__(cooldown=60)
        self.client = AsyncOpenAI(api_key=api_key)
        self._model_name = model_name
        logger.info(f"Initialized OpenAIProvider with model: {model_name}")

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def provider_name(self) -> str:
        return "openai"

    @retry_on_rate_limit(3, 30, catch_exceptions=(openai.RateLimitError, openai.APIStatusError))
    async def analyze(self, user_prompt: str, system_instruction: str, schema: Type[T]) -> tuple[T, int]:
        """
        Analyze text using OpenAI with strict Pydantic schema validation.

        Returns:
            Validated Pydantic object and tokens used

        Raises:
            ProviderError: If API call fails
            ValidationError: If response doesn't match schema
            RateLimitError: If rate limit exceeded
        """
        try:
            logger.debug(f"Calling OpenAI API ({self._model_name}) with schema: {schema.__name__}")

            # Используем .beta.chat.completions.parse для автоматической валидации Pydantic
            response = await self.client.beta.chat.completions.parse(
                model=self._model_name,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=schema,
            )

            # Извлекаем использование токенов
            usage = response.usage
            total_tokens = usage.total_tokens if usage else 0
            logger.info(
                f"📊 [OpenAI] Расход: Prompt={usage.prompt_tokens}, "
                f"Completion={usage.completion_tokens}, "
                f"Total={total_tokens}"
            )

            # response.choices[0].message.parsed уже является объектом твоего класса schema
            result = response.choices[0].message.parsed

            if result is None:
                # Это случается, если модель отказалась отвечать из-за контентных фильтров
                refusal = response.choices[0].message.refusal
                raise ProviderError(f"OpenAI refusal: {refusal}")

            logger.debug("Successfully received validated response from OpenAI")
            return result, total_tokens

        except openai.RateLimitError as e:
            self.mark_failed()
            raise RateLimitError(f"OpenAI Rate Limit exceeded: {e}")

        except openai.APIStatusError as e:
            # Ловим 4xx и 5xx ошибки
            err_msg = str(e).lower()
            if "429" in err_msg:
                self.mark_failed()
                raise RateLimitError(f"OpenAI Quota/Rate Limit: {e}")
            raise ProviderError(f"OpenAI API Error ({e.status_code}): {e.message}")

        except openai.APIConnectionError as e:
            raise ProviderError(f"OpenAI Connection Error: {e}")

        except Exception as e:
            if "validation" in str(e).lower():
                raise ValidationError(f"OpenAI Schema mismatch: {e}")
            raise ProviderError(f"Unexpected failure in OpenAIProvider: {e}")


# Future providers can be added here following the same interface:
# class AnthropicProvider(LLMProvider):
#     async def analyze(self, user_prompt, system_instruction, schema):
#         # Use Anthropic's structured output feature
#         pass
