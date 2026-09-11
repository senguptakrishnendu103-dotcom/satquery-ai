"""
Copernicus Data Space Ecosystem (CDSE) Satellite Data Provider Implementation.
"""

from __future__ import annotations

import json
import logging
import os
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

logger = logging.getLogger("satquery.providers.cdse")

SUPPORTED_CDSE_COLLECTIONS = [
    "SENTINEL-2",
    "S2MSI2A",
    "S2MSI1C",
    "SENTINEL-1",
    "SENTINEL-3",
    "SENTINEL-5P",
]


class CDSEProvider(SatelliteDataProvider):
    """
    Client implementation for the official Copernicus Data Space Ecosystem (CDSE).
    Provides search, metadata extraction, and streaming download capabilities for Sentinel missions.
    """

    def __init__(
        self,
        token_url: Optional[str] = None,
        catalogue_url: Optional[str] = None,
        download_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        timeout_seconds: float = 25.0,
    ) -> None:
        self._token_url = (
            token_url
            or os.getenv("CDSE_TOKEN_URL")
            or "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
        )
        self._catalogue_url = (
            catalogue_url
            or os.getenv("CDSE_CATALOGUE_URL")
            or "https://catalogue.dataspace.copernicus.eu"
        ).rstrip("/")

        self._download_url = (
            download_url
            or os.getenv("CDSE_DOWNLOAD_URL")
            or "https://zipper.dataspace.copernicus.eu/odata/v1/Products"
        ).rstrip("/")

        self._username = username or os.getenv("CDSE_USERNAME")
        self._password = password or os.getenv("CDSE_PASSWORD")
        self._client_id = client_id or os.getenv("CDSE_CLIENT_ID")
        self._client_secret = client_secret or os.getenv("CDSE_CLIENT_SECRET")
        self._timeout = timeout_seconds

        # Token state management
        self._search_access_token: Optional[str] = None
        self._search_token_expiry: float = 0.0
        self._download_access_token: Optional[str] = None
        self._download_token_expiry: float = 0.0
        self._token_lock = threading.Lock()

    @property
    def _access_token(self) -> Optional[str]:
        return self._search_access_token or self._download_access_token

    @_access_token.setter
    def _access_token(self, value: Optional[str]) -> None:
        self._search_access_token = value
        self._download_access_token = value

    @property
    def name(self) -> str:
        return "cdse"

    @property
    def display_name(self) -> str:
        return "Copernicus Data Space Ecosystem (CDSE)"

    @property
    def supported_collections(self) -> List[str]:
        return list(SUPPORTED_CDSE_COLLECTIONS)

    def _resolve_credentials(self) -> Tuple[str, str, str, str]:
        """Dynamically resolve credentials from instance or environment, stripping quotes/spaces."""
        user_val = (self._username or os.getenv("CDSE_USERNAME") or "").strip().strip("'\"")
        pass_val = (self._password or os.getenv("CDSE_PASSWORD") or "").strip().strip("'\"")
        cid_val = (self._client_id or os.getenv("CDSE_CLIENT_ID") or "").strip().strip("'\"")
        csec_val = (self._client_secret or os.getenv("CDSE_CLIENT_SECRET") or "").strip().strip("'\"")
        return user_val, pass_val, cid_val, csec_val

    def has_configured_credentials(self) -> bool:
        """Check if valid CDSE username/password or client_id/client_secret are configured."""
        invalid_placeholders = {
            "your_cdse_username",
            "your_cdse_password",
            "your_cdse_client_id",
            "your_cdse_client_secret",
            "",
        }

        user_val, pass_val, cid_val, csec_val = self._resolve_credentials()

        has_user_pass = bool(
            user_val
            and pass_val
            and user_val not in invalid_placeholders
            and pass_val not in invalid_placeholders
        )
        has_client_credentials = bool(
            cid_val
            and csec_val
            and cid_val not in invalid_placeholders
            and csec_val not in invalid_placeholders
        )

        return has_user_pass or has_client_credentials

    def authenticate(self, force_refresh: bool = False, for_download: bool = False) -> bool:
        """
        Authenticate with CDSE OAuth2 OIDC service.
        Retrieves and caches JWT bearer access token.
        Uses grant_type=password (cdse-public) for downloads when user pass is present,
        or client_credentials (sh-...) for catalogue search.
        """
        now = time.time()
        with self._token_lock:
            if for_download:
                if (
                    not force_refresh
                    and self._download_access_token
                    and now < (self._download_token_expiry - 30)
                ):
                    return True
            else:
                if (
                    not force_refresh
                    and self._search_access_token
                    and now < (self._search_token_expiry - 30)
                ):
                    return True

            if not self.has_configured_credentials():
                logger.warning(
                    "CDSE authentication skipped: Credentials not configured on backend."
                )
                return False

            invalid_placeholders = {"your_cdse_username", "your_cdse_password", "your_cdse_client_id", "your_cdse_client_secret", ""}
            user_val, pass_val, cid_val, csec_val = self._resolve_credentials()
            has_client_credentials = bool(
                cid_val and csec_val
                and cid_val not in invalid_placeholders
                and csec_val not in invalid_placeholders
            )
            has_user_pass = bool(
                user_val and pass_val
                and user_val not in invalid_placeholders
                and pass_val not in invalid_placeholders
            )

            # For downloads, prefer user_pass if available to ensure correct audience for CDSE Zipper
            if for_download and has_user_pass:
                auth_data = {
                    "client_id": "cdse-public",
                    "username": user_val,
                    "password": pass_val,
                    "grant_type": "password",
                }
            elif has_client_credentials:
                auth_data = {
                    "client_id": cid_val,
                    "client_secret": csec_val,
                    "grant_type": "client_credentials",
                }
            elif has_user_pass:
                auth_data = {
                    "client_id": "cdse-public",
                    "username": user_val,
                    "password": pass_val,
                    "grant_type": "password",
                }
            else:
                return False

            encoded_data = urllib.parse.urlencode(auth_data).encode("utf-8")
            req = urllib.request.Request(
                self._token_url,
                data=encoded_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    if resp.status != 200:
                        raise ProviderAuthError(
                            f"CDSE authentication failed with HTTP {resp.status}."
                        )
                    payload = json.loads(resp.read().decode("utf-8"))

                token = payload.get("access_token")
                if not token:
                    raise ProviderAuthError(
                        "CDSE auth response did not contain an access_token."
                    )

                expires_in = int(payload.get("expires_in", 300))
                if for_download:
                    self._download_access_token = token
                    self._download_token_expiry = now + expires_in
                else:
                    self._search_access_token = token
                    self._search_token_expiry = now + expires_in
                    # Also set download token if not set
                    if not self._download_access_token:
                        self._download_access_token = token
                        self._download_token_expiry = now + expires_in

                logger.info(f"CDSE authentication successful ({'download' if for_download else 'search'}). Access token acquired.")
                return True

            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass

                if e.code in (400, 401, 403):
                    raise ProviderAuthError(
                        f"CDSE authentication failed: Invalid credentials or rejected request. HTTP {e.code}: {body}"
                    )
                if e.code == 429:
                    raise ProviderRateLimitError(
                        "CDSE authentication rate limit reached."
                    )
                raise ProviderNetworkError(
                    f"CDSE authentication network error (HTTP {e.code}): {e.reason}"
                )
            except urllib.error.URLError as e:
                raise ProviderNetworkError(
                    f"Failed to connect to CDSE authentication endpoint: {e.reason}"
                )
            except Exception as e:
                if isinstance(e, ProviderError):
                    raise
                raise ProviderError(f"CDSE authentication error: {e}")

    def _get_auth_headers(self, for_download: bool = False) -> Dict[str, str]:
        """Get HTTP headers with active Bearer authorization token if available."""
        headers = {"Accept": "application/json"}
        token_var = self._download_access_token if for_download else self._search_access_token
        if token_var or self.has_configured_credentials():
            try:
                if self.authenticate(for_download=for_download):
                    active_token = self._download_access_token if for_download else self._search_access_token
                    headers["Authorization"] = f"Bearer {active_token}"
            except Exception as e:
                logger.warning(f"Could not refresh CDSE auth token: {e}")
        return headers

    def search(self, request: SearchRequest) -> SearchResponse:
        """
        Search CDSE catalogue for Sentinel satellite observations matching criteria.
        Uses CDSE OData v4 API with URL parameter encoding.
        """
        request.validate()

        collections = request.collections if request.collections else ["SENTINEL-2"]
        filter_parts = []

        # Collection & Product Type filter
        col_name = collections[0].upper() if collections else "SENTINEL-2"
        if col_name in ("SENTINEL-2", "S2MSI2A", "S2MSI1C"):
            filter_parts.append("Collection/Name eq 'SENTINEL-2'")
            if col_name in ("S2MSI2A", "S2MSI1C"):
                filter_parts.append(
                    f"Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/Value eq '{col_name}')"
                )
        elif col_name.startswith("SENTINEL-1"):
            filter_parts.append("Collection/Name eq 'SENTINEL-1'")
        elif col_name.startswith("SENTINEL-3"):
            filter_parts.append("Collection/Name eq 'SENTINEL-3'")
        elif col_name.startswith("SENTINEL-5P"):
            filter_parts.append("Collection/Name eq 'SENTINEL-5P'")
        else:
            filter_parts.append(f"Collection/Name eq '{col_name}'")

        # Bbox filter
        if request.bbox:
            min_lon, min_lat, max_lon, max_lat = request.bbox
            poly_str = f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
            filter_parts.append(
                f"OData.CSC.Intersects(area=geography'SRID=4326;{poly_str}')"
            )

        # Date range filter
        if request.datetime_range:
            parts = request.datetime_range.split("/")
            if len(parts) == 2:
                d_from = parts[0].strip()
                d_to = parts[1].strip()
                if len(d_from) == 10:
                    d_from = f"{d_from}T00:00:00.000Z"
                if len(d_to) == 10:
                    d_to = f"{d_to}T23:59:59.999Z"
                filter_parts.append(
                    f"ContentDate/Start ge {d_from} and ContentDate/Start le {d_to}"
                )
            elif len(parts) == 1 and parts[0].strip():
                d_single = parts[0].strip()
                filter_parts.append(
                    f"ContentDate/Start ge {d_single}T00:00:00.000Z and ContentDate/Start le {d_single}T23:59:59.999Z"
                )

        # Cloud cover filter
        cloud_max = request.filters.get("max_cloud_cover") or request.filters.get("cloud_cover")
        if cloud_max is not None:
            try:
                c_val = float(cloud_max)
                filter_parts.append(
                    f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/Value le {c_val})"
                )
            except (ValueError, TypeError):
                pass

        filter_query = " and ".join(filter_parts)
        query_params = {
            "$filter": filter_query,
            "$top": str(min(request.limit, 50)),
            "$orderby": "ContentDate/Start desc",
        }

        odata_url = f"{self._catalogue_url}/odata/v1/Products?" + urllib.parse.urlencode(query_params)
        headers = self._get_auth_headers()

        try:
            req = urllib.request.Request(odata_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    raise ProviderNetworkError(f"CDSE OData search failed with status {resp.status}")
                odata_body = resp.read().decode("utf-8")
                odata_data = json.loads(odata_body)

            results = odata_data.get("value", [])
            items: List[ProductMetadata] = []
            for entry in results:
                pm = self._parse_odata_entry(entry, target_collection=col_name)
                if pm:
                    items.append(pm)

            return SearchResponse(
                provider=self.name,
                total_matched=len(items),
                items=items,
                context={
                    "query_collections": collections,
                    "bbox": request.bbox,
                    "datetime_range": request.datetime_range,
                    "catalogue_endpoint": odata_url,
                },
            )

        except urllib.error.HTTPError as e:
            if e.code in (400, 422):
                raise InvalidSearchRequestError(f"Invalid CDSE search request (HTTP {e.code})")
            if e.code == 401:
                raise ProviderAuthError("CDSE search authentication failed. Please verify credentials.")
            if e.code == 429:
                raise ProviderRateLimitError("CDSE catalogue rate limit exceeded.")
            raise ProviderNetworkError(f"CDSE search query failed with HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise ProviderNetworkError(f"Network error querying CDSE catalogue: {e.reason}")
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(f"CDSE search error: {e}")

    def _parse_odata_entry(
        self, entry: Dict[str, Any], target_collection: str
    ) -> Optional[ProductMetadata]:
        """Convert a CDSE OData record into a normalized ProductMetadata object."""
        try:
            pid = entry.get("Id") or entry.get("Name") or ""
            name = entry.get("Name") or pid
            content_date = entry.get("ContentDate", {})
            acq_date = content_date.get("Start") or entry.get("OriginDate") or datetime.utcnow().isoformat()

            cloud_cover = None
            attributes = entry.get("Attributes", [])
            for att in attributes:
                if isinstance(att, dict) and att.get("Name") == "cloudCover":
                    try:
                        cloud_cover = float(att.get("Value"))
                    except (ValueError, TypeError):
                        pass

            dl_href = f"{self._download_url}({pid})/$value"
            asset = AssetMetadata(
                key="product",
                href=dl_href,
                title=f"Product Zip Archive — {name}",
                media_type="application/zip",
                roles=["data"],
            )

            # Determine product type from name or attributes
            p_type = "Level-2A" if "L2A" in name else "Level-1C" if "L1C" in name else "SAR"

            return ProductMetadata(
                provider=self.name,
                product_id=pid,
                collection=target_collection,
                title=name,
                datetime=str(acq_date),
                bbox=None,
                geometry=entry.get("Footprint"),
                platform="Sentinel-2" if "S2" in name else "Sentinel-1" if "S1" in name else "Sentinel",
                instrument="MSI" if "S2" in name else "SAR",
                product_type=p_type,
                cloud_cover=cloud_cover,
                online=entry.get("Online", True),
                is_downloadable=True,
                assets=[asset],
                properties=entry,
            )
        except Exception as e:
            logger.warning(f"Error parsing OData record: {e}")
            return None

    def get_product(
        self, product_id: str, collection: Optional[str] = None
    ) -> Optional[ProductMetadata]:
        """Retrieve detailed product record by ID from CDSE catalogue."""
        clean_id = (product_id or "").strip()
        if not clean_id:
            raise InvalidSearchRequestError("product_id cannot be empty.")

        url = f"{self._catalogue_url}/odata/v1/Products({clean_id})"
        headers = self._get_auth_headers()

        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    raise ProductNotFoundError(f"CDSE product '{clean_id}' not found.")
                body = resp.read().decode("utf-8")
                record = json.loads(body)

            return self._parse_odata_entry(record, target_collection=collection or "SENTINEL-2")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise ProductNotFoundError(f"CDSE product '{clean_id}' not found.")
            if e.code == 401:
                raise ProviderAuthError("CDSE authentication failed.")
            raise ProviderNetworkError(f"Failed to fetch product '{clean_id}': HTTP {e.code}")
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderNetworkError(f"Error fetching CDSE product metadata: {e}")

    def _download_via_sentinel_hub_process(
        self,
        product_id: str,
        destination_dir: Path,
        collection: Optional[str] = None,
    ) -> Optional[DownloadResult]:
        """
        Download rendered true-color Sentinel-2 multispectral image using CDSE Sentinel Hub Process API.
        Works directly with Sentinel Hub OAuth client credentials (sh-...).
        """
        clean_id = (product_id or "").strip()
        target_img = destination_dir / f"cdse_{clean_id}.png"

        if target_img.exists() and target_img.stat().st_size > 0:
            return DownloadResult(
                provider=self.name,
                product_id=clean_id,
                collection=collection or "SENTINEL-2",
                local_path=str(target_img.resolve()),
                file_size_bytes=target_img.stat().st_size,
                cached=True,
            )

        bbox = [77.50, 12.90, 77.65, 13.05]
        time_from = "2024-01-01T00:00:00Z"
        time_to = "2024-12-31T23:59:59Z"

        try:
            prod_meta = self.get_product(clean_id, collection=collection)
            if prod_meta and prod_meta.geometry:
                geom = prod_meta.geometry
                if isinstance(geom, dict):
                    coords = geom.get("coordinates")
                    if coords and isinstance(coords, list) and len(coords) > 0:
                        pts = coords[0] if isinstance(coords[0], list) and isinstance(coords[0][0], list) else coords
                        lons = [p[0] for p in pts if isinstance(p, (list, tuple)) and len(p) >= 2]
                        lats = [p[1] for p in pts if isinstance(p, (list, tuple)) and len(p) >= 2]
                        if lons and lats:
                            bbox = [min(lons), min(lats), max(lons), max(lats)]
                elif isinstance(geom, str):
                    import re
                    nums = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", geom)]
                    if "SRID" in geom and len(nums) > 1:
                        nums = nums[1:]
                    if len(nums) >= 4:
                        lons = nums[0::2]
                        lats = nums[1::2]
                        bbox = [min(lons), min(lats), max(lons), max(lats)]
            if prod_meta and prod_meta.datetime:
                dt_str = str(prod_meta.datetime)[:10]
                time_from = f"{dt_str}T00:00:00Z"
                time_to = f"{dt_str}T23:59:59Z"
        except Exception as meta_err:
            logger.warning(f"Could not parse product geometry for '{clean_id}': {meta_err}")

        if not self.authenticate(for_download=False):
            return None

        headers = self._get_auth_headers(for_download=False)
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "image/png"

        sh_dataset_type = "sentinel-2-l2a"
        if collection and "L1C" in collection.upper():
            sh_dataset_type = "sentinel-2-l1c"

        payload = {
            "input": {
                "bounds": {"bbox": bbox},
                "data": [
                    {
                        "type": sh_dataset_type,
                        "dataFilter": {
                            "timeRange": {"from": time_from, "to": time_to},
                            "maxCloudCoverage": 100,
                        },
                    }
                ],
            },
            "output": {
                "width": 512,
                "height": 512,
                "responses": [{"identifier": "default", "format": {"type": "image/png"}}],
            },
            "evalscript": """//VERSION=3
function setup() {
  return { input: ["B04", "B03", "B02"], output: { bands: 3 } };
}
function evaluatePixel(sample) {
  return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02];
}""",
        }

        process_url = "https://sh.dataspace.copernicus.eu/api/v1/process"
        try:
            req = urllib.request.Request(
                process_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45.0) as resp:
                if resp.status == 200:
                    img_bytes = resp.read()
                    if img_bytes:
                        with open(target_img, "wb") as f_out:
                            f_out.write(img_bytes)

                        logger.info(f"Successfully rendered CDSE product '{clean_id}' via Sentinel Hub Process API ({len(img_bytes)} bytes)")
                        return DownloadResult(
                            provider=self.name,
                            product_id=clean_id,
                            collection=collection or "SENTINEL-2",
                            local_path=str(target_img.resolve()),
                            file_size_bytes=len(img_bytes),
                            cached=False,
                        )
        except Exception as e:
            logger.warning(f"Sentinel Hub Process API fetch failed for '{clean_id}': {e}")

        return None

    def download(
        self,
        product_id: str,
        destination_dir: Path,
        collection: Optional[str] = None,
        force_redownload: bool = False,
    ) -> DownloadResult:
        """
        Download product archive (.zip) or multispectral raster image (.png) from CDSE into destination_dir.
        Supports both Sentinel Hub OAuth credentials (sh-...) and CDSE User Account credentials.
        """
        clean_id = (product_id or "").strip()
        if not clean_id:
            raise InvalidSearchRequestError("product_id cannot be empty.")

        destination_dir = Path(destination_dir)
        destination_dir.mkdir(parents=True, exist_ok=True)

        target_zip = destination_dir / f"cdse_{clean_id}.zip"
        target_img = destination_dir / f"cdse_{clean_id}.png"

        if not force_redownload:
            if target_zip.exists() and target_zip.stat().st_size > 0:
                logger.info(f"CDSE product '{clean_id}' found in local cache at {target_zip}")
                return DownloadResult(
                    provider=self.name,
                    product_id=clean_id,
                    collection=collection or "SENTINEL-2",
                    local_path=str(target_zip.resolve()),
                    file_size_bytes=target_zip.stat().st_size,
                    cached=True,
                )
            if target_img.exists() and target_img.stat().st_size > 0:
                logger.info(f"CDSE image for product '{clean_id}' found in local cache at {target_img}")
                return DownloadResult(
                    provider=self.name,
                    product_id=clean_id,
                    collection=collection or "SENTINEL-2",
                    local_path=str(target_img.resolve()),
                    file_size_bytes=target_img.stat().st_size,
                    cached=True,
                )

        # For Sentinel Hub credentials (sh-...), prioritize Sentinel Hub Process API
        is_sh_credentials = bool(self._client_id and self._client_id.strip().startswith("sh-"))
        if is_sh_credentials:
            sh_res = self._download_via_sentinel_hub_process(clean_id, destination_dir, collection=collection)
            if sh_res:
                return sh_res

        # Authenticate with CDSE for product download (prefers user pass)
        if not self.authenticate(for_download=True):
            raise ProviderAuthError(
                f"Cannot download CDSE product '{clean_id}': Backend credentials for CDSE are not configured. "
                "Set CDSE_USERNAME and CDSE_PASSWORD in .env."
            )

        download_url = f"{self._download_url}({clean_id})/$value"
        headers = self._get_auth_headers(for_download=True)
        headers["User-Agent"] = "SatQuery-AI/1.1 (Earth Observation Platform)"

        logger.info(f"Initiating streaming download for CDSE product '{clean_id}' from {download_url}...")

        try:
            req = urllib.request.Request(download_url, headers=headers, method="GET")
            temp_path = destination_dir / f"cdse_{clean_id}.tmp"

            with urllib.request.urlopen(req, timeout=120.0) as resp:
                if resp.status not in (200, 206):
                    raise ProductNotAvailableError(
                        f"CDSE download endpoint returned status {resp.status} for product '{clean_id}'."
                    )

                bytes_downloaded = 0
                chunk_size = 64 * 1024
                with open(temp_path, "wb") as f_out:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        bytes_downloaded += len(chunk)

            if bytes_downloaded == 0 or not temp_path.exists():
                if temp_path.exists():
                    temp_path.unlink()
                raise ProductNotAvailableError(
                    f"Downloaded zero bytes for CDSE product '{clean_id}'."
                )

            # Move temp file to final target zip path
            if target_zip.exists():
                target_zip.unlink()
            shutil.move(str(temp_path), str(target_zip))

            logger.info(
                f"Successfully downloaded CDSE product '{clean_id}' ({bytes_downloaded} bytes) to {target_zip}"
            )

            return DownloadResult(
                provider=self.name,
                product_id=clean_id,
                collection=collection or "SENTINEL-2",
                local_path=str(target_zip.resolve()),
                file_size_bytes=bytes_downloaded,
                cached=False,
            )

        except urllib.error.HTTPError as e:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="ignore")
            except Exception:
                pass

            # Fallback to Sentinel Hub Process API if Zipper fails
            sh_res = self._download_via_sentinel_hub_process(clean_id, destination_dir, collection=collection)
            if sh_res:
                return sh_res

            if e.code == 404:
                raise ProductNotFoundError(f"Product '{clean_id}' not found on CDSE download server.")
            if e.code in (401, 403):
                raise ProviderAuthError(
                    f"Authorization denied by CDSE download server (HTTP {e.code}). "
                    "Please verify CDSE credentials in .env."
                )
            if e.code == 429:
                raise ProviderRateLimitError("CDSE download rate limit exceeded. Please retry later.")
            raise ProviderNetworkError(f"CDSE download failed with HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            raise ProviderNetworkError(f"Network connection failed during CDSE download: {e.reason}")
        except Exception as e:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(f"CDSE download error: {e}")

    def health_check(self) -> bool:
        """Check availability of CDSE catalogue services."""
        health_url = f"{self._catalogue_url}/stac/collections"
        try:
            req = urllib.request.Request(
                health_url,
                headers={"Accept": "application/json"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning(f"CDSE health check failed: {e}")
            return False
