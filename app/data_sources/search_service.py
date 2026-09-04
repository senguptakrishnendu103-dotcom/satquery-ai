"""
Provider-independent satellite search service for SatQuery AI.

Responsibilities
----------------
- Register satellite data providers
- Validate provider selection
- Normalize incoming search requests
- Validate search parameters
- Dispatch searches to the selected provider
- Expose provider metadata/health
"""

import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from app.data_sources.base_provider import (
    SatelliteDataProvider,
    SearchRequest,
    SatelliteProduct,
)

from app.data_sources.providers.copernicus_provider import (
    CopernicusProvider,
)

from app.data_sources.exceptions import (
    ProviderNotFoundError,
    DuplicateProviderError,
    InvalidSearchRequestError,
)


logger = logging.getLogger(
    "satquery.data_sources.search_service"
)


class SatelliteSearchService:
    """
    Provider-independent satellite search service.

    The service is deliberately provider-agnostic.

    Flow:

        API request
            ↓
        SearchRequest validation
            ↓
        provider lookup
            ↓
        provider.search()
            ↓
        normalized SatelliteProduct list
    """

    def __init__(self) -> None:
        self._providers: Dict[
            str,
            SatelliteDataProvider,
        ] = {}

    # ========================================================
    # PROVIDER REGISTRATION
    # ========================================================

    def register_provider(
        self,
        provider: SatelliteDataProvider,
        replace: bool = False,
    ) -> None:
        """
        Register a satellite data provider.

        Args:
            provider:
                Instance implementing SatelliteDataProvider.

            replace:
                Replace an existing provider with the same name.
        """

        if not isinstance(
            provider,
            SatelliteDataProvider,
        ):
            raise TypeError(
                "Provider must be an instance of "
                "SatelliteDataProvider. "
                f"Got '{type(provider).__name__}'."
            )

        provider_name = (
            str(provider.name)
            .strip()
            .lower()
        )

        if not provider_name:
            raise ValueError(
                "Provider name cannot be empty."
            )

        if (
            provider_name in self._providers
            and not replace
        ):
            raise DuplicateProviderError(
                f"Provider '{provider_name}' is already "
                "registered. Set replace=True to overwrite."
            )

        self._providers[
            provider_name
        ] = provider

        logger.info(
            "Registered satellite provider '%s'. "
            "Collections=%s Modalities=%s",
            provider_name,
            provider.supported_collections,
            provider.supported_modalities,
        )

    # ========================================================
    # PROVIDER LOOKUP
    # ========================================================

    def get_provider(
        self,
        name: str,
    ) -> SatelliteDataProvider:
        """
        Retrieve a provider by name.
        """

        if not isinstance(
            name,
            str,
        ) or not name.strip():
            raise ProviderNotFoundError(
                "Provider name must be a "
                "non-empty string."
            )

        provider_key = (
            name.strip().lower()
        )

        provider = (
            self._providers.get(
                provider_key
            )
        )

        if provider is None:

            available = sorted(
                self._providers.keys()
            )

            raise ProviderNotFoundError(
                f"Provider '{name}' is not registered. "
                f"Available providers: {available}"
            )

        return provider

    # ========================================================
    # PROVIDER LIST
    # ========================================================

    def list_providers(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Return metadata for all registered providers.
        """

        providers: List[
            Dict[str, Any]
        ] = []

        for provider in self._providers.values():

            providers.append(
                {
                    "name":
                        provider.name,

                    "supported_collections":
                        list(
                            provider.supported_collections
                        ),

                    "supported_modalities":
                        list(
                            provider.supported_modalities
                        ),
                }
            )

        return providers

    # ========================================================
    # REQUEST VALIDATION
    # ========================================================

    def _validate_request(
        self,
        request: Union[
            SearchRequest,
            Dict[str, Any],
        ],
    ) -> SearchRequest:
        """
        Convert and validate an incoming search request.

        Supports both:
            SearchRequest
            dict
        """

        # ----------------------------------------------------
        # Already normalized
        # ----------------------------------------------------

        if isinstance(
            request,
            SearchRequest,
        ):
            search_req = request

        # ----------------------------------------------------
        # Dictionary from FastAPI
        # ----------------------------------------------------

        elif isinstance(
            request,
            dict,
        ):

            try:

                search_req = (
                    SearchRequest(
                        **request
                    )
                )

            except Exception as exc:

                raise InvalidSearchRequestError(
                    "Failed to parse search "
                    f"request parameters: {exc}"
                ) from exc

        else:

            raise InvalidSearchRequestError(
                "Request must be a "
                "SearchRequest instance "
                "or dictionary. "
                f"Got '{type(request).__name__}'."
            )

        # ----------------------------------------------------
        # Provider-independent validation
        # ----------------------------------------------------

        self._validate_bbox(
            search_req
        )

        self._validate_dates(
            search_req
        )

        self._validate_limit(
            search_req
        )

        self._validate_cloud_cover(
            search_req
        )

        if not isinstance(
            search_req.collection,
            str,
        ) or not search_req.collection.strip():

            raise InvalidSearchRequestError(
                "collection must be a "
                "non-empty string."
            )

        return search_req

    def _validate_bbox(
        self,
        request: SearchRequest,
    ) -> None:
        """
        Validate:

            [min_lon, min_lat,
             max_lon, max_lat]
        """

        bbox = request.bbox

        if not isinstance(
            bbox,
            (list, tuple),
        ):
            raise InvalidSearchRequestError(
                "bbox must be a list or tuple "
                "of four numbers."
            )

        if len(bbox) != 4:
            raise InvalidSearchRequestError(
                "bbox must contain exactly four "
                "values: "
                "[min_lon, min_lat, "
                "max_lon, max_lat]"
            )

        try:

            min_lon = float(
                bbox[0]
            )

            min_lat = float(
                bbox[1]
            )

            max_lon = float(
                bbox[2]
            )

            max_lat = float(
                bbox[3]
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise InvalidSearchRequestError(
                "bbox values must be numeric."
            ) from exc

        if not (
            -180 <= min_lon <= 180
            and
            -180 <= max_lon <= 180
            and
            -90 <= min_lat <= 90
            and
            -90 <= max_lat <= 90
        ):
            raise InvalidSearchRequestError(
                "bbox contains invalid "
                "geographic coordinates."
            )

        if min_lon >= max_lon:
            raise InvalidSearchRequestError(
                "bbox min_lon must be smaller "
                "than max_lon."
            )

        if min_lat >= max_lat:
            raise InvalidSearchRequestError(
                "bbox min_lat must be smaller "
                "than max_lat."
            )

    def _validate_dates(
        self,
        request: SearchRequest,
    ) -> None:
        """
        Validate that start_date and end_date exist
        and that the range is logically ordered.

        Detailed date parsing is delegated to the provider's
        SearchRequest/base_provider implementation.
        """

        if not request.start_date:
            raise InvalidSearchRequestError(
                "start_date is required."
            )

        if not request.end_date:
            raise InvalidSearchRequestError(
                "end_date is required."
            )

        try:

            # Import lazily so this service keeps the
            # existing base-provider contract.
            from app.data_sources.base_provider import (
                parse_datetime,
            )

            start = parse_datetime(
                request.start_date
            )

            end = parse_datetime(
                request.end_date
            )

        except Exception as exc:

            raise InvalidSearchRequestError(
                "Invalid date range: "
                f"{exc}"
            ) from exc

        if start > end:
            raise InvalidSearchRequestError(
                "start_date cannot be later "
                "than end_date."
            )

    def _validate_limit(
        self,
        request: SearchRequest,
    ) -> None:
        """
        Enforce a safe provider-independent result limit.
        """

        try:

            limit = int(
                request.limit
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise InvalidSearchRequestError(
                "limit must be an integer."
            ) from exc

        if limit < 1:
            raise InvalidSearchRequestError(
                "limit must be at least 1."
            )

        if limit > 100:
            raise InvalidSearchRequestError(
                "limit cannot exceed 100."
            )

        request.limit = limit

    def _validate_cloud_cover(
        self,
        request: SearchRequest,
    ) -> None:
        """
        Validate optional cloud-cover constraint.
        """

        if request.max_cloud_cover is None:
            return

        try:

            cloud_cover = float(
                request.max_cloud_cover
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise InvalidSearchRequestError(
                "max_cloud_cover must be numeric."
            ) from exc

        if not (
            0 <= cloud_cover <= 100
        ):
            raise InvalidSearchRequestError(
                "max_cloud_cover must be "
                "between 0 and 100."
            )

        request.max_cloud_cover = (
            cloud_cover
        )

    # ========================================================
    # SEARCH
    # ========================================================

    def search(
        self,
        provider: str,
        request: Union[
            SearchRequest,
            Dict[str, Any],
        ],
    ) -> List[SatelliteProduct]:
        """
        Validate and execute a satellite search.

        Args:
            provider:
                Provider identifier, e.g. 'copernicus'.

            request:
                SearchRequest object or dictionary.

        Returns:
            Normalized SatelliteProduct objects.
        """

        logger.info(
            "Received satellite search request "
            "for provider '%s'.",
            provider,
        )

        # ----------------------------------------------------
        # Resolve provider first
        # ----------------------------------------------------

        target_provider = (
            self.get_provider(
                provider
            )
        )

        # ----------------------------------------------------
        # Validate request
        # ----------------------------------------------------

        search_req = (
            self._validate_request(
                request
            )
        )

        # ----------------------------------------------------
        # Validate requested collection against provider
        # ----------------------------------------------------

        requested_collection = (
            str(
                search_req.collection
            )
            .strip()
            .lower()
            .replace(
                "_",
                "-",
            )
        )

        provider_collections = {
            str(collection)
            .strip()
            .lower()
            .replace(
                "_",
                "-",
            )
            for collection
            in target_provider.supported_collections
        }

        # We allow provider aliases because the provider itself
        # performs final normalization (e.g. S2, Sentinel-2 L2A).
        collection_is_known = (
            requested_collection
            in provider_collections
        )

        if not collection_is_known:

            # CopernicusProvider handles aliases such as:
            # sentinel-2-l2a, S2, sentinel_2_l2a, etc.
            if isinstance(
                target_provider,
                CopernicusProvider,
            ):

                alias_candidates = {
                    "s2":
                        "sentinel-2",

                    "s2-l2a":
                        "sentinel-2-l2a",

                    "s2-l1c":
                        "sentinel-2-l1c",

                    "s1":
                        "sentinel-1",

                    "s1-grd":
                        "sentinel-1-grd",
                }

                normalized_alias = (
                    alias_candidates.get(
                        requested_collection
                    )
                )

                if normalized_alias:
                    search_req.collection = (
                        normalized_alias
                    )

            else:

                raise InvalidSearchRequestError(
                    f"Collection "
                    f"'{search_req.collection}' "
                    f"is not supported by provider "
                    f"'{target_provider.name}'. "
                    f"Supported collections: "
                    f"{target_provider.supported_collections}"
                )

        # ----------------------------------------------------
        # Log final request
        # ----------------------------------------------------

        logger.info(
            "Dispatching search to provider='%s', "
            "collection='%s', bbox=%s, "
            "dates=%s -> %s, cloud<=%s, limit=%d",
            target_provider.name,
            search_req.collection,
            search_req.bbox,
            search_req.start_date,
            search_req.end_date,
            search_req.max_cloud_cover,
            search_req.limit,
        )

        # ----------------------------------------------------
        # Execute provider search
        # ----------------------------------------------------

        results = target_provider.search(
            search_req
        )

        # ----------------------------------------------------
        # Defensive response validation
        # ----------------------------------------------------

        if results is None:
            logger.warning(
                "Provider '%s' returned None. "
                "Treating it as an empty result list.",
                target_provider.name,
            )
            return []

        if not isinstance(
            results,
            list,
        ):
            raise InvalidSearchRequestError(
                "Satellite provider returned "
                "an invalid result type."
            )

        valid_results: List[
            SatelliteProduct
        ] = []

        for result in results:

            if not isinstance(
                result,
                SatelliteProduct,
            ):

                logger.warning(
                    "Ignoring invalid provider result "
                    "of type '%s'.",
                    type(result).__name__,
                )

                continue

            valid_results.append(
                result
            )

        logger.info(
            "Provider '%s' returned %d normalized "
            "satellite products.",
            target_provider.name,
            len(valid_results),
        )

        return valid_results

    # ========================================================
    # PROVIDER HEALTH
    # ========================================================

    def health_check(
        self,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check one provider or all providers.

        This is useful for debugging the live CDSE connection.
        """

        if provider:

            target_provider = (
                self.get_provider(
                    provider
                )
            )

            try:

                healthy = bool(
                    target_provider.health_check()
                )

            except Exception as exc:

                logger.exception(
                    "Provider '%s' health check failed.",
                    target_provider.name,
                )

                healthy = False

            return {
                "provider":
                    target_provider.name,

                "healthy":
                    healthy,
            }

        results: Dict[
            str,
            Any,
        ] = {}

        for provider_name, target_provider in (
            self._providers.items()
        ):

            try:

                healthy = bool(
                    target_provider.health_check()
                )

            except Exception as exc:

                logger.warning(
                    "Provider '%s' health check "
                    "raised an exception: %s",
                    provider_name,
                    exc,
                )

                healthy = False

            results[
                provider_name
            ] = {
                "healthy":
                    healthy,

                "collections":
                    list(
                        target_provider
                        .supported_collections
                    ),

                "modalities":
                    list(
                        target_provider
                        .supported_modalities
                    ),
            }

        return results


# ============================================================
# DEFAULT GLOBAL SERVICE
# ============================================================

satellite_search_service = (
    SatelliteSearchService()
)

satellite_search_service.register_provider(
    CopernicusProvider()
)