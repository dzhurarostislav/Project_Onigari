"""
Custom exceptions for the brain analysis module.

Provides granular error handling for different failure scenarios
in the LLM analysis pipeline.
"""


class AnalysisError(Exception):
    """Base exception for all analysis-related errors."""

    pass


class ProviderError(AnalysisError):
    """
    Raised when an LLM provider API call fails.

    Examples:
    - Network errors
    - Authentication failures
    - API timeouts
    - Service unavailable
    """

    pass


class ValidationError(AnalysisError):
    """
    Raised when LLM response doesn't match the expected Pydantic schema.

    This indicates the model returned invalid JSON or missing required fields.
    """

    pass


class RateLimitError(ProviderError):
    """
    Raised when API rate limits are exceeded.

    Should trigger retry logic with exponential backoff.
    """

    pass


class ContentFilterError(ProviderError):
    """
    Raised when content is blocked by provider's safety filters.

    Some vacancy descriptions might trigger content filters
    (e.g., mentions of weapons, adult content, etc.).
    """

    pass
