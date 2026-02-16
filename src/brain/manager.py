import logging
from typing import Type, TypeVar

from pydantic import BaseModel

from brain.exceptions import AnalysisError, ProviderError, RateLimitError
from brain.interfaces import LLMProvider

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class SmartChainProvider(LLMProvider):
    """
    Smart request router.
    Tries to use providers in order of priority.
    Automatically skips 'sick' (on cooldown).
    """

    def __init__(self, providers: list[LLMProvider]):
        if not providers:
            raise ValueError("SmartChainProvider needs at least one provider!")
        self.providers = providers
        self._last_used_provider: LLMProvider | None = None

    @property
    def provider_name(self) -> str:
        """Returns the name of the provider that worked last, or the name of the first in the list."""
        if self._last_used_provider:
            return f"chain -> {self._last_used_provider.provider_name}"
        return "chain -> pending"

    @property
    def model_name(self) -> str:
        """Returns the model of the last successful provider."""
        if self._last_used_provider:
            return self._last_used_provider.model_name
        return "multi-model"

    def is_healthy(self) -> bool:
        return any(p.is_healthy() for p in self.providers)

    def mark_failed(self) -> None:
        pass  # Chain cannot be "killed" entirely from the outside

    async def analyze(self, user_prompt: str, system_instruction: str, schema: Type[T]) -> tuple[T, int]:
        # We start each request by looking for the highest priority HEALTHY provider
        for provider in self.providers:
            # 1. Health check (Cooldown)
            if not provider.is_healthy():
                logger.debug(f"⏭️ {provider.provider_name} on cooldown, skipping...")
                continue

            try:
                # 2. Attempt analysis
                result, tokens = await provider.analyze(user_prompt, system_instruction, schema)

                # 3. Success! Remember the hero
                self._last_used_provider = provider
                return result, tokens

            except (RateLimitError, ProviderError) as e:
                logger.warning(f"⚠️ {provider.provider_name} failed: {e}. Switching...")

                # If the provider didn't mark itself (e.g., network error, not 429),
                # we force it into a knockout.
                provider.mark_failed()
                continue

        # If the loop ended and there's no result
        raise AnalysisError("💀 Total collapse: all providers are dead or on cooldown.")
