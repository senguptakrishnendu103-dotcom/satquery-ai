"""
Raster ingestion utilities for SatQuery AI.

Purpose
-------
Turn a downloaded Copernicus Data Space product archive into a model-readable
manifest of real raster assets.

Supported product families
--------------------------
- Sentinel-2 SAFE products: JP2 image bands
- Sentinel-1 GRD SAFE products: measurement GeoTIFFs

The ingestor deliberately does NOT fabricate imagery or synthetic bands.

Typical flow
------------
1. download a CDSE product archive with the existing backend/provider code
2. call RasterIngestor.ingest_archive(...)
3. receive an analysis manifest containing:
   - product type/platform
   - extracted SAFE root
   - discovered raster assets
   - semantic band map
   - recommended display raster
   - validation details

The module uses Rasterio when available and otherwise can still inspect ZIP
structure and return discovered assets. Scientific raster validation requires
Rasterio.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger("satquery.utils.raster_ingestor")


try:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import from_origin
    from rasterio.warp import calculate_default_transform, reproject
except ImportError:  # pragma: no cover
    rasterio = None
    Resampling = None
    from_origin = None
    calculate_default_transform = None
    reproject = None


SUPPORTED_ARCHIVE_SUFFIXES = (".zip",)
SUPPORTED_RASTER_SUFFIXES = (
    ".tif",
    ".tiff",
    ".jp2",
    ".j2k",
)

S2_BAND_ORDER_10M = ("B02", "B03", "B04", "B08")
S2_BAND_ORDER_20M = ("B05", "B06", "B07", "B8A", "B11", "B12")
S1_POLARIZATIONS = ("VV", "VH", "HH", "HV")


@dataclass
class RasterAsset:
    """A discovered real raster asset."""

    path: str
    name: str
    asset_type: str
    semantic_band: Optional[str] = None
    polarization: Optional[str] = None
    resolution_m: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    count: Optional[int] = None
    dtype: Optional[str] = None
    crs: Optional[str] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    transform: Optional[Any] = None
    nodata: Optional[float] = None


def _norm_path(value: os.PathLike[str] | str) -> Path:
    return Path(value).expanduser().resolve()


def _safe_extract_zip(zip_path: Path, output_dir: Path) -> Path:
    """
    Safely extract a ZIP without allowing path traversal.
    Returns output_dir.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    root = output_dir.resolve()

    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            member_path = (output_dir / member.filename).resolve()
            if not str(member_path).startswith(str(root) + os.sep) and member_path != root:
                raise ValueError(
                    f"Unsafe ZIP member path detected: {member.filename}"
                )
        archive.extractall(output_dir)

    return output_dir


def _find_safe_roots(extract_dir: Path) -> List[Path]:
    """
    Find Sentinel SAFE directories. Handles:
      <name>.SAFE/
      nested <name>.SAFE/
    """
    roots: List[Path] = []

    for item in extract_dir.rglob("*"):
        if item.is_dir() and item.name.upper().endswith(".SAFE"):
            roots.append(item)

    roots.sort(key=lambda p: (len(p.parts), str(p).lower()))
    return roots


def _find_raster_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for item in root.rglob("*"):
        if item.is_file() and item.suffix.lower() in SUPPORTED_RASTER_SUFFIXES:
            files.append(item)
    return sorted(files, key=lambda p: str(p).lower())


def _detect_product_family(
    archive_path: Path,
    safe_root: Optional[Path],
    raster_files: Sequence[Path],
) -> str:
    text_parts = [archive_path.name.lower()]
    if safe_root:
        text_parts.append(safe_root.name.lower())
    text_parts.extend(p.name.lower() for p in raster_files[:30])
    text = " ".join(text_parts)

    if "sentinel-2" in text or "sentinel_2" in text or "s2" in text:
        return "sentinel-2"

    if "sentinel-1" in text or "sentinel_1" in text or "s1" in text:
        return "sentinel-1"

    # Structural Sentinel-2 clue: GRANULE/.../IMG_DATA + JP2.
    if any("granule" in part.parts and "img_data" in part.parts for part in raster_files):
        if any(p.suffix.lower() in (".jp2", ".j2k") for p in raster_files):
            return "sentinel-2"

    # Structural Sentinel-1 clue: measurement directory + TIFF.
    if any("measurement" in part.parts for part in raster_files):
        if any(p.suffix.lower() in (".tif", ".tiff") for p in raster_files):
            return "sentinel-1"

    return "unknown"


def _extract_s2_band_code(path: Path) -> Optional[str]:
    """
    Extract Sentinel-2 band identifiers from product filenames.

    Examples:
      *_B02_10m.jp2
      *_B8A_20m.jp2
      *_B11_20m.jp2
    """
    name = path.name.upper()

    match = re.search(r"(?:_|-)(B(?:0[1-9]|1[0-2]|8A))(?:_|-|\.)", name)
    if match:
        return match.group(1)

    match = re.search(r"(B8A|B0[1-9]|B1[0-2])", name)
    if match:
        return match.group(1)

    return None


def _extract_s2_resolution(path: Path) -> Optional[float]:
    name = path.name.lower()

    match = re.search(r"(?:_|-)(10m|20m|60m)(?:_|-|\.)", name)
    if match:
        return float(match.group(1).replace("m", ""))

    parts = {part.lower() for part in path.parts}
    for value in (10.0, 20.0, 60.0):
        if f"r{int(value)}m" in parts:
            return value

    return None


def _extract_s1_polarization(path: Path) -> Optional[str]:
    """
    Detect VV/VH/HH/HV from Sentinel-1 measurement filename.
    """
    name = path.name.upper()

    # Prefer explicit token boundaries.
    for pol in S1_POLARIZATIONS:
        if re.search(rf"(?:^|[_-]){pol}(?:[_-]|\.)", name):
            return pol

    # Common Sentinel-1 measurement naming still often contains the token.
    for pol in S1_POLARIZATIONS:
        if pol in name:
            return pol

    return None


def _read_raster_metadata(path: Path) -> Dict[str, Any]:
    """
    Read basic geospatial metadata.

    For a JP2/TIFF this validates that the file is actually readable by Rasterio.
    """
    if rasterio is None:
        return {}

    with rasterio.open(path) as src:
        transform = src.transform

        resolution_x = abs(float(transform.a)) if transform is not None else None
        resolution_y = abs(float(transform.e)) if transform is not None else None

        return {
            "width": int(src.width),
            "height": int(src.height),
            "count": int(src.count),
            "dtype": src.dtypes[0] if src.count else None,
            "crs": str(src.crs) if src.crs else None,
            "bounds": tuple(float(v) for v in src.bounds),
            "resolution_x": resolution_x,
            "resolution_y": resolution_y,
            "nodata": float(src.nodata) if src.nodata is not None else None,
            "transform": src.transform,
        }


def _asset_from_file(
    path: Path,
    product_family: str,
) -> RasterAsset:
    metadata = _read_raster_metadata(path)

    if product_family == "sentinel-2":
        band = _extract_s2_band_code(path)
        resolution = _extract_s2_resolution(path)

        semantic = {
            "B02": "blue",
            "B03": "green",
            "B04": "red",
            "B05": "red_edge_1",
            "B06": "red_edge_2",
            "B07": "red_edge_3",
            "B08": "nir",
            "B8A": "nir_narrow",
            "B11": "swir1",
            "B12": "swir2",
        }.get(band or "")

        return RasterAsset(
            path=str(path),
            name=path.name,
            asset_type="optical_band",
            semantic_band=semantic,
            resolution_m=resolution
            or metadata.get("resolution_x"),
            width=metadata.get("width"),
            height=metadata.get("height"),
            count=metadata.get("count"),
            dtype=metadata.get("dtype"),
            crs=metadata.get("crs"),
            bounds=metadata.get("bounds"),
            transform=metadata.get("transform"),
            nodata=metadata.get("nodata"),
        )

    polarization = _extract_s1_polarization(path)
    return RasterAsset(
        path=str(path),
        name=path.name,
        asset_type="sar_measurement",
        polarization=polarization,
        semantic_band=polarization.lower() if polarization else None,
        resolution_m=metadata.get("resolution_x"),
        width=metadata.get("width"),
        height=metadata.get("height"),
        count=metadata.get("count"),
        dtype=metadata.get("dtype"),
        crs=metadata.get("crs"),
        bounds=metadata.get("bounds"),
        transform=metadata.get("transform"),
        nodata=metadata.get("nodata"),
    )


def _asset_to_json(asset: RasterAsset) -> Dict[str, Any]:
    data = asdict(asset)

    # Affine objects are not JSON serializable.
    if data.get("transform") is not None:
        data["transform"] = tuple(data["transform"])
    return data


def _choose_s2_assets(
    assets: Sequence[RasterAsset],
) -> Dict[str, RasterAsset]:
    """
    Pick a deterministic Sentinel-2 asset for each semantic band.

    Preference:
      - 10 m version where available for RGB/NIR
      - 20 m version for SWIR, later resampled when a common grid is requested
    """
    chosen: Dict[str, RasterAsset] = {}

    priority = {
        "blue": ("B02",),
        "green": ("B03",),
        "red": ("B04",),
        "nir": ("B08",),
        "swir1": ("B11",),
        "swir2": ("B12",),
    }

    for semantic, band_codes in priority.items():
        candidates = [
            a
            for a in assets
            if a.semantic_band == semantic
            and any(code in a.name.upper() for code in band_codes)
        ]

        if not candidates:
            continue

        # Lower resolution number = finer native grid.
        candidates.sort(
            key=lambda a: (
                float(a.resolution_m) if a.resolution_m else 9999.0,
                a.path.lower(),
            )
        )
        chosen[semantic] = candidates[0]

    return chosen


def _choose_s1_assets(
    assets: Sequence[RasterAsset],
) -> Dict[str, RasterAsset]:
    chosen: Dict[str, RasterAsset] = {}

    for polarization in S1_POLARIZATIONS:
        candidates = [
            a
            for a in assets
            if a.polarization == polarization
        ]
        if not candidates:
            continue

        # Use deterministic ordering.
        candidates.sort(key=lambda a: a.path.lower())
        chosen[polarization.lower()] = candidates[0]

    return chosen


def _validate_common_grid(paths: Sequence[Path]) -> Tuple[int, int, Optional[str]]:
    if rasterio is None:
        raise RuntimeError(
            "Rasterio is required for analysis-grid validation."
        )

    if not paths:
        raise ValueError("No raster paths were supplied.")

    with rasterio.open(paths[0]) as ref:
        width, height = ref.width, ref.height
        crs = str(ref.crs) if ref.crs else None

    for path in paths[1:]:
        with rasterio.open(path) as src:
            if src.width != width or src.height != height:
                return width, height, "different_dimensions"
            src_crs = str(src.crs) if src.crs else None
            if src_crs != crs:
                return width, height, "different_crs"

    return width, height, None


def build_multispectral_stack(
    band_paths: Dict[str, str],
    output_path: os.PathLike[str] | str,
    target_resolution_m: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Create a canonical GeoTIFF stack from real Sentinel-2 bands.

    Output band order:
      1 blue
      2 green
      3 red
      4 nir
      5 swir1
      6 swir2

    Bands missing from the product are not fabricated: the function requires
    every requested input path to exist.
    """
    if rasterio is None or reproject is None:
        raise RuntimeError(
            "Rasterio is required to build an analysis-ready multispectral stack."
        )

    required_order = ("blue", "green", "red", "nir", "swir1", "swir2")
    missing = [k for k in required_order if not band_paths.get(k)]
    if missing:
        raise ValueError(
            "Cannot build a full multispectral stack; missing bands: "
            + ", ".join(missing)
        )

    sources = [Path(band_paths[k]) for k in required_order]
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(f"Raster band does not exist: {source}")

    with rasterio.open(sources[0]) as ref:
        dst_crs = ref.crs
        if dst_crs is None:
            raise ValueError("Reference optical raster has no CRS.")

        native_x = abs(float(ref.transform.a))
        native_y = abs(float(ref.transform.e))
        native_resolution = max(native_x, native_y)

        if target_resolution_m is None:
            target_resolution_m = native_resolution

        if target_resolution_m <= 0:
            raise ValueError("target_resolution_m must be positive.")

        transform, width, height = calculate_default_transform(
            ref.crs,
            dst_crs,
            ref.width,
            ref.height,
            *ref.bounds,
            resolution=target_resolution_m,
        )

        profile = ref.profile.copy()
        profile.update(
            driver="GTiff",
            dtype="float32",
            count=len(required_order),
            width=width,
            height=height,
            crs=dst_crs,
            transform=transform,
            compress="deflate",
            predictor=2,
            tiled=True,
            BIGTIFF="IF_SAFER",
            nodata=np.nan,
        )

    output = _norm_path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(output, "w", **profile) as dst:
        for idx, semantic in enumerate(required_order, start=1):
            source = Path(band_paths[semantic])

            with rasterio.open(source) as src:
                destination = np.full(
                    (height, width),
                    np.nan,
                    dtype=np.float32,
                )

                reproject(
                    source=rasterio.band(src, 1),
                    destination=destination,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.bilinear,
                    dst_nodata=np.nan,
                )

                dst.write(destination, idx)
                dst.set_band_description(idx, semantic)

    return {
        "path": str(output),
        "band_map": {
            semantic: index
            for index, semantic in enumerate(required_order, start=1)
        },
        "width": width,
        "height": height,
        "count": len(required_order),
        "crs": str(dst_crs),
        "resolution_m": float(target_resolution_m),
    }


class RasterIngestor:
    """
    Public ingestion API used by main.py.

    Each archive gets an isolated extraction directory so separate products do
    not collide.
    """

    def __init__(
        self,
        storage_dir: os.PathLike[str] | str,
    ) -> None:
        self.storage_dir = _norm_path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def ingest_archive(
        self,
        archive_path: os.PathLike[str] | str,
        *,
        product_id: Optional[str] = None,
        collection: Optional[str] = None,
        create_analysis_stack: bool = True,
    ) -> Dict[str, Any]:
        archive = _norm_path(archive_path)

        if not archive.is_file():
            raise FileNotFoundError(f"Product archive not found: {archive}")

        if archive.suffix.lower() not in SUPPORTED_ARCHIVE_SUFFIXES:
            raise ValueError(
                f"Unsupported archive format '{archive.suffix}'. "
                "Expected a CDSE ZIP product."
            )

        product_key = self._safe_product_key(product_id or archive.stem)
        extraction_dir = self.storage_dir / f"{product_key}_extracted"

        # Idempotent ingestion: clear only our own per-product directory.
        if extraction_dir.exists():
            shutil.rmtree(extraction_dir)

        _safe_extract_zip(archive, extraction_dir)

        safe_roots = _find_safe_roots(extraction_dir)
        safe_root = safe_roots[0] if safe_roots else None

        raster_root = safe_root or extraction_dir
        raster_files = _find_raster_files(raster_root)

        if not raster_files:
            raise ValueError(
                f"No GeoTIFF/TIFF/JP2 raster assets were found in {archive.name}."
            )

        family = self._normalize_family(
            collection=collection,
            detected=_detect_product_family(
                archive,
                safe_root,
                raster_files,
            ),
        )

        if family == "unknown":
            raise ValueError(
                "Unable to determine whether the CDSE product is Sentinel-1 "
                "or Sentinel-2 from its archive structure/name."
            )

        assets = [
            _asset_from_file(path, family)
            for path in raster_files
        ]

        if family == "sentinel-2":
            selected = _choose_s2_assets(assets)
            result = self._build_s2_manifest(
                archive=archive,
                extraction_dir=extraction_dir,
                safe_root=safe_root,
                assets=assets,
                selected=selected,
                product_id=product_id,
                collection=collection,
                create_analysis_stack=create_analysis_stack,
            )
        else:
            selected = _choose_s1_assets(assets)
            result = self._build_s1_manifest(
                archive=archive,
                extraction_dir=extraction_dir,
                safe_root=safe_root,
                assets=assets,
                selected=selected,
                product_id=product_id,
                collection=collection,
            )

        manifest_path = extraction_dir / "analysis_manifest.json"
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, default=str)

        result["manifest_path"] = str(manifest_path)
        return result

    def _build_s2_manifest(
        self,
        *,
        archive: Path,
        extraction_dir: Path,
        safe_root: Optional[Path],
        assets: Sequence[RasterAsset],
        selected: Dict[str, RasterAsset],
        product_id: Optional[str],
        collection: Optional[str],
        create_analysis_stack: bool,
    ) -> Dict[str, Any]:
        required_for_full_stack = (
            "blue",
            "green",
            "red",
            "nir",
            "swir1",
            "swir2",
        )
        available = sorted(selected.keys())

        band_paths = {
            semantic: asset.path
            for semantic, asset in selected.items()
        }

        analysis_asset = None
        stack_error = None

        if create_analysis_stack:
            missing = [
                semantic
                for semantic in required_for_full_stack
                if semantic not in band_paths
            ]
            if not missing:
                stack_path = extraction_dir / "analysis_multispectral.tif"
                try:
                    analysis_asset = build_multispectral_stack(
                        band_paths,
                        stack_path,
                        target_resolution_m=self._infer_target_resolution(
                            selected
                        ),
                    )
                except Exception as exc:
                    stack_error = str(exc)
                    logger.exception(
                        "Unable to create analysis stack for %s", archive.name
                    )

        # A display raster can exist even if SWIR is absent.
        display_asset = None
        display_bands = ("red", "green", "blue")
        if all(k in band_paths for k in display_bands):
            display_asset = {
                "red": band_paths["red"],
                "green": band_paths["green"],
                "blue": band_paths["blue"],
            }

        validation = {
            "rasterio_available": rasterio is not None,
            "safe_detected": safe_root is not None,
            "total_raster_files": len(assets),
            "semantic_bands": available,
            "rgb_ready": all(k in band_paths for k in display_bands),
            "nir_ready": "nir" in band_paths,
            "ndwi_ready": all(k in band_paths for k in ("green", "nir")),
            "ndbi_ready": all(k in band_paths for k in ("swir1", "nir")),
            "full_multispectral_stack_ready": all(
                k in band_paths for k in required_for_full_stack
            ),
            "analysis_stack_created": analysis_asset is not None,
            "analysis_stack_error": stack_error,
        }

        # The analysis path should point to the actual stack where possible.
        # Otherwise expose the real RGB band rather than a fake/preview asset.
        model_file_path = (
            analysis_asset["path"]
            if analysis_asset is not None
            else band_paths.get("red")
        )

        return {
            "status": "success",
            "product_family": "sentinel-2",
            "product_id": product_id,
            "collection": collection,
            "source_archive": str(archive),
            "extraction_dir": str(extraction_dir),
            "safe_root": str(safe_root) if safe_root else None,
            "model_file_path": model_file_path,
            "local_path": model_file_path,
            "analysis_asset": analysis_asset,
            "display_asset": display_asset,
            "band_map": {
                semantic: {
                    "path": asset.path,
                    "name": asset.name,
                    "resolution_m": asset.resolution_m,
                    "width": asset.width,
                    "height": asset.height,
                    "crs": asset.crs,
                }
                for semantic, asset in selected.items()
            },
            "assets": [_asset_to_json(asset) for asset in assets],
            "validation": validation,
        }

    def _build_s1_manifest(
        self,
        *,
        archive: Path,
        extraction_dir: Path,
        safe_root: Optional[Path],
        assets: Sequence[RasterAsset],
        selected: Dict[str, RasterAsset],
        product_id: Optional[str],
        collection: Optional[str],
    ) -> Dict[str, Any]:
        polarizations = sorted(selected.keys())

        measurement_paths = {
            polarization: asset.path
            for polarization, asset in selected.items()
        }

        # Prefer VV for a common default, then VH, HH, HV.
        model_file_path = (
            measurement_paths.get("vv")
            or measurement_paths.get("vh")
            or measurement_paths.get("hh")
            or measurement_paths.get("hv")
        )

        if not model_file_path:
            raise ValueError(
                "Sentinel-1 product was detected, but no VV/VH/HH/HV "
                "measurement raster could be identified."
            )

        validation = {
            "rasterio_available": rasterio is not None,
            "safe_detected": safe_root is not None,
            "total_raster_files": len(assets),
            "polarizations": polarizations,
            "sar_ready": True,
        }

        return {
            "status": "success",
            "product_family": "sentinel-1",
            "product_id": product_id,
            "collection": collection,
            "source_archive": str(archive),
            "extraction_dir": str(extraction_dir),
            "safe_root": str(safe_root) if safe_root else None,
            "model_file_path": model_file_path,
            "local_path": model_file_path,
            "analysis_asset": {
                "path": model_file_path,
                "polarization": Path(model_file_path).name,
            },
            "band_map": {
                polarization: {
                    "path": asset.path,
                    "name": asset.name,
                    "resolution_m": asset.resolution_m,
                    "width": asset.width,
                    "height": asset.height,
                    "crs": asset.crs,
                }
                for polarization, asset in selected.items()
            },
            "assets": [_asset_to_json(asset) for asset in assets],
            "validation": validation,
        }

    @staticmethod
    def _safe_product_key(value: str) -> str:
        value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value))
        value = value.strip("._-")
        return value[:150] or f"product_{os.getpid()}"

    @staticmethod
    def _normalize_family(
        collection: Optional[str],
        detected: str,
    ) -> str:
        value = (collection or "").lower()

        if "sentinel-2" in value or "sentinel_2" in value or value.startswith("s2"):
            return "sentinel-2"

        if "sentinel-1" in value or "sentinel_1" in value or value.startswith("s1"):
            return "sentinel-1"

        return detected

    @staticmethod
    def _infer_target_resolution(
        selected: Dict[str, RasterAsset],
    ) -> float:
        """
        Use the finest available optical grid, normally 10 m for Sentinel-2
        B02/B03/B04/B08. SWIR bands are resampled onto that grid.
        """
        resolutions = [
            float(asset.resolution_m)
            for semantic, asset in selected.items()
            if semantic in ("blue", "green", "red", "nir")
            and asset.resolution_m
            and asset.resolution_m > 0
        ]

        return min(resolutions) if resolutions else 10.0


def ingest_cdse_archive(
    archive_path: os.PathLike[str] | str,
    storage_dir: os.PathLike[str] | str,
    *,
    product_id: Optional[str] = None,
    collection: Optional[str] = None,
    create_analysis_stack: bool = True,
) -> Dict[str, Any]:
    """
    Convenience wrapper used by the FastAPI route.
    """
    return RasterIngestor(storage_dir).ingest_archive(
        archive_path,
        product_id=product_id,
        collection=collection,
        create_analysis_stack=create_analysis_stack,
    )
