from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseRSModel(ABC):
    """
    Abstract Base Class for all Remote Sensing AI Models and analytical
    tools used by SatQuery AI.

    This class defines the common contract between:
        QueryClassifier
              ↓
        AgentOrchestrator
              ↓
        ModelRegistry
              ↓
        Specialist RS Model
              ↓
        Structured Analysis Result
              ↓
        Response Generator

    IMPORTANT:
    This class does NOT generate hardcoded natural-language answers.

    Specialist models are responsible for producing analysis/evidence.
    A separate response-generation layer can consume that evidence and
    produce dynamic, grounded natural-language responses.
    """

    # ==================================================================
    # CORE MODEL IDENTITY
    # ==================================================================

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Human-readable model name.

        Example:
            "RS-VQA Transformer v2.4"
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Short description of the model's purpose.
        """
        pass

    # ==================================================================
    # MODEL CAPABILITIES
    # ==================================================================

    @property
    @abstractmethod
    def supported_input_types(self) -> List[str]:
        """
        Input configurations supported by this model.

        Existing SatQuery input types include:

            single_optical
            bi_temporal
            optical_sar

        A model may support one or multiple configurations.
        """
        pass

    @property
    @abstractmethod
    def supported_tasks(self) -> List[str]:
        """
        SatQuery task categories supported by this model.

        Existing categories include:

            SINGLE_IMAGE_VQA
            IMAGE_CAPTIONING
            OBJECT_GROUNDING
            CHANGE_DETECTION
            OPTICAL_SAR_ANALYSIS
            WATER_DETECTION
            BUILT_UP_ANALYSIS
        """
        pass

    # ==================================================================
    # OPTIONAL MODEL METADATA
    #
    # These are intentionally NOT abstract properties.
    #
    # This means your existing model subclasses do not break simply
    # because they don't implement the new metadata.
    # ==================================================================

    @property
    def version(self) -> str:
        """
        Model version.

        Subclasses can override this when a real model is integrated.
        """
        return "unknown"

    @property
    def provider(self) -> str:
        """
        Model provider/runtime.

        Examples:
            local
            huggingface
            cloud
            custom
        """
        return "custom"

    @property
    def model_family(self) -> str:
        """
        Broad model family.

        Examples:
            vqa
            captioning
            grounding
            change_detection
            optical_sar
        """
        return "remote_sensing"

    @property
    def requires_geospatial_input(self) -> bool:
        """
        Indicates whether the model expects geospatially meaningful
        imagery/metadata rather than only generic RGB images.
        """
        return True

    @property
    def supports_geotiff(self) -> bool:
        """
        Indicates whether the model can directly consume GeoTIFF/TIFF
        observations.
        """
        return False

    @property
    def supports_multispectral(self) -> bool:
        """
        Indicates whether the model can directly consume multispectral
        observations.
        """
        return False

    @property
    def supports_sar(self) -> bool:
        """
        Indicates whether the model can directly consume SAR data.
        """
        return False

    # ==================================================================
    # MAIN EXECUTION CONTRACT
    # ==================================================================

    @abstractmethod
    def execute(
        self,
        images: List[Dict[str, Any]],
        query: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute the remote-sensing analysis.

        Parameters
        ----------
        images:
            Observation dictionaries supplied by the observation layer.

            Example:

            {
                "filename": "sentinel_2024.tif",
                "modality": "OPTICAL",
                "acquisition_date": "2024-06-15",
                "width": 10980,
                "height": 10980,
                "metadata": {...}
            }

        query:
            Original natural-language user question.

        metadata:
            Execution context generated by the orchestrator.

        Returns
        -------
        Dict[str, Any]

        The result should contain:

            answer
            confidence
            visual_evidence
            execution_details

        Example conceptual structure:

            {
                "answer": "...",
                "confidence": 0.94,

                "visual_evidence": [
                    {
                        "id": "E-01",
                        "label": "Detected region",
                        "geometry": {...},
                        "confidence": 0.94
                    }
                ],

                "execution_details": {
                    "parameters_used": {...},
                    "inference_time_ms": 428,
                    "bands_used": [...]
                }
            }

        The answer may be generated by the specialist model or may be
        a concise model-level result. A separate response-generation
        layer can subsequently create the final conversational answer.
        """
        pass

    # ==================================================================
    # CAPABILITY CHECKING
    # ==================================================================

    def can_handle(
        self,
        task: str,
        input_type: str,
    ) -> bool:
        """
        Determine whether this model can handle a requested task and
        input configuration.

        This provides a clean capability interface for registry.py
        without requiring hardcoded model-specific logic elsewhere.
        """

        if not task or not input_type:
            return False

        supported_tasks = [
            str(item).upper()
            for item in self.supported_tasks
        ]

        supported_inputs = [
            str(item).lower()
            for item in self.supported_input_types
        ]

        return (
            str(task).upper() in supported_tasks
            and str(input_type).lower() in supported_inputs
        )

    # ==================================================================
    # RESULT VALIDATION
    # ==================================================================

    def validate_result(
        self,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate and normalize the minimum specialist-model result
        contract.

        This does NOT alter the actual analysis.

        It simply prevents one specialist model returning malformed
        data from breaking ResultPanel / EarthCanvas / HistoryView.
        """

        if not isinstance(result, dict):
            raise ValueError(
                f"{self.name} returned an invalid result. "
                "Expected a dictionary."
            )

        # --------------------------------------------------------------
        # Answer
        # --------------------------------------------------------------

        answer = result.get(
            "answer",
            "",
        )

        if answer is None:
            answer = ""

        answer = str(answer)

        # --------------------------------------------------------------
        # Confidence
        #
        # Internally we standardize specialist confidence to 0-1.
        # The ExecutionTracker can convert this to 0-100 for UI.
        # --------------------------------------------------------------

        confidence = result.get(
            "confidence",
            0.0,
        )

        try:
            confidence = float(
                confidence
            )
        except (
            TypeError,
            ValueError,
        ):
            confidence = 0.0

        # Support models that accidentally return percentages.
        if 1.0 < confidence <= 100.0:
            confidence /= 100.0

        confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        # --------------------------------------------------------------
        # Visual evidence
        # --------------------------------------------------------------

        visual_evidence = result.get(
            "visual_evidence",
            [],
        )

        if visual_evidence is None:
            visual_evidence = []

        if not isinstance(
            visual_evidence,
            (list, dict),
        ):
            visual_evidence = []

        # --------------------------------------------------------------
        # Execution details
        # --------------------------------------------------------------

        execution_details = result.get(
            "execution_details",
            {},
        )

        if not isinstance(
            execution_details,
            dict,
        ):
            execution_details = {}

        # --------------------------------------------------------------
        # Preserve additional fields returned by real models.
        #
        # This is important for future model integration.
        # --------------------------------------------------------------

        normalized_result = dict(
            result
        )

        normalized_result.update(
            {
                "answer": answer,
                "confidence": confidence,
                "visual_evidence": visual_evidence,
                "execution_details": execution_details,
            }
        )

        return normalized_result

    # ==================================================================
    # MODEL INFORMATION
    # ==================================================================

    def get_model_info(self) -> Dict[str, Any]:
        """
        Return machine-readable model metadata.

        Useful for:
            - Models UI
            - execution audit
            - registry
            - debugging
            - future API responses
        """

        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "provider": self.provider,
            "model_family": self.model_family,

            "supported_tasks": list(
                self.supported_tasks
            ),

            "supported_input_types": list(
                self.supported_input_types
            ),

            "capabilities": {
                "geospatial_input": (
                    self.requires_geospatial_input
                ),
                "geotiff": (
                    self.supports_geotiff
                ),
                "multispectral": (
                    self.supports_multispectral
                ),
                "sar": (
                    self.supports_sar
                ),
            },
        }