"""
Base Provider Abstraction & Normalized Data Contracts for SatQuery AI.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SearchRequest:
    """Standardized search query across all satellite data providers."""
    provider: str
    collections: List[str] = field(default_factory=list)
    bbox: Optional[Tuple[float, float, float, float]] = None  # (minLon, minLat, maxLon, maxLat)
    datetime_range: Optional[str] = None  # "YYYY-MM-DD" or "YYYY-MM-DD/YYYY-MM-DD"
    limit: int = 10
    filters: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate bounding box and limit."""
        if self.limit < 1 or self.limit > 100:
            raise ValueError(f"Search limit must be between 1 and 100, got {self.limit}")
        if self.bbox:
            min_lon, min_lat, max_lon, max_lat = self.bbox
            if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
                raise ValueError(f"Invalid longitude in bbox: {self.bbox}")
            if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
                raise ValueError(f"Invalid latitude in bbox: {self.bbox}")
            if min_lon > max_lon or min_lat > max_lat:
                raise ValueError(f"Invalid bbox coordinates (min > max): {self.bbox}")


@dataclass
class AssetMetadata:
    """Metadata describing an individual downloadable raster or metadata file asset."""
    key: str
    href: str
    title: Optional[str] = None
    media_type: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    band_name: Optional[str] = None
    size_bytes: Optional[int] = None


@dataclass
class ProductMetadata:
    """Normalized satellite product metadata."""
    provider: str
    product_id: str
    collection: str
    title: str
    datetime: str
    bbox: Optional[Tuple[float, float, float, float]] = None
    geometry: Optional[Dict[str, Any]] = None
    platform: Optional[str] = None
    instrument: Optional[str] = None
    product_type: Optional[str] = None
    cloud_cover: Optional[float] = None
    online: bool = True
    is_downloadable: bool = True
    assets: List[AssetMetadata] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "product_id": self.product_id,
            "collection": self.collection,
            "title": self.title,
            "datetime": self.datetime,
            "bbox": list(self.bbox) if self.bbox else None,
            "geometry": self.geometry,
            "platform": self.platform,
            "instrument": self.instrument,
            "product_type": self.product_type,
            "cloud_cover": self.cloud_cover,
            "online": self.online,
            "is_downloadable": self.is_downloadable,
            "assets": [
                {
                    "key": a.key,
                    "href": a.href,
                    "title": a.title,
                    "media_type": a.media_type,
                    "roles": a.roles,
                    "band_name": a.band_name,
                    "size_bytes": a.size_bytes,
                }
                for a in self.assets
            ],
            "properties": self.properties,
        }


@dataclass
class SearchResponse:
    """Standardized search response containing normalized product items."""
    provider: str
    total_matched: int
    items: List[ProductMetadata]
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "total_matched": self.total_matched,
            "items": [item.to_dict() for item in self.items],
            "context": self.context,
        }


@dataclass
class DownloadResult:
    """Result of materializing a satellite product locally."""
    provider: str
    product_id: str
    collection: str
    local_path: str
    file_size_bytes: int
    cached: bool = False
    download_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    assets_extracted: List[str] = field(default_factory=list)


class SatelliteDataProvider(abc.ABC):
    """Abstract interface for all satellite data access providers."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider unique key (e.g. 'bhoonidhi')."""
        pass

    @property
    @abc.abstractmethod
    def display_name(self) -> str:
        """Human-readable provider label (e.g. 'ISRO / NRSC Bhoonidhi')."""
        pass

    @property
    @abc.abstractmethod
    def supported_collections(self) -> List[str]:
        """List of supported satellite mission/sensor collections."""
        pass

    @abc.abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with provider using configured credentials."""
        pass

    @abc.abstractmethod
    def search(self, request: SearchRequest) -> SearchResponse:
        """Search catalogue for satellite observations matching criteria."""
        pass

    @abc.abstractmethod
    def get_product(self, product_id: str, collection: Optional[str] = None) -> Optional[ProductMetadata]:
        """Retrieve detailed metadata for a specific product."""
        pass

    @abc.abstractmethod
    def download(
        self,
        product_id: str,
        destination_dir: Path,
        collection: Optional[str] = None,
        force_redownload: bool = False,
    ) -> DownloadResult:
        """Download product to local storage, returning local path and metadata."""
        pass

    @abc.abstractmethod
    def health_check(self) -> bool:
        """Check availability and connectivity of provider service."""
        pass
