import os
import time
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

from app.models.base_model import BaseRSModel


# ============================================================
# Utility functions
# ============================================================

def _get_image_source(image: Dict[str, Any]) -> Any:
    """
    Return the actual image/raster object from an observation.

    Supported keys are intentionally compatible with the rest
    of SatQuery AI.
    """

    for key in (
        "image",
        "raster",
        "array",
        "image_path",
        "file_path",
        "path",
    ):
        if image.get(key) is not None:
            return image[key]

    raise ValueError(
        "Observation does not contain an accessible image/raster."
    )


def _normalize_confidence(value: Any) -> float:
    """
    Normalize confidence to [0, 1].

    If no real confidence is available, return 0 rather than
    fabricating one.
    """

    if value is None:
        return 0.0

    try:
        value = float(value)

        if value > 1:
            value /= 100.0

        return max(0.0, min(1.0, value))

    except (TypeError, ValueError):
        return 0.0


def _safe_percentage(mask: np.ndarray) -> float:
    total = mask.size

    if total == 0:
        return 0.0

    return float(mask.sum() / total * 100.0)


# ============================================================
# Optical + SAR Fusion
# ============================================================

class OpticalSARFusionModel(BaseRSModel):
    """
    Optical + SAR multimodal analysis adapter.

    This class is deliberately separated from the actual fusion
    neural network. Once a trained checkpoint is selected, its
    inference implementation can be connected through
    _load_model() and _run_fusion().

    No scientific result is fabricated when a model is unavailable.
    """

    MODEL_ENV = "SATQUERY_OPTSAR_MODEL_ID"

    @property
    def name(self) -> str:
        return "OptSAR-Net Multi-Modal Fusion v1.8"

    @property
    def description(self) -> str:
        return (
            "Fuses optical multispectral imagery with SAR backscatter "
            "for multimodal remote-sensing analysis."
        )

    @property
    def supported_input_types(self) -> List[str]:
        return ["optical_sar"]

    @property
    def supported_tasks(self) -> List[str]:
        return ["OPTICAL_SAR_ANALYSIS"]

    @property
    def supports_geotiff(self) -> bool:
        return True

    @property
    def supports_multispectral(self) -> bool:
        return True

    @property
    def supports_sar(self) -> bool:
        return True

    def __init__(self):
        self.model = None
        self.model_id = os.getenv(self.MODEL_ENV)

    # --------------------------------------------------------
    # Main execution
    # --------------------------------------------------------

    def execute(
        self,
        images: List[Dict[str, Any]],
        query: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:

        start = time.perf_counter()

        self._validate_inputs(images)

        optical_image = self._find_modality(
            images,
            "optical",
        )

        sar_image = self._find_modality(
            images,
            "sar",
        )

        # If an actual trained fusion model is configured,
        # use it.
        if self.model_id:

            self._ensure_model_loaded()

            fusion_result = self._run_fusion(
                optical_image=optical_image,
                sar_image=sar_image,
                query=query,
                metadata=metadata,
            )

        else:
            raise RuntimeError(
                f"No Optical-SAR fusion model configured. "
                f"Set {self.MODEL_ENV} to a compatible trained "
                "multimodal checkpoint."
            )

        elapsed_ms = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        result = self._normalize_result(fusion_result)

        result.setdefault(
            "execution_details",
            {},
        )

        result["execution_details"].update(
            {
                "model_architecture": result[
                    "execution_details"
                ].get(
                    "model_architecture",
                    self.name,
                ),
                "model_id": self.model_id,
                "inference_time_ms": elapsed_ms,
            }
        )

        return result

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    def _validate_inputs(
        self,
        images: List[Dict[str, Any]],
    ) -> None:

        if len(images) < 2:
            raise ValueError(
                "Optical-SAR analysis requires both optical "
                "and SAR observations."
            )

        if not self._find_modality(images, "optical"):
            raise ValueError(
                "Optical observation is required for Optical-SAR analysis."
            )

        if not self._find_modality(images, "sar"):
            raise ValueError(
                "SAR observation is required for Optical-SAR analysis."
            )

    def _find_modality(
        self,
        images: List[Dict[str, Any]],
        modality: str,
    ) -> Optional[Dict[str, Any]]:

        for image in images:

            current = str(
                image.get("modality", "")
            ).lower()

            if modality in current:
                return image

        return None

    # --------------------------------------------------------
    # Model loading
    # --------------------------------------------------------

    def _ensure_model_loaded(self) -> None:

        if self.model is not None:
            return

        self._load_model()

    def _load_model(self) -> None:

        raise NotImplementedError(
            "Connect _load_model() to the selected trained "
            f"Optical-SAR checkpoint: {self.model_id}"
        )

    # --------------------------------------------------------
    # Fusion inference
    # --------------------------------------------------------

    def _run_fusion(
        self,
        optical_image: Dict[str, Any],
        sar_image: Dict[str, Any],
        query: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:

        if self.model is None:
            raise RuntimeError(
                "Optical-SAR fusion model is not initialized."
            )

        raise NotImplementedError(
            "Implement model-specific Optical-SAR inference "
            "in _run_fusion()."
        )

    # --------------------------------------------------------
    # Result normalization
    # --------------------------------------------------------

    def _normalize_result(
        self,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:

        if not isinstance(result, dict):
            raise ValueError(
                "Optical-SAR model returned an invalid result."
            )

        normalized = dict(result)

        normalized["confidence"] = _normalize_confidence(
            normalized.get("confidence")
        )

        normalized.setdefault(
            "answer",
            "Optical-SAR analysis completed.",
        )

        normalized.setdefault(
            "visual_evidence",
            {},
        )

        normalized.setdefault(
            "execution_details",
            {},
        )

        return normalized


# ============================================================
# NDWI Water Detection
# ============================================================

class WaterBodyDetectionTool(BaseRSModel):
    """
    Physics/spectral-index based water extraction tool.

    NDWI = (Green - NIR) / (Green + NIR)

    This is a real analytical operation rather than a hardcoded
    detection result.
    """

    @property
    def name(self) -> str:
        return "Hydro-NDWI Water Segmentation Tool"

    @property
    def description(self) -> str:
        return (
            "Computes NDWI from optical imagery and extracts "
            "water pixels using a configurable threshold."
        )

    @property
    def supported_input_types(self) -> List[str]:
        return [
            "single_optical",
            "optical_sar",
        ]

    @property
    def supported_tasks(self) -> List[str]:
        return ["WATER_DETECTION"]

    @property
    def supports_geotiff(self) -> bool:
        return True

    @property
    def supports_multispectral(self) -> bool:
        return True

    def execute(
        self,
        images: List[Dict[str, Any]],
        query: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:

        start = time.perf_counter()

        if not images:
            raise ValueError(
                "Water detection requires an optical observation."
            )

        image = self._select_optical_image(images)

        green = self._get_band(
            image,
            metadata,
            "green",
        )

        nir = self._get_band(
            image,
            metadata,
            "nir",
        )

        if green is None or nir is None:
            raise ValueError(
                "NDWI requires Green and NIR bands. "
                "The uploaded observation does not expose both bands."
            )

        green, nir = self._align_bands(
            green,
            nir,
        )

        ndwi = self._calculate_ndwi(
            green,
            nir,
        )

        threshold = self._get_threshold(
            metadata,
        )

        water_mask = (
            ndwi >= threshold
        )

        water_percentage = _safe_percentage(
            water_mask
        )

        elapsed_ms = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        answer = (
            f"NDWI water extraction completed. "
            f"{water_percentage:.2f}% of the analysed pixels "
            f"exceed the configured water threshold of "
            f"{threshold:.3f}."
        )

        return {
            "answer": answer,

            # NDWI itself is deterministic, so this is not a
            # neural-network confidence score.
            "confidence": 0.0,

            "visual_evidence": {
                "overlay_type": "water_mask",
                "label": "NDWI Spectral Water Mask",

                "mask": water_mask,

                "statistics": {
                    "water_pixel_percentage": water_percentage,
                    "threshold": threshold,
                    "ndwi_min": float(np.nanmin(ndwi)),
                    "ndwi_max": float(np.nanmax(ndwi)),
                    "ndwi_mean": float(np.nanmean(ndwi)),
                },
            },

            "execution_details": {
                "model_architecture": (
                    "NDWI Spectral Index + "
                    "Configurable Threshold"
                ),
                "inference_time_ms": elapsed_ms,
                "parameters_used": {
                    "ndwi_formula": (
                        "(Green - NIR) / (Green + NIR)"
                    ),
                    "threshold": threshold,
                },
            },
        }

    # --------------------------------------------------------
    # Band handling
    # --------------------------------------------------------

    def _select_optical_image(
        self,
        images: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        for image in images:

            modality = str(
                image.get("modality", "")
            ).lower()

            if (
                "optical" in modality
                or "multispectral" in modality
            ):
                return image

        raise ValueError(
            "An optical or multispectral observation is required "
            "for NDWI analysis."
        )

    def _get_band(
        self,
        image: Dict[str, Any],
        metadata: Dict[str, Any],
        band_name: str,
    ) -> Optional[np.ndarray]:

        # Preferred representation:
        #
        # image["bands"]["green"]
        #
        # image["bands"]["nir"]

        bands = image.get("bands")

        if isinstance(bands, dict):

            value = bands.get(band_name)

            if value is not None:
                return np.asarray(
                    value,
                    dtype=np.float32,
                )

        # Metadata can also contain a band map generated by
        # the GeoTIFF ingestion layer.
        band_map = (
            image.get("band_map")
            or metadata.get("band_map")
        )

        if isinstance(band_map, dict):

            value = band_map.get(band_name)

            if value is not None:
                return np.asarray(
                    value,
                    dtype=np.float32,
                )

        return None

    def _align_bands(
        self,
        green: np.ndarray,
        nir: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:

        if green.shape != nir.shape:
            raise ValueError(
                "Green and NIR bands must have matching dimensions "
                "before NDWI calculation."
            )

        return green, nir

    def _calculate_ndwi(
        self,
        green: np.ndarray,
        nir: np.ndarray,
    ) -> np.ndarray:

        denominator = green + nir

        ndwi = np.divide(
            green - nir,
            denominator,
            out=np.zeros_like(green, dtype=np.float32),
            where=np.abs(denominator) > 1e-8,
        )

        return ndwi

    def _get_threshold(
        self,
        metadata: Dict[str, Any],
    ) -> float:

        threshold = metadata.get(
            "ndwi_threshold",
            os.getenv(
                "SATQUERY_NDWI_THRESHOLD",
                "0.30",
            ),
        )

        try:
            return float(threshold)

        except (TypeError, ValueError):
            return 0.30


# ============================================================
# NDBI Built-Up Detection
# ============================================================

class BuiltUpAreaDetectionTool(BaseRSModel):
    """
    Spectral-index based built-up extraction.

    NDBI = (SWIR - NIR) / (SWIR + NIR)

    This tool performs the actual calculation against supplied
    multispectral data.
    """

    @property
    def name(self) -> str:
        return "Urban-NDBI Built-Up Detector"

    @property
    def description(self) -> str:
        return (
            "Computes NDBI from SWIR and NIR optical bands and "
            "extracts candidate built-up pixels using a configurable "
            "threshold."
        )

    @property
    def supported_input_types(self) -> List[str]:
        return [
            "single_optical",
            "optical_sar",
        ]

    @property
    def supported_tasks(self) -> List[str]:
        return ["BUILT_UP_ANALYSIS"]

    @property
    def supports_geotiff(self) -> bool:
        return True

    @property
    def supports_multispectral(self) -> bool:
        return True

    def execute(
        self,
        images: List[Dict[str, Any]],
        query: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:

        start = time.perf_counter()

        if not images:
            raise ValueError(
                "Built-up analysis requires an optical observation."
            )

        image = self._select_optical_image(images)

        swir = self._get_band(
            image,
            metadata,
            "swir",
        )

        nir = self._get_band(
            image,
            metadata,
            "nir",
        )

        if swir is None or nir is None:
            raise ValueError(
                "NDBI requires SWIR and NIR bands. "
                "The uploaded observation does not expose both bands."
            )

        if swir.shape != nir.shape:
            raise ValueError(
                "SWIR and NIR bands must have matching dimensions "
                "before NDBI calculation."
            )

        ndbi = self._calculate_ndbi(
            swir,
            nir,
        )

        threshold = self._get_threshold(
            metadata,
        )

        builtup_mask = (
            ndbi >= threshold
        )

        builtup_percentage = _safe_percentage(
            builtup_mask
        )

        elapsed_ms = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        answer = (
            f"NDBI built-up extraction completed. "
            f"{builtup_percentage:.2f}% of the analysed pixels "
            f"exceed the configured built-up threshold of "
            f"{threshold:.3f}."
        )

        return {
            "answer": answer,

            # Deterministic spectral index, not a calibrated
            # ML confidence score.
            "confidence": 0.0,

            "visual_evidence": {
                "overlay_type": "builtup_mask",
                "label": "NDBI Built-Up Candidate Mask",

                "mask": builtup_mask,

                "statistics": {
                    "builtup_pixel_percentage": builtup_percentage,
                    "threshold": threshold,
                    "ndbi_min": float(np.nanmin(ndbi)),
                    "ndbi_max": float(np.nanmax(ndbi)),
                    "ndbi_mean": float(np.nanmean(ndbi)),
                },
            },

            "execution_details": {
                "model_architecture": (
                    "NDBI Spectral Index + "
                    "Configurable Threshold"
                ),
                "inference_time_ms": elapsed_ms,
                "parameters_used": {
                    "ndbi_formula": (
                        "(SWIR - NIR) / (SWIR + NIR)"
                    ),
                    "threshold": threshold,
                },
            },
        }

    # --------------------------------------------------------
    # Band handling
    # --------------------------------------------------------

    def _select_optical_image(
        self,
        images: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        for image in images:

            modality = str(
                image.get("modality", "")
            ).lower()

            if (
                "optical" in modality
                or "multispectral" in modality
            ):
                return image

        raise ValueError(
            "An optical or multispectral observation is required "
            "for NDBI analysis."
        )

    def _get_band(
        self,
        image: Dict[str, Any],
        metadata: Dict[str, Any],
        band_name: str,
    ) -> Optional[np.ndarray]:

        bands = image.get("bands")

        if isinstance(bands, dict):

            value = bands.get(band_name)

            if value is not None:
                return np.asarray(
                    value,
                    dtype=np.float32,
                )

        band_map = (
            image.get("band_map")
            or metadata.get("band_map")
        )

        if isinstance(band_map, dict):

            value = band_map.get(band_name)

            if value is not None:
                return np.asarray(
                    value,
                    dtype=np.float32,
                )

        return None

    def _calculate_ndbi(
        self,
        swir: np.ndarray,
        nir: np.ndarray,
    ) -> np.ndarray:

        denominator = swir + nir

        ndbi = np.divide(
            swir - nir,
            denominator,
            out=np.zeros_like(
                swir,
                dtype=np.float32,
            ),
            where=np.abs(denominator) > 1e-8,
        )

        return ndbi

    def _get_threshold(
        self,
        metadata: Dict[str, Any],
    ) -> float:

        threshold = metadata.get(
            "ndbi_threshold",
            os.getenv(
                "SATQUERY_NDBI_THRESHOLD",
                "0.20",
            ),
        )

        try:
            return float(threshold)

        except (TypeError, ValueError):
            return 0.20