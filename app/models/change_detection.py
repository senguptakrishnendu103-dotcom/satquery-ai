"""
SatQuery AI - Bi-Temporal Change Detection.

Real-data change detection adapter.

The implementation supports:
- GeoTIFF/TIFF/JP2 inputs through Rasterio
- PNG/JPEG inputs through PIL as a benchmark/demo-compatible path
- geospatial alignment of Image B onto Image A when CRS/transform exist
- multispectral band comparison when both observations expose compatible bands
- deterministic raster-difference change masks
- georeferenced evidence masks when SATQUERY_MASK_DIR is configured

No synthetic imagery, fabricated dates, fabricated change percentages, or
hardcoded confidence values are generated.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from app.models.base_model import BaseRSModel
from app.utils.image_resolver import ImageResolver

try:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import reproject
except ImportError:  # pragma: no cover
    rasterio = None
    Resampling = None
    reproject = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


class BiTemporalChangeDetectionModel(BaseRSModel):
    """
    Deterministic change-detection adapter.

    When SATQUERY_CHANGE_MODEL_ID is configured, the class exposes an explicit
    extension point for a trained change-detection checkpoint. Until an actual
    checkpoint adapter is implemented, deterministic raster comparison is used.

    The deterministic result is not a probabilistic model prediction and
    therefore does not report a fabricated confidence value.
    """

    @property
    def name(self) -> str:
        return os.getenv(
            "SATQUERY_CHANGE_MODEL_NAME",
            "SatQuery Bi-Temporal Change Detector",
        )

    @property
    def description(self) -> str:
        return (
            "Bi-temporal remote-sensing change detection for comparing "
            "spatially corresponding observations acquired at different dates."
        )

    @property
    def supported_input_types(self) -> List[str]:
        return ["bi_temporal"]

    @property
    def supported_tasks(self) -> List[str]:
        return ["CHANGE_DETECTION"]

    @property
    def version(self) -> str:
        return os.getenv(
            "SATQUERY_CHANGE_MODEL_VERSION",
            "deterministic-raster-v1",
        )

    @property
    def provider(self) -> str:
        return os.getenv(
            "SATQUERY_CHANGE_MODEL_PROVIDER",
            "local",
        )

    @property
    def model_family(self) -> str:
        return "bi_temporal_change_detection"

    @property
    def supports_geotiff(self) -> bool:
        return True

    @property
    def supports_multispectral(self) -> bool:
        return True

    @property
    def requires_geospatial_input(self) -> bool:
        return False

    def __init__(self) -> None:
        self.model_id = os.getenv("SATQUERY_CHANGE_MODEL_ID")
        self._model = None
        self._load_error: Optional[str] = None

    # ==================================================================
    # MAIN EXECUTION
    # ==================================================================

    def execute(
        self,
        images: List[Dict[str, Any]],
        query: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()

        self._validate_observations(images)

        image_a = images[0]
        image_b = images[1]

        date_a = self._resolve_date(image_a, metadata, "date_a")
        date_b = self._resolve_date(image_b, metadata, "date_b")

        observation_metadata = {
            "date_a": date_a,
            "date_b": date_b,
            "modality_a": image_a.get("modality"),
            "modality_b": image_b.get("modality"),
            "product_id_a": image_a.get("product_id"),
            "product_id_b": image_b.get("product_id"),
        }

        try:
            analysis = self._run_change_detection(
                image_a=image_a,
                image_b=image_b,
                query=query,
                metadata={
                    **metadata,
                    **observation_metadata,
                },
            )
        except Exception as exc:
            raise RuntimeError(
                f"Bi-temporal change analysis failed: {exc}"
            ) from exc

        inference_time_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        statistics = analysis.get("change_statistics") or {}
        answer = analysis.get("answer") or self._build_evidence_summary(
            statistics,
            date_a,
            date_b,
        )

        confidence = self._normalize_confidence(
            analysis.get("confidence")
        )

        visual_evidence = analysis.get("visual_evidence")
        if visual_evidence is None:
            visual_evidence = {
                "overlay_type": "change_detection_mask",
                "label": f"Bi-Temporal Change Map ({date_a} vs {date_b})",
                "changed_regions": [],
                "change_mask_url": None,
            }

        execution_details = {
            "model_architecture": analysis.get(
                "model_architecture",
                self.name,
            ),
            "model_id": self.model_id,
            "provider": self.provider,
            "version": self.version,
            "inference_time_ms": inference_time_ms,
            "execution_status": analysis.get(
                "execution_status",
                "completed",
            ),
            "parameters_used": {
                **(analysis.get("parameters_used") or {}),
                "image_a_date": date_a,
                "image_b_date": date_b,
                "input_count": 2,
            },
            "observation_metadata": observation_metadata,
            "confidence_note": (
                "Confidence is 0 when the result is deterministic or "
                "uncalibrated rather than a trained probabilistic prediction."
            ),
        }

        if analysis.get("dataset_reference") is not None:
            execution_details["dataset_reference"] = analysis[
                "dataset_reference"
            ]

        result: Dict[str, Any] = {
            "answer": answer,
            "confidence": confidence,
            "visual_evidence": visual_evidence,
            "execution_details": execution_details,
            "change_statistics": statistics,
        }

        for key in (
            "change_categories",
            "uncertainty",
            "raw_model_output",
            "geometries",
        ):
            if key in analysis:
                result[key] = analysis[key]

        return self.validate_result(result)

    # ==================================================================
    # INPUT VALIDATION
    # ==================================================================

    @staticmethod
    def _validate_observations(
        images: List[Dict[str, Any]],
    ) -> None:
        if not images or len(images) != 2:
            raise ValueError(
                "Bi-temporal change detection requires exactly two observations."
            )

        for index, image in enumerate(images):
            if not isinstance(image, dict):
                raise TypeError(
                    f"Observation {index + 1} must be a dictionary."
                )

            source = (
                image.get("file_path")
                or image.get("local_path")
                or image.get("image_path")
                or image.get("path")
                or image.get("image")
            )

            if not source:
                raise ValueError(
                    f"Observation {index + 1} does not contain a usable "
                    "image/raster source."
                )

            if isinstance(source, (str, Path)):
                if not Path(source).is_file():
                    raise FileNotFoundError(
                        f"Observation {index + 1} file does not exist: {source}"
                    )

    # ==================================================================
    # CHANGE ENGINE
    # ==================================================================

    def _run_change_detection(
        self,
        image_a: Dict[str, Any],
        image_b: Dict[str, Any],
        query: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Prefer a configured trained checkpoint only when a concrete adapter
        exists. Otherwise execute deterministic real-raster comparison.
        """
        if self.model_id:
            try:
                model = self._load_model()
                return self._infer(
                    model=model,
                    image_a=image_a,
                    image_b=image_b,
                    query=query,
                    metadata=metadata,
                )
            except NotImplementedError:
                # An explicitly configured model without an adapter should not
                # block the deterministic real-data path.
                pass
            except Exception as exc:
                raise RuntimeError(
                    f"Configured change model failed: {exc}"
                ) from exc

        return self._run_deterministic_change(
            image_a=image_a,
            image_b=image_b,
            metadata=metadata,
        )

    def _run_deterministic_change(
        self,
        image_a: Dict[str, Any],
        image_b: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compare actual raster pixels.

        For geospatial rasters, B is reprojected onto A's grid. For ordinary
        image files, B is resized to A's display dimensions using bilinear
        interpolation.

        For multispectral data, corresponding bands are compared after robust
        per-band normalization.
        """
        source_a = self._resolve_source(image_a)
        source_b = self._resolve_source(image_b)

        if self._is_raster_file(source_a) and self._is_raster_file(source_b):
            return self._compare_geospatial_rasters(
                Path(source_a),
                Path(source_b),
                image_a=image_a,
                image_b=image_b,
                metadata=metadata,
            )

        if Image is None:
            raise RuntimeError(
                "Pillow is required for non-raster image comparison."
            )

        # PNG/JPEG benchmark compatibility path.
        display_a = ImageResolver.load_image(image_a)
        display_b = ImageResolver.load_image(image_b)

        width, height = display_a.size
        display_b = display_b.resize(
            (width, height),
            Image.Resampling.BILINEAR,
        )

        array_a = np.asarray(display_a, dtype=np.float32)
        array_b = np.asarray(display_b, dtype=np.float32)

        diff = self._robust_difference(
            array_a,
            array_b,
        )

        return self._build_change_result(
            diff=diff,
            image=image_a,
            source_kind="display_image_difference",
            metadata=metadata,
            transform=None,
            crs=None,
            pixel_size_m=None,
        )

    def _compare_geospatial_rasters(
        self,
        path_a: Path,
        path_b: Path,
        image_a: Dict[str, Any],
        image_b: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        if rasterio is None or reproject is None:
            raise RuntimeError(
                "Rasterio is required for GeoTIFF/JP2 bi-temporal analysis."
            )

        with rasterio.open(path_a) as src_a, rasterio.open(path_b) as src_b:
            if src_a.count < 1 or src_b.count < 1:
                raise ValueError("Both rasters must contain at least one band.")

            # Reference grid = Image A.
            target_height = src_a.height
            target_width = src_a.width
            target_transform = src_a.transform
            target_crs = src_a.crs

            if target_crs is None:
                raise ValueError(
                    "Image A does not contain a CRS; geospatial alignment "
                    "cannot be guaranteed."
                )

            a = src_a.read(out_dtype="float32")
            b = self._reproject_to_reference(
                src_b,
                target_shape=(target_height, target_width),
                dst_transform=target_transform,
                dst_crs=target_crs,
            )

            # Match comparable band count. Prefer common leading bands for
            # generic user-uploaded stacks; canonical ingested Sentinel-2
            # stacks have identical band order.
            band_count = min(a.shape[0], b.shape[0])
            if band_count < 1:
                raise ValueError("No comparable bands were found.")

            a = a[:band_count]
            b = b[:band_count]

            diff = self._robust_difference(
                np.moveaxis(a, 0, -1),
                np.moveaxis(b, 0, -1),
            )

            transform = src_a.transform
            pixel_size_m = self._infer_pixel_size_m(
                transform,
                target_crs,
            )

            result = self._build_change_result(
                diff=diff,
                image=image_a,
                source_kind="geospatial_raster_difference",
                metadata=metadata,
                transform=transform,
                crs=target_crs,
                pixel_size_m=pixel_size_m,
            )

            # Record actual grid information for auditing.
            result["parameters_used"].update(
                {
                    "reference_width": src_a.width,
                    "reference_height": src_a.height,
                    "image_a_band_count": src_a.count,
                    "image_b_band_count": src_b.count,
                    "image_a_crs": str(src_a.crs),
                    "image_b_crs": str(src_b.crs) if src_b.crs else None,
                    "reference_transform": tuple(src_a.transform),
                }
            )

            return result

    @staticmethod
    def _reproject_to_reference(
        source,
        target_shape: Tuple[int, int],
        dst_transform,
        dst_crs,
    ) -> np.ndarray:
        if rasterio is None or reproject is None:
            raise RuntimeError("Rasterio is required for raster alignment.")

        target_height, target_width = target_shape
        result = np.full(
            (source.count, target_height, target_width),
            np.nan,
            dtype=np.float32,
        )

        for band_index in range(1, source.count + 1):
            reproject(
                source=rasterio.band(source, band_index),
                destination=result[band_index - 1],
                src_transform=source.transform,
                src_crs=source.crs,
                src_nodata=source.nodata,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                dst_nodata=np.nan,
                resampling=Resampling.bilinear,
            )

        return result

    # ==================================================================
    # DIFFERENCE / NORMALIZATION
    # ==================================================================

    @staticmethod
    def _robust_difference(
        array_a: np.ndarray,
        array_b: np.ndarray,
    ) -> np.ndarray:
        """
        Calculate robust absolute change.

        Each channel is normalized using joint 2nd/98th percentiles before
        differences are averaged. This avoids one raw digital-number scale
        dominating a multi-band comparison.
        """
        a = np.asarray(array_a, dtype=np.float32)
        b = np.asarray(array_b, dtype=np.float32)

        if a.shape != b.shape:
            raise ValueError(
                f"Aligned arrays must have the same shape; "
                f"got {a.shape} and {b.shape}."
            )

        if a.ndim == 2:
            a = a[..., np.newaxis]
            b = b[..., np.newaxis]

        if a.ndim != 3:
            raise ValueError(
                f"Expected HxW or HxWxC arrays; got {a.shape}."
            )

        channel_diffs: List[np.ndarray] = []

        for channel in range(a.shape[-1]):
            ca = a[..., channel]
            cb = b[..., channel]

            finite = np.isfinite(ca) & np.isfinite(cb)
            if not np.any(finite):
                continue

            combined = np.concatenate(
                (
                    ca[finite].reshape(-1),
                    cb[finite].reshape(-1),
                )
            )

            lo = float(np.percentile(combined, 2))
            hi = float(np.percentile(combined, 98))

            if hi <= lo:
                lo = float(np.min(combined))
                hi = float(np.max(combined))

            if hi <= lo:
                diff = np.zeros_like(ca, dtype=np.float32)
            else:
                na = np.clip(
                    (ca - lo) / (hi - lo),
                    0.0,
                    1.0,
                )
                nb = np.clip(
                    (cb - lo) / (hi - lo),
                    0.0,
                    1.0,
                )
                diff = np.abs(na - nb)

            diff[~finite] = np.nan
            channel_diffs.append(diff)

        if not channel_diffs:
            raise ValueError("No finite overlapping pixel values were found.")

        stacked = np.stack(channel_diffs, axis=-1)
        valid = np.isfinite(stacked)
        counts = np.count_nonzero(valid, axis=-1)

        total = np.nansum(
            np.where(valid, stacked, 0.0),
            axis=-1,
        )

        return np.divide(
            total,
            counts,
            out=np.full(
                total.shape,
                np.nan,
                dtype=np.float32,
            ),
            where=counts > 0,
        )

    # ==================================================================
    # RESULT BUILDING
    # ==================================================================

    def _build_change_result(
        self,
        *,
        diff: np.ndarray,
        image: Dict[str, Any],
        source_kind: str,
        metadata: Dict[str, Any],
        transform: Any,
        crs: Any,
        pixel_size_m: Optional[float],
    ) -> Dict[str, Any]:
        """
        Convert a real difference surface into a measurable change mask.

        Threshold is configurable via:
            metadata["change_threshold"]
            SATQUERY_CHANGE_THRESHOLD
        """
        threshold = self._get_threshold(metadata)

        valid_mask = np.isfinite(diff)
        change_mask = (diff >= threshold) & valid_mask

        valid_count = int(np.count_nonzero(valid_mask))
        changed_count = int(np.count_nonzero(change_mask))

        changed_percentage = (
            float(changed_count / valid_count * 100.0)
            if valid_count
            else 0.0
        )

        changed_area_sqkm = None
        if pixel_size_m is not None:
            changed_area_sqkm = round(
                changed_count * (pixel_size_m ** 2) / 1_000_000.0,
                4,
            )

        boxes = self._build_region_boxes(
            change_mask,
        )

        overlay_path = self._save_overlay(
            change_mask,
            image,
            prefix="change_detection",
            transform=transform,
            crs=crs,
        )

        label = self._format_date_pair(
            metadata.get("date_a"),
            metadata.get("date_b"),
        )

        statistics = {
            "changed_percentage": round(changed_percentage, 2),
            "changed_area_sqkm": changed_area_sqkm,
            "changed_pixels": changed_count,
            "valid_pixels": valid_count,
            "total_pixels": int(diff.size),
            "mean_change_score": self._safe_mean(diff[valid_mask]),
            "max_change_score": self._safe_max(diff[valid_mask]),
        }

        answer = self._build_evidence_summary(
            statistics,
            metadata.get("date_a"),
            metadata.get("date_b"),
        )

        return {
            "answer": answer,
            "confidence": 0.0,
            "execution_status": "completed",
            "visual_evidence": {
                "overlay_type": "change_detection_mask",
                "label": f"Bi-Temporal Change Map ({label})",
                "changed_regions": boxes,
                "change_mask_url": overlay_path,
                "method": source_kind,
            },
            "change_statistics": statistics,
            "parameters_used": {
                "algorithm": "Robust normalized absolute raster difference",
                "threshold": threshold,
                "valid_pixel_rule": "finite values in both observations",
                "reference_observation": "Image A",
                "pixel_size_m": pixel_size_m,
            },
        }

    @staticmethod
    def _build_region_boxes(
        mask: np.ndarray,
        rows: int = 6,
        cols: int = 6,
        min_density: float = 0.08,
        max_boxes: int = 12,
    ) -> List[Dict[str, Any]]:
        """
        Return coarse evidence regions as normalized image coordinates.

        These are evidence regions, not object-detection bounding boxes.
        """
        if mask.ndim != 2:
            raise ValueError("Change mask must be 2-D.")

        height, width = mask.shape
        boxes: List[Dict[str, Any]] = []

        cell_height = max(1, height // rows)
        cell_width = max(1, width // cols)

        for row in range(rows):
            for col in range(cols):
                y0 = row * cell_height
                x0 = col * cell_width
                y1 = (
                    height
                    if row == rows - 1
                    else min(height, (row + 1) * cell_height)
                )
                x1 = (
                    width
                    if col == cols - 1
                    else min(width, (col + 1) * cell_width)
                )

                cell = mask[y0:y1, x0:x1]
                if cell.size == 0:
                    continue

                density = float(np.mean(cell))

                if density >= min_density:
                    boxes.append(
                        {
                            "x": round(x0 / width * 100.0, 2),
                            "y": round(y0 / height * 100.0, 2),
                            "w": round((x1 - x0) / width * 100.0, 2),
                            "h": round((y1 - y0) / height * 100.0, 2),
                            "change_density": round(density, 4),
                            "label": (
                                f"Changed region "
                                f"({density * 100.0:.1f}% of cell)"
                            ),
                            "confidence": None,
                        }
                    )

        boxes.sort(
            key=lambda item: item["change_density"],
            reverse=True,
        )
        return boxes[:max_boxes]

    @staticmethod
    def _build_evidence_summary(
        statistics: Dict[str, Any],
        date_a: Optional[Any],
        date_b: Optional[Any],
    ) -> str:
        changed_percentage = statistics.get("changed_percentage")
        changed_area = statistics.get("changed_area_sqkm")

        date_a_text = str(date_a) if date_a else "Image A"
        date_b_text = str(date_b) if date_b else "Image B"

        if changed_percentage is None:
            return (
                f"Bi-temporal analysis between {date_a_text} and {date_b_text} "
                "completed; no change percentage was returned."
            )

        if changed_area is not None:
            return (
                f"Bi-temporal raster analysis between {date_a_text} and "
                f"{date_b_text} identified pixels above the configured "
                f"change threshold across approximately "
                f"{changed_percentage:.2f}% of valid pixels "
                f"({changed_area:.4f} km²)."
            )

        return (
            f"Bi-temporal raster analysis between {date_a_text} and "
            f"{date_b_text} identified pixels above the configured "
            f"change threshold across approximately "
            f"{changed_percentage:.2f}% of valid pixels."
        )

    # ==================================================================
    # OVERLAY OUTPUT
    # ==================================================================

    @staticmethod
    def _save_overlay(
        mask: np.ndarray,
        image: Dict[str, Any],
        prefix: str,
        transform: Any,
        crs: Any,
    ) -> Optional[str]:
        output_dir = os.getenv("SATQUERY_MASK_DIR")

        if not output_dir:
            return None

        Path(output_dir).mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = int(time.time() * 1000)
        output_path = Path(output_dir) / f"{prefix}_{timestamp}.tif"

        source = (
            image.get("file_path")
            or image.get("local_path")
            or image.get("image_path")
            or image.get("path")
        )

        if rasterio is None or not source or not os.path.isfile(source):
            return None

        if transform is None or crs is None:
            return None

        with rasterio.open(source) as src:
            profile = src.profile.copy()

            profile.update(
                {
                    "driver": "GTiff",
                    "count": 1,
                    "dtype": "uint8",
                    "width": mask.shape[1],
                    "height": mask.shape[0],
                    "transform": transform,
                    "crs": crs,
                    "nodata": 0,
                    "compress": "deflate",
                }
            )

            with rasterio.open(
                output_path,
                "w",
                **profile,
            ) as dst:
                dst.write(
                    mask.astype(np.uint8),
                    1,
                )
                dst.set_band_description(
                    1,
                    "change_mask",
                )

        return str(output_path)

    # ==================================================================
    # SOURCE / METADATA HELPERS
    # ==================================================================

    @staticmethod
    def _resolve_source(image: Dict[str, Any]) -> str:
        for key in (
            "file_path",
            "local_path",
            "image_path",
            "path",
        ):
            value = image.get(key)
            if isinstance(value, str) and value.strip():
                return value

        raise ValueError(
            "Observation contains no local file path."
        )

    @staticmethod
    def _is_raster_file(source: str) -> bool:
        suffix = Path(source).suffix.lower()
        return suffix in {
            ".tif",
            ".tiff",
            ".jp2",
            ".j2k",
            ".img",
            ".vrt",
        }

    @staticmethod
    def _resolve_date(
        image: Dict[str, Any],
        metadata: Dict[str, Any],
        key: str,
    ) -> Optional[str]:
        value = image.get("acquisition_date") or image.get("acquisitionDate")
        if value:
            return str(value)

        fallback = metadata.get(key)
        if fallback:
            return str(fallback)

        return None

    @staticmethod
    def _infer_pixel_size_m(
        transform: Any,
        crs: Any,
    ) -> Optional[float]:
        if transform is None or crs is None:
            return None

        try:
            x = abs(float(transform.a))
            y = abs(float(transform.e))
        except (AttributeError, TypeError, ValueError):
            return None

        if x <= 0 or y <= 0:
            return None

        # CRS in geographic degrees is not directly convertible to metres
        # without considering latitude. In that case, do not invent an area.
        try:
            if getattr(crs, "is_geographic", False):
                return None
        except Exception:
            pass

        return float((x + y) / 2.0)

    @staticmethod
    def _format_date_pair(
        date_a: Optional[Any],
        date_b: Optional[Any],
    ) -> str:
        return (
            f"{date_a or 'Image A'} vs {date_b or 'Image B'}"
        )

    @staticmethod
    def _get_threshold(
        metadata: Dict[str, Any],
    ) -> float:
        value = metadata.get("change_threshold")

        if value is None:
            value = os.getenv(
                "SATQUERY_CHANGE_THRESHOLD",
                "0.25",
            )

        try:
            threshold = float(value)
        except (TypeError, ValueError):
            threshold = 0.25

        if not 0.0 < threshold < 1.0:
            raise ValueError(
                "SATQUERY_CHANGE_THRESHOLD must be between 0 and 1."
            )

        return threshold

    @staticmethod
    def _safe_mean(values: np.ndarray) -> Optional[float]:
        if values.size == 0:
            return None
        return float(np.mean(values))

    @staticmethod
    def _safe_max(values: np.ndarray) -> Optional[float]:
        if values.size == 0:
            return None
        return float(np.max(values))

    # ==================================================================
    # TRAINED MODEL EXTENSION POINT
    # ==================================================================

    def _load_model(self):
        """
        Concrete trained-model loading extension point.

        A checkpoint format must be selected before this can honestly be
        implemented (PyTorch, TorchScript, ONNX, Hugging Face, or service API).
        """
        if self._model is not None:
            return self._model

        if self._load_error:
            raise RuntimeError(self._load_error)

        if not self.model_id:
            self._load_error = (
                "SATQUERY_CHANGE_MODEL_ID is not configured."
            )
            raise RuntimeError(self._load_error)

        raise NotImplementedError(
            "The configured bi-temporal change model "
            f"'{self.model_id}' does not yet have a concrete inference adapter."
        )

    @staticmethod
    def _infer(
        model: Any,
        image_a: Dict[str, Any],
        image_b: Dict[str, Any],
        query: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        if model is None:
            raise RuntimeError(
                "Change-detection inference model is unavailable."
            )

        raise NotImplementedError(
            "Implement the concrete change-detection inference adapter."
        )

    # ==================================================================
    # CONFIDENCE
    # ==================================================================

    @staticmethod
    def _normalize_confidence(
        confidence: Any,
    ) -> float:
        if confidence is None:
            return 0.0

        try:
            value = float(confidence)
        except (TypeError, ValueError):
            return 0.0

        if 1.0 < value <= 100.0:
            value /= 100.0

        return max(
            0.0,
            min(
                1.0,
                value,
            ),
        )
