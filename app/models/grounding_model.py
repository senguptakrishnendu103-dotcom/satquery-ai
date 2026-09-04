import os
from typing import Dict, Any, List, Optional

from app.models.base_model import BaseRSModel
from app.utils.image_resolver import ImageResolver



class TextGuidedGroundingModel(BaseRSModel):
    """
    Text-guided spatial grounding adapter.

    The model receives an image and a natural-language query and returns
    spatial evidence such as bounding boxes and/or masks.

    IMPORTANT:
    - No hardcoded detections.
    - No fabricated coordinates.
    - No fabricated confidence scores.
    - No fabricated inference times.
    - Actual model/checkpoint is configured through environment variables.
    """

    MODEL_ENV = "SATQUERY_GROUNDING_MODEL_ID"

    @property
    def name(self) -> str:
        return "RS-Grounder-YOLO-World (Zero-Shot Spatial Grounding)"

    @property
    def description(self) -> str:
        return (
            "Text-guided spatial grounding for remote-sensing imagery. "
            "Localizes user-requested physical targets or land-cover features "
            "using bounding boxes and/or segmentation masks."
        )

    @property
    def supported_input_types(self) -> List[str]:
        return [
            "single_optical",
            "optical_sar",
        ]

    @property
    def supported_tasks(self) -> List[str]:
        return [
            "OBJECT_GROUNDING",
        ]

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
        self.processor = None
        self.model_id = os.getenv(self.MODEL_ENV)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        images: List[Dict[str, Any]],
        query: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute text-guided spatial grounding.

        A configured grounding checkpoint is required for a genuine grounding
        result. The previous ImageResolver heuristic is intentionally not used as
        a hidden substitute because that would make a heuristic look like a model
        prediction.
        """
        start_time = time.perf_counter()

        self._validate_inputs(images, query)

        image = images[0]

        if not self.model_id:
            raise RuntimeError(
                "No grounding model is configured. "
                "Set SATQUERY_GROUNDING_MODEL_ID before running OBJECT_GROUNDING."
            )

        self._ensure_model_loaded()

        if self.model is None:
            raise RuntimeError(
                f"Grounding model '{self.model_id}' could not be initialized."
            )

        grounding_prompt = self._build_grounding_prompt(
            query,
            image=image,
            metadata=metadata,
        )

        grounding_result = self._run_grounding(
            image=image,
            prompt=grounding_prompt,
            metadata=metadata,
        )

        normalized = self._normalize_grounding_result(
            grounding_result,
            image=image,
        )

        answer = self._build_answer(
            query=query,
            result=normalized,
        )

        confidence = self._extract_confidence(normalized)

        inference_time_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        return self.validate_result(
            {
                "answer": answer,
                "confidence": confidence,
                "visual_evidence": {
                    "overlay_type": self._get_overlay_type(normalized),
                    "target_feature": normalized.get(
                        "target_feature",
                        self._extract_target(query),
                    ),
                    "boxes": normalized.get("boxes", []),
                    "masks": normalized.get("masks", []),
                    "coordinate_system": normalized.get(
                        "coordinate_system",
                        "pixel",
                    ),
                },
                "execution_details": {
                    "model_architecture": normalized.get(
                        "model_architecture",
                        self.name,
                    ),
                    "model_id": self.model_id,
                    "parameters_used": normalized.get(
                        "parameters_used",
                        {},
                    ),
                    "inference_time_ms": inference_time_ms,
                    "execution_status": "completed",
                    "input_asset": {
                        "file_path": image.get("file_path"),
                        "provider": image.get("provider"),
                        "product_id": image.get("product_id"),
                        "collection": image.get("collection"),
                        "source_type": image.get("source_type"),
                    },
                },
            }
        )
    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_inputs(
        self,
        images: List[Dict[str, Any]],
        query: str,
    ) -> None:

        if not images:
            raise ValueError(
                "OBJECT_GROUNDING requires at least one image."
            )

        if len(images) > 1:
            raise ValueError(
                "Text-guided grounding currently expects one primary image."
            )

        if not query or not query.strip():
            raise ValueError(
                "A natural-language grounding query is required."
            )

        image = images[0]

        local_path = (
            image.get("file_path")
            or image.get("local_path")
            or image.get("image_path")
            or image.get("path")
        )

        if not local_path:
            raise ValueError(
                "Grounding input does not contain a model-readable local asset."
            )

        if isinstance(local_path, str) and not os.path.isfile(local_path):
            raise FileNotFoundError(
                f"Grounding raster does not exist: {local_path}"
            )

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _ensure_model_loaded(self) -> None:
        """
        Lazily load the configured grounding checkpoint.

        The checkpoint framework/format is intentionally not guessed.
        """
        if self.model is not None:
            return

        if not self.model_id:
            raise RuntimeError(
                "SATQUERY_GROUNDING_MODEL_ID is not configured."
            )

        self._load_model()

    def _load_model(self) -> None:
        """
        Concrete model-loading extension point.

        Implement this once the selected grounding checkpoint/framework is
        known (YOLO-World, Grounding DINO, OWL-ViT, Transformers, etc.).
        """
        raise NotImplementedError(
            "The configured grounding model does not yet have a concrete "
            f"inference adapter: {self.model_id}"
        )

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_grounding_prompt(
        self,
        query: str,
        image: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        image = image or {}
        metadata = metadata or {}

        modality = image.get("modality") or "optical"
        product_family = (
            image.get("product_family")
            or metadata.get("product_family")
            or "unknown"
        )

        return (
            "You are a remote-sensing spatial grounding model. "
            "Locate only the target requested by the user in the supplied "
            "Earth-observation image. Return spatial evidence supported by "
            "the image and do not invent detections.\n\n"
            f"Modality: {modality}\n"
            f"Product family: {product_family}\n"
            f"Target request: {query.strip()}"
        )

    # ------------------------------------------------------------------
    # Actual inference boundary
    # ------------------------------------------------------------------

    def _run_grounding(
        self,
        image: Dict[str, Any],
        prompt: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Concrete inference boundary.

        The configured model must return actual boxes/masks. No heuristic fallback
        is silently substituted.
        """
        if self.model is None:
            raise RuntimeError(
                "Grounding model is not initialized."
            )

        raise NotImplementedError(
            "Implement the model-specific grounding call for "
            f"'{self.model_id}'."
        )
    # ------------------------------------------------------------------
    # Result normalization
    # ------------------------------------------------------------------

    def _normalize_grounding_result(
        self,
        result: Dict[str, Any],
        image: Dict[str, Any],
    ) -> Dict[str, Any]:

        if not isinstance(result, dict):
            raise ValueError(
                "Grounding model returned an invalid result."
            )

        normalized = dict(result)

        boxes = normalized.get("boxes", [])

        if boxes is None:
            boxes = []

        normalized["boxes"] = [
            self._normalize_box(box)
            for box in boxes
            if isinstance(box, dict)
        ]

        masks = normalized.get("masks", [])

        if masks is None:
            masks = []

        normalized["masks"] = masks

        # If the model did not provide confidence, do NOT invent one.
        confidence = normalized.get("confidence")

        if confidence is not None:
            try:
                confidence = float(confidence)

                if confidence > 1:
                    confidence /= 100.0

                confidence = max(
                    0.0,
                    min(1.0, confidence),
                )

                normalized["confidence"] = confidence

            except (TypeError, ValueError):
                normalized["confidence"] = 0.0

        else:
            normalized["confidence"] = 0.0

        normalized.setdefault(
            "model_architecture",
            self.name,
        )

        return normalized

    def _normalize_box(
        self,
        box: Dict[str, Any],
    ) -> Dict[str, Any]:

        normalized = dict(box)

        # Preserve actual coordinates from the model.
        # Do not create fallback coordinates.
        for key in ("x", "y", "w", "h"):
            if key in normalized:
                try:
                    normalized[key] = float(normalized[key])
                except (TypeError, ValueError):
                    normalized[key] = None

        if "confidence" in normalized:
            try:
                confidence = float(normalized["confidence"])

                if confidence > 1:
                    confidence /= 100.0

                normalized["confidence"] = max(
                    0.0,
                    min(1.0, confidence),
                )

            except (TypeError, ValueError):
                normalized["confidence"] = None

        return normalized

    # ------------------------------------------------------------------
    # Answer generation
    # ------------------------------------------------------------------

    def _build_answer(
        self,
        query: str,
        result: Dict[str, Any],
    ) -> str:

        boxes = result.get("boxes", [])
        masks = result.get("masks", [])

        target = result.get(
            "target_feature",
            self._extract_target(query),
        )

        if not boxes and not masks:
            return (
                f"No visually supported instance of '{target}' "
                "was returned by the grounding model."
            )

        detections = len(boxes)

        if detections > 0:
            return (
                f"The grounding model localized {detections} "
                f"instance(s) matching '{target}'. "
                "The detected regions are shown in the spatial evidence overlay."
            )

        return (
            f"The grounding model produced spatial evidence for "
            f"'{target}'. The corresponding mask is shown in the evidence overlay."
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_target(self, query: str) -> str:
        """
        Provides a display label only.

        This does NOT determine where an object is located.
        """

        cleaned = query.strip()

        if len(cleaned) > 120:
            cleaned = cleaned[:117] + "..."

        return cleaned

    def _extract_confidence(
        self,
        result: Dict[str, Any],
    ) -> float:

        confidence = result.get("confidence")

        if confidence is None:
            return 0.0

        try:
            confidence = float(confidence)

            if confidence > 1:
                confidence /= 100.0

            return max(
                0.0,
                min(1.0, confidence),
            )

        except (TypeError, ValueError):
            return 0.0

    def _get_overlay_type(
        self,
        result: Dict[str, Any],
    ) -> str:

        if result.get("masks"):
            return "segmentation_masks"

        if result.get("boxes"):
            return "bounding_boxes"

        return "none"