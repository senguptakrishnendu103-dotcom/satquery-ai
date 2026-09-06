"""
ISRO / NRSC Bhoonidhi Satellite Data Provider Implementation.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.providers.base import (
    AssetMetadata,
    DownloadResult,
    ProductMetadata,
    SatelliteDataProvider,
    SearchRequest,
    SearchResponse,
)
from app.providers.exceptions import (
    InvalidSearchRequestError,
    ProductNotAvailableError,
    ProductNotFoundError,
    ProviderAuthError,
    ProviderError,
    ProviderNetworkError,
    ProviderRateLimitError,
)

logger = logging.getLogger("satquery.providers.bhoonidhi")

SUPPORTED_ISRO_COLLECTIONS = [
    "RESOURCESAT-2A",
    "RESOURCESAT-2",
    "CARTOSAT-1",
    "CARTOSAT-2",
    "RISAT-1",
    "EOS-04",
    "EOS-06",
]


class BhoonidhiProvider(SatelliteDataProvider):
    """
    Secure client implementation for the official ISRO / NRSC Bhoonidhi Open Data Hub.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._base_url = (
            base_url
            or os.getenv("BHOONIDHI_API_BASE_URL")
            or "https://bhoonidhi.nrsc.gov.in/api/v1"
        ).rstrip("/")

        self._username = username or os.getenv("BHOONIDHI_USERNAME")
        self._password = password or os.getenv("BHOONIDHI_PASSWORD")
        self._api_key = api_key or os.getenv("BHOONIDHI_API_KEY")
        self._timeout = timeout_seconds

        # Token state management
        self._access_token: Optional[str] = None
        self._token_expiry_timestamp: float = 0.0
        self._token_lock = threading.Lock()

    @property
    def name(self) -> str:
        return "bhoonidhi"

    @property
    def display_name(self) -> str:
        return "ISRO / NRSC Bhoonidhi"

    @property
    def supported_collections(self) -> List[str]:
        return list(SUPPORTED_ISRO_COLLECTIONS)

    def has_configured_credentials(self) -> bool:
        """Check if username and password or API key are provided."""
        return bool((self._username and self._password) or self._api_key)

    def authenticate(self, force_refresh: bool = False) -> bool:
        """
        Authenticate or reuse cached token.
        Avoids making repeated authentication calls if the current token is still valid.
        """
        with self._token_lock:
            now = time.time()
            if (
                not force_refresh
                and self._access_token
                and now < self._token_expiry_timestamp - 60.0
            ):
                return True

            if not self.has_configured_credentials():
                # Allow public search if supported, but flag credential requirement
                logger.info("Bhoonidhi credentials not configured. Public search only.")
                return False

            auth_url = f"{self._base_url}/auth/token"
            payload = {
                "username": self._username,
                "password": self._password,
            }
            if self._api_key:
                payload["api_key"] = self._api_key

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                auth_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "SatQuery-AI/1.1 (ISRO-Bhoonidhi-Adapter)",
                },
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    self._access_token = (
                        resp_data.get("access_token")
                        or resp_data.get("token")
                        or resp_data.get("jwt")
                    )
                    expires_in = float(resp_data.get("expires_in", 3600))
                    self._token_expiry_timestamp = now + expires_in
                    logger.info("Successfully authenticated with ISRO Bhoonidhi.")
                    return True
            except urllib.error.HTTPError as err:
                if err.code in (401, 403):
                    logger.error("ISRO Bhoonidhi authentication failed: Invalid credentials.")
                    raise ProviderAuthError("ISRO Bhoonidhi authentication failed. Check credentials.")
                elif err.code == 429:
                    raise ProviderRateLimitError("ISRO Bhoonidhi rate limit reached. Please retry later.")
                else:
                    raise ProviderNetworkError(f"ISRO Bhoonidhi auth service error: HTTP {err.code}")
            except Exception as e:
                raise ProviderNetworkError(f"Failed to connect to ISRO Bhoonidhi auth endpoint: {e}")

    def _get_auth_headers(self) -> Dict[str, str]:
        """Build request headers with bearer token or api key."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "SatQuery-AI/1.1 (ISRO-Bhoonidhi-Adapter)",
        }
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        elif self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    def search(self, request: SearchRequest) -> SearchResponse:
        """
        Execute search query against ISRO Bhoonidhi catalogue.
        """
        request.validate()

        # Attempt auth if credentials exist
        if self.has_configured_credentials() and not self._access_token:
            try:
                self.authenticate()
            except ProviderAuthError:
                raise
            except Exception as e:
                logger.warning(f"Bhoonidhi authentication attempt failed: {e}. Proceeding with public search.")

        # Build query params
        params: Dict[str, Any] = {
            "limit": request.limit,
        }
        if request.collections:
            params["collection"] = ",".join(request.collections)
        if request.bbox:
            min_lon, min_lat, max_lon, max_lat = request.bbox
            params["bbox"] = f"{min_lon},{min_lat},{max_lon},{max_lat}"
        if request.datetime_range:
            params["datetime"] = request.datetime_range

        # Property filters
        for k, v in request.filters.items():
            if v is not None:
                params[k] = str(v)

        query_string = urllib.parse.urlencode(params)
        search_url = f"{self._base_url}/search?{query_string}"

        req = urllib.request.Request(
            search_url,
            headers=self._get_auth_headers(),
            method="GET",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return self._normalize_search_response(data)
        except urllib.error.HTTPError as err:
            if err.code == 401:
                # Refresh token and retry once
                if self.has_configured_credentials():
                    self.authenticate(force_refresh=True)
                    req = urllib.request.Request(
                        search_url,
                        headers=self._get_auth_headers(),
                        method="GET",
                    )
                    try:
                        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                            data = json.loads(resp.read().decode("utf-8"))
                            return self._normalize_search_response(data)
                    except Exception as retry_err:
                        raise ProviderError(f"Bhoonidhi search failed after re-auth: {retry_err}")
                raise ProviderAuthError("Bhoonidhi session expired or unauthorized.")
            elif err.code == 404:
                return SearchResponse(provider="bhoonidhi", total_matched=0, items=[])
            elif err.code == 429:
                raise ProviderRateLimitError("Bhoonidhi search rate limit exceeded. Please wait.")
            elif err.code >= 500:
                raise ProviderNetworkError(f"ISRO Bhoonidhi service returned server error: HTTP {err.code}")
            else:
                raise ProviderError(f"ISRO Bhoonidhi search failed: HTTP {err.code}")
        except urllib.error.URLError as err:
            raise ProviderNetworkError(f"Unable to reach ISRO Bhoonidhi catalogue: {err}")

    def _normalize_search_response(self, raw_data: Dict[str, Any]) -> SearchResponse:
        """
        Normalize Bhoonidhi JSON response (GeoJSON FeatureCollection or STAC)
        into standard SearchResponse.
        """
        items: List[ProductMetadata] = []
        features = raw_data.get("features") or raw_data.get("items") or raw_data.get("products") or []
        total_matched = int(raw_data.get("total_matched") or raw_data.get("numberMatched") or len(features))

        for feat in features:
            props = feat.get("properties") or feat
            product_id = feat.get("id") or props.get("product_id") or props.get("identifier") or props.get("id")
            if not product_id:
                continue

            collection = (
                feat.get("collection")
                or props.get("collection")
                or props.get("mission")
                or props.get("satellite")
                or "ISRO_GENERIC"
            )

            datetime_str = (
                props.get("datetime")
                or props.get("acquisition_date")
                or props.get("startTime")
                or props.get("date")
                or datetime.utcnow().strftime("%Y-%m-%d")
            )

            bbox_list = feat.get("bbox") or props.get("bbox")
            bbox_tuple = None
            if bbox_list and len(bbox_list) == 4:
                bbox_tuple = (float(bbox_list[0]), float(bbox_list[1]), float(bbox_list[2]), float(bbox_list[3]))

            # Discovered assets
            assets: List[AssetMetadata] = []
            raw_assets = feat.get("assets") or props.get("assets") or {}
            if isinstance(raw_assets, dict):
                for key, val in raw_assets.items():
                    if isinstance(val, dict) and "href" in val:
                        assets.append(
                            AssetMetadata(
                                key=key,
                                href=val["href"],
                                title=val.get("title"),
                                media_type=val.get("type"),
                                roles=val.get("roles", []),
                                band_name=val.get("band_name") or key,
                                size_bytes=val.get("size"),
                            )
                        )

            is_online = bool(props.get("online", True))
            is_downloadable = bool(props.get("is_downloadable", True))

            items.append(
                ProductMetadata(
                    provider="bhoonidhi",
                    product_id=str(product_id),
                    collection=str(collection),
                    title=str(props.get("title") or props.get("product_name") or product_id),
                    datetime=str(datetime_str),
                    bbox=bbox_tuple,
                    geometry=feat.get("geometry"),
                    platform=props.get("platform") or props.get("satellite") or collection,
                    instrument=props.get("instrument") or props.get("sensor"),
                    product_type=props.get("product_type") or props.get("processing_level"),
                    cloud_cover=float(props["cloud_cover"]) if props.get("cloud_cover") is not None else None,
                    online=is_online,
                    is_downloadable=is_downloadable,
                    assets=assets,
                    properties=props,
                )
            )

        return SearchResponse(
            provider="bhoonidhi",
            total_matched=total_matched,
            items=items,
            context={"provider": "bhoonidhi", "timestamp": datetime.utcnow().isoformat() + "Z"},
        )

    def get_product(self, product_id: str, collection: Optional[str] = None) -> Optional[ProductMetadata]:
        """Fetch detailed metadata for a single product."""
        safe_id = self._sanitize_product_id(product_id)
        url = f"{self._base_url}/products/{safe_id}"
        if collection:
            url += f"?collection={urllib.parse.quote(collection)}"

        req = urllib.request.Request(
            url,
            headers=self._get_auth_headers(),
            method="GET",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                response = self._normalize_search_response({"features": [data]})
                return response.items[0] if response.items else None
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return None
            elif err.code == 401:
                raise ProviderAuthError("Authentication required for product details.")
            else:
                raise ProviderError(f"Failed to fetch product details: HTTP {err.code}")
        except Exception as e:
            raise ProviderNetworkError(f"Network error fetching product details: {e}")

    def download(
        self,
        product_id: str,
        destination_dir: Path,
        collection: Optional[str] = None,
        force_redownload: bool = False,
    ) -> DownloadResult:
        """
        Securely download satellite observation package from Bhoonidhi.
        Includes path-traversal prevention, local caching, and file integrity checks.
        """
        safe_id = self._sanitize_product_id(product_id)
        destination_dir = Path(destination_dir).resolve()
        destination_dir.mkdir(parents=True, exist_ok=True)

        # Cache check: if product was already materialized in destination_dir
        cached_candidates = list(destination_dir.glob(f"{safe_id}*"))
        if not force_redownload and cached_candidates:
            target_path = cached_candidates[0]
            if target_path.is_file() and target_path.stat().st_size > 0:
                logger.info(f"Using cached Bhoonidhi product: {target_path}")
                return DownloadResult(
                    provider="bhoonidhi",
                    product_id=safe_id,
                    collection=collection or "ISRO",
                    local_path=str(target_path),
                    file_size_bytes=target_path.stat().st_size,
                    cached=True,
                )

        if self.has_configured_credentials() and not self._access_token:
            self.authenticate()

        download_url = f"{self._base_url}/products/{safe_id}/download"
        req = urllib.request.Request(
            download_url,
            headers=self._get_auth_headers(),
            method="GET",
        )

        target_file = destination_dir / f"{safe_id}.zip"

        try:
            with urllib.request.urlopen(req, timeout=120.0) as resp:
                # Check for direct file stream
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    payload = json.loads(resp.read().decode("utf-8"))
                    if payload.get("status") == "order_only" or not payload.get("download_url"):
                        raise ProductNotAvailableError(
                            f"Product '{safe_id}' is order-only on Bhoonidhi and not available for direct download."
                        )

                with open(target_file, "wb") as f_out:
                    shutil.copyfileobj(resp, f_out)

                size_bytes = target_file.stat().st_size
                if size_bytes == 0:
                    raise ProviderError("Downloaded product file is empty (0 bytes).")

                return DownloadResult(
                    provider="bhoonidhi",
                    product_id=safe_id,
                    collection=collection or "ISRO",
                    local_path=str(target_file),
                    file_size_bytes=size_bytes,
                    cached=False,
                )

        except urllib.error.HTTPError as err:
            if err.code == 401:
                raise ProviderAuthError("Unauthorized download request on Bhoonidhi.")
            elif err.code == 404:
                raise ProductNotFoundError(f"Product '{safe_id}' not found on Bhoonidhi.")
            elif err.code in (412, 403):
                raise ProductNotAvailableError(
                    f"Product '{safe_id}' is restricted or order-only on Bhoonidhi."
                )
            elif err.code == 429:
                raise ProviderRateLimitError("Download rate limit reached on Bhoonidhi.")
            else:
                raise ProviderNetworkError(f"Bhoonidhi download failed with HTTP {err.code}")
        except urllib.error.URLError as err:
            raise ProviderNetworkError(f"Connection failed during download: {err}")

    def health_check(self) -> bool:
        """Check if Bhoonidhi service is online."""
        url = f"{self._base_url}/health"
        req = urllib.request.Request(url, headers={"User-Agent": "SatQuery-AI/1.1"}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    @staticmethod
    def _sanitize_product_id(product_id: str) -> str:
        """Enforce strict alpha-numeric identifier pattern to prevent path traversal."""
        if not product_id or not isinstance(product_id, str):
            raise InvalidSearchRequestError("Invalid product ID: Empty or non-string.")
        clean_id = product_id.strip()
        if "/" in clean_id or "\\" in clean_id or ".." in clean_id or not re.match(r"^[a-zA-Z0-9_.-]+$", clean_id):
            raise InvalidSearchRequestError(f"Potential path traversal or invalid characters in product ID: {product_id}")
        return clean_id
