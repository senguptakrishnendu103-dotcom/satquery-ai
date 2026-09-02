"""
SatQuery AI - Data Sources Abstraction Module (Stage 1)

This package provides a clean, provider-agnostic abstraction layer for searching
and metadata extraction from external satellite data repositories.
"""

from app.data_sources.exceptions import (
    SatelliteProviderError,
    SatelliteSearchError,
    ProviderNotFoundError,
    InvalidSearchRequestError,
    DuplicateProviderError,
)
from app.data_sources.base_provider import (
    SearchRequest,
    SatelliteProduct,
    SatelliteDataProvider,
)
from app.data_sources.search_service import (
    SatelliteSearchService,
    satellite_search_service,
)
from app.data_sources.providers.copernicus_provider import CopernicusProvider

__all__ = [
    "SatelliteProviderError",
    "SatelliteSearchError",
    "ProviderNotFoundError",
    "InvalidSearchRequestError",
    "DuplicateProviderError",
    "SearchRequest",
    "SatelliteProduct",
    "SatelliteDataProvider",
    "SatelliteSearchService",
    "satellite_search_service",
    "CopernicusProvider",
]
