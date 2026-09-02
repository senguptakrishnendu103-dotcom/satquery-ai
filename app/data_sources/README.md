# SatQuery AI Data Sources Architecture (Stage 1 & Stage 2)

This module implements **Stage 1** (Provider Abstraction) and **Stage 2** (Live Copernicus Data Space Ecosystem Search Integration) for **SatQuery AI**.

It provides a provider-agnostic abstraction layer that allows SatQuery AI to search external satellite repositories (such as Copernicus CDSE) and normalize real product metadata without coupling core AI agent orchestrators to specific provider APIs or downloading binary assets prior to user selection.

---

## 🏗️ Architecture Overview

```
User Query / Agent
       │
       ▼
SatelliteSearchService (app/data_sources/search_service.py)
       │
  (Validates SearchRequest parameters)
       │
       ▼
SatelliteDataProvider (Abstract Base Class in base_provider.py)
       ├── CopernicusProvider (Live CDSE OData API Integration)
       ├── BhuvanProvider (Future)
       └── USGSProvider (Future)
       │
       ▼
Copernicus Data Space Ecosystem (CDSE) Catalogue
(https://catalogue.dataspace.copernicus.eu/odata/v1/Products)
       │
       ▼
SatelliteProduct Metadata (Normalized representation with GeoJSON Footprint)
```

---

## 📁 Key Components

### 1. `base_provider.py`
Defines data structures and the provider contract:
- **`SearchRequest`**: Strongly typed & validated search parameters (`bbox`, `start_date`, `end_date`, `collection`, `max_cloud_cover`, `limit`, `platform`, `processing_level`).
  - Strict spatial validation: WGS84 geographic bounding box `[min_lon, min_lat, max_lon, max_lat]` with bounds check (`-180 <= lon <= 180`, `-90 <= lat <= 90`, `min_lon <= max_lon`, `min_lat <= max_lat`).
  - Strict temporal validation: `start_date <= end_date`.
- **`SatelliteProduct`**: Normalized representation of satellite product metadata (`product_id`, `provider`, `collection`, `platform`, `instrument`, `modality`, `acquisition_datetime`, `processing_level`, `cloud_cover`, `bbox`, `crs`, `resolution`, `available_bands`, `download_url`, `geo_footprint`, `metadata`, `assets`).
- **`SatelliteDataProvider`**: Abstract base class defining `name`, `supported_collections`, `supported_modalities`, `search()`, `get_product()`, and `get_download_url()`.

### 2. `search_service.py`
Defines `SatelliteSearchService`, which:
- Registers data providers (`register_provider`).
- Prevents duplicate provider registration unless explicitly instructed (`replace=True`).
- Validates search requests prior to provider execution.
- Dispatches search queries to registered providers.

### 3. `providers/copernicus_provider.py`
Live implementation of `CopernicusProvider(SatelliteDataProvider)` for Copernicus Data Space Ecosystem (CDSE).
- Base Endpoint: `https://catalogue.dataspace.copernicus.eu/odata/v1/Products`
- Supported Collections:
  - `sentinel-2` / `sentinel-2-l2a` / `sentinel-2-l1c` (Optical / Multispectral)
  - `sentinel-1` / `sentinel-1-grd` (SAR)
- OData Filter Query Construction: Combines collection filtering, ISO UTC date ranges, and spatial intersection via `OData.CSC.Intersects(area=geography'SRID=4326;POLYGON(...)')`.
- Spatial Footprint & Intersection: Parses WKT Footprints into GeoJSON polygons and performs client-side bounding box intersection checks.
- Resilience: Retries on transient HTTP 429 & 5xx errors with exponential backoff.
- Credentials: `CDSE_USERNAME`, `CDSE_PASSWORD`, `SATQUERY_COPERNICUS_CLIENT_ID`, `SATQUERY_COPERNICUS_CLIENT_SECRET` can be configured via environment variables for Stage 3 downloads. Search operates without requiring authentication headers.

### 4. `exceptions.py`
Provides custom domain exceptions:
- `SatelliteProviderError` (Base exception)
- `SatelliteSearchError`
- `ProviderNotFoundError`
- `InvalidSearchRequestError`
- `DuplicateProviderError`

---

## 💻 Usage Examples

### 1. Performing a Search via `SatelliteSearchService`

```python
from app.data_sources import satellite_search_service

request = {
    "bbox": [-60.5, -3.2, -59.8, -2.5],
    "start_date": "2024-01-01",
    "end_date": "2024-08-30",
    "collection": "sentinel-2-l2a",
    "max_cloud_cover": 20.0,
    "limit": 5
}

# Search Copernicus provider
try:
    results = satellite_search_service.search("copernicus", request)
    for prod in results:
        print(f"ID: {prod.product_id} | Platform: {prod.platform} | Cloud Cover: {prod.cloud_cover}%")
        print(f"Footprint: {prod.geo_footprint}")
except Exception as e:
    print(f"Search request error: {e}")
```

---

## 🧪 Running Unit & Integration Tests

### Run Offline Unit Test Suite (Mocked HTTP):

```bash
python -m unittest tests/test_data_sources.py
```

### Run Live CDSE Integration Test Suite (Hits Live CDSE API):

```bash
$env:SATQUERY_RUN_LIVE_CDSE_TESTS="1"; python -m unittest tests/test_data_sources.py
```
