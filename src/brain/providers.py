"""
LLM provider implementations.

Currently supports Google Gemini with native JSON schema validation.
Future providers: OpenAI, Anthropic, local models.
"""

import logging
from typing import Type, TypeVar

import google.generativeai as genai
from pydantic import BaseModel

from brain.exceptions import ProviderError, RateLimitError, ValidationError
from brain.interfaces import LLMProvider

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(LLMProvider):
    """
    Google Gemini implementation with native JSON schema support.
    
    Uses Gemini's 'response_schema' feature for bulletproof structured output.
    No need for manual JSON parsing or retry logic - the model is forced to
    return valid JSON matching the Pydantic schema.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Google AI API key
            model_name: Model to use (default: gemini-1.5-flash for speed/cost)
        """
        genai.configure(api_key=api_key)
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

    async def analyze(
        self, 
        user_prompt: str, 
        system_instruction: str, 
        schema: Type[T]
    ) -> T:
        """
        Analyze text using Gemini with strict JSON schema validation.
        
        Args:
            user_prompt: The main input content
            system_instruction: The persona/rules for this specific task
            schema: Pydantic model class to enforce output structure
            
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
            model = genai.GenerativeModel(
                model_name=self._model_name,
                system_instruction=system_instruction
            )

            # Configure strict JSON output with schema validation
            generation_config = genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=schema
            )

            # Safety settings: Allow analysis of potentially toxic content
            # We MUST analyze aggressive/manipulative vacancy text without being blocked
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

            logger.debug(f"Calling Gemini API with schema: {schema.__name__}")

            # Generate content asynchronously
            response = await model.generate_content_async(
                user_prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )

            # Validate and return Pydantic object
            # Gemini usually returns valid JSON, but we validate just in case
            result = schema.model_validate_json(response.text)
            
            logger.debug(f"Successfully validated response as {schema.__name__}")
            return result

        except genai.types.generation_types.BlockedPromptException as e:
            logger.error(f"Content blocked by safety filters: {e}")
            raise ProviderError(f"Content blocked by Gemini safety filters: {e}")

        except genai.types.generation_types.StopCandidateException as e:
            logger.error(f"Generation stopped: {e}")
            raise ProviderError(f"Gemini stopped generation: {e}")

        except Exception as e:
            # Check if it's a rate limit error
            if "quota" in str(e).lower() or "rate limit" in str(e).lower():
                logger.error(f"Rate limit exceeded: {e}")
                raise RateLimitError(f"Gemini API rate limit exceeded: {e}")
            
            # Check if it's a validation error
            if "validation" in str(e).lower():
                logger.error(f"Schema validation failed: {e}")
                raise ValidationError(f"Response doesn't match schema {schema.__name__}: {e}")
            
            # Generic provider error
            logger.error(f"Gemini API error: {e}", exc_info=True)
            raise ProviderError(f"Gemini API call failed: {e}")


# Future providers can be added here following the same interface:
# class OpenAIProvider(LLMProvider):
#     async def analyze(self, user_prompt, system_instruction, schema):
#         # Use OpenAI's structured output feature
#         pass
