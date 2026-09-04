from typing import Dict, List, Optional, Any, Tuple

from app.models.base_model import BaseRSModel
from app.models.vqa_model import (
    RemoteSensingVQAModel,
    RemoteSensingCaptioningModel,
)
from app.models.grounding_model import (
    TextGuidedGroundingModel,
)
from app.models.change_detection import (
    BiTemporalChangeDetectionModel,
)
from app.models.optical_sar import (
    OpticalSARFusionModel,
    WaterBodyDetectionTool,
    BuiltUpAreaDetectionTool,
)


class ModelRegistry:
    """
    Capability-based model registry for SatQuery AI.

    The registry is responsible for:

    - Registering specialist remote-sensing models/tools.
    - Inspecting model capabilities.
    - Selecting the best available specialist for a task/input pair.
    - Supporting plug-and-play model replacement.
    - Exposing model metadata to the frontend/API.
    - Providing safe fallback behavior.

    IMPORTANT
    ---------
    The registry does NOT generate answers.

    It only answers:

        "Which registered capability should handle this request?"

    Actual visual analysis and generative response generation happen
    inside the selected model / response-generation layers.
    """

    # ------------------------------------------------------------------
    # Existing fallback model name preserved for compatibility with
    # AgentOrchestrator.
    # ------------------------------------------------------------------

    FALLBACK_MODEL_NAME = (
        "RS-VQA Transformer v2.4 "
        "(Fine-Tuned on RSVQA/VRSBench)"
    )

    # ------------------------------------------------------------------
    # Optional capability priorities.
    #
    # These are routing preferences, NOT answer hardcoding.
    #
    # A real fine-tuned specialist can therefore be given a higher
    # priority than a generic fallback without changing the orchestrator.
    # ------------------------------------------------------------------

    DEFAULT_PRIORITIES = {
        "OPTICAL_SAR_ANALYSIS": 100,
        "CHANGE_DETECTION": 100,
        "OBJECT_GROUNDING": 95,
        "WATER_DETECTION": 90,
        "BUILT_UP_ANALYSIS": 90,
        "SINGLE_IMAGE_VQA": 85,
        "IMAGE_CAPTIONING": 85,
        "UNKNOWN": 0,
    }

    def __init__(self):
        self._models: Dict[str, BaseRSModel] = {}

        # Optional per-model priority overrides.
        self._priorities: Dict[str, int] = {}

        self._register_default_models()

    # ==================================================================
    # DEFAULT MODEL REGISTRATION
    # ==================================================================

    def _register_default_models(self) -> None:
        """
        Register the specialist models shipped with SatQuery.

        This list defines available capabilities, not answer logic.

        New models can later be registered without changing the
        orchestrator.
        """

        models = [
            RemoteSensingVQAModel(),
            RemoteSensingCaptioningModel(),
            TextGuidedGroundingModel(),
            BiTemporalChangeDetectionModel(),
            OpticalSARFusionModel(),
            WaterBodyDetectionTool(),
            BuiltUpAreaDetectionTool(),
        ]

        for model in models:
            self.register(model)

    # ==================================================================
    # REGISTRATION
    # ==================================================================

    def register(
        self,
        model: BaseRSModel,
        priority: Optional[int] = None,
    ) -> None:
        """
        Register a remote-sensing model/tool.

        Existing usage remains valid:

            registry.register(model)

        Optional priority can be supplied for routing:

            registry.register(model, priority=95)

        If a model with the same name already exists, it is replaced.
        This makes model upgrades/replacement straightforward.
        """

        if not isinstance(
            model,
            BaseRSModel,
        ):
            raise TypeError(
                "ModelRegistry only accepts instances of "
                "BaseRSModel."
            )

        model_name = str(
            model.name
        ).strip()

        if not model_name:
            raise ValueError(
                "A registered model must have a non-empty name."
            )

        self._models[
            model_name
        ] = model

        if priority is not None:
            self._priorities[
                model_name
            ] = self._normalize_priority(
                priority
            )

    # ==================================================================
    # UNREGISTER
    # ==================================================================

    def unregister(
        self,
        name: str,
    ) -> bool:
        """
        Remove a registered model.

        Returns True if a model was removed.
        """

        if not name:
            return False

        model_name = str(
            name
        ).strip()

        if model_name not in self._models:
            return False

        del self._models[
            model_name
        ]

        self._priorities.pop(
            model_name,
            None,
        )

        return True

    # ==================================================================
    # LIST MODELS
    # ==================================================================

    def list_models(
        self,
    ) -> List[Dict[str, Any]]:
        """
        Return metadata for all registered models.

        Existing fields are preserved:

            name
            description
            supported_input_types
            supported_tasks

        Additional capability metadata is included for the upgraded
        Models UI and audit layer.
        """

        models = []

        for model in self._models.values():
            models.append(
                self._build_model_info(
                    model
                )
            )

        return models

    # ==================================================================
    # GET MODEL
    # ==================================================================

    def get_model(
        self,
        name: str,
    ) -> Optional[BaseRSModel]:
        """
        Retrieve a model by exact name.

        Existing behavior is preserved.
        """

        if not name:
            return None

        return self._models.get(
            str(name).strip()
        )

    # ==================================================================
    # MODEL CAPABILITY CHECK
    # ==================================================================

    def find_capable_models(
        self,
        task: str,
        input_type: str,
    ) -> List[BaseRSModel]:
        """
        Return every registered model capable of handling the requested
        task AND input configuration.

        This is useful for debugging, model inspection and future
        dynamic model selection.
        """

        normalized_task = self._normalize_task(
            task
        )

        normalized_input = self._normalize_input_type(
            input_type
        )

        candidates = []

        for model in self._models.values():

            if self._model_can_handle(
                model,
                normalized_task,
                normalized_input,
            ):
                candidates.append(
                    model
                )

        return candidates

    # ==================================================================
    # CAPABILITY REPORT
    # ==================================================================

    def capability_report(
        self,
        task: str,
        input_type: str,
    ) -> Dict[str, Any]:
        """
        Return an auditable capability report for the requested task/input.

        This is useful to the API, agent audit panel, and debugging without
        executing a model.
        """
        normalized_task = self._normalize_task(task)
        normalized_input = self._normalize_input_type(input_type)

        capable = self.find_capable_models(
            normalized_task,
            normalized_input,
        )

        return {
            "task": normalized_task,
            "input_type": normalized_input,
            "available": bool(capable),
            "candidates": [
                {
                    "name": model.name,
                    "priority": self._get_priority(
                        model,
                        normalized_task,
                    ),
                    "supported_tasks": list(model.supported_tasks),
                    "supported_input_types": list(
                        model.supported_input_types
                    ),
                }
                for model in self._rank_candidates(
                    capable,
                    normalized_task,
                    normalized_input,
                )
            ],
        }

    # ==================================================================
    # PRIMARY MODEL SELECTION
    # ==================================================================

    def select_model_for_task(
        self,
        task: str,
        input_type: str,
    ) -> Optional[BaseRSModel]:
        """
        Select the best registered specialist model for a task/input pair.

        Existing method signature is preserved.

        Selection strategy:

        1. Exact task + exact input capability.
        2. Rank matching specialists by capability/priority.
        3. Fall back to a model supporting the task.
        4. Fall back to the configured general VQA model.

        No natural-language answer is generated here.
        """

        normalized_task = self._normalize_task(
            task
        )

        normalized_input = self._normalize_input_type(
            input_type
        )

        # --------------------------------------------------------------
        # 1. Find exact capability matches.
        # --------------------------------------------------------------

        candidates = self.find_capable_models(
            normalized_task,
            normalized_input,
        )

        if candidates:
            ranked = self._rank_candidates(
                candidates,
                normalized_task,
                normalized_input,
            )

            return ranked[0]

        # --------------------------------------------------------------
        # 2. Do NOT fall back to a task-only model if it cannot consume
        #    the requested input configuration.
        #
        # Returning an incompatible model here only causes a later
        # capability failure in the orchestrator. An honest registry should
        # return None and let the caller report that no compatible specialist
        # is available.
        # --------------------------------------------------------------

        # --------------------------------------------------------------
        # 3. General VQA fallback only when it can consume this input type.
        # --------------------------------------------------------------

        fallback = self.get_model(
            self.FALLBACK_MODEL_NAME
        )

        if fallback and self._model_can_handle(
            fallback,
            "SINGLE_IMAGE_VQA",
            normalized_input,
        ):
            return fallback

        # --------------------------------------------------------------
        # 4. Find any general fallback with the requested input capability.
        # --------------------------------------------------------------

        return self._find_general_fallback(
            input_type=normalized_input
        )

    # ==================================================================
    # BEST CANDIDATE RANKING
    # ==================================================================

    def _rank_candidates(
        self,
        candidates: List[BaseRSModel],
        task: str,
        input_type: str,
    ) -> List[BaseRSModel]:
        """
        Rank candidate models by capability quality.

        Ranking factors:

        - Explicit registry priority.
        - Exact input capability.
        - Exact task capability.
        - Specialized model family.
        - Geospatial capability.

        This is intentionally deterministic so model routing is
        reproducible and auditable.
        """

        def score(
            model: BaseRSModel,
        ) -> Tuple[int, int, int, int, str]:

            model_tasks = [
                str(item).upper()
                for item in model.supported_tasks
            ]

            model_inputs = [
                str(item).lower()
                for item in model.supported_input_types
            ]

            priority = self._get_priority(
                model,
                task,
            )

            exact_task = (
                1
                if task in model_tasks
                else 0
            )

            exact_input = (
                1
                if input_type in model_inputs
                else 0
            )

            geospatial = (
                1
                if model.requires_geospatial_input
                else 0
            )

            # Reverse numeric fields through the final sorted key.
            return (
                priority,
                exact_input,
                exact_task,
                geospatial,
                model.name,
            )

        return sorted(
            candidates,
            key=score,
            reverse=True,
        )

    # ==================================================================
    # MODEL CAPABILITY HELPERS
    # ==================================================================

    @staticmethod
    def _model_can_handle(
        model: BaseRSModel,
        task: str,
        input_type: str,
    ) -> bool:
        """
        Use BaseRSModel.can_handle() when available.

        Falls back to direct capability inspection so older subclasses
        remain compatible.
        """

        normalized_task = str(task).strip().upper()
        normalized_input = str(input_type).strip().lower()

        try:
            return bool(
                model.can_handle(
                    normalized_task,
                    normalized_input,
                )
            )
        except (
            AttributeError,
            TypeError,
        ):
            supported_tasks = [
                str(item).strip().upper()
                for item in model.supported_tasks
            ]

            supported_inputs = [
                str(item).strip().lower()
                for item in model.supported_input_types
            ]

            return (
                normalized_task in supported_tasks
                and normalized_input in supported_inputs
            )

    @staticmethod
    def _model_supports_task(
        model: BaseRSModel,
        task: str,
    ) -> bool:
        """
        Determine whether a model supports a task.
        """

        return task in [
            str(item).upper()
            for item in model.supported_tasks
        ]

    # ==================================================================
    # PRIORITY
    # ==================================================================

    def _get_priority(
        self,
        model: BaseRSModel,
        task: str,
    ) -> int:
        """
        Determine routing priority.

        Explicit model priority takes precedence.
        Otherwise the task's default priority is used.
        """

        if model.name in self._priorities:
            return self._priorities[
                model.name
            ]

        return self.DEFAULT_PRIORITIES.get(
            task,
            50,
        )

    @staticmethod
    def _normalize_priority(
        priority: Any,
    ) -> int:
        try:
            value = int(
                priority
            )
        except (
            TypeError,
            ValueError,
        ):
            value = 50

        return max(
            0,
            min(
                1000,
                value,
            ),
        )

    # ==================================================================
    # MODEL INFORMATION
    # ==================================================================

    def _build_model_info(
        self,
        model: BaseRSModel,
    ) -> Dict[str, Any]:
        """
        Build frontend/API-friendly model metadata.

        Works with both the upgraded BaseRSModel and older subclasses.
        """

        try:
            info = model.get_model_info()

            if isinstance(
                info,
                dict,
            ):
                info = dict(info)
            else:
                info = {}

        except (
            AttributeError,
            TypeError,
        ):
            info = {}

        # Existing fields are guaranteed.
        info.update(
            {
                "name": model.name,
                "description": model.description,
                "supported_input_types": list(
                    model.supported_input_types
                ),
                "supported_tasks": list(
                    model.supported_tasks
                ),
            }
        )

        # Additional registry metadata.
        model_tasks = list(model.supported_tasks)
        priority_task = (
            str(model_tasks[0]).upper()
            if model_tasks
            else "UNKNOWN"
        )

        info["routing_priority"] = self._get_priority(
            model,
            priority_task,
        )

        info["registered"] = True
        info["capabilities"] = {
            "geotiff": bool(
                getattr(model, "supports_geotiff", False)
            ),
            "multispectral": bool(
                getattr(model, "supports_multispectral", False)
            ),
            "sar": bool(
                getattr(model, "supports_sar", False)
            ),
            "geospatial_input": bool(
                getattr(model, "requires_geospatial_input", False)
            ),
        }

        return info

    # ==================================================================
    # NORMALIZATION
    # ==================================================================

    @staticmethod
    def _normalize_task(
        task: Any,
    ) -> str:
        if not task:
            return "UNKNOWN"

        return str(
            task
        ).strip().upper()

    @staticmethod
    def _normalize_input_type(
        input_type: Any,
    ) -> str:
        if not input_type:
            return "single_optical"

        return str(
            input_type
        ).strip().lower()

    # ==================================================================
    # FALLBACK
    # ==================================================================

    def _find_general_fallback(
        self,
        input_type: str = "single_optical",
    ) -> Optional[BaseRSModel]:
        """
        Find a general-purpose fallback that can actually consume the
        requested input type.

        Preference:
            1. SINGLE_IMAGE_VQA
            2. IMAGE_CAPTIONING
            3. Any compatible registered model

        An incompatible model is never returned.
        """

        normalized_input = self._normalize_input_type(input_type)

        for model in self._models.values():
            if self._model_can_handle(
                model,
                "SINGLE_IMAGE_VQA",
                normalized_input,
            ):
                return model

        for model in self._models.values():
            if self._model_can_handle(
                model,
                "IMAGE_CAPTIONING",
                normalized_input,
            ):
                return model

        for model in self._models.values():
            supported_inputs = [
                str(item).lower()
                for item in model.supported_input_types
            ]
            if normalized_input in supported_inputs:
                return model

        return None


# ======================================================================
# SINGLETON INSTANCE
#
# Existing imports throughout the project remain compatible:
#
#     from app.models.registry import registry_instance
# ======================================================================

registry_instance = ModelRegistry()