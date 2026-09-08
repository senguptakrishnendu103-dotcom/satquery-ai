import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

# Load .env variables if present
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    with open(_env_file, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ[_k.strip()] = _v.strip()

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
)
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agent.orchestrator import agent_orchestrator
from app.models.registry import registry_instance
from app.utils.metadata_extractor import MetadataExtractor
from app.utils.raster_ingestor import RasterIngestor
from app.utils.image_resolver import ImageResolver
from app.demo.datasets import DEMO_SCENARIOS
from app.resources.sih_registry import (
    sih_resource_registry,
    ResourceNotConfiguredError,
    SampleNotFoundError,
    InvalidSampleFileError,
    SIHResourceError,
)
from app.providers import (
    get_provider,
    list_providers,
    SearchRequest,
    ProviderError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProductNotFoundError,
    ProductNotAvailableError,
    ProviderNetworkError,
    InvalidSearchRequestError,
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

FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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

MAX_UPLOAD_SIZE_MB = int(
    os.getenv("SATQUERY_MAX_UPLOAD_MB", "500")
)

MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


# ============================================================
# SCHEMAS
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


class DataSearchRequest(BaseModel):
    provider: str = Field(default="bhoonidhi")
    collections: List[str] = Field(default_factory=list)
    bbox: Optional[List[float]] = None
    datetime_range: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)
    filters: Dict[str, Any] = Field(default_factory=dict)


class DataDownloadRequest(BaseModel):
    provider: str = Field(default="bhoonidhi")
    product_id: str
    collection: Optional[str] = None
    force_redownload: bool = False


class SIHLoadRequest(BaseModel):
    resource_id: str
    sample_id: str
    pair_mode: bool = False


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

        # Demo observations are the only observations allowed to proceed
        # without a model-readable raster. A thumbnail/preview is display
        # media, not an analysis asset. An observation product is model-ready
        # only when an actual local or explicitly resolvable analysis asset
        # is present.
        if source_type in ("demo", "sample"):
            continue

        remote_analysis_asset = (
            image.get("analysis_asset")
            or image.get("remote_analysis_asset")
            or image.get("analysis_asset_url")
            or image.get("remote_asset_url")
            or image.get("image_url")
            or image.get("imageUrl")
            or image.get("quicklook_url")
            or image.get("url")
            or image.get("path")
        )
        if remote_analysis_asset:
            continue

        local_path = image.get("file_path") or image.get("local_path")

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
                        "Upload the GeoTIFF/TIFF raster file "
                        "before running analysis."
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
# SIH DATA RESOURCES (SIH26167)
# ============================================================

@app.get("/api/resources/sih")
def get_sih_resources(resource_type: Optional[str] = None, available_only: bool = False):
    """
    List all standardized SIH26167 benchmark and training datasets.
    """
    return {
        "resources": sih_resource_registry.list_resources(
            resource_type=resource_type,
            available_only=available_only,
        ),
        "summary": sih_resource_registry.get_summary(),
    }


@app.get("/api/resources/sih/{resource_id}/samples")
def get_sih_resource_samples(
    resource_id: str,
    limit: Optional[int] = 50,
    filter_task: Optional[str] = None,
):
    """
    Browse samples for an authentic SIH dataset/benchmark.
    """
    res = sih_resource_registry.get_resource(resource_id)
    if not res:
        raise HTTPException(
            status_code=404,
            detail=f"SIH data resource '{resource_id}' not found.",
        )

    return {
        "resource": res.get_metadata(),
        "samples": res.list_samples(limit=limit, filter_task=filter_task),
    }


@app.post("/api/resources/sih/load")
def load_sih_sample(req: SIHLoadRequest):
    """
    Materialize an authentic SIH dataset/benchmark sample into the SatQuery observation workspace.
    """
    res = sih_resource_registry.get_resource(req.resource_id)
    if not res:
        raise HTTPException(
            status_code=404,
            detail=f"SIH data resource '{req.resource_id}' not found.",
        )

    try:
        obs_data = res.materialize_observation(
            req.sample_id,
            output_dir=str(UPLOAD_DIR),
            pair_mode=req.pair_mode,
        )
        return {
            "status": "success",
            "resource_id": req.resource_id,
            "sample_id": req.sample_id,
            "data": obs_data,
        }
    except ResourceNotConfiguredError as err:
        raise HTTPException(status_code=412, detail=str(err))
    except SampleNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except InvalidSampleFileError as err:
        raise HTTPException(status_code=422, detail=str(err))
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except SIHResourceError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load SIH sample: {exc}",
        )


# ============================================================
# WEB SATELLITE DATA FETCHING (BHOONIDHI & PROVIDERS)
# ============================================================

@app.get("/api/data/providers")
def get_satellite_providers():
    """
    List available satellite data providers and their supported mission collections.
    """
    return {
        "providers": list_providers()
    }


@app.post("/api/data/search")
def search_satellite_data(req: DataSearchRequest):
    """
    Search external satellite catalogue (e.g. ISRO Bhoonidhi) for real observations.
    """
    try:
        prov = get_provider(req.provider)
        bbox_tuple = tuple(req.bbox) if req.bbox and len(req.bbox) == 4 else None
        search_req = SearchRequest(
            provider=req.provider,
            collections=req.collections,
            bbox=bbox_tuple,
            datetime_range=req.datetime_range,
            limit=req.limit,
            filters=req.filters,
        )
        search_req.validate()
        resp = prov.search(search_req)
        return resp.to_dict()
    except (InvalidSearchRequestError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ProviderAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ProviderRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ProviderNetworkError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Satellite search failed: {e}")


@app.post("/api/data/download")
def download_satellite_product(req: DataDownloadRequest):
    """
    Download a selected satellite product and run through common ingestion.
    """
    try:
        prov = get_provider(req.provider)
        download_dir = UPLOAD_DIR / "bhoonidhi_downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        dl_result = prov.download(
            product_id=req.product_id,
            destination_dir=download_dir,
            collection=req.collection,
            force_redownload=req.force_redownload,
        )

        file_path = Path(dl_result.local_path)
        clean_name = file_path.name

        if file_path.suffix.lower() == ".zip":
            manifest = RasterIngestor(download_dir).ingest_archive(
                file_path,
                product_id=req.product_id,
                collection=req.collection,
            )
            candidate_asset = (
                manifest.get("model_file_path")
                or manifest.get("local_path")
                or (manifest.get("analysis_asset") if isinstance(manifest.get("analysis_asset"), str) else None)
                or (manifest.get("analysis_asset", {}).get("path") if isinstance(manifest.get("analysis_asset"), dict) else None)
                or manifest.get("raster_path")
                or file_path
            )
            analysis_asset = Path(candidate_asset)
            clean_name = analysis_asset.name
            metadata = MetadataExtractor.extract_metadata(str(analysis_asset), clean_name)
            metadata["archive_manifest"] = manifest
            metadata["analysis_asset"] = str(analysis_asset)
            metadata["analysisAsset"] = str(analysis_asset)
        else:
            analysis_asset = file_path
            metadata = MetadataExtractor.extract_metadata(str(file_path), clean_name)
            metadata["analysis_asset"] = str(file_path)
            metadata["analysisAsset"] = str(file_path)

        metadata["id"] = f"fetch_{uuid.uuid4().hex}"
        metadata["provider"] = req.provider
        metadata["product_id"] = req.product_id
        metadata["collection"] = req.collection or metadata.get("platform")
        metadata["source_type"] = "web_fetch"
        metadata["file_path"] = str(analysis_asset)
        metadata["local_path"] = str(analysis_asset)
        metadata["cached"] = dl_result.cached
        metadata["download_timestamp"] = dl_result.download_timestamp

        public_url = ImageResolver.ensure_displayable_preview(str(analysis_asset))
        metadata["url"] = public_url
        metadata["image_url"] = public_url
        metadata["imageUrl"] = public_url
        metadata["thumbnailUrl"] = public_url
        metadata["thumbnail_url"] = public_url

        return {
            "status": "success",
            "download_result": {
                "provider": dl_result.provider,
                "product_id": dl_result.product_id,
                "collection": dl_result.collection,
                "local_path": dl_result.local_path,
                "file_size_bytes": dl_result.file_size_bytes,
                "cached": dl_result.cached,
                "download_timestamp": dl_result.download_timestamp,
            },
            "observation": metadata,
        }
    except ProductNotAvailableError as e:
        raise HTTPException(status_code=412, detail=str(e))
    except ProductNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProviderAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ProviderRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ProviderNetworkError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Product download failed: {e}")


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

    public_url = ImageResolver.ensure_displayable_preview(str(destination.resolve()))

    # --------------------------------------------------------
    # IMPORTANT MODEL INPUT CONTRACT
    # --------------------------------------------------------

    metadata["id"] = f"upload_{uuid.uuid4().hex}"

    metadata["filename"] = clean_name
    metadata["name"] = clean_name

    metadata["url"] = public_url
    metadata["image_url"] = public_url
    metadata["imageUrl"] = public_url
    metadata["thumbnailUrl"] = public_url
    metadata["thumbnail_url"] = public_url

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
        import traceback
        traceback.print_exc()
        # Do not pretend the analysis completed.
        detail_msg = exc.detail if isinstance(getattr(exc, "detail", None), (str, dict)) else str(exc)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "SatQuery analysis failed.",
                "error": detail_msg,
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
# REPORTS & PDF INTELLIGENCE BRIEFS
# ============================================================

from fastapi.responses import HTMLResponse, Response
from app.utils.report_generator import generate_intelligence_brief_html


class ReportBriefRequest(BaseModel):
    result: Dict[str, Any]
    query_text: Optional[str] = ""
    execution_id: Optional[str] = ""
    observations: Optional[List[Dict[str, Any]]] = None


@app.post("/api/reports/brief", response_class=HTMLResponse)
def get_report_brief_html(payload: ReportBriefRequest):
    html_content = generate_intelligence_brief_html(
        result=payload.result,
        query_text=payload.query_text or "",
        execution_id=payload.execution_id or "",
        observations=payload.observations or []
    )
    return HTMLResponse(content=html_content)


@app.get("/api/reports/brief/{history_id}", response_class=HTMLResponse)
def get_history_report_brief_html(history_id: str):
    # Find in in-memory history if present
    found_entry = None
    for entry in ANALYSIS_HISTORY:
        if entry.get("id") == history_id or str(entry.get("timestamp")) == history_id:
            found_entry = entry
            break

    if found_entry:
        full_res = found_entry.get("full_result", {})
        html_content = generate_intelligence_brief_html(
            result=full_res,
            query_text=found_entry.get("query", ""),
            execution_id=history_id
        )
        return HTMLResponse(content=html_content)

    raise HTTPException(status_code=404, detail="Historical execution record not found")


@app.post("/api/reports/download")
def download_report_brief(payload: ReportBriefRequest):
    html_content = generate_intelligence_brief_html(
        result=payload.result,
        query_text=payload.query_text or "",
        execution_id=payload.execution_id or "",
        observations=payload.observations or []
    )
    exec_id = payload.execution_id or f"SQ-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="satquery-brief-{exec_id}.html"'
        }
    )


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