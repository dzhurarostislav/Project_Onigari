"""
LLM provider implementations.

Currently supports Google Gemini with native JSON schema validation.
Future providers: OpenAI, Anthropic, local models.
"""

import logging
from typing import Type, TypeVar

from functools import wraps
import asyncio

from google import genai
from google.genai import types, errors

from pydantic import BaseModel

from brain.context import tokens_counter
from brain.exceptions import ProviderError, RateLimitError, ValidationError
from brain.interfaces import LLMProvider

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

def retry_on_rate_limit(retries: int = 3, base_delay: float = 5.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except errors.ClientError as e:
                    if "429" in str(e) or "quota" in str(e).lower():
                        # Для 15 RPM задержка в 5-10 секунд — это глоток воздуха
                        wait_time = base_delay * (attempt + 1) 
                        logger.warning(f"⏳ Лимит (15 RPM). Ждем {wait_time}с... (Попытка {attempt + 1})")
                        await asyncio.sleep(wait_time)
                        continue
                    raise e
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class GeminiProvider(LLMProvider):
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
    
    @retry_on_rate_limit(retries=3, base_delay=60.0)
    async def analyze(
        self, 
        user_prompt: str, 
        system_instruction: str, 
        schema: Type[T]
    ) -> T:
        """
        Analyze text using Gemini with strict JSON schema validation.

        Returns:
            Validated Pydantic object

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
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="BLOCK_NONE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="BLOCK_NONE"
                    ),
                ]
            )

            logger.debug(f"Calling Gemini API with schema: {schema.__name__}")

            # Generate content asynchronously
            response = await self.client.aio.models.generate_content(
                model=self._model_name,
                contents=user_prompt,
                config=config
            )

            usage = response.usage_metadata
            total_tokens = usage.total_token_count if usage else 0
            tokens_counter.set(tokens_counter.get() + total_tokens)
            logger.info(
                f"📊 Расход: Prompt={usage.prompt_token_count}, "
                f"Candidates={usage.candidates_token_count}, "
                f"Total={usage.total_token_count}"
            )

            # Validate and return Pydantic object
            # Gemini usually returns valid JSON, but we validate just in case
            result = schema.model_validate_json(response.text)
            
            logger.debug(f"Successfully validated response as {schema.__name__}")
            return result


        except errors.ClientError as e:
            # Ловит 4xx ошибки (включая 429 Rate Limit)
            err_msg = str(e).lower()
            if "429" in err_msg or "quota" in err_msg:
                raise RateLimitError(f"Gemini Rate Limit: {e}")
            raise ProviderError(f"Gemini Client Error: {e}")

        except errors.APIError as e:
            # Ловит 5xx ошибки сервера
            raise ProviderError(f"Gemini Server Failure: {e}")

        except Exception as e:
            if "validation" in str(e).lower():
                raise ValidationError(f"Schema mismatch: {e}")
            raise ProviderError(f"Unexpected failure: {e}")


# Future providers can be added here following the same interface:
# class OpenAIProvider(LLMProvider):
#     async def analyze(self, user_prompt, system_instruction, schema):
#         # Use OpenAI's structured output feature
#         pass
