"""
Copernicus Data Space Ecosystem (CDSE) Satellite Data Provider (Stage 2).

This module implements live catalogue search, spatial/temporal query construction,
and metadata normalization for Copernicus Sentinel-1 (SAR) and Sentinel-2 (Multispectral)
data via the official CDSE OData API v1 (https://catalogue.dataspace.copernicus.eu/odata/v1/Products).
"""

import os
import re
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Union
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

logger = logging.getLogger("satquery.data_sources.copernicus")

# Base CDSE OData Catalogue Endpoints
CDSE_CATALOGUE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
CDSE_DOWNLOAD_BASE_URL = "https://zipper.dataspace.copernicus.eu/odata/v1/Products"

# Supported Collection Configuration & Modality Mapping
SUPPORTED_COLLECTIONS: Dict[str, Dict[str, Any]] = {
    "sentinel-2": {
        "cdse_collection": "SENTINEL-2",
        "product_types": ["S2MSI2A", "S2MSI1C"],
        "modalities": ["optical", "multispectral"],
        "default_instrument": "MSI",
    },
    "sentinel-2-l2a": {
        "cdse_collection": "SENTINEL-2",
        "product_types": ["S2MSI2A"],
        "processing_level": "Level-2A",
        "modalities": ["optical", "multispectral"],
        "default_instrument": "MSI",
    },
    "sentinel-2-l1c": {
        "cdse_collection": "SENTINEL-2",
        "product_types": ["S2MSI1C"],
        "processing_level": "Level-1C",
        "modalities": ["optical", "multispectral"],
        "default_instrument": "MSI",
    },
    "sentinel-1": {
        "cdse_collection": "SENTINEL-1",
        "product_types": ["GRD"],
        "modalities": ["sar"],
        "default_instrument": "C-SAR",
    },
    "sentinel-1-grd": {
        "cdse_collection": "SENTINEL-1",
        "product_types": ["GRD"],
        "processing_level": "GRD",
        "modalities": ["sar"],
        "default_instrument": "C-SAR",
    },
}


def normalize_collection_key(raw_collection: str) -> str:
    """Normalize raw collection identifier strings (e.g. 'SENTINEL_2_L2A' -> 'sentinel-2-l2a')."""
    if not raw_collection or not isinstance(raw_collection, str):
        raise InvalidSearchRequestError("Collection identifier must be a non-empty string.")

    cleaned = raw_collection.strip().lower().replace("_", "-")
    if cleaned in SUPPORTED_COLLECTIONS:
        return cleaned

    # Fallback checks for common aliases
    if "sentinel-2" in cleaned or "s2" in cleaned:
        if "l2a" in cleaned:
            return "sentinel-2-l2a"
        if "l1c" in cleaned:
            return "sentinel-2-l1c"
        return "sentinel-2"
    if "sentinel-1" in cleaned or "s1" in cleaned:
        return "sentinel-1"

    available = list(SUPPORTED_COLLECTIONS.keys())
    raise InvalidSearchRequestError(
        f"Unsupported collection '{raw_collection}'. Supported collections: {available}"
    )


def parse_wkt_footprint(
    footprint_raw: Optional[str]
) -> Tuple[Optional[Tuple[float, float, float, float]], Optional[Dict[str, Any]]]:
    """
    Parse a CDSE WKT Footprint string into a bounding box and GeoJSON polygon geometry.

    Example input: geography'SRID=4326;POLYGON ((-8.07 14.47, -8.07 13.47, -7.06 13.47, -7.06 14.47, -8.07 14.47))'
    """
    if not footprint_raw or not isinstance(footprint_raw, str):
        return None, None

    # Extract coordinate numbers
    coords_text = re.sub(r"^.*?POLYGON\s*\(\((.*?)\)\).*$", r"\1", footprint_raw, flags=re.DOTALL | re.IGNORECASE)
    pairs = re.findall(r"([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)", coords_text)

    if not pairs:
        return None, None

    points: List[List[float]] = []
    lons: List[float] = []
    lats: List[float] = []

    for lon_str, lat_str in pairs:
        try:
            lon = float(lon_str)
            lat = float(lat_str)
            points.append([lon, lat])
            lons.append(lon)
            lats.append(lat)
        except ValueError:
            continue

    if not lons or not lats:
        return None, None

    bbox = (min(lons), min(lats), max(lons), max(lats))
    geojson_polygon = {
        "type": "Polygon",
        "coordinates": [points]
    }
    return bbox, geojson_polygon


def intersects_bbox(
    bbox1: Tuple[float, float, float, float],
    bbox2: Tuple[float, float, float, float]
) -> bool:
    """Check if two bounding boxes [min_lon, min_lat, max_lon, max_lat] intersect."""
    min_lon1, min_lat1, max_lon1, max_lat1 = bbox1
    min_lon2, min_lat2, max_lon2, max_lat2 = bbox2
    return not (
        max_lon1 < min_lon2 or
        min_lon1 > max_lon2 or
        max_lat1 < min_lat2 or
        min_lat1 > max_lat2
    )


class CopernicusProvider(SatelliteDataProvider):
    """
    Copernicus Data Space Ecosystem (CDSE) Provider.

    Provides live CDSE OData API search, filtering, and normalization for
    Sentinel-1 (SAR) and Sentinel-2 (Multispectral) satellite imagery.
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        connect_timeout: float = 10.0,
        read_timeout: float = 30.0,
        max_retries: int = 3,
        session: Optional[requests.Session] = None,
    ):
        """Initialize Copernicus provider with optional credentials and timeouts."""
        self._username = username or os.getenv("CDSE_USERNAME") or os.getenv("SATQUERY_COPERNICUS_CLIENT_ID")
        self._password = password or os.getenv("CDSE_PASSWORD") or os.getenv("SATQUERY_COPERNICUS_CLIENT_SECRET")
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.max_retries = max_retries
        self._session = session or requests.Session()
        self._session.headers.update({
            "User-Agent": "SatQuery-AI/1.0",
            "Accept": "application/json"
        })
        logger.info("CopernicusProvider initialized for CDSE OData API (Credentials set: %s)", bool(self._username))

    @property
    def name(self) -> str:
        return "copernicus"

    @property
    def supported_collections(self) -> List[str]:
        return list(SUPPORTED_COLLECTIONS.keys())

    @property
    def supported_modalities(self) -> List[str]:
        return ["optical", "multispectral", "sar"]

    def health_check(self) -> bool:
        """Verify reachability of the public CDSE OData catalogue endpoint."""
        try:
            resp = self._session.get(
                CDSE_CATALOGUE_URL,
                params={"$top": 1},
                timeout=(self.connect_timeout, self.read_timeout)
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning("CDSE health check failed: %s", str(e))
            return False

    def _execute_request(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute HTTP GET request against CDSE OData API with retry logic for transient errors."""
        retry_count = 0
        backoff = 1.0

        while True:
            try:
                resp = self._session.get(
                    url,
                    params=params,
                    timeout=(self.connect_timeout, self.read_timeout)
                )

                if resp.status_code == 200:
                    try:
                        return resp.json()
                    except Exception as e:
                        raise SatelliteSearchError(f"Failed to parse JSON response from CDSE API: {str(e)}")

                if resp.status_code == 400:
                    raise InvalidSearchRequestError(f"CDSE catalogue request rejected (HTTP 400): {resp.text[:250]}")

                if resp.status_code in (401, 403):
                    raise SatelliteProviderError(f"CDSE authorization failed (HTTP {resp.status_code}): {resp.text[:250]}")

                if resp.status_code == 404:
                    raise SatelliteProviderError(f"CDSE product endpoint not found (HTTP 404): {url}")

                if resp.status_code in (429, 500, 502, 503, 504):
                    if retry_count < self.max_retries:
                        logger.warning(
                            "CDSE API returned HTTP %d. Retrying (%d/%d) in %.1fs...",
                            resp.status_code, retry_count + 1, self.max_retries, backoff
                        )
                        time.sleep(backoff)
                        retry_count += 1
                        backoff *= 2.0
                        continue
                    raise SatelliteSearchError(
                        f"CDSE API error HTTP {resp.status_code} after {self.max_retries} retries: {resp.text[:250]}"
                    )

                raise SatelliteSearchError(f"Unexpected CDSE API response HTTP {resp.status_code}: {resp.text[:250]}")

            except (requests.Timeout, requests.ConnectionError) as e:
                if retry_count < self.max_retries:
                    logger.warning(
                        "CDSE network exception (%s). Retrying (%d/%d) in %.1fs...",
                        type(e).__name__, retry_count + 1, self.max_retries, backoff
                    )
                    time.sleep(backoff)
                    retry_count += 1
                    backoff *= 2.0
                    continue
                raise SatelliteSearchError(f"Network error connecting to CDSE catalogue: {str(e)}")

    def _build_odata_filter(self, request: SearchRequest, coll_config: Dict[str, Any]) -> str:
        """Construct OData $filter clause from SearchRequest parameters."""
        filters = []

        # 1. Collection Name filter
        cdse_collection = coll_config["cdse_collection"]
        filters.append(f"Collection/Name eq '{cdse_collection}'")

        # 2. Temporal filter (ContentDate/Start in UTC ISO format)
        parsed_start = parse_datetime(request.start_date)
        parsed_end = parse_datetime(request.end_date)
        start_iso = parsed_start.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        end_iso = parsed_end.strftime("%Y-%m-%dT%H:%M:%S.999Z")
        filters.append(f"ContentDate/Start ge {start_iso} and ContentDate/Start le {end_iso}")

        # 3. Spatial Intersects filter
        min_lon, min_lat, max_lon, max_lat = request.bbox
        polygon_wkt = f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
        filters.append(f"OData.CSC.Intersects(area=geography'SRID=4326;{polygon_wkt}')")

        # 4. Processing level / Product type filter if configured
        if "product_types" in coll_config and len(coll_config["product_types"]) == 1:
            ptype = coll_config["product_types"][0]
            filters.append(f"contains(Name, '{ptype}')")

        return " and ".join(filters)

    def _build_odata_params(self, request: SearchRequest, coll_config: Dict[str, Any]) -> Dict[str, Any]:
        """Construct OData query dictionary."""
        params: Dict[str, Any] = {
            "$filter": self._build_odata_filter(request, coll_config),
            "$top": request.limit,
            "$expand": "Attributes",
        }

        # Sorting
        orderby = request.query_params.get("orderby", "ContentDate/Start desc") if request.query_params else "ContentDate/Start desc"
        params["$orderby"] = orderby

        # Skip offset for pagination
        if request.query_params and "skip" in request.query_params:
            params["$skip"] = request.query_params["skip"]

        return params

    def _extract_attributes_dict(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert CDSE Attributes list into a dictionary."""
        attrs_list = raw_item.get("Attributes", [])
        attr_dict = {}
        if isinstance(attrs_list, list):
            for attr in attrs_list:
                if isinstance(attr, dict) and "Name" in attr and "Value" in attr:
                    attr_dict[attr["Name"]] = attr["Value"]
        return attr_dict

    def _normalize_product(self, raw_item: Dict[str, Any], requested_collection: str) -> SatelliteProduct:
        """Normalize raw CDSE OData product JSON into provider-independent SatelliteProduct structure."""
        product_id = raw_item.get("Id", "")
        name = raw_item.get("Name", "")
        attr_dict = self._extract_attributes_dict(raw_item)

        # 1. Spatial extent & GeoJSON geometry
        footprint_raw = raw_item.get("Footprint")
        bbox, geo_footprint = parse_wkt_footprint(footprint_raw)

        # 2. Temporal metadata
        content_date = raw_item.get("ContentDate", {})
        start_str = content_date.get("Start") if isinstance(content_date, dict) else None
        acq_datetime = None
        if start_str:
            try:
                acq_datetime = parse_datetime(start_str)
            except Exception:
                acq_datetime = None

        # 3. Platform & Instrument
        platform_short = attr_dict.get("platformShortName")
        platform_serial = attr_dict.get("platformSerialIdentifier")
        if platform_short and platform_serial:
            platform = f"{platform_short.title()}{platform_serial.upper()}"
        elif platform_short:
            platform = platform_short.title()
        elif name.startswith("S2A"):
            platform = "Sentinel-2A"
        elif name.startswith("S2B"):
            platform = "Sentinel-2B"
        elif name.startswith("S1A"):
            platform = "Sentinel-1A"
        elif name.startswith("S1B"):
            platform = "Sentinel-1B"
        else:
            platform = None

        instrument = attr_dict.get("instrumentShortName")
        if not instrument:
            if "SENTINEL-2" in str(platform_short or "").upper() or name.startswith("S2"):
                instrument = "MSI"
            elif "SENTINEL-1" in str(platform_short or "").upper() or name.startswith("S1"):
                instrument = "C-SAR"

        # 4. Modality mapping
        coll_key = normalize_collection_key(requested_collection)
        coll_config = SUPPORTED_COLLECTIONS[coll_key]
        modalities = coll_config["modalities"]
        modality = modalities[0] if modalities else None

        # 5. Processing level
        processing_level = attr_dict.get("processingLevel") or attr_dict.get("productType")
        if not processing_level:
            if "MSIL2A" in name:
                processing_level = "L2A"
            elif "MSIL1C" in name:
                processing_level = "L1C"
            elif "GRD" in name:
                processing_level = "GRD"

        # 6. Cloud cover calculation (Sentinel-2 only)
        cloud_cover = None
        if "sar" not in modalities:
            raw_cloud = attr_dict.get("cloudCover") or attr_dict.get("cloudCoverPercentage")
            if raw_cloud is not None:
                try:
                    cloud_cover = float(raw_cloud)
                    cloud_cover = max(0.0, min(100.0, cloud_cover))
                except (ValueError, TypeError):
                    cloud_cover = None

        # 7. Web & download URLs
        product_url = f"{CDSE_CATALOGUE_URL}({product_id})" if product_id else None
        thumbnail_url = f"{CDSE_CATALOGUE_URL}({product_id})/$value" if product_id else None
        download_url = f"{CDSE_DOWNLOAD_BASE_URL}({product_id})/$value" if product_id else None

        # Metadata bundle
        metadata_bundle = {
            "name": name,
            "s3_path": raw_item.get("S3Path"),
            "content_length": raw_item.get("ContentLength"),
            "origin_date": raw_item.get("OriginDate"),
            "publication_date": raw_item.get("PublicationDate"),
            "attributes": attr_dict,
            "geo_footprint": geo_footprint,
        }

        assets_bundle = {
            "download": {"href": download_url, "type": "application/octet-stream"},
            "thumbnail": {"href": thumbnail_url, "type": "image/jpeg"},
        }

        return SatelliteProduct(
            product_id=product_id or name,
            provider=self.name,
            collection=coll_key,
            platform=platform,
            instrument=instrument,
            modality=modality,
            acquisition_datetime=acq_datetime,
            processing_level=processing_level,
            cloud_cover=cloud_cover,
            bbox=bbox,
            crs="EPSG:4326",
            resolution=10.0 if modality == "optical" else 20.0,
            available_bands=["B02", "B03", "B04", "B08"] if modality == "optical" else ["VV", "VH"],
            product_url=product_url,
            thumbnail_url=thumbnail_url,
            download_url=download_url,
            geo_footprint=geo_footprint,
            metadata=metadata_bundle,
            assets=assets_bundle,
        )

    def search(self, request: SearchRequest) -> List[SatelliteProduct]:
        """
        Search Copernicus Data Space Ecosystem catalogue for matching satellite products.

        Args:
            request: Validated SearchRequest parameters.

        Returns:
            List of normalized SatelliteProduct objects matching spatial, temporal, and filter parameters.
        """
        start_time = time.time()
        coll_key = normalize_collection_key(request.collection)
        coll_config = SUPPORTED_COLLECTIONS[coll_key]

        logger.info(
            "CDSE search started for collection '%s' (BBox: %s, Dates: %s to %s, Limit: %d)",
            coll_key, request.bbox, request.start_date, request.end_date, request.limit
        )

        # Build OData params & query filter
        params = self._build_odata_params(request, coll_config)
        logger.info("CDSE query constructed: filter='%s'", params.get("$filter"))

        # Fetch products from CDSE API
        raw_response = self._execute_request(CDSE_CATALOGUE_URL, params=params)
        raw_items = raw_response.get("value", [])

        elapsed = time.time() - start_time
        logger.info("CDSE response received in %.2fs (Raw items: %d)", elapsed, len(raw_items))

        normalized_products: List[SatelliteProduct] = []

        for item in raw_items:
            try:
                product = self._normalize_product(item, coll_key)

                # Client-side spatial intersection verification
                if product.bbox and not intersects_bbox(product.bbox, request.bbox):
                    logger.debug("Skipping product '%s': BBox %s does not intersect target %s", product.product_id, product.bbox, request.bbox)
                    continue

                # Client-side cloud cover filter
                if request.max_cloud_cover is not None and product.cloud_cover is not None:
                    if product.cloud_cover > request.max_cloud_cover:
                        logger.debug("Skipping product '%s': Cloud cover %.2f exceeds max allowed %.2f", product.product_id, product.cloud_cover, request.max_cloud_cover)
                        continue

                normalized_products.append(product)

                if len(normalized_products) >= request.limit:
                    break

            except Exception as e:
                logger.warning("Failed to normalize CDSE product item: %s. Error: %s", item.get("Id"), str(e))
                continue

        logger.info("CDSE search completed in %.2fs: %d normalized products returned.", time.time() - start_time, len(normalized_products))
        return normalized_products

    def get_product(self, product_id: str) -> SatelliteProduct:
        """Retrieve metadata for a specific product ID from CDSE."""
        if not product_id or not isinstance(product_id, str):
            raise SatelliteProviderError("Product ID must be a non-empty string.")

        logger.info("Retrieving CDSE product metadata for ID '%s'", product_id)
        url = f"{CDSE_CATALOGUE_URL}({product_id.strip()})"
        params = {"$expand": "Attributes"}
        raw_item = self._execute_request(url, params=params)
        return self._normalize_product(raw_item, "sentinel-2")

    def get_download_url(self, product_id: str) -> str:
        """Get direct download URL for a specific CDSE product."""
        if not product_id or not isinstance(product_id, str):
            raise SatelliteProviderError("Product ID must be a non-empty string.")
        return f"{CDSE_DOWNLOAD_BASE_URL}({product_id.strip()})/$value"
