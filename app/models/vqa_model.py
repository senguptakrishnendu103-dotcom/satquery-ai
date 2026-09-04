import os
import time
from typing import Dict, Any, List, Optional

from app.models.base_model import BaseRSModel
from app.utils.image_resolver import ImageResolver


# ----------------------------------------------------------------------
# Optional Hugging Face dependencies
#
# The application can still start if transformers/torch are not
# installed. The actual model is loaded lazily when execute() is called.
# ----------------------------------------------------------------------

try:
    import torch
except ImportError:
    torch = None

try:
    from transformers import pipeline
except ImportError:
    pipeline = None


class _VisionLanguageModelRuntime:
    """
    Shared lazy-loading runtime for generative vision-language models.

    This class intentionally does not contain a hardcoded model ID.

    Configure the actual model through environment variables:

        SATQUERY_VQA_MODEL_ID
        SATQUERY_CAPTION_MODEL_ID

    This allows the model to be replaced without changing the Python
    source code.

    Example:

        SATQUERY_VQA_MODEL_ID=<your-compatible-RS-VLM>
        SATQUERY_CAPTION_MODEL_ID=<your-compatible-RS-caption-model>

    Public Hugging Face models can generally be used without an API key.
    Gated/private models may require HUGGINGFACE_TOKEN.
    """

    def __init__(
        self,
        model_id: Optional[str],
        task: str = "image-text-to-text",
    ):
        self.model_id = (
            model_id.strip()
            if model_id
            else ""
        )

        self.task = task
        self._pipeline = None
        self._load_error: Optional[str] = None

    # ==================================================================
    # MODEL LOADING
    # ==================================================================

    def load(self):
        """
        Lazily initialize the Hugging Face inference pipeline.

        The model is NOT downloaded when this Python module is imported.
        It is loaded only when an actual analysis request reaches it.
        """

        if self._pipeline is not None:
            return self._pipeline

        if self._load_error is not None:
            raise RuntimeError(
                self._load_error
            )

        if not self.model_id:
            self._load_error = (
                "No vision-language model is configured. "
                "Set the appropriate SATQUERY_*_MODEL_ID "
                "environment variable before running analysis."
            )
            raise RuntimeError(
                self._load_error
            )

        if pipeline is None:
            self._load_error = (
                "The 'transformers' package is not installed. "
                "Install the project's ML dependencies before "
                "running a generative remote-sensing model."
            )
            raise RuntimeError(
                self._load_error
            )

        if torch is None:
            self._load_error = (
                "The 'torch' package is not installed. "
                "Install the project's ML dependencies before "
                "running a generative remote-sensing model."
            )
            raise RuntimeError(
                self._load_error
            )

        try:
            device = (
                0
                if torch.cuda.is_available()
                else -1
            )

            token = os.getenv(
                "HUGGINGFACE_TOKEN"
            )

            pipeline_kwargs = {
                "task": self.task,
                "model": self.model_id,
                "device": device,
            }

            if token:
                pipeline_kwargs[
                    "token"
                ] = token

            self._pipeline = pipeline(
                **pipeline_kwargs
            )

            return self._pipeline

        except Exception as exc:
            self._load_error = (
                f"Unable to load configured vision-language "
                f"model '{self.model_id}': {exc}"
            )

            raise RuntimeError(
                self._load_error
            ) from exc

    # ==================================================================
    # GENERATION
    # ==================================================================

    def generate(
        self,
        image: Any,
        prompt: str,
        max_new_tokens: int = 256,
        temperature: float = 0.2,
    ) -> str:
        """
        Generate a response from the visual-language model.

        The exact pipeline output varies between model families, so the
        response is normalized into plain text.
        """

        model_pipeline = self.load()

        generation_kwargs = {
            "max_new_tokens": max_new_tokens,
        }

        # Some pipeline/model combinations accept temperature while
        # others don't. We only provide it when generation is stochastic.
        if temperature > 0:
            generation_kwargs[
                "temperature"
            ] = temperature

        try:
            result = model_pipeline(
                {
                    "image": image,
                    "text": prompt,
                },
                **generation_kwargs,
            )

        except TypeError:
            # Some Transformers versions/model pipelines use a different
            # multimodal input format. Retry using a simple list format.
            result = model_pipeline(
                [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "image": image,
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
                **generation_kwargs,
            )

        return self._extract_text(
            result
        )

    # ==================================================================
    # OUTPUT NORMALIZATION
    # ==================================================================

    @staticmethod
    def _extract_text(
        result: Any,
    ) -> str:
        """
        Normalize common Hugging Face image-text generation outputs.
        """

        if result is None:
            return ""

        if isinstance(
            result,
            str,
        ):
            return result.strip()

        if isinstance(
            result,
            list,
        ):
            if not result:
                return ""

            # Common pipeline format:
            #
            # [
            #   {
            #       "generated_text": "..."
            #   }
            # ]
            first = result[0]

            if isinstance(
                first,
                str,
            ):
                return first.strip()

            if isinstance(
                first,
                dict,
            ):
                for key in (
                    "generated_text",
                    "text",
                    "answer",
                    "caption",
                ):
                    value = first.get(
                        key
                    )

                    if value:
                        if isinstance(
                            value,
                            str,
                        ):
                            return value.strip()

                        # Some conversational VLMs return a message list.
                        extracted = (
                            _VisionLanguageModelRuntime
                            ._extract_text_from_nested(
                                value
                            )
                        )

                        if extracted:
                            return extracted

        if isinstance(
            result,
            dict,
        ):
            for key in (
                "generated_text",
                "text",
                "answer",
                "caption",
            ):
                value = result.get(
                    key
                )

                if value:
                    return str(
                        value
                    ).strip()

        return str(
            result
        ).strip()

    @staticmethod
    def _extract_text_from_nested(
        value: Any,
    ) -> str:
        if isinstance(
            value,
            str,
        ):
            return value.strip()

        if isinstance(
            value,
            list,
        ):
            for item in reversed(value):
                if isinstance(
                    item,
                    dict,
                ):
                    text = (
                        item.get("text")
                        or item.get("content")
                    )

                    if text:
                        return str(
                            text
                        ).strip()

                elif isinstance(
                    item,
                    str,
                ):
                    return item.strip()

        return ""


# ======================================================================
# REMOTE SENSING VQA
# ======================================================================


class RemoteSensingVQAModel(BaseRSModel):
    """
    Generative Remote-Sensing Visual Question Answering model.

    This class is an adapter around a configurable vision-language model.

    It does NOT contain hardcoded answers.

    The actual model is configured externally using:

        SATQUERY_VQA_MODEL_ID

    Example architecture:

        GeoTIFF / optical image
                 ↓
        image preprocessing
                 ↓
        remote-sensing VLM
                 ↓
        generated answer
    """

    @property
    def name(self) -> str:
        return os.getenv(
            "SATQUERY_VQA_MODEL_NAME",
            "SatQuery Remote-Sensing VQA",
        )

    @property
    def description(self) -> str:
        return (
            "Generative vision-language model adapter for "
            "question answering over remote-sensing imagery."
        )

    @property
    def supported_input_types(self) -> List[str]:
        return [
            "single_optical",
        ]

    @property
    def supported_tasks(self) -> List[str]:
        return [
            "SINGLE_IMAGE_VQA",
        ]

    @property
    def version(self) -> str:
        return os.getenv(
            "SATQUERY_VQA_MODEL_VERSION",
            "configured-runtime",
        )

    @property
    def provider(self) -> str:
        return "huggingface-local"

    @property
    def model_family(self) -> str:
        return "remote_sensing_vlm"

    @property
    def supports_geotiff(self) -> bool:
        return True

    @property
    def supports_multispectral(self) -> bool:
        return True

    def __init__(self):
        self._runtime = _VisionLanguageModelRuntime(
            model_id=os.getenv(
                "SATQUERY_VQA_MODEL_ID"
            ),
            task="image-text-to-text",
        )

    # ==================================================================
    # EXECUTION
    # ==================================================================

    def execute(
        self,
        images: List[Dict[str, Any]],
        query: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute generative VQA over the actual observation.

        A configured VLM is mandatory for a genuine VQA result. The method does
        not silently replace a failed/missing VLM with a heuristic answer.
        """
        start_time = time.perf_counter()

        if not images:
            raise ValueError(
                "RemoteSensingVQAModel requires at least one observation."
            )

        observation = images[0]

        if not self._runtime.model_id:
            raise RuntimeError(
                "No remote-sensing VQA model is configured. "
                "Set SATQUERY_VQA_MODEL_ID before running SINGLE_IMAGE_VQA."
            )

        # Convert the real raster asset into a displayable RGB image before passing
        # it to a generic image-text pipeline. This preserves actual spatial image
        # content while avoiding the incorrect assumption that every HF VLM can
        # directly ingest a GeoTIFF/JP2 path.
        image = self._resolve_model_image(observation)

        prompt = self._build_prompt(
            query,
            observation,
            metadata,
        )

        try:
            answer = self._runtime.generate(
                image=image,
                prompt=prompt,
                max_new_tokens=int(
                    os.getenv(
                        "SATQUERY_VQA_MAX_NEW_TOKENS",
                        "256",
                    )
                ),
                temperature=float(
                    os.getenv(
                        "SATQUERY_VQA_TEMPERATURE",
                        "0.2",
                    )
                ),
            )
        except Exception as exc:
            raise RuntimeError(
                f"Configured remote-sensing VQA model failed: {exc}"
            ) from exc

        answer = str(answer or "").strip()
        if not answer:
            raise RuntimeError(
                "The configured remote-sensing VQA model returned an empty answer."
            )

        inference_time_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        result = {
            "answer": answer,
            # A genuine calibrated model confidence must come from the model.
            # Until that adapter exists, this remains 0.0.
            "confidence": self._get_model_confidence(),
            "visual_evidence": {
                "overlay_type": "vqa_input",
                "label": "VLM Analysis Input",
                "boxes": [],
                "regions": [],
            },
            "execution_details": {
                "model_architecture": self.name,
                "model_id": self._runtime.model_id,
                "provider": self.provider,
                "inference_time_ms": inference_time_ms,
                "input_asset": {
                    "file_path": observation.get("file_path"),
                    "product_id": observation.get("product_id"),
                    "provider": observation.get("provider"),
                    "collection": observation.get("collection"),
                    "source_type": observation.get("source_type"),
                },
                "input_representation": "RGB render from supplied raster asset",
                "parameters_used": {
                    "max_new_tokens": int(
                        os.getenv(
                            "SATQUERY_VQA_MAX_NEW_TOKENS",
                            "256",
                        )
                    ),
                    "temperature": float(
                        os.getenv(
                            "SATQUERY_VQA_TEMPERATURE",
                            "0.2",
                        )
                    ),
                    "input_type": metadata.get(
                        "model_input_type",
                        "single_optical",
                    ),
                },
                "dataset_reference": os.getenv(
                    "SATQUERY_VQA_DATASET_REFERENCE",
                    "Configured remote-sensing training/adaptation data",
                ),
            },
        }

        return self.validate_result(result)
    # ==================================================================
    # PROMPT CONSTRUCTION
    # ==================================================================

    @staticmethod
    def _build_prompt(
        query: str,
        observation: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> str:
        """
        Build a grounded remote-sensing VQA instruction.

        This is a prompt template, not an answer template.
        """

        modality = observation.get(
            "modality",
            "OPTICAL",
        )

        acquisition_date = observation.get(
            "acquisition_date",
            "unknown",
        )

        metadata = observation.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        sensor = (
            observation.get("sensor")
            or metadata.get("sensor")
            or "unknown"
        )

        product_family = (
            observation.get("product_family")
            or metadata.get("product_family")
            or "unknown"
        )

        return (
            "You are SatQuery, a remote-sensing visual "
            "analysis assistant. Answer the user's question "
            "using only information supported by the supplied "
            "Earth-observation image. Do not invent objects, "
            "locations, measurements, dates, sensor properties "
            "or percentages that cannot be established from "
            "the image or supplied metadata. If the image does "
            "not provide enough evidence, say so clearly. "
            "Prefer concise scientific language and distinguish "
            "observation from inference.\n\n"
            f"Observation modality: {modality}\n"
            f"Acquisition date: {acquisition_date}\n"
            f"Sensor: {sensor}\n"
            f"Product family: {product_family}\n"
            f"User question: {query}\n\n"
            "Return a direct answer to the question."
        )

    # ==================================================================
    # IMAGE RESOLUTION
    # ==================================================================

    @staticmethod
    @staticmethod
    def _resolve_model_image(
        observation: Dict[str, Any],
    ) -> Any:
        """
        Resolve a real observation into the PIL image representation expected by
        a generic image-text VLM.

        ImageResolver handles:
          - GeoTIFF/TIFF/JP2
          - PNG/JPEG
          - canonical multispectral analysis stacks
          - real local observation paths

        No synthetic image is produced.
        """
        try:
            return ImageResolver.load_image(observation)
        except Exception as exc:
            raise RuntimeError(
                f"Unable to convert observation raster to a VLM image: {exc}"
            ) from exc

    # Backward-compatible alias for callers that may still reference _resolve_image.
    @staticmethod
    def _resolve_image(
        observation: Dict[str, Any],
    ) -> Any:
        return RemoteSensingVQAModel._resolve_model_image(observation)
    # ==================================================================
    # CONFIDENCE
    # ==================================================================

    @staticmethod
    def _get_model_confidence() -> float:
        """
        Read an optional externally supplied confidence policy.

        We do not fabricate calibrated model confidence.

        Configure:
            SATQUERY_DEFAULT_VQA_CONFIDENCE=0.0

        A real model adapter can later replace this with calibrated
        probability/logit-based confidence.
        """

        try:
            value = float(
                os.getenv(
                    "SATQUERY_DEFAULT_VQA_CONFIDENCE",
                    "0.0",
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            value = 0.0

        return max(
            0.0,
            min(
                1.0,
                value,
            ),
        )


# ======================================================================
# REMOTE SENSING CAPTIONING
# ======================================================================


class RemoteSensingCaptioningModel(BaseRSModel):
    """
    Generative remote-sensing scene captioning model.

    The model ID is externally configured through:

        SATQUERY_CAPTION_MODEL_ID

    No scene description is hardcoded into this class.
    """

    @property
    def name(self) -> str:
        return os.getenv(
            "SATQUERY_CAPTION_MODEL_NAME",
            "SatQuery Remote-Sensing Captioner",
        )

    @property
    def description(self) -> str:
        return (
            "Generative vision-language model adapter for "
            "describing remote-sensing scenes and land-cover context."
        )

    @property
    def supported_input_types(self) -> List[str]:
        return [
            "single_optical",
        ]

    @property
    def supported_tasks(self) -> List[str]:
        return [
            "IMAGE_CAPTIONING",
        ]

    @property
    def version(self) -> str:
        return os.getenv(
            "SATQUERY_CAPTION_MODEL_VERSION",
            "configured-runtime",
        )

    @property
    def provider(self) -> str:
        return "huggingface-local"

    @property
    def model_family(self) -> str:
        return "remote_sensing_captioning_vlm"

    @property
    def supports_geotiff(self) -> bool:
        return True

    @property
    def supports_multispectral(self) -> bool:
        return True

    def __init__(self):
        self._runtime = _VisionLanguageModelRuntime(
            model_id=os.getenv(
                "SATQUERY_CAPTION_MODEL_ID"
            ),
            task="image-text-to-text",
        )

    # ==================================================================
    # EXECUTION
    # ==================================================================

    def execute(
        self,
        images: List[Dict[str, Any]],
        query: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a scene description from the actual observation.

        A configured captioning VLM is mandatory for a genuine captioning result;
        failures are surfaced instead of silently substituting deterministic RGB
        heuristics.
        """
        start_time = time.perf_counter()

        if not images:
            raise ValueError(
                "RemoteSensingCaptioningModel requires at least one observation."
            )

        observation = images[0]

        if not self._runtime.model_id:
            raise RuntimeError(
                "No remote-sensing captioning model is configured. "
                "Set SATQUERY_CAPTION_MODEL_ID before running IMAGE_CAPTIONING."
            )

        image = RemoteSensingVQAModel._resolve_model_image(
            observation
        )

        prompt = self._build_prompt(
            query,
            observation,
        )

        try:
            answer = self._runtime.generate(
                image=image,
                prompt=prompt,
                max_new_tokens=int(
                    os.getenv(
                        "SATQUERY_CAPTION_MAX_NEW_TOKENS",
                        "256",
                    )
                ),
                temperature=float(
                    os.getenv(
                        "SATQUERY_CAPTION_TEMPERATURE",
                        "0.2",
                    )
                ),
            )
        except Exception as exc:
            raise RuntimeError(
                f"Configured remote-sensing captioning model failed: {exc}"
            ) from exc

        answer = str(answer or "").strip()
        if not answer:
            raise RuntimeError(
                "The configured remote-sensing captioning model returned an empty answer."
            )

        inference_time_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        result = {
            "answer": answer,
            "confidence": self._get_model_confidence(),
            "visual_evidence": {
                "overlay_type": "scene_description",
                "label": "VLM Scene Description Input",
                "regions": [],
            },
            "execution_details": {
                "model_architecture": self.name,
                "model_id": self._runtime.model_id,
                "provider": self.provider,
                "inference_time_ms": inference_time_ms,
                "input_asset": {
                    "file_path": observation.get("file_path"),
                    "product_id": observation.get("product_id"),
                    "provider": observation.get("provider"),
                    "collection": observation.get("collection"),
                    "source_type": observation.get("source_type"),
                },
                "input_representation": "RGB render from supplied raster asset",
                "parameters_used": {
                    "max_new_tokens": int(
                        os.getenv(
                            "SATQUERY_CAPTION_MAX_NEW_TOKENS",
                            "256",
                        )
                    ),
                    "temperature": float(
                        os.getenv(
                            "SATQUERY_CAPTION_TEMPERATURE",
                            "0.2",
                        )
                    ),
                },
                "dataset_reference": os.getenv(
                    "SATQUERY_CAPTION_DATASET_REFERENCE",
                    "Configured remote-sensing training/adaptation data",
                ),
            },
        }

        return self.validate_result(result)
    # ==================================================================
    # PROMPT
    # ==================================================================

    @staticmethod
    def _build_prompt(
        query: str,
        observation: Dict[str, Any],
    ) -> str:
        modality = observation.get(
            "modality",
            "OPTICAL",
        )

        return (
            "You are SatQuery, a remote-sensing scene "
            "description assistant. Describe only features "
            "supported by the supplied Earth-observation image. "
            "Do not invent percentages, geographic locations, "
            "sensor properties or objects that are not supported "
            "by the image. Clearly distinguish visible evidence "
            "from interpretation. Use concise scientific language.\n\n"
            f"Observation modality: {modality}\n"
            f"Requested description: {query}\n\n"
            "Provide a useful scene description."
        )

    @staticmethod
    def _get_model_confidence() -> float:
        try:
            value = float(
                os.getenv(
                    "SATQUERY_DEFAULT_CAPTION_CONFIDENCE",
                    "0.0",
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            value = 0.0

        return max(
            0.0,
            min(
                1.0,
                value,
            ),
        )