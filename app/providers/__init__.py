"""
Provider Layer for SatQuery AI.
"""

import os
from pathlib import Path

def _ensure_env_loaded():
    search_paths = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for p in search_paths:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass
            break

_ensure_env_loaded()

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
