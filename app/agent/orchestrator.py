import time
from typing import Dict, Any, List

from app.agent.query_classifier import QueryClassifier
from app.agent.execution_tracker import ExecutionTracker
from app.models.registry import registry_instance


class AgentOrchestrator:
    """
    Central AI Agent Orchestrator for SatQuery AI.

    Responsibilities:
    - Interpret the incoming user query.
    - Determine the appropriate SatQuery analysis task.
    - Determine the input configuration.
    - Select a specialist model from the existing model registry.
    - Execute the selected model.
    - Generate observable execution steps.
    - Build an auditable execution summary.
    - Return one unified analytical package to the API/frontend.

    IMPORTANT:
    The public process_query() interface and the existing response
    structure are intentionally preserved so existing frontend/API
    integrations continue to work.
    """

    # ------------------------------------------------------------------
    # Existing fallback model name.
    # Kept unchanged for compatibility with the current registry.
    # ------------------------------------------------------------------
    FALLBACK_MODEL_NAME = (
        "RS-VQA Transformer v2.4 "
        "(Fine-Tuned on RSVQA/VRSBench)"
    )

    # ------------------------------------------------------------------
    # Supported input modes already used by the frontend.
    # ------------------------------------------------------------------
    SUPPORTED_INPUT_MODES = {
        "single_image",
        "bi_temporal",
        "optical_sar",
    }

    def __init__(self):
        self.classifier = QueryClassifier()
        self.tracker = ExecutionTracker()

    # ==================================================================
    # PUBLIC ENTRY POINT
    # ==================================================================

    def process_query(
        self,
        query: str,
        images: List[Dict[str, Any]],
        input_mode: str = "single_image",
    ) -> Dict[str, Any]:
        """
        Execute a SatQuery analysis request.

        Existing signature intentionally preserved.

        Parameters
        ----------
        query:
            Natural-language Earth observation question.

        images:
            List of observation dictionaries.

        input_mode:
            Existing frontend input mode:
                - single_image
                - bi_temporal
                - optical_sar

        Returns
        -------
        Dict[str, Any]
            Existing SatQuery analytical response structure.
        """

        start_time = time.time()

        # --------------------------------------------------------------
        # 0. Normalize incoming request
        # --------------------------------------------------------------
        normalized_query = self._normalize_query(query)
        normalized_images = self._normalize_images(images)

        num_images = len(normalized_images)

        # Preserve the old fallback behavior for demo/no-image calls.
        effective_num_images = (
            num_images if num_images > 0 else 1
        )

        modalities = self._extract_modalities(
            normalized_images
        )

        # --------------------------------------------------------------
        # 1. Classify question & task
        # --------------------------------------------------------------
        classification = self.classifier.classify(
            normalized_query,
            effective_num_images,
            modalities,
            input_mode,
        )

        task = classification.get(
            "task",
            "single_image_analysis",
        )

        reasoning = classification.get(
            "reasoning",
            "",
        )

        # --------------------------------------------------------------
        # 2. Determine model input configuration
        #
        # IMPORTANT:
        # Explicit input_mode gets priority.
        #
        # This prevents:
        #
        # OPTICAL + SAR
        #      ↓
        # two images
        #      ↓
        # incorrectly becoming BI-TEMPORAL.
        # --------------------------------------------------------------
        model_input_type = self._determine_model_input_type(
            input_mode=input_mode,
            num_images=num_images,
            modalities=modalities,
        )

        # --------------------------------------------------------------
        # 3. Select specialist model from existing registry
        # --------------------------------------------------------------
        model = registry_instance.select_model_for_task(
            task,
            model_input_type,
        )

        # --------------------------------------------------------------
        # 4. Safe fallback
        #
        # Existing fallback behavior is preserved.
        # --------------------------------------------------------------
        if not model:
            model = registry_instance.get_model(
                self.FALLBACK_MODEL_NAME
            )

        # --------------------------------------------------------------
        # 5. Extract execution metadata
        # --------------------------------------------------------------
        meta = self._build_execution_metadata(
            normalized_images,
            input_mode,
            model_input_type,
            task,
        )

        # --------------------------------------------------------------
        # 6. Execute selected specialist model
        # --------------------------------------------------------------
        try:
            model_result = model.execute(
                normalized_images,
                normalized_query,
                meta,
            )

        except Exception as exc:
            # Keep the orchestrator from silently failing.
            #
            # We re-raise with useful context instead of returning
            # malformed analytical results to the frontend.
            raise RuntimeError(
                "SatQuery model execution failed "
                f"for task '{task}' using model "
                f"'{getattr(model, 'name', 'unknown')}'."
            ) from exc

        # --------------------------------------------------------------
        # 7. Normalize model result
        #
        # We don't change the model interface. We only protect the
        # orchestrator against incomplete model responses.
        # --------------------------------------------------------------
        normalized_result = self._normalize_model_result(
            model_result
        )

        # --------------------------------------------------------------
        # 8. Generate observable execution steps
        # --------------------------------------------------------------
        steps = self.tracker.generate_steps(
            normalized_query,
            input_mode,
            effective_num_images,
        )

        # --------------------------------------------------------------
        # 9. Build tools used by the execution
        #
        # Existing tools are preserved.
        # --------------------------------------------------------------
        tools_used = [
            getattr(
                model,
                "name",
                self.FALLBACK_MODEL_NAME,
            ),
            "Raster pre-processor",
            "GeoTIFF Spatial Alignment",
            "Feature Mask Overlay Engine",
        ]

        # --------------------------------------------------------------
        # 10. Build auditable execution summary
        # --------------------------------------------------------------
        audit_summary = self.tracker.build_audit_summary(
            task=task,
            input_images=(
                normalized_images
                if normalized_images
                else [
                    {
                        "filename": "sample_optical.png",
                        "width": 800,
                        "height": 600,
                    }
                ]
            ),
            model_name=getattr(
                model,
                "name",
                self.FALLBACK_MODEL_NAME,
            ),
            tools_used=tools_used,
            parameters=normalized_result[
                "execution_details"
            ].get(
                "parameters_used",
                {},
            ),
            confidence=normalized_result[
                "confidence"
            ],
            reasoning=reasoning,
            start_time=start_time,
        )

        # --------------------------------------------------------------
        # 11. Add non-breaking execution metadata when supported
        #
        # We intentionally do not modify the structure expected by
        # existing frontend components.
        # --------------------------------------------------------------

        elapsed_seconds = round(
            time.time() - start_time,
            3,
        )

        # Add useful telemetry to the audit summary only if it is a
        # dictionary. This preserves compatibility with the existing
        # tracker implementation.
        if isinstance(audit_summary, dict):
            audit_summary.setdefault(
                "input_mode",
                input_mode,
            )

            audit_summary.setdefault(
                "model_input_type",
                model_input_type,
            )

            audit_summary.setdefault(
                "num_images",
                effective_num_images,
            )

            audit_summary.setdefault(
                "modalities",
                modalities,
            )

            audit_summary.setdefault(
                "execution_time_seconds",
                elapsed_seconds,
            )

            audit_summary.setdefault(
                "task_confidence",
                classification.get(
                    "confidence",
                    None,
                ),
            )

        # --------------------------------------------------------------
        # 12. Unified SatQuery response
        #
        # EXISTING RESPONSE KEYS ARE PRESERVED.
        # --------------------------------------------------------------
        return {
            "query": normalized_query,

            "task": task,

            "input_mode": input_mode,

            "selected_model": {
                "name": getattr(
                    model,
                    "name",
                    self.FALLBACK_MODEL_NAME,
                ),
                "description": getattr(
                    model,
                    "description",
                    "SatQuery specialist model",
                ),
            },

            "processing_steps": steps,

            "answer": normalized_result[
                "answer"
            ],

            "confidence": normalized_result[
                "confidence"
            ],

            "visual_evidence": normalized_result[
                "visual_evidence"
            ],

            "execution_summary": audit_summary,
        }

    # ==================================================================
    # QUERY NORMALIZATION
    # ==================================================================

    @staticmethod
    def _normalize_query(
        query: str,
    ) -> str:
        """
        Normalize user query without changing its meaning.

        This prevents empty/whitespace-only strings from propagating
        through the pipeline.
        """

        if query is None:
            return ""

        return str(query).strip()

    # ==================================================================
    # IMAGE NORMALIZATION
    # ==================================================================

    @staticmethod
    def _normalize_images(
        images: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Normalize observation dictionaries while preserving all
        original fields.

        We do not mutate the caller's list/dictionaries.
        """

        if not images:
            return []

        normalized = []

        for image in images:
            if not isinstance(image, dict):
                continue

            image_copy = dict(image)

            # Normalize modality only when present.
            if image_copy.get("modality"):
                image_copy["modality"] = str(
                    image_copy["modality"]
                ).upper()

            normalized.append(
                image_copy
            )

        return normalized

    # ==================================================================
    # MODALITY EXTRACTION
    # ==================================================================

    @staticmethod
    def _extract_modalities(
        images: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Extract normalized modalities from observation metadata.

        Existing classifier receives lower-case modality names, so that
        behavior is preserved.
        """

        if not images:
            return ["optical"]

        modalities = []

        for image in images:
            modality = str(
                image.get(
                    "modality",
                    "optical",
                )
            ).lower()

            if modality not in modalities:
                modalities.append(
                    modality
                )

        return modalities or ["optical"]

    # ==================================================================
    # MODEL INPUT ROUTING
    # ==================================================================

    def _determine_model_input_type(
        self,
        input_mode: str,
        num_images: int,
        modalities: List[str],
    ) -> str:
        """
        Determine the model input configuration.

        Priority:

        1. Explicit optical_sar mode
        2. Explicit bi_temporal mode
        3. Automatically detected optical + SAR
        4. Multiple observations
        5. Single observation

        This fixes the ambiguity in the previous implementation while
        retaining the same model input labels.
        """

        normalized_mode = (
            input_mode or "single_image"
        ).lower()

        # --------------------------------------------------------------
        # Explicit cross-modal mode
        # --------------------------------------------------------------
        if normalized_mode == "optical_sar":
            return "optical_sar"

        # --------------------------------------------------------------
        # Explicit temporal mode
        # --------------------------------------------------------------
        if normalized_mode == "bi_temporal":
            return "bi_temporal"

        # --------------------------------------------------------------
        # Automatic optical + SAR detection
        # --------------------------------------------------------------
        has_sar = "sar" in modalities

        has_optical = (
            "optical" in modalities
            or "multispectral" in modalities
        )

        if (
            num_images >= 2
            and has_sar
            and has_optical
        ):
            return "optical_sar"

        # --------------------------------------------------------------
        # Multiple observations
        # --------------------------------------------------------------
        if num_images >= 2:
            return "bi_temporal"

        # --------------------------------------------------------------
        # Default
        # --------------------------------------------------------------
        return "single_optical"

    # ==================================================================
    # EXECUTION METADATA
    # ==================================================================

    @staticmethod
    def _build_execution_metadata(
        images: List[Dict[str, Any]],
        input_mode: str,
        model_input_type: str,
        task: str,
    ) -> Dict[str, Any]:
        """
        Build metadata passed to the specialist model.

        Existing fields date_a/date_b are preserved.
        Additional metadata gives future models more context.
        """

        date_a = (
            images[0].get(
                "acquisition_date",
                "2024",
            )
            if len(images) > 0
            else "2024"
        )

        date_b = (
            images[1].get(
                "acquisition_date",
                "2026",
            )
            if len(images) > 1
            else "2026"
        )

        metadata = {
            # Existing fields
            "input_mode": input_mode,
            "num_images": (
                len(images)
                if images
                else 1
            ),
            "date_a": date_a,
            "date_b": date_b,

            # New non-breaking fields
            "model_input_type": model_input_type,
            "task": task,
            "modalities": [
                image.get(
                    "modality",
                    "OPTICAL",
                )
                for image in images
            ],
        }

        # --------------------------------------------------------------
        # Preserve useful sensor information when available.
        # --------------------------------------------------------------
        sensors = []

        for image in images:
            sensor = image.get(
                "sensor"
            )

            if sensor and sensor not in sensors:
                sensors.append(sensor)

            nested_metadata = image.get(
                "metadata"
            )

            if isinstance(
                nested_metadata,
                dict,
            ):
                nested_sensor = nested_metadata.get(
                    "sensor"
                )

                if (
                    nested_sensor
                    and nested_sensor
                    not in sensors
                ):
                    sensors.append(
                        nested_sensor
                    )

        if sensors:
            metadata[
                "sensors"
            ] = sensors

        return metadata

    # ==================================================================
    # MODEL RESULT NORMALIZATION
    # ==================================================================

    @staticmethod
    def _normalize_model_result(
        model_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Normalize a specialist model response.

        Existing model response fields are retained.

        This prevents small differences between future specialist
        implementations from breaking ResultPanel.
        """

        if not isinstance(
            model_result,
            dict,
        ):
            raise ValueError(
                "SatQuery specialist returned "
                "an invalid result."
            )

        answer = model_result.get(
            "answer",
            "Analysis completed, but no textual answer was returned.",
        )

        confidence = model_result.get(
            "confidence",
            0,
        )

        # --------------------------------------------------------------
        # Keep confidence within the UI's expected range.
        # --------------------------------------------------------------
        try:
            confidence = float(
                confidence
            )
        except (
            TypeError,
            ValueError,
        ):
            confidence = 0.0

        confidence = max(
            0.0,
            min(
                100.0,
                confidence,
            ),
        )

        # Preserve integer-style confidence where possible.
        if confidence.is_integer():
            confidence = int(
                confidence
            )

        visual_evidence = model_result.get(
            "visual_evidence",
            [],
        )

        if visual_evidence is None:
            visual_evidence = []

        execution_details = model_result.get(
            "execution_details",
            {},
        )

        if not isinstance(
            execution_details,
            dict,
        ):
            execution_details = {}

        return {
            "answer": answer,
            "confidence": confidence,
            "visual_evidence": visual_evidence,
            "execution_details": execution_details,
        }


# ======================================================================
# SINGLETON AGENT ORCHESTRATOR INSTANCE
#
# Existing import behavior is preserved.
# ======================================================================

agent_orchestrator = AgentOrchestrator()