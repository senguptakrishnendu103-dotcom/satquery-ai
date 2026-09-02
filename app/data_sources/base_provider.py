"""
Base Data Provider Abstraction & Data Models for SatQuery AI.

This module defines the abstract base class `SatelliteDataProvider`, alongside
the typed request (`SearchRequest`) and response metadata (`SatelliteProduct`)
structures used across the data search architecture.
"""

from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple, Union
from pydantic import BaseModel, Field, model_validator

from app.data_sources.exceptions import InvalidSearchRequestError


def parse_datetime(val: Union[str, date, datetime]) -> datetime:
    """Helper utility to parse dates or string ISO representations into datetime objects."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime.combine(val, datetime.min.time())
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            raise ValueError("Date string cannot be empty.")
        # Attempt common ISO formats
        for fmt in (
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(val_str, fmt)
            except ValueError:
                pass
        # Standard datetime.fromisoformat fallback
        try:
            return datetime.fromisoformat(val_str.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"Unable to parse date string '{val}' into valid datetime.")
    raise ValueError(f"Invalid date type '{type(val).__name__}'. Expected datetime, date, or str.")


class SearchRequest(BaseModel):
    """
    Structured search request for querying satellite data providers.

    Bounding Box format: [min_lon, min_lat, max_lon, max_lat]
    """
    bbox: Tuple[float, float, float, float] = Field(
        ...,
        description="Bounding box [min_lon, min_lat, max_lon, max_lat] in WGS84 geographic coordinates."
    )
    start_date: Union[str, date, datetime] = Field(
        ...,
        description="Beginning of acquisition date window."
    )
    end_date: Union[str, date, datetime] = Field(
        ...,
        description="End of acquisition date window."
    )
    collection: str = Field(
        ...,
        description="Target satellite collection identifier (e.g. 'sentinel-2', 'landsat-8')."
    )
    max_cloud_cover: Optional[float] = Field(
        default=None,
        description="Maximum allowed cloud cover percentage (0.0 to 100.0)."
    )
    limit: int = Field(
        default=20,
        description="Maximum number of satellite products to return."
    )
    platform: Optional[str] = Field(
        default=None,
        description="Optional satellite platform (e.g. 'Sentinel-2A', 'Sentinel-2B')."
    )
    processing_level: Optional[str] = Field(
        default=None,
        description="Optional processing level (e.g. 'L1C', 'L2A')."
    )
    query_params: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional provider-specific query parameters."
    )

    @model_validator(mode="before")
    @classmethod
    def validate_request_parameters(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # 1. Collection validation
        collection = data.get("collection")
        if not collection or not isinstance(collection, str) or not collection.strip():
            raise InvalidSearchRequestError("Collection parameter must be a non-empty string.")

        # 2. Limit validation
        limit = data.get("limit", 20)
        if not isinstance(limit, int) or limit <= 0:
            raise InvalidSearchRequestError(f"Limit must be a positive integer. Got: {limit}")

        # 3. Bounding box validation
        bbox = data.get("bbox")
        if not bbox or not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            raise InvalidSearchRequestError("Bounding box must be a list/tuple of 4 floats: [min_lon, min_lat, max_lon, max_lat].")

        try:
            min_lon, min_lat, max_lon, max_lat = [float(x) for x in bbox]
        except (ValueError, TypeError) as e:
            raise InvalidSearchRequestError(f"Bounding box elements must be numeric floats. Error: {str(e)}")

        if not (-180.0 <= min_lon <= 180.0):
            raise InvalidSearchRequestError(f"Minimum longitude ({min_lon}) out of valid range [-180, 180].")
        if not (-180.0 <= max_lon <= 180.0):
            raise InvalidSearchRequestError(f"Maximum longitude ({max_lon}) out of valid range [-180, 180].")
        if not (-90.0 <= min_lat <= 90.0):
            raise InvalidSearchRequestError(f"Minimum latitude ({min_lat}) out of valid range [-90, 90].")
        if not (-90.0 <= max_lat <= 90.0):
            raise InvalidSearchRequestError(f"Maximum latitude ({max_lat}) out of valid range [-90, 90].")

        if min_lon > max_lon:
            raise InvalidSearchRequestError(f"Invalid bounding box: min_lon ({min_lon}) is greater than max_lon ({max_lon}).")
        if min_lat > max_lat:
            raise InvalidSearchRequestError(f"Invalid bounding box: min_lat ({min_lat}) is greater than max_lat ({max_lat}).")

        # 4. Date validation
        start_date_raw = data.get("start_date")
        end_date_raw = data.get("end_date")

        if start_date_raw is None or end_date_raw is None:
            raise InvalidSearchRequestError("Both start_date and end_date are required.")

        try:
            parsed_start = parse_datetime(start_date_raw)
        except Exception as e:
            raise InvalidSearchRequestError(f"Invalid start_date '{start_date_raw}': {str(e)}")

        try:
            parsed_end = parse_datetime(end_date_raw)
        except Exception as e:
            raise InvalidSearchRequestError(f"Invalid end_date '{end_date_raw}': {str(e)}")

        if parsed_start > parsed_end:
            raise InvalidSearchRequestError(
                f"Invalid date range: start_date ({parsed_start.isoformat()}) is after end_date ({parsed_end.isoformat()})."
            )

        # 5. Max cloud cover validation
        max_cloud = data.get("max_cloud_cover")
        if max_cloud is not None:
            try:
                max_cloud_val = float(max_cloud)
                if not (0.0 <= max_cloud_val <= 100.0):
                    raise InvalidSearchRequestError(f"max_cloud_cover must be between 0.0 and 100.0. Got: {max_cloud_val}")
            except (ValueError, TypeError):
                raise InvalidSearchRequestError(f"max_cloud_cover must be a valid float. Got: {max_cloud}")

        return data


class SatelliteProduct(BaseModel):
    """
    Provider-independent representation of a satellite product / scene metadata.

    Fields that are unavailable are set to None or empty structures.
    Do NOT invent values for missing metadata.
    """
    product_id: str = Field(..., description="Unique product identifier from the data provider.")
    provider: str = Field(..., description="Name of the satellite data provider (e.g. 'copernicus').")
    collection: str = Field(..., description="Satellite collection (e.g. 'sentinel-2').")
    platform: Optional[str] = Field(default=None, description="Satellite platform (e.g. 'Sentinel-2A').")
    instrument: Optional[str] = Field(default=None, description="Sensor instrument (e.g. 'MSI', 'C-SAR').")
    modality: Optional[str] = Field(default=None, description="Imaging modality (e.g. 'optical', 'sar', 'multispectral').")
    acquisition_datetime: Optional[datetime] = Field(default=None, description="Timestamp of observation acquisition.")
    processing_level: Optional[str] = Field(default=None, description="Processing level (e.g. 'L2A', 'GRD').")
    cloud_cover: Optional[float] = Field(default=None, description="Cloud cover percentage (0.0 to 100.0).")
    bbox: Optional[Tuple[float, float, float, float]] = Field(default=None, description="Product spatial extent [min_lon, min_lat, max_lon, max_lat].")
    crs: Optional[str] = Field(default=None, description="Coordinate Reference System (e.g. 'EPSG:4326').")
    resolution: Optional[float] = Field(default=None, description="Spatial resolution in meters per pixel.")
    available_bands: List[str] = Field(default_factory=list, description="List of available spectral bands (e.g. ['B02', 'B03', 'B04', 'B08']).")
    product_url: Optional[str] = Field(default=None, description="Provider product details web URL.")
    thumbnail_url: Optional[str] = Field(default=None, description="Preview thumbnail image URL.")
    download_url: Optional[str] = Field(default=None, description="Direct download URL if available.")
    geo_footprint: Optional[Dict[str, Any]] = Field(default=None, description="GeoJSON polygon geometry footprint of the product observation area.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Raw provider metadata dictionary.")
    assets: Dict[str, Any] = Field(default_factory=dict, description="Assets dictionary mapping keys to asset details.")


class SatelliteDataProvider(ABC):
    """
    Abstract Base Class for external satellite data providers.

    This class defines the interface required for registering and querying
    external data providers without coupling the core application logic to any
    specific satellite API implementation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier name (e.g., 'copernicus')."""
        pass

    @property
    @abstractmethod
    def supported_collections(self) -> List[str]:
        """List of satellite collections supported by this provider."""
        pass

    @property
    @abstractmethod
    def supported_modalities(self) -> List[str]:
        """List of remote-sensing modalities supported by this provider."""
        pass

    @abstractmethod
    def search(self, request: SearchRequest) -> List[SatelliteProduct]:
        """
        Search provider catalogue for satellite products matching the request parameters.

        Args:
            request: Validated SearchRequest object.

        Returns:
            List of SatelliteProduct metadata objects matching the search criteria.
        """
        pass

    @abstractmethod
    def get_product(self, product_id: str) -> SatelliteProduct:
        """
        Retrieve product metadata for a specific product ID.

        Args:
            product_id: Unique product identifier string.

        Returns:
            SatelliteProduct object.
        """
        pass

    @abstractmethod
    def get_download_url(self, product_id: str) -> str:
        """
        Retrieve direct download URL for a specific product ID.

        Args:
            product_id: Unique product identifier string.

        Returns:
            URL string for downloading the product asset.
        """
        pass
