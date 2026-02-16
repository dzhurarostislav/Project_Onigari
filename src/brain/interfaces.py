"""
Abstract interfaces for LLM providers.

This module defines the contract that all LLM providers must implement,
ensuring consistent behavior across different AI services (Google, OpenAI, Anthropic, etc.).
"""

from abc import ABC, abstractmethod
from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """
    Abstract contract for any LLM provider used in the Onigari project.

    All providers must support structured output via Pydantic schemas,
    ensuring type-safe and validated responses from the AI models.

    This abstraction allows easy switching between providers without
    changing the analyzer logic.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Return the name of the model being used.

        Examples: 'gemini-1.5-flash', 'gpt-4o', 'claude-3-opus'
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Return the provider name.

        Examples: 'google', 'openai', 'anthropic'
        """
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if the provider is healthy.
        Returns False if the provider recently failed (rate limit / 5xx).
        """
        pass

    @abstractmethod
    def mark_failed(self):
        """
        Mark the provider as unhealthy (e.g., after rate limit or 5xx error).
        """
        pass

    @abstractmethod
    async def analyze(self, user_prompt: str, system_instruction: str, schema: Type[T]) -> tuple[T, int]:
        """
        Analyze text and return strict JSON validated by the provided schema.

        Args:
            user_prompt: The main input content to analyze.
            system_instruction: The persona/rules/context for the model.
            schema: Pydantic model class to enforce output structure.

        Returns:
            An instance of the schema class with validated data and tokens used.

        Raises:
            ProviderError: If the API call fails.
            ValidationError: If the response doesn't match the schema.
        """
        pass
