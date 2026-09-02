"""
Satellite Search Service Module for SatQuery AI.

This module provides a provider-independent orchestration service (`SatelliteSearchService`)
that registers satellite data providers, validates incoming search requests, and routes
queries to the appropriate provider.
"""

import logging
from typing import Dict, List, Any, Union, Optional

from app.data_sources.base_provider import (
    SatelliteDataProvider,
    SearchRequest,
    SatelliteProduct,
)
from app.data_sources.providers.copernicus_provider import CopernicusProvider
from app.data_sources.exceptions import (
    ProviderNotFoundError,
    DuplicateProviderError,
    InvalidSearchRequestError,
)

logger = logging.getLogger("satquery.data_sources.search_service")


class SatelliteSearchService:
    """
    Provider-independent Satellite Search Service.

    Manages provider registration, request validation, and query dispatching
    across multiple remote-sensing data sources.
    """

    def __init__(self):
        self._providers: Dict[str, SatelliteDataProvider] = {}

    def register_provider(
        self,
        provider: SatelliteDataProvider,
        replace: bool = False
    ) -> None:
        """
        Register a satellite data provider with the service.

        Args:
            provider: Instance of a class implementing SatelliteDataProvider.
            replace: If True, overwrite an existing provider registered under the same name.

        Raises:
            TypeError: If provider does not inherit from SatelliteDataProvider.
            DuplicateProviderError: If a provider with the same name is already registered and replace is False.
        """
        if not isinstance(provider, SatelliteDataProvider):
            raise TypeError(
                f"Provider must be an instance of SatelliteDataProvider. Got '{type(provider).__name__}'."
            )

        provider_name = provider.name.lower().strip()

        if provider_name in self._providers and not replace:
            raise DuplicateProviderError(
                f"Provider '{provider_name}' is already registered. Set replace=True to overwrite."
            )

        self._providers[provider_name] = provider
        logger.info(
            "Registered satellite data provider: '%s' (collections: %s)",
            provider_name,
            provider.supported_collections
        )

    def get_provider(self, name: str) -> SatelliteDataProvider:
        """
        Retrieve a registered provider by name.

        Args:
            name: Provider name string (case-insensitive).

        Returns:
            SatelliteDataProvider instance.

        Raises:
            ProviderNotFoundError: If provider is not registered.
        """
        if not name or not isinstance(name, str):
            raise ProviderNotFoundError("Provider name must be a non-empty string.")

        provider_key = name.lower().strip()
        if provider_key not in self._providers:
            available = list(self._providers.keys())
            raise ProviderNotFoundError(
                f"Provider '{name}' is not registered. Available providers: {available}"
            )
        return self._providers[provider_key]

    def list_providers(self) -> List[Dict[str, Any]]:
        """
        List all currently registered providers and their metadata.

        Returns:
            List of dictionaries containing provider details.
        """
        return [
            {
                "name": p.name,
                "supported_collections": p.supported_collections,
                "supported_modalities": p.supported_modalities,
            }
            for p in self._providers.values()
        ]

    def search(
        self,
        provider: str,
        request: Union[SearchRequest, Dict[str, Any]]
    ) -> List[SatelliteProduct]:
        """
        Validate search request and search satellite products through the specified provider.

        Args:
            provider: Name of the registered provider to search (e.g., 'copernicus').
            request: SearchRequest object or dictionary matching search request parameters.

        Returns:
            List of SatelliteProduct metadata objects.

        Raises:
            ProviderNotFoundError: If the specified provider is not registered.
            InvalidSearchRequestError: If the search request validation fails.
            SatelliteSearchError: If search execution fails at the provider layer.
        """
        logger.info("Received search request targeting provider '%s'.", provider)

        # 1. Validate request structure
        if isinstance(request, dict):
            try:
                search_req = SearchRequest(**request)
            except InvalidSearchRequestError:
                raise
            except Exception as e:
                raise InvalidSearchRequestError(f"Failed to parse search request parameters: {str(e)}")
        elif isinstance(request, SearchRequest):
            search_req = request
        else:
            raise InvalidSearchRequestError(
                f"Request must be a SearchRequest instance or dict. Got '{type(request).__name__}'."
            )

        # 2. Retrieve provider
        target_provider = self.get_provider(provider)

        logger.info(
            "Executing search on provider '%s' for collection '%s' over bbox %s",
            target_provider.name,
            search_req.collection,
            search_req.bbox
        )

        # 3. Dispatch search to provider
        return target_provider.search(search_req)


# Default global instance pre-configured with Stage 1 provider stubs
satellite_search_service = SatelliteSearchService()
satellite_search_service.register_provider(CopernicusProvider())
