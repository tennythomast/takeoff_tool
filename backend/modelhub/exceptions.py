class LLMError(Exception):
    """Base class for LLM-related errors"""
    pass


class ProviderError(LLMError):
    """Base class for provider-specific errors"""
    def __init__(self, message: str, provider: str, status_code: int = None, raw_error: dict = None):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.raw_error = raw_error or {}


class QuotaExceededError(ProviderError):
    """Raised when provider quota/rate limit is exceeded"""
    pass


class InvalidRequestError(ProviderError):
    """Raised when request is invalid (e.g., malformed prompt)"""
    pass


class AuthenticationError(ProviderError):
    """Raised when API key is invalid"""
    pass


class ContextLengthError(ProviderError):
    """Raised when input exceeds model's context length"""
    pass


class NoValidModelError(LLMError):
    """Raised when no valid model can be found for the request"""
    pass


class NoValidAdapterError(LLMError):
    """Raised when no valid adapter is found for a provider"""
    pass
