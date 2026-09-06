"""
Provider Exception Hierarchy for SatQuery AI.
"""

class ProviderError(Exception):
    """Base exception for all satellite data provider operations."""
    pass


class ProviderAuthError(ProviderError):
    """Raised when authentication against the provider fails or credentials are invalid."""
    pass


class ProviderRateLimitError(ProviderError):
    """Raised when provider rate limits are exceeded (e.g. HTTP 429)."""
    pass


class ProductNotFoundError(ProviderError):
    """Raised when the requested product does not exist on the provider."""
    pass


class ProductNotAvailableError(ProviderError):
    """Raised when the product is catalogue-only / order-only and not directly downloadable."""
    pass


class ProviderNetworkError(ProviderError):
    """Raised when communication with provider times out or fails at network level."""
    pass


class InvalidSearchRequestError(ProviderError):
    """Raised when search parameters (BBox, Date, Collection) are invalid."""
    pass
