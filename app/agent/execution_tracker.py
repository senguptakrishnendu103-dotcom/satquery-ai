import time
from typing import Dict, Any, List


class ExecutionTracker:
    """
    Generates observable processing steps and auditable execution summaries
    for SatQuery AI.

    Existing public method signatures and output keys are preserved.
    The tracker is intentionally model-agnostic and keeps the execution
    trace focused on observable workflow events.
    """

    # Aligns with the seven stages already used by the SatQuery UI.
    EXECUTION_STAGES = [
        {
            "step": 1,
            "name": "Understanding request",
            "short_name": "UNDERSTAND",
            "description": "Interpreting the natural-language Earth observation request.",
        },
        {
            "step": 2,
            "name": "Checking observations",
            "short_name": "VALIDATE",
            "description": "Checking observation count, modality and available metadata.",
        },
        {
            "step": 3,
            "name": "Determining analysis type",
            "short_name": "CLASSIFY",
            "description": "Determining the appropriate remote-sensing analysis category.",
        },
        {
            "step": 4,
            "name": "Selecting specialist model",
            "short_name": "ROUTE",
            "description": "Routing the request to the appropriate registered specialist capability.",
        },
        {
            "step": 5,
            "name": "Running analysis",
            "short_name": "ANALYZE",
            "description": "Executing the selected remote-sensing model or analytical tool.",
        },
        {
            "step": 6,
            "name": "Generating evidence",
            "short_name": "EVIDENCE",
            "description": "Preparing spatial evidence, masks, bounding regions or other outputs.",
        },
        {
            "step": 7,
            "name": "Preparing result",
            "short_name": "RESULT",
            "description": "Compiling answer, confidence and auditable execution metadata.",
        },
    ]

    def generate_steps(
        self,
        query: str,
        input_mode: str,
        num_images: int,
    ) -> List[Dict[str, Any]]:
        """
        Generate the observable execution workflow.

        Existing keys are retained:
            step, name, status, detail

        Additional fields support the upgraded Replay/History UI.
        """

        safe_query = self._safe_text(query)
        safe_mode = input_mode or "single_image"

        try:
            safe_num_images = max(0, int(num_images or 0))
        except (TypeError, ValueError):
            safe_num_images = 0

        return [
            {
                "step": stage["step"],
                "name": stage["name"],
                "short_name": stage["short_name"],
                "status": "completed",
                "detail": self._build_step_detail(
                    stage["step"],
                    safe_query,
                    safe_mode,
                    safe_num_images,
                ),
                "description": stage["description"],
            }
            for stage in self.EXECUTION_STAGES
        ]

    def build_audit_summary(
        self,
        task: str,
        input_images: List[Dict[str, Any]],
        model_name: str,
        tools_used: List[str],
        parameters: Dict[str, Any],
        confidence: float,
        reasoning: str,
        start_time: float,
    ) -> Dict[str, Any]:
        """
        Build the auditable execution summary.

        Confidence is safely normalized to 0-100, supporting both:
            0.91 -> 91
            91   -> 91

        This prevents the previous 0-1 vs 0-100 mismatch from producing
        values such as 9100%.
        """

        execution_time_sec = self._calculate_execution_time(start_time)
        formatted_inputs = self._format_inputs(input_images)
        normalized_confidence = self._normalize_confidence(confidence)

        safe_tools = self._normalize_string_list(tools_used)
        safe_parameters = parameters if isinstance(parameters, dict) else {}

        return {
            # Existing frontend/API fields
            "task": task or "unknown",
            "inputs": formatted_inputs,
            "models_used": [
                model_name or "Unknown specialist model"
            ],
            "tools_used": safe_tools,
            "parameters": safe_parameters,
            "confidence_percentage": normalized_confidence,
            "confidence_disclaimer": (
                "AI-assisted remote-sensing analysis. "
                "The confidence value represents system/model confidence "
                "for this execution and is not a guarantee of ground truth. "
                "Results should be reviewed for critical geospatial decisions."
            ),
            # Kept for compatibility. This should contain concise task/
            # classification rationale, not private chain-of-thought.
            "classifier_reasoning": self._safe_text(reasoning),
            "execution_time_seconds": execution_time_sec,
            "audit_timestamp": time.strftime(
                "%Y-%m-%d %H:%M:%S UTC",
                time.gmtime(),
            ),

            # Additional non-breaking audit metadata
            "workflow_version": "SatQuery-Audit-v1",
            "execution_status": "completed",
            "input_count": len(formatted_inputs),
            "tool_count": len(safe_tools),
            "has_parameters": bool(safe_parameters),
            "confidence_scale": "0-100",
            "audit_scope": "Observable execution metadata only",
        }

    def _format_inputs(
        self,
        input_images: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Convert observation dictionaries into a stable audit format.

        Existing fields are preserved:
            label, name, date, modality, dimensions
        """

        if not input_images:
            input_images = [
                {
                    "filename": "sample_optical.png",
                    "width": 800,
                    "height": 600,
                }
            ]

        formatted_inputs = []

        for idx, image in enumerate(input_images):
            if not isinstance(image, dict):
                image = {}

            width = image.get("width", 800)
            height = image.get("height", 600)

            formatted_inputs.append(
                {
                    "label": f"Image {self._image_label(idx)}",
                    "name": image.get(
                        "filename",
                        f"Uploaded_Image_{idx + 1}.png",
                    ),
                    "date": image.get(
                        "acquisition_date",
                        "2024 / Metadata unavailable",
                    ),
                    "modality": image.get(
                        "modality",
                        "Optical Remote Sensing",
                    ),
                    "dimensions": f"{width}x{height} px",

                    # Useful for provenance/report generation later.
                    "sensor": self._extract_sensor(image),
                    "resolution": self._extract_resolution(image),
                    "format": self._extract_format(image),
                }
            )

        return formatted_inputs

    def _build_step_detail(
        self,
        step_number: int,
        query: str,
        input_mode: str,
        num_images: int,
    ) -> str:
        """Generate concise observable execution details."""

        if step_number == 1:
            return f"Received natural-language query: '{query}'"

        if step_number == 2:
            return (
                f"Validated {num_images} remote sensing image(s) "
                f"[Mode: {input_mode}]"
            )

        if step_number == 3:
            return (
                "Task classification completed; "
                "analysis configuration determined"
            )

        if step_number == 4:
            return (
                "Specialist capability selected "
                "from the SatQuery model registry"
            )

        if step_number == 5:
            return (
                "Remote-sensing neural architecture "
                "or analytical tool executed"
            )

        if step_number == 6:
            return (
                "Spatial evidence outputs prepared "
                "for map and result inspection"
            )

        if step_number == 7:
            return (
                "Answer, confidence and audit metadata "
                "compiled into the final result"
            )

        return "Execution stage completed"

    @staticmethod
    def _normalize_confidence(confidence: Any) -> int:
        """
        Normalize confidence to the frontend's 0-100 range.

        Supports:
            0.91
            91
            "0.91"
            "91"
        """

        try:
            value = float(confidence)
        except (TypeError, ValueError):
            return 0

        if 0.0 <= value <= 1.0:
            value *= 100.0

        value = max(0.0, min(100.0, value))
        return int(round(value))

    @staticmethod
    def _calculate_execution_time(start_time: float) -> float:
        """Calculate a safe execution duration in seconds."""

        try:
            elapsed = time.time() - float(start_time)
        except (TypeError, ValueError):
            elapsed = 0.0

        return round(max(0.0, elapsed), 3)

    @staticmethod
    def _extract_sensor(image: Dict[str, Any]) -> Any:
        """Support both flat and nested observation metadata."""

        sensor = image.get("sensor")
        if sensor:
            return sensor

        metadata = image.get("metadata")
        if isinstance(metadata, dict):
            return metadata.get(
                "sensor",
                "Metadata unavailable",
            )

        return "Metadata unavailable"

    @staticmethod
    def _extract_resolution(image: Dict[str, Any]) -> Any:
        """Extract GSD/resolution when available."""

        resolution = image.get("ground_sampling_distance")
        if resolution:
            return resolution

        resolution = image.get("resolution")
        if resolution:
            return resolution

        metadata = image.get("metadata")
        if isinstance(metadata, dict):
            return metadata.get(
                "groundSamplingDistance",
                metadata.get(
                    "resolution",
                    "Metadata unavailable",
                ),
            )

        return "Metadata unavailable"

    @staticmethod
    def _extract_format(image: Dict[str, Any]) -> str:
        """Extract format or infer it from the filename."""

        explicit_format = image.get("format")
        if explicit_format:
            return str(explicit_format).upper()

        filename = str(
            image.get("filename", "")
        ).lower()

        if filename.endswith((".tif", ".tiff", ".geotiff")):
            return "GEOTIFF"

        if filename.endswith(".png"):
            return "PNG"

        if filename.endswith((".jpg", ".jpeg")):
            return "JPEG"

        return "UNKNOWN"

    @staticmethod
    def _safe_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _normalize_string_list(values: Any) -> List[str]:
        if not values:
            return []

        if not isinstance(values, (list, tuple)):
            values = [values]

        return [
            str(value)
            for value in values
            if value is not None
        ]

    @staticmethod
    def _image_label(index: int) -> str:
        if 0 <= index < 26:
            return chr(65 + index)

        return str(index + 1)


# The orchestrator creates its own ExecutionTracker instance, preserving
# the existing project architecture.
