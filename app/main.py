import os
import shutil
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Response
import requests

@app.get("/api/data-sources/copernicus/quicklook/{product_id}")
def get_copernicus_quicklook(product_id: str):
    """
    Proxy live satellite quicklook raster from Copernicus Data Space Ecosystem (CDSE).
    Streams the genuine product JPEG quicklook image into SatQuery canvas and model pipeline.
    """
    clean_id = product_id.strip()
    url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({clean_id})/$value"
    try:
        resp = requests.get(url, timeout=12)
        if resp.status_code == 200 and len(resp.content) > 0:
            return Response(content=resp.content, media_type="image/jpeg")
    except Exception as e:
        pass

    raise HTTPException(status_code=404, detail="Copernicus quicklook image temporarily unavailable")
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent.orchestrator import agent_orchestrator
from app.models.registry import registry_instance
from app.utils.metadata_extractor import MetadataExtractor
from app.demo.datasets import DEMO_SCENARIOS
from app.data_sources import (
    satellite_search_service,
    SatelliteSearchError,
    InvalidSearchRequestError,
    ProviderNotFoundError,
)

app = FastAPI(
    title="SatQuery AI",
    description="Ask questions. Understand Earth. AI-Powered Remote-Sensing Analysis Platform API.",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "app", "static", "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
FRONTEND_DIST_DIR = os.path.join(BASE_DIR, "frontend", "dist")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if os.path.exists(os.path.join(FRONTEND_DIST_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST_DIR, "assets")), name="assets")


# In-memory session history log
ANALYSIS_HISTORY: List[Dict[str, Any]] = []

class AnalyzeRequest(BaseModel):
    query: str
    input_mode: str = "single_image" # 'single_image', 'bi_temporal', 'optical_sar'
    images: List[Dict[str, Any]]

class SatelliteSearchApiRequest(BaseModel):
    provider: str = "copernicus"
    bbox: List[float]  # [min_lon, min_lat, max_lon, max_lat]
    start_date: str
    end_date: str
    collection: str = "sentinel-2-l2a"
    max_cloud_cover: Optional[float] = None
    limit: int = 10

@app.get("/api/health")
def health_check():
    return {"status": "online", "platform": "SatQuery AI", "tagline": "Ask questions. Understand Earth."}

@app.get("/api/data-sources/providers")
def list_satellite_providers():
    """Returns list of registered satellite data providers."""
    return {"providers": satellite_search_service.list_providers()}

@app.post("/api/data-sources/search")
def search_satellite_data(req: SatelliteSearchApiRequest):
    """
    Search external satellite data catalogue (e.g. Copernicus CDSE).
    Returns normalized SatelliteProduct metadata list.
    """
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
            }
        )
        return {
            "status": "success",
            "provider": req.provider,
            "count": len(results),
            "products": [prod.model_dump() for prod in results]
        }
    except InvalidSearchRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ProviderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SatelliteSearchError as e:
        raise HTTPException(status_code=502, detail=f"Satellite provider search failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal search error: {str(e)}")

@app.get("/api/models")
def get_models():
    """Returns registry of available remote-sensing models & analytical tools."""
    return {"models": registry_instance.list_models()}

@app.get("/api/demos")
def get_demos():
    """Returns built-in demo scenarios."""
    return {"demos": DEMO_SCENARIOS}

@app.get("/api/demos/{demo_id}")
def get_demo_by_id(demo_id: str):
    for demo in DEMO_SCENARIOS:
        if demo["id"] == demo_id:
            return demo
    raise HTTPException(status_code=404, detail="Demo scenario not found")

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    """Uploads a satellite image and extracts genuine metadata."""
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    metadata = MetadataExtractor.extract_metadata(file_path, file.filename)
    if not metadata.get("valid", True):
        raise HTTPException(status_code=400, detail=metadata.get("error", "Invalid file"))

    # Return public relative URL
    metadata["url"] = f"/static/uploads/{file.filename}"
    return metadata

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    """
    Main endpoint for SatQuery AI analysis.
    Receives user query, input_mode, and image metadata list.
    Returns task classification, selected model, step-by-step progress, natural language answer,
    visual evidence overlay instructions, confidence, and auditable execution summary.
    """
    if not req.query or len(req.query.strip()) == 0:
        raise HTTPException(status_code=400, detail="Query string cannot be empty")

    if not req.images or len(req.images) == 0:
        raise HTTPException(status_code=400, detail="At least one satellite image is required")

    if req.input_mode == "bi_temporal" and len(req.images) < 2:
        return {
            "error": True,
            "message": "Two images are required for bi-temporal change analysis (Image A and Image B)."
        }

    # Execute orchestrator pipeline
    result = agent_orchestrator.process_query(
        query=req.query,
        images=req.images,
        input_mode=req.input_mode
    )

    # Save to history
    history_entry = {
        "id": f"rec_{len(ANALYSIS_HISTORY)+1}",
        "query": req.query,
        "input_mode": req.input_mode,
        "task": result["task"],
        "model_used": result["selected_model"]["name"],
        "confidence": result["confidence"],
        "answer_summary": result["answer"][:120] + "...",
        "timestamp": result["execution_summary"]["audit_timestamp"],
        "full_result": result
    }
    ANALYSIS_HISTORY.insert(0, history_entry)

    return result

@app.get("/api/history")
def get_history():
    """Returns analysis execution history."""
    return {"history": ANALYSIS_HISTORY}

@app.get("/")
@app.get("/{path:path}")
def serve_frontend(path: str = ""):
    """Serve React SPA built frontend or static file fallback."""
    from fastapi.responses import FileResponse
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail=f"API endpoint '/{path}' not found")
    if path:
        possible_file = os.path.join(FRONTEND_DIST_DIR, path)
        if os.path.exists(possible_file) and os.path.isfile(possible_file):
            return FileResponse(possible_file)
    frontend_index = os.path.join(FRONTEND_DIST_DIR, "index.html")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SatQuery AI Backend Server Ready."}

