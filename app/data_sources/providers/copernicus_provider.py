"""
Copernicus Data Space Ecosystem (CDSE) Satellite Data Provider.

Responsibilities
----------------
- Live CDSE catalogue search
- Spatial filtering
- Temporal filtering
- Collection filtering
- Product-type filtering
- Cloud-cover filtering
- Metadata normalization
- Genuine CDSE quicklook discovery
- Product download URL generation

This module intentionally separates:
    1. Catalogue metadata/search
    2. Quicklook/preview assets
    3. Actual product download

Actual product downloading/authentication should be handled by the
ingestion layer, not exposed directly to the frontend.
"""

import logging
import os
import re
import time

from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import requests

from app.data_sources.base_provider import (
    SatelliteDataProvider,
    SearchRequest,
    SatelliteProduct,
    parse_datetime,
)

from app.data_sources.exceptions import (
    SatelliteProviderError,
    SatelliteSearchError,
    InvalidSearchRequestError,
)


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger(
    "satquery.data_sources.copernicus"
)


# ============================================================
# CDSE ENDPOINTS
# ============================================================

CDSE_CATALOGUE_URL = (
    "https://catalogue.dataspace.copernicus.eu"
    "/odata/v1/Products"
)

CDSE_DOWNLOAD_BASE_URL = (
    "https://download.dataspace.copernicus.eu"
    "/odata/v1/Products"
)


# ============================================================
# SUPPORTED COLLECTIONS
# ============================================================

SUPPORTED_COLLECTIONS: Dict[str, Dict[str, Any]] = {

    # --------------------------------------------------------
    # Sentinel-2 generic
    # --------------------------------------------------------

    "sentinel-2": {
        "cdse_collection": "SENTINEL-2",
        "product_types": [
            "S2MSI2A",
            "S2MSI1C",
        ],
        "modalities": [
            "optical",
            "multispectral",
        ],
        "default_instrument": "MSI",
    },

    # --------------------------------------------------------
    # Sentinel-2 L2A
    # --------------------------------------------------------

    "sentinel-2-l2a": {
        "cdse_collection": "SENTINEL-2",
        "product_types": [
            "S2MSI2A",
        ],
        "processing_level": "Level-2A",
        "modalities": [
            "optical",
            "multispectral",
        ],
        "default_instrument": "MSI",
    },

    # --------------------------------------------------------
    # Sentinel-2 L1C
    # --------------------------------------------------------

    "sentinel-2-l1c": {
        "cdse_collection": "SENTINEL-2",
        "product_types": [
            "S2MSI1C",
        ],
        "processing_level": "Level-1C",
        "modalities": [
            "optical",
            "multispectral",
        ],
        "default_instrument": "MSI",
    },

    # --------------------------------------------------------
    # Sentinel-1
    # --------------------------------------------------------

    "sentinel-1": {
        "cdse_collection": "SENTINEL-1",
        "product_types": [
            "GRD",
        ],
        "modalities": [
            "sar",
        ],
        "default_instrument": "C-SAR",
    },

    # --------------------------------------------------------
    # Sentinel-1 GRD
    # --------------------------------------------------------

    "sentinel-1-grd": {
        "cdse_collection": "SENTINEL-1",
        "product_types": [
            "GRD",
        ],
        "processing_level": "GRD",
        "modalities": [
            "sar",
        ],
        "default_instrument": "C-SAR",
    },
}


# ============================================================
# COLLECTION NORMALIZATION
# ============================================================

def normalize_collection_key(
    raw_collection: str,
) -> str:
    """
    Normalize a user/frontend collection identifier.

    Examples:
        SENTINEL_2_L2A -> sentinel-2-l2a
        Sentinel-2 L2A -> sentinel-2-l2a
        S2 -> sentinel-2
        S1 -> sentinel-1
    """

    if not raw_collection or not isinstance(
        raw_collection,
        str,
    ):
        raise InvalidSearchRequestError(
            "Collection identifier must be a "
            "non-empty string."
        )

    cleaned = (
        raw_collection
        .strip()
        .lower()
        .replace("_", "-")
        .replace(" ", "-")
    )

    # Remove repeated hyphens.
    cleaned = re.sub(
        r"-+",
        "-",
        cleaned,
    )

    if cleaned in SUPPORTED_COLLECTIONS:
        return cleaned

    # Sentinel-2 aliases.
    if (
        "sentinel-2" in cleaned
        or cleaned == "s2"
        or cleaned.startswith("s2-")
    ):
        if "l2a" in cleaned:
            return "sentinel-2-l2a"

        if "l1c" in cleaned:
            return "sentinel-2-l1c"

        return "sentinel-2"

    # Sentinel-1 aliases.
    if (
        "sentinel-1" in cleaned
        or cleaned == "s1"
        or cleaned.startswith("s1-")
    ):
        if "grd" in cleaned:
            return "sentinel-1-grd"

        return "sentinel-1"

    available = list(
        SUPPORTED_COLLECTIONS.keys()
    )

    raise InvalidSearchRequestError(
        f"Unsupported collection "
        f"'{raw_collection}'. "
        f"Supported collections: {available}"
    )


# ============================================================
# FOOTPRINT HELPERS
# ============================================================

def parse_wkt_footprint(
    footprint_raw: Optional[str],
) -> Tuple[
    Optional[Tuple[float, float, float, float]],
    Optional[Dict[str, Any]],
]:
    """
    Parse a CDSE WKT footprint into:

        bbox:
            (min_lon, min_lat, max_lon, max_lat)

        GeoJSON polygon:
            {
                "type": "Polygon",
                "coordinates": [...]
            }

    Handles strings such as:

        geography'SRID=4326;
        POLYGON ((-8.07 14.47, ...))'
    """

    if not footprint_raw or not isinstance(
        footprint_raw,
        str,
    ):
        return None, None

    # Extract POLYGON coordinates.
    match = re.search(
        r"POLYGON\s*\(\((.*?)\)\)",
        footprint_raw,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return None, None

    coords_text = match.group(1)

    pairs = re.findall(
        r"([+-]?\d+(?:\.\d+)?)"
        r"\s+"
        r"([+-]?\d+(?:\.\d+)?)",
        coords_text,
    )

    if not pairs:
        return None, None

    points: List[List[float]] = []
    lons: List[float] = []
    lats: List[float] = []

    for lon_str, lat_str in pairs:

        try:
            lon = float(lon_str)
            lat = float(lat_str)

        except (
            ValueError,
            TypeError,
        ):
            continue

        # Basic geographic sanity checks.
        if not -180 <= lon <= 180:
            continue

        if not -90 <= lat <= 90:
            continue

        points.append(
            [lon, lat]
        )

        lons.append(lon)
        lats.append(lat)

    if not points:
        return None, None

    bbox = (
        min(lons),
        min(lats),
        max(lons),
        max(lats),
    )

    # Ensure polygon is closed.
    if points[0] != points[-1]:
        points.append(
            points[0]
        )

    geojson_polygon = {
        "type": "Polygon",
        "coordinates": [
            points
        ],
    }

    return (
        bbox,
        geojson_polygon,
    )


def intersects_bbox(
    bbox1: Tuple[
        float,
        float,
        float,
        float,
    ],
    bbox2: Tuple[
        float,
        float,
        float,
        float,
    ],
) -> bool:
    """
    Check whether two bounding boxes intersect.
    """

    (
        min_lon1,
        min_lat1,
        max_lon1,
        max_lat1,
    ) = bbox1

    (
        min_lon2,
        min_lat2,
        max_lon2,
        max_lat2,
    ) = bbox2

    return not (
        max_lon1 < min_lon2
        or min_lon1 > max_lon2
        or max_lat1 < min_lat2
        or min_lat1 > max_lat2
    )


# ============================================================
# PROVIDER
# ============================================================

class CopernicusProvider(
    SatelliteDataProvider
):
    """
    Copernicus Data Space Ecosystem provider.

    Supports:
        - Sentinel-1 SAR
        - Sentinel-2 optical/multispectral

    Search is performed against the official CDSE
    OData catalogue.
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        connect_timeout: float = 10.0,
        read_timeout: float = 30.0,
        max_retries: int = 3,
        session: Optional[
            requests.Session
        ] = None,
    ):
        """
        Initialize provider.

        Credentials are optional for public catalogue search.

        They should NOT be exposed to the frontend.
        """

        self._username = (
            username
            or os.getenv(
                "CDSE_USERNAME"
            )
        )

        self._password = (
            password
            or os.getenv(
                "CDSE_PASSWORD"
            )
        )

        self.connect_timeout = (
            connect_timeout
        )

        self.read_timeout = (
            read_timeout
        )

        self.max_retries = max(
            0,
            int(max_retries),
        )

        self._session = (
            session
            or requests.Session()
        )

        self._session.headers.update(
            {
                "User-Agent":
                    "SatQuery-AI/1.1",
                "Accept":
                    "application/json",
            }
        )

        logger.info(
            "CopernicusProvider initialized. "
            "CDSE credentials configured: %s",
            bool(
                self._username
                and self._password
            ),
        )

    # ========================================================
    # PROVIDER PROPERTIES
    # ========================================================

    @property
    def name(self) -> str:
        return "copernicus"

    @property
    def supported_collections(
        self,
    ) -> List[str]:

        return list(
            SUPPORTED_COLLECTIONS.keys()
        )

    @property
    def supported_modalities(
        self,
    ) -> List[str]:

        return [
            "optical",
            "multispectral",
            "sar",
        ]

    # ========================================================
    # HEALTH
    # ========================================================

    def health_check(self) -> bool:
        """
        Check whether the public CDSE catalogue is reachable.
        """

        try:

            response = self._session.get(
                CDSE_CATALOGUE_URL,
                params={
                    "$top": 1,
                },
                timeout=(
                    self.connect_timeout,
                    self.read_timeout,
                ),
            )

            return (
                response.status_code == 200
            )

        except Exception as exc:

            logger.warning(
                "CDSE health check failed: %s",
                exc,
            )

            return False

    # ========================================================
    # HTTP REQUEST
    # ========================================================

    def _execute_request(
        self,
        url: str,
        params: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP GET against CDSE.

        Retries:
            429
            500
            502
            503
            504

        Network:
            timeout
            connection errors
        """

        retry_count = 0
        backoff = 1.0

        while True:

            try:

                response = (
                    self._session.get(
                        url,
                        params=params,
                        timeout=(
                            self.connect_timeout,
                            self.read_timeout,
                        ),
                    )
                )

                # ------------------------------------------------
                # SUCCESS
                # ------------------------------------------------

                if response.status_code == 200:

                    try:

                        payload = (
                            response.json()
                        )

                    except ValueError as exc:

                        raise SatelliteSearchError(
                            "Failed to parse JSON "
                            "response from CDSE API."
                        ) from exc

                    if not isinstance(
                        payload,
                        dict,
                    ):
                        raise SatelliteSearchError(
                            "CDSE API returned "
                            "an unexpected response."
                        )

                    return payload

                # ------------------------------------------------
                # BAD REQUEST
                # ------------------------------------------------

                if response.status_code == 400:

                    raise InvalidSearchRequestError(
                        "CDSE catalogue request "
                        "rejected (HTTP 400): "
                        f"{response.text[:500]}"
                    )

                # ------------------------------------------------
                # AUTH
                # ------------------------------------------------

                if response.status_code in (
                    401,
                    403,
                ):

                    raise SatelliteProviderError(
                        "CDSE authorization failed "
                        f"(HTTP {response.status_code}): "
                        f"{response.text[:500]}"
                    )

                # ------------------------------------------------
                # NOT FOUND
                # ------------------------------------------------

                if response.status_code == 404:

                    raise SatelliteProviderError(
                        "CDSE endpoint or product "
                        "not found (HTTP 404)."
                    )

                # ------------------------------------------------
                # RETRYABLE
                # ------------------------------------------------

                if response.status_code in (
                    429,
                    500,
                    502,
                    503,
                    504,
                ):

                    if (
                        retry_count
                        < self.max_retries
                    ):

                        retry_count += 1

                        logger.warning(
                            "CDSE returned HTTP %d. "
                            "Retry %d/%d in %.1fs.",
                            response.status_code,
                            retry_count,
                            self.max_retries,
                            backoff,
                        )

                        time.sleep(
                            backoff
                        )

                        backoff = min(
                            backoff * 2.0,
                            16.0,
                        )

                        continue

                    raise SatelliteSearchError(
                        "CDSE API error "
                        f"HTTP {response.status_code} "
                        f"after {self.max_retries} "
                        "retries: "
                        f"{response.text[:500]}"
                    )

                # ------------------------------------------------
                # UNKNOWN
                # ------------------------------------------------

                raise SatelliteSearchError(
                    "Unexpected CDSE API response "
                    f"HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                )

            except (
                requests.Timeout,
                requests.ConnectionError,
            ) as exc:

                if (
                    retry_count
                    < self.max_retries
                ):

                    retry_count += 1

                    logger.warning(
                        "CDSE network error "
                        "(%s). Retry %d/%d "
                        "in %.1fs.",
                        type(exc).__name__,
                        retry_count,
                        self.max_retries,
                        backoff,
                    )

                    time.sleep(
                        backoff
                    )

                    backoff = min(
                        backoff * 2.0,
                        16.0,
                    )

                    continue

                raise SatelliteSearchError(
                    "Network error connecting "
                    "to CDSE catalogue: "
                    f"{exc}"
                ) from exc

    # ========================================================
    # ATTRIBUTE HELPERS
    # ========================================================

    def _extract_attributes_dict(
        self,
        raw_item: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Convert CDSE Attributes list into:

            {
                "productType": "...",
                "cloudCover": "...",
                ...
            }
        """

        attributes = (
            raw_item.get(
                "Attributes"
            )
            or []
        )

        result: Dict[str, Any] = {}

        if not isinstance(
            attributes,
            list,
        ):
            return result

        for attribute in attributes:

            if not isinstance(
                attribute,
                dict,
            ):
                continue

            name = attribute.get(
                "Name"
            )

            if not name:
                continue

            if "Value" in attribute:
                result[name] = (
                    attribute["Value"]
                )

        return result

    def _get_attribute(
        self,
        attr_dict: Dict[str, Any],
        *names: str,
    ) -> Any:
        """
        Return the first matching attribute name.
        """

        for name in names:

            if name in attr_dict:
                return attr_dict[name]

        # Case-insensitive fallback.
        lowered = {
            str(key).lower(): value
            for key, value
            in attr_dict.items()
        }

        for name in names:

            value = lowered.get(
                name.lower()
            )

            if value is not None:
                return value

        return None

    # ========================================================
    # QUICKLOOK
    # ========================================================

    def _extract_quicklook_asset(
        self,
        raw_item: Dict[str, Any],
    ) -> Optional[
        Dict[str, Any]
    ]:
        """
        Find the genuine CDSE QUICKLOOK asset.

        CDSE exposes quicklooks through the Assets
        collection, not through Products(<id>)/$value.
        """

        assets = (
            raw_item.get(
                "Assets"
            )
            or []
        )

        if not isinstance(
            assets,
            list,
        ):
            return None

        for asset in assets:

            if not isinstance(
                asset,
                dict,
            ):
                continue

            asset_type = str(
                asset.get(
                    "Type",
                    "",
                )
            ).upper()

            asset_name = str(
                asset.get(
                    "Name",
                    "",
                )
            ).upper()

            asset_title = str(
                asset.get(
                    "Title",
                    "",
                )
            ).upper()

            if (
                asset_type == "QUICKLOOK"
                or asset_name == "QUICKLOOK"
                or "QUICKLOOK"
                in asset_name
                or "QUICKLOOK"
                in asset_title
            ):
                return asset

        return None

    def _build_asset_url(
        self,
        asset: Dict[str, Any],
    ) -> Optional[str]:
        """
        Return the official CDSE asset download URL.
        """

        download_link = asset.get(
            "DownloadLink"
        )

        if download_link:
            return str(
                download_link
            )

        asset_id = asset.get(
            "Id"
        )

        if not asset_id:
            return None

        return (
            "https://catalogue.dataspace.copernicus.eu"
            "/odata/v1/Assets"
            f"({asset_id})/$value"
        )

    # ========================================================
    # COLLECTION DETECTION
    # ========================================================

    def _detect_collection_key(
        self,
        raw_item: Dict[str, Any],
    ) -> str:
        """
        Determine which supported collection a product belongs to.

        This is used by get_product(), where the original code
        incorrectly assumed every product was Sentinel-2.
        """

        collection = (
            raw_item.get(
                "Collection"
            )
            or {}
        )

        if isinstance(
            collection,
            dict,
        ):
            collection_name = str(
                collection.get(
                    "Name",
                    "",
                )
            ).upper()

        else:
            collection_name = str(
                collection
            ).upper()

        name = str(
            raw_item.get(
                "Name",
                "",
            )
        ).upper()

        if (
            collection_name
            == "SENTINEL-1"
            or name.startswith("S1")
        ):

            if (
                "GRD"
                in name
            ):
                return "sentinel-1-grd"

            return "sentinel-1"

        if (
            collection_name
            == "SENTINEL-2"
            or name.startswith("S2")
        ):

            if (
                "MSIL2A"
                in name
            ):
                return "sentinel-2-l2a"

            if (
                "MSIL1C"
                in name
            ):
                return "sentinel-2-l1c"

            return "sentinel-2"

        raise SatelliteProviderError(
            "Unsupported CDSE product collection: "
            f"{collection_name or name}"
        )

    # ========================================================
    # ODATA FILTER
    # ========================================================

    def _build_odata_filter(
        self,
        request: SearchRequest,
        coll_config: Dict[str, Any],
    ) -> str:
        """
        Build a CDSE OData $filter.

        Filters:
            - collection
            - sensing date
            - geographic intersection
            - product type
        """

        filters: List[str] = []

        # ----------------------------------------------------
        # Collection
        # ----------------------------------------------------

        cdse_collection = (
            coll_config[
                "cdse_collection"
            ]
        )

        filters.append(
            "Collection/Name eq "
            f"'{cdse_collection}'"
        )

        # ----------------------------------------------------
        # Dates
        # ----------------------------------------------------

        try:

            parsed_start = (
                parse_datetime(
                    request.start_date
                )
            )

            parsed_end = (
                parse_datetime(
                    request.end_date
                )
            )

        except Exception as exc:

            raise InvalidSearchRequestError(
                "Invalid date range: "
                f"{exc}"
            ) from exc

        if parsed_start > parsed_end:

            raise InvalidSearchRequestError(
                "start_date cannot be later "
                "than end_date."
            )

        start_iso = (
            parsed_start.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            )
        )

        end_iso = (
            parsed_end.strftime(
                "%Y-%m-%dT%H:%M:%S.999Z"
            )
        )

        filters.append(
            "ContentDate/Start ge "
            f"{start_iso}"
        )

        filters.append(
            "ContentDate/Start le "
            f"{end_iso}"
        )

        # ----------------------------------------------------
        # Spatial intersection
        # ----------------------------------------------------

        if (
            not request.bbox
            or len(request.bbox) != 4
        ):

            raise InvalidSearchRequestError(
                "bbox must contain exactly "
                "four coordinates: "
                "[min_lon, min_lat, "
                "max_lon, max_lat]"
            )

        (
            min_lon,
            min_lat,
            max_lon,
            max_lat,
        ) = request.bbox

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

        if not (
            -180
            <= min_lon
            <= 180
            and -180
            <= max_lon
            <= 180
            and -90
            <= min_lat
            <= 90
            and -90
            <= max_lat
            <= 90
        ):

            raise InvalidSearchRequestError(
                "bbox contains invalid "
                "geographic coordinates."
            )

        polygon_wkt = (
            "POLYGON(("
            f"{min_lon} {min_lat}, "
            f"{max_lon} {min_lat}, "
            f"{max_lon} {max_lat}, "
            f"{min_lon} {max_lat}, "
            f"{min_lon} {min_lat}"
            "))"
        )

        filters.append(
            "OData.CSC.Intersects("
            "area=geography"
            "'SRID=4326;"
            f"{polygon_wkt}')"
        )

        # ----------------------------------------------------
        # Product type
        # ----------------------------------------------------

        product_types = (
            coll_config.get(
                "product_types"
            )
            or []
        )

        if product_types:

            product_filters = []

            for product_type in product_types:

                escaped_type = (
                    str(
                        product_type
                    ).replace(
                        "'",
                        "''",
                    )
                )

                product_filters.append(
                    "Attributes/"
                    "OData.CSC.StringAttribute/"
                    "any(att:"
                    "att/Name eq "
                    "'productType' "
                    "and "
                    "att/OData.CSC.StringAttribute/"
                    "Value eq "
                    f"'{escaped_type}'"
                    ")"
                )

            if len(
                product_filters
            ) == 1:

                filters.append(
                    product_filters[0]
                )

            else:

                filters.append(
                    "("
                    + " or ".join(
                        product_filters
                    )
                    + ")"
                )

        return " and ".join(
            filters
        )

    # ========================================================
    # ODATA PARAMS
    # ========================================================

    def _build_odata_params(
        self,
        request: SearchRequest,
        coll_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build CDSE OData query parameters.
        """

        params: Dict[str, Any] = {
            "$filter":
                self._build_odata_filter(
                    request,
                    coll_config,
                ),

            "$top":
                request.limit,

            "$expand":
                "Attributes",

            "$orderby":
                "ContentDate/Start desc",
        }

        # ----------------------------------------------------
        # Optional frontend/backend query parameters
        # ----------------------------------------------------

        query_params = (
            request.query_params
            or {}
        )

        if (
            "orderby"
            in query_params
        ):

            orderby = str(
                query_params[
                    "orderby"
                ]
            ).strip()

            allowed_orderby = {
                "ContentDate/Start",
                "ContentDate/End",
                "PublicationDate",
                "ModificationDate",
            }

            # Accept "field desc"/"field asc".
            parts = orderby.split()

            if (
                parts
                and parts[0]
                in allowed_orderby
            ):

                direction = (
                    parts[1].lower()
                    if len(parts) > 1
                    else "asc"
                )

                if direction not in {
                    "asc",
                    "desc",
                }:

                    direction = "asc"

                params[
                    "$orderby"
                ] = (
                    f"{parts[0]} "
                    f"{direction}"
                )

        # ----------------------------------------------------
        # Pagination
        # ----------------------------------------------------

        if (
            "skip"
            in query_params
        ):

            try:

                skip = int(
                    query_params[
                        "skip"
                    ]
                )

            except (
                TypeError,
                ValueError,
            ):

                raise InvalidSearchRequestError(
                    "query_params.skip "
                    "must be an integer."
                )

            if skip < 0:
                raise InvalidSearchRequestError(
                    "query_params.skip "
                    "cannot be negative."
                )

            params[
                "$skip"
            ] = skip

        return params

    # ========================================================
    # NORMALIZATION
    # ========================================================

    def _normalize_product(
        self,
        raw_item: Dict[str, Any],
        requested_collection: str,
    ) -> SatelliteProduct:
        """
        Convert raw CDSE OData JSON into the provider-neutral
        SatelliteProduct model.
        """

        if not isinstance(
            raw_item,
            dict,
        ):
            raise SatelliteProviderError(
                "Invalid CDSE product payload."
            )

        product_id = str(
            raw_item.get(
                "Id",
                "",
            )
        )

        name = str(
            raw_item.get(
                "Name",
                "",
            )
        )

        if not product_id:

            raise SatelliteProviderError(
                "CDSE product has no Id."
            )

        # ----------------------------------------------------
        # Attributes
        # ----------------------------------------------------

        attr_dict = (
            self._extract_attributes_dict(
                raw_item
            )
        )

        # ----------------------------------------------------
        # Spatial
        # ----------------------------------------------------

        footprint_raw = (
            raw_item.get(
                "Footprint"
            )
        )

        bbox, geo_footprint = (
            parse_wkt_footprint(
                footprint_raw
            )
        )

        # Prefer GeoFootprint if already returned by CDSE.
        cdse_geofootprint = (
            raw_item.get(
                "GeoFootprint"
            )
        )

        if isinstance(
            cdse_geofootprint,
            dict,
        ):

            geo_footprint = (
                cdse_geofootprint
            )

            if (
                not bbox
                and geo_footprint.get(
                    "coordinates"
                )
            ):

                try:

                    coords = (
                        geo_footprint[
                            "coordinates"
                        ]
                    )

                    # Polygon coordinates:
                    # [[[lon, lat], ...]]
                    flat_points = []

                    for ring in coords:

                        if not isinstance(
                            ring,
                            list,
                        ):
                            continue

                        for point in ring:

                            if (
                                isinstance(
                                    point,
                                    list,
                                )
                                and len(point)
                                >= 2
                            ):

                                flat_points.append(
                                    point
                                )

                    if flat_points:

                        lons = [
                            float(
                                p[0]
                            )
                            for p
                            in flat_points
                        ]

                        lats = [
                            float(
                                p[1]
                            )
                            for p
                            in flat_points
                        ]

                        bbox = (
                            min(lons),
                            min(lats),
                            max(lons),
                            max(lats),
                        )

                except Exception:
                    pass

        # ----------------------------------------------------
        # Temporal
        # ----------------------------------------------------

        content_date = (
            raw_item.get(
                "ContentDate"
            )
            or {}
        )

        start_str = (
            content_date.get(
                "Start"
            )
            if isinstance(
                content_date,
                dict,
            )
            else None
        )

        acquisition_datetime = None

        if start_str:

            try:

                acquisition_datetime = (
                    parse_datetime(
                        start_str
                    )
                )

            except Exception:

                acquisition_datetime = None

        # ----------------------------------------------------
        # Platform
        # ----------------------------------------------------

        platform_short = (
            self._get_attribute(
                attr_dict,
                "platformShortName",
            )
        )

        platform_serial = (
            self._get_attribute(
                attr_dict,
                "platformSerialIdentifier",
            )
        )

        if (
            platform_short
            and platform_serial
        ):

            platform = (
                f"{str(platform_short).title()}"
                f"{str(platform_serial).upper()}"
            )

        elif platform_short:

            platform = str(
                platform_short
            ).title()

        elif name.startswith(
            "S2A"
        ):

            platform = "Sentinel-2A"

        elif name.startswith(
            "S2B"
        ):

            platform = "Sentinel-2B"

        elif name.startswith(
            "S2C"
        ):

            platform = "Sentinel-2C"

        elif name.startswith(
            "S1A"
        ):

            platform = "Sentinel-1A"

        elif name.startswith(
            "S1B"
        ):

            platform = "Sentinel-1B"

        elif name.startswith(
            "S1C"
        ):

            platform = "Sentinel-1C"

        else:

            platform = None

        # ----------------------------------------------------
        # Instrument
        # ----------------------------------------------------

        instrument = (
            self._get_attribute(
                attr_dict,
                "instrumentShortName",
            )
        )

        if not instrument:

            if (
                name.startswith("S2")
                or str(
                    platform_short
                    or ""
                ).upper()
                == "SENTINEL-2"
            ):

                instrument = "MSI"

            elif (
                name.startswith("S1")
                or str(
                    platform_short
                    or ""
                ).upper()
                == "SENTINEL-1"
            ):

                instrument = "C-SAR"

        # ----------------------------------------------------
        # Collection
        # ----------------------------------------------------

        collection_key = (
            normalize_collection_key(
                requested_collection
            )
        )

        coll_config = (
            SUPPORTED_COLLECTIONS[
                collection_key
            ]
        )

        modalities = (
            coll_config.get(
                "modalities"
            )
            or []
        )

        modality = (
            modalities[0]
            if modalities
            else None
        )

        # ----------------------------------------------------
        # Product type
        # ----------------------------------------------------

        product_type = (
            self._get_attribute(
                attr_dict,
                "productType",
            )
        )

        # ----------------------------------------------------
        # Processing level
        # ----------------------------------------------------

        processing_level = (
            self._get_attribute(
                attr_dict,
                "processingLevel",
            )
        )

        if not processing_level:
            processing_level = (
                product_type
            )

        if not processing_level:

            if "MSIL2A" in name:
                processing_level = "L2A"

            elif "MSIL1C" in name:
                processing_level = "L1C"

            elif "GRD" in name:
                processing_level = "GRD"

        # ----------------------------------------------------
        # Cloud cover
        # ----------------------------------------------------

        cloud_cover = None

        if "sar" not in [
            str(m).lower()
            for m in modalities
        ]:

            raw_cloud = (
                self._get_attribute(
                    attr_dict,
                    "cloudCover",
                    "cloudCoverPercentage",
                    "cloudyPixelPercentage",
                )
            )

            if raw_cloud is not None:

                try:

                    cloud_cover = float(
                        raw_cloud
                    )

                    cloud_cover = max(
                        0.0,
                        min(
                            100.0,
                            cloud_cover,
                        ),
                    )

                except (
                    ValueError,
                    TypeError,
                ):

                    cloud_cover = None

        # ----------------------------------------------------
        # Resolution
        # ----------------------------------------------------

        resolution = None

        raw_resolution = (
            self._get_attribute(
                attr_dict,
                "resolution",
                "groundSamplingDistance",
                "spatialResolution",
            )
        )

        if raw_resolution is not None:

            try:

                resolution = float(
                    raw_resolution
                )

            except (
                ValueError,
                TypeError,
            ):

                resolution = None

        # Sentinel-2 MSI commonly has 10m bands, but don't
        # pretend the entire product has a single resolution.
        if (
            resolution is None
            and collection_key.startswith(
                "sentinel-2"
            )
        ):
            resolution = 10.0

        # Sentinel-1 GRD is commonly 10m pixel spacing,
        # but this is only a fallback.
        if (
            resolution is None
            and collection_key.startswith(
                "sentinel-1"
            )
        ):
            resolution = 10.0

        # ----------------------------------------------------
        # Bands
        # ----------------------------------------------------

        if (
            collection_key.startswith(
                "sentinel-2"
            )
        ):

            available_bands = [
                "B01",
                "B02",
                "B03",
                "B04",
                "B05",
                "B06",
                "B07",
                "B08",
                "B8A",
                "B09",
                "B10",
                "B11",
                "B12",
            ]

        elif (
            collection_key.startswith(
                "sentinel-1"
            )
        ):

            available_bands = [
                "VV",
                "VH",
            ]

        else:

            available_bands = []

        # ----------------------------------------------------
        # URLs
        # ----------------------------------------------------

        product_url = (
            f"{CDSE_CATALOGUE_URL}"
            f"({product_id})"
        )

        download_url = (
            f"{CDSE_DOWNLOAD_BASE_URL}"
            f"({product_id})/$value"
        )

        # ----------------------------------------------------
        # QUICKLOOK
        # ----------------------------------------------------

        quicklook_asset = (
            self._extract_quicklook_asset(
                raw_item
            )
        )

        quicklook_url = None
        quicklook_id = None

        if quicklook_asset:

            quicklook_id = (
                quicklook_asset.get(
                    "Id"
                )
            )

            quicklook_url = (
                self._build_asset_url(
                    quicklook_asset
                )
            )

        # ----------------------------------------------------
        # Metadata bundle
        # ----------------------------------------------------

        metadata_bundle = {

            "name":
                name,

            "product_id":
                product_id,

            "product_type":
                product_type,

            "platform":
                platform,

            "instrument":
                instrument,

            "s3_path":
                raw_item.get(
                    "S3Path"
                ),

            "content_type":
                raw_item.get(
                    "ContentType"
                ),

            "content_length":
                raw_item.get(
                    "ContentLength"
                ),

            "origin_date":
                raw_item.get(
                    "OriginDate"
                ),

            "publication_date":
                raw_item.get(
                    "PublicationDate"
                ),

            "modification_date":
                raw_item.get(
                    "ModificationDate"
                ),

            "online":
                raw_item.get(
                    "Online"
                ),

            "eviction_date":
                raw_item.get(
                    "EvictionDate"
                ),

            "checksum":
                raw_item.get(
                    "Checksum"
                ),

            "attributes":
                attr_dict,

            "geo_footprint":
                geo_footprint,

            "quicklook_asset":
                quicklook_asset,

            "quicklook_asset_id":
                quicklook_id,

            "collection_name":
                coll_config.get(
                    "cdse_collection"
                ),
        }

        # ----------------------------------------------------
        # Assets bundle
        # ----------------------------------------------------

        assets_bundle: Dict[
            str,
            Any,
        ] = {}

        assets_bundle[
            "download"
        ] = {

            "href":
                download_url,

            "type":
                "application/octet-stream",

            "requires_auth":
                True,
        }

        if quicklook_url:

            assets_bundle[
                "quicklook"
            ] = {

                "id":
                    quicklook_id,

                "href":
                    quicklook_url,

                "type":
                    str(
                        quicklook_asset.get(
                            "Type",
                            "image/jpeg",
                        )
                    ),

                "requires_auth":
                    False,
            }

        # Preserve all other assets.
        raw_assets = (
            raw_item.get(
                "Assets"
            )
            or []
        )

        if isinstance(
            raw_assets,
            list,
        ):

            assets_bundle[
                "catalogue_assets"
            ] = raw_assets

        # ----------------------------------------------------
        # SatelliteProduct
        # ----------------------------------------------------

        return SatelliteProduct(

            product_id=
                product_id,

            provider=
                self.name,

            collection=
                collection_key,

            platform=
                platform,

            instrument=
                instrument,

            modality=
                modality,

            acquisition_datetime=
                acquisition_datetime,

            processing_level=
                processing_level,

            cloud_cover=
                cloud_cover,

            bbox=
                bbox,

            crs=
                "EPSG:4326",

            resolution=
                resolution,

            available_bands=
                available_bands,

            product_url=
                product_url,

            thumbnail_url=
                quicklook_url,

            download_url=
                download_url,

            geo_footprint=
                geo_footprint,

            metadata=
                metadata_bundle,

            assets=
                assets_bundle,
        )

    # ========================================================
    # SEARCH
    # ========================================================

    def search(
        self,
        request: SearchRequest,
    ) -> List[SatelliteProduct]:
        """
        Search CDSE for products matching:

            collection
            date range
            bbox
            cloud cover
            limit
        """

        start_time = time.time()

        # ----------------------------------------------------
        # Normalize collection
        # ----------------------------------------------------

        collection_key = (
            normalize_collection_key(
                request.collection
            )
        )

        coll_config = (
            SUPPORTED_COLLECTIONS[
                collection_key
            ]
        )

        logger.info(
            "CDSE search started: "
            "collection=%s bbox=%s "
            "dates=%s -> %s limit=%d",
            collection_key,
            request.bbox,
            request.start_date,
            request.end_date,
            request.limit,
        )

        # ----------------------------------------------------
        # Validate limit
        # ----------------------------------------------------

        try:

            limit = int(
                request.limit
            )

        except (
            TypeError,
            ValueError,
        ):

            raise InvalidSearchRequestError(
                "limit must be an integer."
            )

        if limit < 1:
            raise InvalidSearchRequestError(
                "limit must be at least 1."
            )

        if limit > 100:
            raise InvalidSearchRequestError(
                "limit cannot exceed 100."
            )

        # ----------------------------------------------------
        # Build request
        # ----------------------------------------------------

        params = (
            self._build_odata_params(
                request,
                coll_config,
            )
        )

        # Ensure our validated limit is used.
        params[
            "$top"
        ] = limit

        logger.debug(
            "CDSE OData params: %s",
            params,
        )

        # ----------------------------------------------------
        # Request
        # ----------------------------------------------------

        raw_response = (
            self._execute_request(
                CDSE_CATALOGUE_URL,
                params=params,
            )
        )

        raw_items = (
            raw_response.get(
                "value",
                [],
            )
        )

        if not isinstance(
            raw_items,
            list,
        ):
            raise SatelliteSearchError(
                "CDSE returned an invalid "
                "'value' collection."
            )

        logger.info(
            "CDSE returned %d raw products "
            "in %.2fs.",
            len(raw_items),
            time.time()
            - start_time,
        )

        # ----------------------------------------------------
        # Normalize
        # ----------------------------------------------------

        normalized_products: List[
            SatelliteProduct
        ] = []

        for raw_item in raw_items:

            try:

                product = (
                    self._normalize_product(
                        raw_item,
                        collection_key,
                    )
                )

                # ------------------------------------------------
                # Spatial verification
                # ------------------------------------------------

                if (
                    product.bbox
                    and not intersects_bbox(
                        product.bbox,
                        request.bbox,
                    )
                ):

                    logger.debug(
                        "Skipping product %s: "
                        "bbox does not intersect "
                        "requested bbox.",
                        product.product_id,
                    )

                    continue

                # ------------------------------------------------
                # Cloud verification
                # ------------------------------------------------

                if (
                    request.max_cloud_cover
                    is not None
                    and product.cloud_cover
                    is not None
                ):

                    if (
                        product.cloud_cover
                        > request.max_cloud_cover
                    ):

                        logger.debug(
                            "Skipping product %s: "
                            "cloud cover %.2f > %.2f.",
                            product.product_id,
                            product.cloud_cover,
                            request.max_cloud_cover,
                        )

                        continue

                # ------------------------------------------------
                # Defensive collection verification
                # ------------------------------------------------

                expected_collection = (
                    coll_config[
                        "cdse_collection"
                    ]
                )

                actual_collection = (
                    (
                        raw_item.get(
                            "Collection"
                        )
                        or {}
                    )
                )

                if isinstance(
                    actual_collection,
                    dict,
                ):

                    actual_collection_name = str(
                        actual_collection.get(
                            "Name",
                            "",
                        )
                    ).upper()

                    if (
                        actual_collection_name
                        and actual_collection_name
                        != expected_collection
                    ):

                        logger.warning(
                            "Skipping product %s: "
                            "expected collection %s "
                            "but received %s.",
                            product.product_id,
                            expected_collection,
                            actual_collection_name,
                        )

                        continue

                # ------------------------------------------------
                # Product type defensive verification
                # ------------------------------------------------

                expected_product_types = (
                    coll_config.get(
                        "product_types"
                    )
                    or []
                )

                actual_product_type = (
                    product.metadata.get(
                        "product_type"
                    )
                )

                if (
                    expected_product_types
                    and actual_product_type
                    and actual_product_type
                    not in expected_product_types
                ):

                    logger.warning(
                        "Skipping product %s: "
                        "unexpected product type %s.",
                        product.product_id,
                        actual_product_type,
                    )

                    continue

                normalized_products.append(
                    product
                )

                if (
                    len(
                        normalized_products
                    )
                    >= limit
                ):
                    break

            except Exception as exc:

                logger.warning(
                    "Failed to normalize CDSE "
                    "product %s: %s",
                    raw_item.get(
                        "Id"
                    ),
                    exc,
                )

                continue

        logger.info(
            "CDSE search completed in %.2fs: "
            "%d products returned.",
            time.time()
            - start_time,
            len(
                normalized_products
            ),
        )

        return normalized_products

    # ========================================================
    # GET PRODUCT
    # ========================================================

    def get_product(
        self,
        product_id: str,
    ) -> SatelliteProduct:
        """
        Retrieve a single CDSE product.

        Unlike the previous implementation, this detects
        Sentinel-1 vs Sentinel-2 instead of always assuming
        Sentinel-2.
        """

        if (
            not product_id
            or not isinstance(
                product_id,
                str,
            )
        ):

            raise SatelliteProviderError(
                "Product ID must be "
                "a non-empty string."
            )

        clean_id = (
            product_id.strip()
        )

        if not clean_id:

            raise SatelliteProviderError(
                "Product ID must be "
                "a non-empty string."
            )

        logger.info(
            "Retrieving CDSE product metadata: %s",
            clean_id,
        )

        url = (
            f"{CDSE_CATALOGUE_URL}"
            f"({clean_id})"
        )

        params = {
            "$expand":
                "Attributes,Assets",
        }

        raw_item = (
            self._execute_request(
                url,
                params=params,
            )
        )

        collection_key = (
            self._detect_collection_key(
                raw_item
            )
        )

        return (
            self._normalize_product(
                raw_item,
                collection_key,
            )
        )

    # ========================================================
    # DOWNLOAD URL
    # ========================================================

    def get_download_url(
        self,
        product_id: str,
    ) -> str:
        """
        Return the official CDSE product download URL.

        Authentication is required when the URL is actually used.
        """

        if (
            not product_id
            or not isinstance(
                product_id,
                str,
            )
        ):

            raise SatelliteProviderError(
                "Product ID must be "
                "a non-empty string."
            )

        clean_id = (
            product_id.strip()
        )

        if not clean_id:

            raise SatelliteProviderError(
                "Product ID must be "
                "a non-empty string."
            )

        return (
            f"{CDSE_DOWNLOAD_BASE_URL}"
            f"({clean_id})/$value"
        )

    # ========================================================
    # QUICKLOOK URL
    # ========================================================

    def get_quicklook_url(
        self,
        product_id: str,
    ) -> Optional[str]:
        """
        Retrieve a product and return its genuine CDSE
        quicklook asset URL.
        """

        product = (
            self.get_product(
                product_id
            )
        )

        if not product.assets:
            return None

        quicklook = (
            product.assets.get(
                "quicklook"
            )
        )

        if not isinstance(
            quicklook,
            dict,
        ):
            return None

        href = quicklook.get(
            "href"
        )

        if not href:
            return None

        return str(
            href
        )