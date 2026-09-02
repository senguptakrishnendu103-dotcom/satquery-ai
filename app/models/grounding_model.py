import os
from typing import Dict, Any, List, Optional

from app.models.base_model import BaseRSModel


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

        self._validate_inputs(images, query)

        image = images[0]

        # Load the actual grounding model lazily.
        self._ensure_model_loaded()

        # Extract the grounding target from the natural-language query.
        grounding_prompt = self._build_grounding_prompt(query)

        # Run actual grounding inference.
        grounding_result = self._run_grounding(
            image=image,
            prompt=grounding_prompt,
            metadata=metadata,
        )

        # Normalize the result so the rest of SatQuery AI receives
        # a consistent structure.
        normalized = self._normalize_grounding_result(
            grounding_result,
            image=image,
        )

        answer = self._build_answer(
            query=query,
            result=normalized,
        )

        confidence = self._extract_confidence(normalized)

        return {
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
                "highlight_color": "#00FF9D",
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
            },
        }

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

        if not any(
            image.get(key)
            for key in (
                "image",
                "image_path",
                "file_path",
                "path",
                "imageUrl",
                "image_url",
            )
        ):
            raise ValueError(
                "Grounding input does not contain an accessible image."
            )

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _ensure_model_loaded(self) -> None:
        """
        Lazily load the configured grounding model.

        Keeping loading lazy prevents model initialization during
        application startup.
        """

        if self.model is not None:
            return

        if not self.model_id:
            raise RuntimeError(
                f"No grounding model configured. "
                f"Set {self.MODEL_ENV} to a compatible model/checkpoint."
            )

        self._load_model()

    def _load_model(self) -> None:
        """
        Concrete model initialization belongs here.

        This intentionally does not pretend that every YOLO-World/
        transformer checkpoint has the same API.
        """

        try:
            import torch
        except ImportError as exc:
            raise RuntimeError(
                "PyTorch is required for the grounding model."
            ) from exc

        try:
            # The exact loader depends on the selected checkpoint.
            #
            # Example architecture:
            #
            # from ultralytics import YOLO
            # self.model = YOLO(self.model_id)
            #
            # Do not uncomment this blindly unless the configured
            # checkpoint is actually compatible with that API.

            raise NotImplementedError(
                "Connect _load_model() to the selected grounding "
                f"checkpoint: {self.model_id}"
            )

        except Exception:
            raise

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_grounding_prompt(self, query: str) -> str:
        """
        Convert the user's natural-language request into a concise
        grounding prompt.

        The model itself performs the actual visual localization.
        """

        return (
            "Locate the physical feature requested by the user in the "
            "remote-sensing image. Return only visually supported "
            "detections.\n\n"
            f"User query: {query.strip()}"
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
        Run the configured grounding model.

        Expected result format:

        {
            "boxes": [
                {
                    "x": ...,
                    "y": ...,
                    "w": ...,
                    "h": ...,
                    "label": "...",
                    "confidence": ...
                }
            ],

            "masks": [...],

            "target_feature": "...",

            "confidence": ...,

            "coordinate_system": "pixel",

            "parameters_used": {...}
        }

        The exact implementation depends on the selected model.
        """

        if self.model is None:
            raise RuntimeError(
                "Grounding model has not been initialized."
            )

        raise NotImplementedError(
            "Implement model-specific grounding inference in "
            "_run_grounding()."
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