import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Form,
    HTTPException,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agent.orchestrator import agent_orchestrator
from app.models.registry import registry_instance
from app.utils.metadata_extractor import MetadataExtractor
from app.utils.raster_ingestor import RasterIngestor
from app.demo.datasets import DEMO_SCENARIOS

from app.data_sources import (
    satellite_search_service,
    SatelliteSearchError,
    InvalidSearchRequestError,
    ProviderNotFoundError,
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="SatQuery AI",
    description=(
        "Ask questions. Understand Earth. "
        "AI-Powered Remote-Sensing Analysis Platform API."
    ),
    version="1.1.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

APP_DIR = BASE_DIR / "app"
STATIC_DIR = APP_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
CDSE_PRODUCT_DIR = UPLOAD_DIR / "cdse_products"

FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CDSE_PRODUCT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)

assets_dir = FRONTEND_DIST_DIR / "assets"

if assets_dir.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(assets_dir)),
        name="assets",
    )


# ============================================================
# IN-MEMORY HISTORY
# ============================================================

ANALYSIS_HISTORY: List[Dict[str, Any]] = []


# ============================================================
# CONFIGURATION
# ============================================================

CDSE_CATALOGUE_URL = (
    "https://catalogue.dataspace.copernicus.eu"
    "/odata/v1/Products"
)

CDSE_DOWNLOAD_URL = (
    "https://download.dataspace.copernicus.eu"
    "/odata/v1/Products"
)

CDSE_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu"
    "/auth/realms/CDSE/protocol/openid-connect/token"
)

MAX_UPLOAD_SIZE_MB = int(
    os.getenv("SATQUERY_MAX_UPLOAD_MB", "500")
)

MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


# ============================================================
# REQUEST MODELS
# ============================================================

class AnalyzeRequest(BaseModel):
    query: str

    input_mode: str = Field(
        default="single_image",
        description=(
            "single_image | bi_temporal | optical_sar"
        ),
    )

    images: List[Dict[str, Any]]


class SatelliteSearchApiRequest(BaseModel):
    provider: str = "copernicus"

    bbox: List[float]

    start_date: str
    end_date: str

    collection: str = "sentinel-2-l2a"

    max_cloud_cover: Optional[float] = None

    limit: int = Field(default=10, ge=1, le=100)


class CopernicusIngestRequest(BaseModel):
    product_id: str

    modality: str = "optical"

    download_product: bool = False


# ============================================================
# HELPERS
# ============================================================

ALLOWED_INPUT_MODES = {
    "single_image",
    "bi_temporal",
    "optical_sar",
}


def safe_filename(filename: Optional[str]) -> str:
    """
    Prevent directory traversal and unsafe filenames.
    """
    if not filename:
        filename = "uploaded_image"

    filename = Path(filename).name

    # Keep only reasonably safe characters.
    cleaned = "".join(
        char
        if char.isalnum() or char in "._-"
        else "_"
        for char in filename
    )

    if not cleaned:
        cleaned = "uploaded_image"

    return cleaned


def create_upload_path(filename: str) -> Path:
    """
    Create a unique local path while preserving extension.
    """
    clean_name = safe_filename(filename)

    suffix = Path(clean_name).suffix.lower()

    if not suffix:
        suffix = ".bin"

    unique_name = f"{uuid.uuid4().hex}{suffix}"

    return UPLOAD_DIR / unique_name


def local_path_from_public_url(url: str) -> Optional[str]:
    """
    Convert our own /static/uploads/... URL into an
    absolute local filesystem path.

    External URLs are deliberately rejected here.
    """
    if not url:
        return None

    url = url.split("?", 1)[0]

    prefix = "/static/uploads/"

    if not url.startswith(prefix):
        return None

    relative_name = url[len(prefix):]

    candidate = (UPLOAD_DIR / relative_name).resolve()

    upload_root = UPLOAD_DIR.resolve()

    try:
        candidate.relative_to(upload_root)
    except ValueError:
        return None

    if not candidate.exists():
        return None

    return str(candidate)


def resolve_image_path(image: Dict[str, Any]) -> Optional[str]:
    """
    Resolve all supported frontend image references to an
    actual local file.

    Supported:
      - file_path
      - image_path
      - path
      - local_path
      - url
      - imageUrl
      - image_url
    """

    direct_keys = [
        "file_path",
        "image_path",
        "path",
        "local_path",
    ]

    for key in direct_keys:
        value = image.get(key)

        if not value:
            continue

        path = Path(str(value))

        if path.exists() and path.is_file():
            return str(path.resolve())

    url_keys = [
        "url",
        "imageUrl",
        "image_url",
    ]

    for key in url_keys:
        value = image.get(key)

        if not value:
            continue

        local_path = local_path_from_public_url(str(value))

        if local_path:
            return local_path

    return None


def normalize_image_for_analysis(
    image: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert frontend observation metadata into a backend
    model-ready observation descriptor.
    """

    normalized = dict(image)

    local_path = resolve_image_path(image)

    if local_path:
        normalized["file_path"] = local_path
        normalized["local_path"] = local_path

    # Normalize common frontend naming differences.
    if "acquisitionDate" in normalized and "acquisition_date" not in normalized:
        normalized["acquisition_date"] = normalized["acquisitionDate"]

    if "satelliteId" in normalized and "satellite_id" not in normalized:
        normalized["satellite_id"] = normalized["satelliteId"]

    if "imageUrl" in normalized and "image_url" not in normalized:
        normalized["image_url"] = normalized["imageUrl"]

    if "thumbnailUrl" in normalized and "thumbnail_url" not in normalized:
        normalized["thumbnail_url"] = normalized["thumbnailUrl"]

    return normalized


def validate_analysis_images(
    images: List[Dict[str, Any]],
    input_mode: str,
) -> List[Dict[str, Any]]:
    """
    Validate that the observations supplied to the orchestrator
    actually refer to usable local assets.

    Demo observations can explicitly opt out using source_type=demo.
    """

    if input_mode not in ALLOWED_INPUT_MODES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported input_mode '{input_mode}'. "
                f"Expected one of: {sorted(ALLOWED_INPUT_MODES)}"
            ),
        )

    normalized_images = [
        normalize_image_for_analysis(image)
        for image in images
    ]

    if input_mode == "bi_temporal" and len(normalized_images) != 2:
        raise HTTPException(
            status_code=400,
            detail=(
                "Bi-temporal analysis requires exactly two observations."
            ),
        )

    if input_mode == "optical_sar" and len(normalized_images) != 2:
        raise HTTPException(
            status_code=400,
            detail=(
                "Optical + SAR analysis requires exactly two observations."
            ),
        )

    if input_mode == "single_image" and len(normalized_images) < 1:
        raise HTTPException(
            status_code=400,
            detail="At least one observation is required.",
        )

    for index, image in enumerate(normalized_images):
        source_type = str(
            image.get("source_type", "")
        ).lower()

        # Demo scenarios may not have physical raster files.
        if source_type == "demo":
            continue

        local_path = image.get("file_path")

        if not local_path:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        f"Observation {index + 1} does not contain "
                        "a usable raster file."
                    ),
                    "filename": image.get(
                        "filename",
                        image.get("name", "unknown"),
                    ),
                    "hint": (
                        "Upload the GeoTIFF/TIFF or ingest the "
                        "CDSE product before running analysis."
                    ),
                },
            )

        if not os.path.isfile(local_path):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Raster file not found for observation "
                    f"{index + 1}: {local_path}"
                ),
            )

    return normalized_images


def get_cdse_access_token() -> Optional[str]:
    """
    Obtain a CDSE access token using backend-only environment
    variables.

    Required only for authenticated product downloads.

    NEVER expose these credentials to the frontend.
    """

    username = os.getenv("CDSE_USERNAME")
    password = os.getenv("CDSE_PASSWORD")

    if not username or not password:
        return None

    response = requests.post(
        CDSE_TOKEN_URL,
        data={
            "client_id": "cdse-public",
            "grant_type": "password",
            "username": username,
            "password": password,
        },
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"CDSE authentication failed: HTTP {response.status_code}"
        )

    payload = response.json()

    token = payload.get("access_token")

    if not token:
        raise RuntimeError(
            "CDSE authentication succeeded but no access_token was returned."
        )

    return token


def get_cdse_product(product_id: str) -> Dict[str, Any]:
    """
    Retrieve one genuine CDSE product and its Assets.
    """

    clean_id = product_id.strip()

    if not clean_id:
        raise HTTPException(
            status_code=400,
            detail="CDSE product_id cannot be empty.",
        )

    url = (
        f"{CDSE_CATALOGUE_URL}"
        f"({clean_id})"
        "?$expand=Assets"
    )

    try:
        response = requests.get(
            url,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"CDSE catalogue request failed: {exc}",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=404,
            detail=(
                f"CDSE product '{clean_id}' could not be retrieved. "
                f"HTTP {response.status_code}"
            ),
        )

    return response.json()


def find_quicklook_asset(
    product: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Find the genuine QUICKLOOK asset returned by CDSE.
    """

    assets = product.get("Assets") or []

    for asset in assets:
        asset_type = str(
            asset.get("Type", "")
        ).upper()

        asset_name = str(
            asset.get("Name", "")
        ).upper()

        if (
            asset_type == "QUICKLOOK"
            or asset_name == "QUICKLOOK"
        ):
            return asset

    return None


def product_to_observation(
    product: Dict[str, Any],
    modality: str,
    quicklook_url: Optional[str],
    local_product_path: Optional[str] = None,
    ingestion_manifest: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Convert a CDSE catalogue product into the observation
    contract expected by the frontend/orchestrator.
    """

    product_id = product.get("Id")
    product_name = product.get("Name")

    content_date = product.get("ContentDate") or {}

    acquisition_date = (
        content_date.get("Start")
        if isinstance(content_date, dict)
        else None
    )

    collection = product.get("Collection") or {}

    collection_name = (
        collection.get("Name")
        if isinstance(collection, dict)
        else None
    )

    manifest = ingestion_manifest or {}

    # Prefer the model-ready asset created by RasterIngestor.
    model_file_path = (
        manifest.get("model_file_path")
        or manifest.get("local_path")
        or local_product_path
    )

    band_map = manifest.get("band_map") or {}
    assets = manifest.get("assets") or []

    observation: Dict[str, Any] = {
        "id": f"cdse_{product_id}",
        "product_id": product_id,
        "filename": product_name,
        "name": product_name,

        "source_type": "copernicus",
        "provider": "copernicus",
        "isDemo": False,

        "modality": modality,
        "collection": collection_name,

        "acquisition_date": acquisition_date,
        "acquisitionDate": acquisition_date,

        "image_url": quicklook_url or "",
        "imageUrl": quicklook_url or "",

        "thumbnail_url": quicklook_url or "",
        "thumbnailUrl": quicklook_url or "",

        "product_metadata": product,

        # Critical: actual model-ready local raster.
        "file_path": model_file_path,
        "local_path": model_file_path,

        # Real ingestion information for downstream routing/models.
        "ingestion_manifest": manifest or None,
        "band_map": band_map,
        "assets": assets,
        "analysis_asset": manifest.get("analysis_asset"),
        "display_asset": manifest.get("display_asset"),
        "extraction_dir": manifest.get("extraction_dir"),
        "safe_root": manifest.get("safe_root"),
        "product_family": manifest.get("product_family"),

        "crs": product.get("CRS"),
        "footprint": product.get("Footprint"),
        "geofootprint": product.get("GeoFootprint"),
        "s3_path": product.get("S3Path"),

        "ingestion_status": (
            "ready"
            if model_file_path and manifest
            else ("downloaded" if local_product_path else "catalogue_only")
        ),
    }

    # Promote selected semantic raster paths for code that expects flat fields.
    if isinstance(band_map, dict):
        for semantic, info in band_map.items():
            if isinstance(info, dict) and info.get("path"):
                observation[semantic] = info["path"]

    return observation


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "platform": "SatQuery AI",
        "tagline": "Ask questions. Understand Earth.",
        "version": "1.1.0",
    }


# ============================================================
# PROVIDERS
# ============================================================

@app.get("/api/data-sources/providers")
def list_satellite_providers():
    """
    Return registered satellite data providers.
    """

    return {
        "providers": satellite_search_service.list_providers()
    }


# ============================================================
# SATELLITE SEARCH
# ============================================================

@app.post("/api/data-sources/search")
def search_satellite_data(
    req: SatelliteSearchApiRequest,
):
    """
    Search an external satellite catalogue.

    The search result is metadata only.
    Actual raster ingestion happens separately.
    """

    if len(req.bbox) != 4:
        raise HTTPException(
            status_code=400,
            detail=(
                "bbox must contain exactly four values: "
                "[min_lon, min_lat, max_lon, max_lat]"
            ),
        )

    min_lon, min_lat, max_lon, max_lat = req.bbox

    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(
            status_code=400,
            detail="Invalid bbox coordinates.",
        )

    if req.max_cloud_cover is not None:
        if not 0 <= req.max_cloud_cover <= 100:
            raise HTTPException(
                status_code=400,
                detail="max_cloud_cover must be between 0 and 100.",
            )

    try:
        results = satellite_search_service.search(
            provider=req.provider,
            request={
                "bbox": req.bbox,
                "start_date": req.start_date,
                "end_date": req.end_date,
                "collection": req.collection,
                "max_cloud_cover": req.max_cloud_cover,
                "limit": req.limit,
            },
        )

        return {
            "status": "success",
            "provider": req.provider,
            "count": len(results),
            "products": [
                prod.model_dump()
                for prod in results
            ],
        }

    except InvalidSearchRequestError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except ProviderNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except SatelliteSearchError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Satellite provider search failed: {exc}"
            ),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal search error: {exc}",
        )


# ============================================================
# CDSE PRODUCT DETAILS
# ============================================================

@app.get(
    "/api/data-sources/copernicus/product/{product_id}"
)
def get_copernicus_product(product_id: str):
    """
    Return genuine CDSE product metadata including assets.
    """

    product = get_cdse_product(product_id)

    quicklook = find_quicklook_asset(product)

    return {
        "status": "success",
        "product": product,
        "quicklook": quicklook,
    }


# ============================================================
# CDSE QUICKLOOK
# ============================================================

@app.get(
    "/api/data-sources/copernicus/quicklook/{product_id}"
)
def get_copernicus_quicklook(product_id: str):
    """
    Proxy the genuine CDSE QUICKLOOK asset.

    IMPORTANT:
    Products(<id>)/$value is a product download endpoint.
    Quicklooks are exposed as Assets(<asset_id>)/$value.
    """

    product = get_cdse_product(product_id)

    quicklook = find_quicklook_asset(product)

    if not quicklook:
        raise HTTPException(
            status_code=404,
            detail=(
                "This CDSE product does not expose "
                "a QUICKLOOK asset."
            ),
        )

    asset_id = quicklook.get("Id")

    if not asset_id:
        raise HTTPException(
            status_code=404,
            detail="CDSE QUICKLOOK asset has no asset ID.",
        )

    url = (
        f"{CDSE_CATALOGUE_URL.rsplit('/Products', 1)[0]}"
        f"/Assets({asset_id})/$value"
    )

    try:
        response = requests.get(
            url,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"CDSE quicklook request failed: {exc}",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=404,
            detail=(
                "CDSE quicklook unavailable. "
                f"HTTP {response.status_code}"
            ),
        )

    media_type = (
        response.headers.get(
            "content-type",
            "image/jpeg",
        )
    )

    return Response(
        content=response.content,
        media_type=media_type,
    )


# ============================================================
# CDSE PRODUCT INGESTION
# ============================================================

@app.post(
    "/api/data-sources/copernicus/ingest"
)
def ingest_copernicus_product(
    req: CopernicusIngestRequest,
):
    """
    Select a real CDSE catalogue product and optionally download + extract
    its actual raster assets.

    download_product=True:
      CDSE product ZIP
          -> local ZIP
          -> safe SAFE extraction
          -> Sentinel-1/Sentinel-2 raster discovery
          -> analysis-ready manifest
          -> model-ready observation
    """

    allowed_modalities = {"optical", "sar", "optical_sar"}
    modality = req.modality.strip().lower()

    if modality not in allowed_modalities:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported modality '{req.modality}'. "
                f"Expected one of: {sorted(allowed_modalities)}"
            ),
        )

    product = get_cdse_product(req.product_id)

    quicklook = find_quicklook_asset(product)
    quicklook_url = None

    if quicklook and quicklook.get("Id"):
        quicklook_url = (
            "/api/data-sources/copernicus/"
            f"quicklook/{req.product_id}"
        )

    local_archive_path: Optional[str] = None
    ingestion_manifest: Optional[Dict[str, Any]] = None

    if req.download_product:
        token = get_cdse_access_token()

        if not token:
            raise HTTPException(
                status_code=503,
                detail=(
                    "CDSE product download is not configured. "
                    "Set CDSE_USERNAME and CDSE_PASSWORD on the "
                    "backend server."
                ),
            )

        product_id = product.get("Id")
        download_url = (
            f"{CDSE_DOWNLOAD_URL}"
            f"({product_id})/$value"
        )

        product_name = safe_filename(
            product.get("Name") or f"{product_id}.zip"
        )

        if not Path(product_name).suffix:
            product_name += ".zip"

        destination = UPLOAD_DIR / (
            f"cdse_{uuid.uuid4().hex}_"
            f"{product_name}"
        )

        try:
            with requests.get(
                download_url,
                headers={
                    "Authorization": f"Bearer {token}"
                },
                stream=True,
                timeout=120,
            ) as response:

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            "CDSE product download failed. "
                            f"HTTP {response.status_code}"
                        ),
                    )

                with open(destination, "wb") as output:
                    total_bytes = 0

                    for chunk in response.iter_content(
                        chunk_size=1024 * 1024
                    ):
                        if not chunk:
                            continue

                        total_bytes += len(chunk)

                        if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                            try:
                                destination.unlink()
                            except OSError:
                                pass

                            raise HTTPException(
                                status_code=413,
                                detail=(
                                    "Downloaded CDSE product exceeds the "
                                    f"configured maximum size of "
                                    f"{MAX_UPLOAD_SIZE_MB} MB."
                                ),
                            )

                        output.write(chunk)

            local_archive_path = str(destination.resolve())

        except HTTPException:
            raise

        except requests.RequestException as exc:
            raise HTTPException(
                status_code=502,
                detail=f"CDSE download request failed: {exc}",
            )

        # --------------------------------------------------------
        # CRITICAL: extract the real SAFE/raster assets.
        # --------------------------------------------------------
        try:
            ingestor = RasterIngestor(CDSE_PRODUCT_DIR)

            ingestion_manifest = ingestor.ingest_archive(
                local_archive_path,
                product_id=str(product.get("Id") or req.product_id),
                collection=(
                    (product.get("Collection") or {}).get("Name")
                    if isinstance(product.get("Collection"), dict)
                    else None
                ),
                create_analysis_stack=True,
            )

        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Downloaded CDSE archive could not be ingested: {exc}",
            )

        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"CDSE raster ingestion failed validation: {exc}",
            )

        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "CDSE product was downloaded, but the raster-processing "
                    f"environment is not ready: {exc}"
                ),
            )

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected CDSE raster ingestion error: {exc}",
            )

    observation = product_to_observation(
        product=product,
        modality=modality,
        quicklook_url=quicklook_url,
        local_product_path=local_archive_path,
        ingestion_manifest=ingestion_manifest,
    )

    if req.download_product:
        model_path = observation.get("file_path")

        if not model_path or not os.path.isfile(model_path):
            raise HTTPException(
                status_code=500,
                detail=(
                    "CDSE product downloaded, but no model-ready raster "
                    "asset was produced by the ingestion pipeline."
                ),
            )

        message = "CDSE product downloaded and converted to analysis-ready raster assets."

    else:
        message = "CDSE product selected successfully; no raster was downloaded."

    return {
        "status": "success",
        "message": message,
        "observation": observation,
        "downloaded": bool(local_archive_path),
        "ingested": bool(ingestion_manifest),
        "ingestion": ingestion_manifest,
    }


# ============================================================
# MODELS
# ============================================================

@app.get("/api/models")
def get_models():
    """
    Return registered remote-sensing models and tools.
    """

    return {
        "models": registry_instance.list_models()
    }


# ============================================================
# DEMOS
# ============================================================

@app.get("/api/demos")
def get_demos():
    return {
        "demos": DEMO_SCENARIOS
    }


@app.get("/api/demos/{demo_id}")
def get_demo_by_id(demo_id: str):
    for demo in DEMO_SCENARIOS:
        if demo["id"] == demo_id:
            return demo

    raise HTTPException(
        status_code=404,
        detail="Demo scenario not found",
    )


# ============================================================
# UPLOAD
# ============================================================

@app.post("/api/upload")
async def upload_image(
    file: UploadFile = File(...),
):
    """
    Upload a genuine raster file and extract metadata.

    The returned object contains BOTH:
      - public URL for the frontend
      - local file_path for the backend/model pipeline
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file has no filename.",
        )

    clean_name = safe_filename(file.filename)

    allowed_extensions = {
        ".tif",
        ".tiff",
        ".jp2",
        ".png",
        ".jpg",
        ".jpeg",
    }

    suffix = Path(clean_name).suffix.lower()

    if suffix not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{suffix}'. "
                "Supported formats: GeoTIFF/TIFF, JP2, PNG, JPEG."
            ),
        )

    destination = create_upload_path(clean_name)

    total_bytes = 0

    try:
        with open(destination, "wb") as buffer:

            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                total_bytes += len(chunk)

                if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                    buffer.close()

                    try:
                        destination.unlink()
                    except OSError:
                        pass

                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"File exceeds the maximum upload size "
                            f"of {MAX_UPLOAD_SIZE_MB} MB."
                        ),
                    )

                buffer.write(chunk)

    except HTTPException:
        raise

    except Exception as exc:
        try:
            destination.unlink()
        except OSError:
            pass

        raise HTTPException(
            status_code=500,
            detail=f"Could not save uploaded file: {exc}",
        )

    try:
        metadata = MetadataExtractor.extract_metadata(
            str(destination),
            clean_name,
        )

    except Exception as exc:
        try:
            destination.unlink()
        except OSError:
            pass

        raise HTTPException(
            status_code=400,
            detail=f"Metadata extraction failed: {exc}",
        )

    if not metadata.get("valid", True):
        try:
            destination.unlink()
        except OSError:
            pass

        raise HTTPException(
            status_code=400,
            detail=metadata.get(
                "error",
                "Invalid remote-sensing file.",
            ),
        )

    public_url = (
        f"/static/uploads/{destination.name}"
    )

    # --------------------------------------------------------
    # IMPORTANT MODEL INPUT CONTRACT
    # --------------------------------------------------------

    metadata["id"] = f"upload_{uuid.uuid4().hex}"

    metadata["filename"] = clean_name
    metadata["name"] = clean_name

    metadata["url"] = public_url
    metadata["image_url"] = public_url
    metadata["imageUrl"] = public_url

    metadata["file_path"] = str(
        destination.resolve()
    )

    metadata["local_path"] = str(
        destination.resolve()
    )

    metadata["source_type"] = "upload"
    metadata["isDemo"] = False
    metadata["ingestion_status"] = "ready"

    metadata["file_size_bytes"] = total_bytes

    return metadata


# ============================================================
# ANALYSIS
# ============================================================

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    """
    Main SatQuery AI execution endpoint.

    Flow:

      Frontend observation
          ↓
      Resolve local raster
          ↓
      Validate input mode
          ↓
      Agent orchestration
          ↓
      Specialist model/tool
          ↓
      Evidence + confidence
          ↓
      Auditable result
    """

    query = req.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Query string cannot be empty.",
        )

    if not req.images:
        raise HTTPException(
            status_code=400,
            detail="At least one satellite image is required.",
        )

    # --------------------------------------------------------
    # VALIDATE + RESOLVE REAL FILES
    # --------------------------------------------------------

    normalized_images = validate_analysis_images(
        images=req.images,
        input_mode=req.input_mode,
    )

    # --------------------------------------------------------
    # RUN AGENT
    # --------------------------------------------------------

    try:
        result = agent_orchestrator.process_query(
            query=query,
            images=normalized_images,
            input_mode=req.input_mode,
        )

    except HTTPException:
        raise

    except Exception as exc:
        # Do not pretend the analysis completed.
        raise HTTPException(
            status_code=500,
            detail={
                "message": "SatQuery analysis failed.",
                "error": str(exc),
            },
        )

    if not isinstance(result, dict):
        raise HTTPException(
            status_code=500,
            detail="Agent returned an invalid response.",
        )

    # --------------------------------------------------------
    # REQUIRED RESULT CONTRACT
    # --------------------------------------------------------

    if "task" not in result:
        result["task"] = "unknown"

    if "answer" not in result:
        result["answer"] = (
            "The analysis completed without a generated answer."
        )

    if "confidence" not in result:
        result["confidence"] = 0

    if "visual_evidence" not in result:
        result["visual_evidence"] = []

    if "execution_summary" not in result:
        result["execution_summary"] = {}

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    execution_summary = result.get(
        "execution_summary",
        {},
    )

    timestamp = execution_summary.get(
        "audit_timestamp"
    )

    history_entry = {
        "id": f"rec_{len(ANALYSIS_HISTORY) + 1}",
        "query": query,
        "input_mode": req.input_mode,
        "task": result.get("task"),
        "model_used": (
            result.get("selected_model", {})
            .get("name")
        ),
        "confidence": result.get("confidence", 0),
        "answer_summary": str(
            result.get("answer", "")
        )[:120],
        "timestamp": timestamp,
        "full_result": result,
    }

    ANALYSIS_HISTORY.insert(
        0,
        history_entry,
    )

    # Prevent unbounded memory growth.
    if len(ANALYSIS_HISTORY) > 100:
        del ANALYSIS_HISTORY[100:]

    return result


# ============================================================
# HISTORY
# ============================================================

@app.get("/api/history")
def get_history():
    return {
        "history": ANALYSIS_HISTORY
    }


# ============================================================
# FRONTEND
# ============================================================

@app.get("/")
@app.get("/{path:path}")
def serve_frontend(path: str = ""):
    """
    Serve the React SPA.
    """

    from fastapi.responses import FileResponse

    if path.startswith("api/"):
        raise HTTPException(
            status_code=404,
            detail=f"API endpoint '/{path}' not found",
        )

    if path:
        possible_file = (
            FRONTEND_DIST_DIR / path
        )

        if (
            possible_file.exists()
            and possible_file.is_file()
        ):
            return FileResponse(
                str(possible_file)
            )

    frontend_index = (
        FRONTEND_DIST_DIR / "index.html"
    )

    if frontend_index.exists():
        return FileResponse(
            str(frontend_index)
        )

    index_path = (
        STATIC_DIR / "index.html"
    )

    if index_path.exists():
        return FileResponse(
            str(index_path)
        )

    return {
        "message": "SatQuery AI Backend Server Ready."
    }