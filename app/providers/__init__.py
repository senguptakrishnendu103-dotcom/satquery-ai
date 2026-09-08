"""
Provider Layer for SatQuery AI.
"""

from app.providers.base import (
    AssetMetadata,
    DownloadResult,
    ProductMetadata,
    SatelliteDataProvider,
    SearchRequest,
    SearchResponse,
)
from app.providers.bhoonidhi import BhoonidhiProvider
from app.providers.cdse import CDSEProvider
from app.providers.exceptions import (
    InvalidSearchRequestError,
    ProductNotAvailableError,
    ProductNotFoundError,
    ProviderAuthError,
    ProviderError,
    ProviderNetworkError,
    ProviderRateLimitError,
)
from app.providers.registry import get_provider, list_providers, register_provider

__all__ = [
    "SatelliteDataProvider",
    "BhoonidhiProvider",
    "CDSEProvider",
    "SearchRequest",
    "SearchResponse",
    "ProductMetadata",
    "AssetMetadata",
    "DownloadResult",
    "ProviderError",
    "ProviderAuthError",
    "ProviderRateLimitError",
    "ProductNotFoundError",
    "ProductNotAvailableError",
    "ProviderNetworkError",
    "InvalidSearchRequestError",
    "get_provider",
    "list_providers",
    "register_provider",
]
