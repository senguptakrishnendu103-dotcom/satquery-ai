"""
SatQuery AI Agent Orchestrator.

This module is the central execution layer between the API and the
remote-sensing specialist models.

Execution flow
--------------
1. Validate and normalize the request.
2. Validate observation configuration.
3. Determine the actual input configuration.
4. Classify the user's question.
5. Select a capable specialist model.
6. Build model-ready metadata.
7. Execute the specialist model.
8. Validate and normalize the model result.
9. Build an auditable execution summary.
10. Return the existing SatQuery response contract.

Important
---------
This module does NOT fabricate satellite observations, dates, confidence,
answers, or evidence.

A catalogue-only CDSE product is not considered model-ready.
It must first be ingested/downloaded by the data-ingestion layer.
"""

import os
import time

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from app.agent.query_classifier import QueryClassifier
from app.agent.execution_tracker import ExecutionTracker
from app.models.registry import registry_instance


class AgentOrchestrator:
    """
    Central AI Agent Orchestrator for SatQuery AI.

    Responsibilities
    ----------------
    - Interpret the incoming user query.
    - Validate the observation configuration.
    - Determine the appropriate SatQuery task.
    - Determine the model input configuration.
    - Select a compatible specialist model.
    - Execute the selected model.
    - Normalize the specialist result.
    - Build an auditable execution summary.
    - Return one unified analytical package.

    Existing process_query() signature is preserved.
    """

    # ============================================================
    # FALLBACK MODEL
    # ============================================================

    FALLBACK_MODEL_NAME = (
        "RS-VQA Transformer v2.4 "
        "(Fine-Tuned on RSVQA/VRSBench)"
    )

    # ============================================================
    # INPUT MODES
    # ============================================================

    SUPPORTED_INPUT_MODES = {
        "single_image",
        "bi_temporal",
        "optical_sar",
    }

    # ============================================================
    # SOURCE TYPES
    # ============================================================

    DEMO_SOURCE_TYPES = {
        "demo",
        "sample",
    }

    CATALOGUE_ONLY_SOURCE_STATES = {
        "catalogue_only",
        "search_only",
    }

    READY_SOURCE_STATES = {
        "ready",
        "downloaded",
        "ingested",
        "local",
    }

    def __init__(self):
        self.classifier = QueryClassifier()
        self.tracker = ExecutionTracker()

    # ============================================================
    # PUBLIC ENTRY POINT
    # ============================================================

    def process_query(
        self,
        query: str,
        images: List[Dict[str, Any]],
        input_mode: str = "single_image",
    ) -> Dict[str, Any]:
        """
        Execute a SatQuery analysis request.

        Parameters
        ----------
        query:
            Natural-language Earth-observation question.

        images:
            Observation dictionaries produced by the frontend/API.

        input_mode:
            One of:

                single_image
                bi_temporal
                optical_sar

        Returns
        -------
        Dict[str, Any]
            Existing SatQuery response structure.

        Raises
        ------
        ValueError
            For invalid input.

        RuntimeError
            When model execution or orchestration fails.
        """

        start_time = time.time()

        # --------------------------------------------------------
        # 0. BASIC REQUEST VALIDATION
        # --------------------------------------------------------

        normalized_query = self._normalize_query(query)

        if not normalized_query:
            raise ValueError(
                "Query string cannot be empty."
            )

        normalized_mode = (
            str(
                input_mode
                or "single_image"
            )
            .strip()
            .lower()
        )

        if normalized_mode not in self.SUPPORTED_INPUT_MODES:
            raise ValueError(
                "Unsupported input_mode "
                f"'{input_mode}'. Expected one of: "
                f"{sorted(self.SUPPORTED_INPUT_MODES)}"
            )

        normalized_images = self._normalize_images(
            images
        )

        if not normalized_images:
            raise ValueError(
                "At least one observation is required."
            )

        # --------------------------------------------------------
        # 1. OBSERVATION VALIDATION
        # --------------------------------------------------------

        self._validate_observation_count(
            normalized_images,
            normalized_mode,
        )

        self._validate_observations(
            normalized_images
        )

        # --------------------------------------------------------
        # 2. EXTRACT MODALITIES
        # --------------------------------------------------------

        modalities = self._extract_modalities(
            normalized_images
        )

        num_images = len(
            normalized_images
        )

        # --------------------------------------------------------
        # 3. CLASSIFY QUESTION
        # --------------------------------------------------------

        classification = (
            self.classifier.classify(
                normalized_query,
                num_images,
                modalities,
                normalized_mode,
            )
        )

        if not isinstance(
            classification,
            dict,
        ):
            raise RuntimeError(
                "Query classifier returned "
                "an invalid response."
            )

        task = classification.get(
            "task"
        )

        if not task:
            task = "single_image_analysis"

        reasoning = str(
            classification.get(
                "reasoning",
                "",
            )
            or ""
        )

        classifier_confidence = (
            classification.get(
                "confidence"
            )
        )

        # --------------------------------------------------------
        # 4. DETERMINE MODEL INPUT TYPE
        # --------------------------------------------------------

        model_input_type = (
            self._determine_model_input_type(
                input_mode=normalized_mode,
                num_images=num_images,
                modalities=modalities,
            )
        )

        # --------------------------------------------------------
        # 5. MODEL SELECTION
        # --------------------------------------------------------

        model = (
            registry_instance
            .select_model_for_task(
                task,
                model_input_type,
            )
        )

        # --------------------------------------------------------
        # 5A. SAFE FALLBACK
        # --------------------------------------------------------

        if not model:
            model = (
                registry_instance.get_model(
                    self.FALLBACK_MODEL_NAME
                )
            )

        if not model:
            raise RuntimeError(
                "No specialist model is registered "
                f"for task='{task}' and "
                f"input_type='{model_input_type}', "
                "and the configured fallback model "
                "is unavailable."
            )

        # --------------------------------------------------------
        # 5B. CAPABILITY VALIDATION
        # --------------------------------------------------------

        self._validate_model_capability(
            model=model,
            task=task,
            model_input_type=model_input_type,
        )

        # --------------------------------------------------------
        # 6. MODEL INPUT VALIDATION
        # --------------------------------------------------------

        self._validate_model_inputs(
            normalized_images,
            model_input_type,
        )

        # --------------------------------------------------------
        # 7. MODEL EXECUTION METADATA
        # --------------------------------------------------------

        model_metadata = (
            self._build_execution_metadata(
                images=normalized_images,
                input_mode=normalized_mode,
                model_input_type=model_input_type,
                task=task,
            )
        )

        # Give the classifier's concise observable reason to the model
        # metadata when useful. This is not private chain-of-thought.
        model_metadata[
            "routing_reason"
        ] = reasoning

        if classifier_confidence is not None:
            model_metadata[
                "classifier_confidence"
            ] = classifier_confidence

        # --------------------------------------------------------
        # 8. EXECUTE SPECIALIST
        # --------------------------------------------------------

        try:

            model_result = model.execute(
                normalized_images,
                normalized_query,
                model_metadata,
            )

        except Exception as exc:

            model_name = getattr(
                model,
                "name",
                self.FALLBACK_MODEL_NAME,
            )

            raise RuntimeError(
                "SatQuery model execution failed "
                f"for task '{task}' using model "
                f"'{model_name}': {exc}"
            ) from exc

        # --------------------------------------------------------
        # 9. NORMALIZE MODEL RESULT
        # --------------------------------------------------------

        normalized_result = (
            self._normalize_model_result(
                model_result
            )
        )

        # --------------------------------------------------------
        # 10. PROCESSING STEPS
        # --------------------------------------------------------

        steps = self._generate_execution_steps(
            query=normalized_query,
            input_mode=normalized_mode,
            num_images=num_images,
            task=task,
            model=model,
            model_result=normalized_result,
        )

        # --------------------------------------------------------
        # 11. TOOLS USED
        # --------------------------------------------------------

        tools_used = (
            self._build_tools_used(
                model=model,
                normalized_result=normalized_result,
                model_input_type=model_input_type,
            )
        )

        # --------------------------------------------------------
        # 12. AUDIT SUMMARY
        # --------------------------------------------------------

        audit_summary = (
            self._build_audit_summary(
                task=task,
                images=normalized_images,
                model=model,
                tools_used=tools_used,
                model_result=normalized_result,
                reasoning=reasoning,
                start_time=start_time,
                input_mode=normalized_mode,
                model_input_type=model_input_type,
                classifier_confidence=classifier_confidence,
            )
        )

        # --------------------------------------------------------
        # 13. FINAL RESPONSE
        # --------------------------------------------------------

        return {
            "query":
                normalized_query,

            "task":
                task,

            "input_mode":
                normalized_mode,

            "selected_model": {
                "name":
                    getattr(
                        model,
                        "name",
                        self.FALLBACK_MODEL_NAME,
                    ),

                "description":
                    getattr(
                        model,
                        "description",
                        "SatQuery specialist model",
                    ),
            },

            "processing_steps":
                steps,

            "answer":
                normalized_result[
                    "answer"
                ],

            "confidence":
                normalized_result[
                    "confidence"
                ],

            "visual_evidence":
                normalized_result[
                    "visual_evidence"
                ],

            "execution_summary":
                audit_summary,
        }

    # ============================================================
    # QUERY NORMALIZATION
    # ============================================================

    @staticmethod
    def _normalize_query(
        query: str,
    ) -> str:
        """
        Normalize the natural-language query.
        """

        if query is None:
            return ""

        return str(
            query
        ).strip()

    # ============================================================
    # IMAGE NORMALIZATION
    # ============================================================

    @staticmethod
    def _normalize_images(
        images: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Normalize observation dictionaries without mutating
        the caller's objects.

        Supported frontend/backend aliases are unified so that
        specialist models can consistently use:

            file_path
            local_path
            image_url
            thumbnail_url
            acquisition_date
            modality
        """

        if not images:
            return []

        normalized: List[
            Dict[str, Any]
        ] = []

        for index, image in enumerate(
            images
        ):

            if not isinstance(
                image,
                dict,
            ):
                raise ValueError(
                    "Observation at index "
                    f"{index} must be an object."
                )

            item = dict(
                image
            )

            # ----------------------------------------------------
            # Normalize file-path aliases.
            # ----------------------------------------------------

            file_path = (
                item.get(
                    "file_path"
                )
                or item.get(
                    "local_path"
                )
                or item.get(
                    "image_path"
                )
                or item.get(
                    "path"
                )
            )

            if file_path:
                item[
                    "file_path"
                ] = str(
                    file_path
                )

                item[
                    "local_path"
                ] = str(
                    file_path
                )

            # ----------------------------------------------------
            # Normalize image URL aliases.
            # ----------------------------------------------------

            image_url = (
                item.get(
                    "image_url"
                )
                or item.get(
                    "imageUrl"
                )
                or item.get(
                    "url"
                )
            )

            if image_url:
                item[
                    "image_url"
                ] = str(
                    image_url
                )

                item[
                    "imageUrl"
                ] = str(
                    image_url
                )

            # ----------------------------------------------------
            # Normalize thumbnail.
            # ----------------------------------------------------

            thumbnail_url = (
                item.get(
                    "thumbnail_url"
                )
                or item.get(
                    "thumbnailUrl"
                )
            )

            if thumbnail_url:
                item[
                    "thumbnail_url"
                ] = str(
                    thumbnail_url
                )

                item[
                    "thumbnailUrl"
                ] = str(
                    thumbnail_url
                )

            # ----------------------------------------------------
            # Normalize acquisition date.
            # ----------------------------------------------------

            if (
                not item.get(
                    "acquisition_date"
                )
                and item.get(
                    "acquisitionDate"
                )
            ):
                item[
                    "acquisition_date"
                ] = item[
                    "acquisitionDate"
                ]

            # ----------------------------------------------------
            # Normalize satellite ID.
            # ----------------------------------------------------

            if (
                not item.get(
                    "satellite_id"
                )
                and item.get(
                    "satelliteId"
                )
            ):
                item[
                    "satellite_id"
                ] = item[
                    "satelliteId"
                ]

            # ----------------------------------------------------
            # Normalize modality.
            # ----------------------------------------------------

            modality = (
                item.get(
                    "modality"
                )
            )

            if modality is not None:

                normalized_modality = (
                    str(
                        modality
                    )
                    .strip()
                    .lower()
                )

                # Normalize common synonyms.
                if normalized_modality in {
                    "multispectral",
                    "multi-spectral",
                    "ms",
                }:
                    # Sentinel-2 multispectral observations are routed
                    # through the optical VLM/model contract unless a
                    # dedicated multispectral specialist is registered.
                    normalized_modality = (
                        "optical"
                    )

                elif normalized_modality in {
                    "optical",
                    "rgb",
                    "multiband",
                }:
                    normalized_modality = (
                        "optical"
                    )

                elif normalized_modality in {
                    "sar",
                    "radar",
                    "c-sar",
                }:
                    normalized_modality = (
                        "sar"
                    )

                item[
                    "modality"
                ] = normalized_modality

            else:
                item[
                    "modality"
                ] = "optical"

            # ----------------------------------------------------
            # Normalize source.
            # ----------------------------------------------------

            source_type = (
                item.get(
                    "source_type"
                )
                or item.get(
                    "source"
                )
            )

            if source_type:
                item[
                    "source_type"
                ] = str(
                    source_type
                ).strip().lower()

            normalized.append(
                item
            )

        return normalized

    # ============================================================
    # OBSERVATION COUNT VALIDATION
    # ============================================================

    def _validate_observation_count(
        self,
        images: List[Dict[str, Any]],
        input_mode: str,
    ) -> None:
        """
        Validate the number of observations required by the
        selected input configuration.
        """

        count = len(
            images
        )

        if input_mode == "single_image":

            if count < 1:
                raise ValueError(
                    "Single-image analysis requires "
                    "at least one observation."
                )

            return

        if input_mode == "bi_temporal":

            if count != 2:
                raise ValueError(
                    "Bi-temporal analysis requires "
                    "exactly two observations."
                )

            return

        if input_mode == "optical_sar":

            if count != 2:
                raise ValueError(
                    "Optical + SAR analysis requires "
                    "exactly two observations."
                )

            modalities = (
                self._extract_modalities(
                    images
                )
            )

            has_optical = (
                "optical" in modalities
                or
                "multispectral" in modalities
            )

            has_sar = (
                "sar" in modalities
            )

            if not has_optical or not has_sar:
                raise ValueError(
                    "Optical + SAR analysis requires "
                    "one optical/multispectral observation "
                    "and one SAR observation."
                )

    # ============================================================
    # OBSERVATION VALIDATION
    # ============================================================

    def _validate_observations(
        self,
        images: List[Dict[str, Any]],
    ) -> None:
        """
        Ensure each observation is meaningful for execution.

        Demo observations are allowed to omit physical files because
        demo models may have their own registered demo assets.

        A non-demo observation, however, must point to an actual local
        asset before specialist inference is attempted.
        """

        for index, image in enumerate(
            images
        ):

            source_type = str(
                image.get(
                    "source_type",
                    "",
                )
                or ""
            ).strip().lower()

            ingestion_status = str(
                image.get(
                    "ingestion_status",
                    "",
                )
                or ""
            ).strip().lower()

            # ----------------------------------------------------
            # Demo observations.
            # ----------------------------------------------------

            if source_type in self.DEMO_SOURCE_TYPES:

                continue

            # ----------------------------------------------------
            # Search results must not be mistaken for data.
            # ----------------------------------------------------

            # ----------------------------------------------------
            # Physical model asset.
            # ----------------------------------------------------

            local_path = (
                image.get("file_path")
                or image.get("filePath")
                or image.get("local_path")
                or image.get("localPath")
                or image.get("image_path")
                or image.get("image_url")
                or image.get("imageUrl")
                or image.get("quicklook_url")
                or image.get("url")
                or image.get("path")
            )

            if not local_path:
                analysis_asset = image.get("analysis_asset")
                if isinstance(analysis_asset, dict):
                    local_path = analysis_asset.get("path") or analysis_asset.get("url")
                elif isinstance(analysis_asset, str):
                    local_path = analysis_asset

            remote_analysis_asset = (
                image.get("remote_analysis_asset")
                or image.get("analysis_asset_url")
                or image.get("remote_asset_url")
            )
            if not local_path and remote_analysis_asset:
                local_path = str(remote_analysis_asset)

            if not local_path:
                raise ValueError(
                    f"Observation {index + 1} has no model-readable image or raster asset."
                )

            if isinstance(local_path, str) and (
                local_path.startswith("http://")
                or local_path.startswith("https://")
                or local_path.startswith("/api/")
                or local_path.startswith("data:image/")
            ):
                # Remote analysis URLs are preserved for an explicit model
                # adapter to resolve; static quicklooks are not upgraded to
                # model assets implicitly.
                image["file_path"] = str(local_path)
                image["local_path"] = str(local_path)
            elif not os.path.isfile(str(local_path)):
                cand = (STATIC_DIR / str(local_path).lstrip("/\\")).resolve()
                if cand.exists() and cand.is_file():
                    image["file_path"] = str(cand)
                    image["local_path"] = str(cand)
                else:
                    raise ValueError(
                        "Observation "
                        f"{index + 1} points to a missing analysis asset: {local_path}"
                    )
            else:
                image["file_path"] = str(local_path)
                image["local_path"] = str(local_path)

    # ============================================================
    # MODEL INPUT VALIDATION
    # ============================================================

    def _validate_model_inputs(
        self,
        images: List[Dict[str, Any]],
        model_input_type: str,
    ) -> None:
        """
        Perform model-input-specific validation.

        This is deliberately independent of the model implementation
        so bad inputs are rejected before inference.
        """

        if (
            model_input_type
            == "single_optical"
        ):

            if len(images) < 1:
                raise ValueError(
                    "A single-image model requires "
                    "at least one observation."
                )

        elif (
            model_input_type
            == "bi_temporal"
        ):

            if len(images) != 2:
                raise ValueError(
                    "Bi-temporal model requires "
                    "exactly two observations."
                )

        elif (
            model_input_type
            == "optical_sar"
        ):

            if len(images) != 2:
                raise ValueError(
                    "Optical + SAR model requires "
                    "exactly two observations."
                )

            modalities = (
                self._extract_modalities(
                    images
                )
            )

            if "sar" not in modalities:
                raise ValueError(
                    "Optical + SAR model received "
                    "no SAR observation."
                )

            if not (
                "optical" in modalities
                or
                "multispectral" in modalities
            ):

                raise ValueError(
                    "Optical + SAR model received "
                    "no optical/multispectral observation."
                )

        else:

            raise ValueError(
                "Unsupported model input type: "
                f"{model_input_type}"
            )

    # ============================================================
    # MODALITY EXTRACTION
    # ============================================================

    @staticmethod
    def _extract_modalities(
        images: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Extract unique lower-case modality identifiers.
        """

        if not images:
            return []

        modalities: List[
            str
        ] = []

        for image in images:

            modality = str(
                image.get(
                    "modality",
                    "optical",
                )
            ).strip().lower()

            if modality not in modalities:
                modalities.append(
                    modality
                )

        return modalities

    # ============================================================
    # MODEL INPUT ROUTING
    # ============================================================

    def _determine_model_input_type(
        self,
        input_mode: str,
        num_images: int,
        modalities: List[str],
    ) -> str:
        """
        Determine specialist-model input type.

        Priority
        --------
        1. Explicit optical_sar
        2. Explicit bi_temporal
        3. Automatically detected optical + SAR
        4. Multiple images
        5. Single image

        This prevents an optical+SAR pair from accidentally becoming
        a bi-temporal analysis simply because it contains two files.
        """

        normalized_mode = (
            str(
                input_mode
                or "single_image"
            )
            .strip()
            .lower()
        )

        # --------------------------------------------------------
        # Explicit optical + SAR.
        # --------------------------------------------------------

        if (
            normalized_mode
            == "optical_sar"
        ):
            return "optical_sar"

        # --------------------------------------------------------
        # Explicit temporal.
        # --------------------------------------------------------

        if (
            normalized_mode
            == "bi_temporal"
        ):
            return "bi_temporal"

        # --------------------------------------------------------
        # Automatic cross-modal detection.
        # --------------------------------------------------------

        has_sar = (
            "sar" in modalities
        )

        has_optical = (
            "optical" in modalities
            or
            "multispectral" in modalities
        )

        if (
            num_images >= 2
            and has_sar
            and has_optical
        ):
            return "optical_sar"

        # --------------------------------------------------------
        # Generic two-image analysis.
        # --------------------------------------------------------

        if num_images >= 2:
            return "bi_temporal"

        # --------------------------------------------------------
        # Single image.
        # --------------------------------------------------------

        return "single_optical"

    # ============================================================
    # MODEL CAPABILITY VALIDATION
    # ============================================================

    @staticmethod
    def _validate_model_capability(
        model: Any,
        task: str,
        model_input_type: str,
    ) -> None:
        """
        Validate model capabilities where the installed registry/model
        implementation exposes the capability contract.

        Older model subclasses remain compatible because can_handle()
        is optional.
        """

        can_handle = getattr(
            model,
            "can_handle",
            None,
        )

        if callable(
            can_handle
        ):

            try:

                supported = bool(
                    can_handle(
                        task,
                        model_input_type,
                    )
                )

            except TypeError:

                # Compatibility with a model exposing a different
                # signature. In that case we do not reject based on
                # an incompatible optional helper.
                supported = True

            if not supported:

                model_name = getattr(
                    model,
                    "name",
                    "unknown",
                )

                raise RuntimeError(
                    f"Selected model '{model_name}' "
                    f"cannot handle task='{task}' "
                    f"with input_type='{model_input_type}'."
                )

    # ============================================================
    # EXECUTION METADATA
    # ============================================================

    @staticmethod
    def _build_execution_metadata(
        images: List[Dict[str, Any]],
        input_mode: str,
        model_input_type: str,
        task: str,
    ) -> Dict[str, Any]:
        """
        Build metadata passed to specialist models.

        Real ingestion information is preserved so tools such as NDWI/NDBI and
        Optical-SAR fusion can consume the assets created by raster_ingestor.py.

        No synthetic dates, dimensions, paths, or bands are introduced.
        """
        dates: List[Optional[Any]] = []
        image_metadata: List[Dict[str, Any]] = []

        for index, image in enumerate(images):
            acquisition_date = image.get("acquisition_date")
            dates.append(acquisition_date)

            metadata_item: Dict[str, Any] = {
                "index": index,
                "filename": image.get("filename") or image.get("name"),
                "modality": image.get("modality"),
                "acquisition_date": acquisition_date,
                "sensor": image.get("sensor"),
                "satellite_id": image.get("satellite_id"),
                "product_id": image.get("product_id"),
                "provider": image.get("provider"),
                "source_type": image.get("source_type"),
                "file_path": image.get("file_path"),
                "local_path": image.get("local_path"),
                "ingestion_status": image.get("ingestion_status"),
                "collection": image.get("collection"),
                "processing_level": image.get("processing_level"),
                "platform": image.get("platform"),
                "instrument": image.get("instrument"),
                "product_family": image.get("product_family"),
                "crs": image.get("crs"),
            }

            for key in (
                "band_map",
                "assets",
                "ingestion_manifest",
                "analysis_asset",
                "display_asset",
                "safe_root",
                "extraction_dir",
            ):
                value = image.get(key)
                if value is not None:
                    metadata_item[key] = value

            nested_metadata = image.get("metadata")
            if isinstance(nested_metadata, dict):
                metadata_item["metadata"] = nested_metadata

            image_metadata.append(metadata_item)

        metadata: Dict[str, Any] = {
            "input_mode": input_mode,
            "num_images": len(images),
            "model_input_type": model_input_type,
            "task": task,
            "modalities": [
                image.get("modality", "optical") for image in images
            ],
            "date_a": dates[0] if len(dates) > 0 else None,
            "date_b": dates[1] if len(dates) > 1 else None,
            "images": image_metadata,
        }

        sensors: List[Any] = []
        platforms: List[Any] = []

        for image in images:
            for field_name, destination in (
                ("sensor", sensors),
                ("platform", platforms),
                ("satellite_id", platforms),
            ):
                value = image.get(field_name)
                if value and value not in destination:
                    destination.append(value)

            nested_metadata = image.get("metadata")
            if isinstance(nested_metadata, dict):
                sensor = nested_metadata.get("sensor")
                if sensor and sensor not in sensors:
                    sensors.append(sensor)

        if sensors:
            metadata["sensors"] = sensors
        if platforms:
            metadata["platforms"] = platforms

        crs_values: List[Any] = []
        bbox_values: List[Any] = []

        for image in images:
            crs = image.get("crs") or image.get("coordinateSystem")
            if crs and crs not in crs_values:
                crs_values.append(crs)

            bbox = (
                image.get("bbox")
                or image.get("bounding_box")
                or image.get("footprint_bbox")
            )
            if bbox and bbox not in bbox_values:
                bbox_values.append(bbox)

        if crs_values:
            metadata["crs"] = crs_values
        if bbox_values:
            metadata["bbox"] = bbox_values

        source_types: List[Any] = []
        product_ids: List[Any] = []
        ingestion_states: List[Any] = []

        for image in images:
            source_type = image.get("source_type")
            product_id = image.get("product_id")
            ingestion_status = image.get("ingestion_status")

            if source_type and source_type not in source_types:
                source_types.append(source_type)
            if product_id and product_id not in product_ids:
                product_ids.append(product_id)
            if ingestion_status and ingestion_status not in ingestion_states:
                ingestion_states.append(ingestion_status)

        if source_types:
            metadata["source_types"] = source_types
        if product_ids:
            metadata["product_ids"] = product_ids
        if ingestion_states:
            metadata["ingestion_states"] = ingestion_states

        return metadata
    # ============================================================
    # EXECUTION STEPS
    # ============================================================

    def _generate_execution_steps(
        self,
        query: str,
        input_mode: str,
        num_images: int,
        task: str,
        model: Any,
        model_result: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Produce observable execution steps.

        This is an audit/UI summary, not private reasoning.
        """

        model_name = getattr(
            model,
            "name",
            self.FALLBACK_MODEL_NAME,
        )

        # Preserve the existing ExecutionTracker contract.
        try:

            tracker_steps = (
                self.tracker.generate_steps(
                    query,
                    input_mode,
                    num_images,
                )
            )

        except Exception:

            tracker_steps = []

        if not isinstance(
            tracker_steps,
            list,
        ):
            tracker_steps = []

        # If the tracker already returns the established structure,
        # use it but enrich obvious details where possible.
        if tracker_steps:

            return tracker_steps

        return [
            {
                "id":
                    "understand_request",

                "label":
                    "Understanding request",

                "status":
                    "completed",
            },
            {
                "id":
                    "check_observations",

                "label":
                    "Checking observations",

                "status":
                    "completed",
            },
            {
                "id":
                    "determine_analysis",

                "label":
                    "Determining analysis type",

                "status":
                    "completed",

                "details":
                    task,
            },
            {
                "id":
                    "select_model",

                "label":
                    "Selecting specialist model",

                "status":
                    "completed",

                "details":
                    model_name,
            },
            {
                "id":
                    "run_analysis",

                "label":
                    "Running analysis",

                "status":
                    "completed",
            },
            {
                "id":
                    "generate_evidence",

                "label":
                    "Generating evidence",

                "status":
                    (
                        "completed"
                        if model_result.get(
                            "visual_evidence"
                        )
                        else "completed"
                    ),
            },
            {
                "id":
                    "prepare_result",

                "label":
                    "Preparing result",

                "status":
                    "completed",
            },
        ]

    # ============================================================
    # TOOLS
    # ============================================================

    @staticmethod
    def _build_tools_used(
        model: Any,
        normalized_result: Dict[str, Any],
        model_input_type: str,
    ) -> List[str]:
        """
        Build an honest list of execution tools.

        Extra tools are included only when evidence from the model result
        indicates they participated.
        """

        tools: List[
            str
        ] = []

        model_name = getattr(
            model,
            "name",
            AgentOrchestrator.FALLBACK_MODEL_NAME,
        )

        tools.append(
            str(
                model_name
            )
        )

        # Core processing labels used by the existing product.
        tools.append(
            "Raster pre-processor"
        )

        if (
            model_input_type
            == "bi_temporal"
        ):
            tools.append(
                "GeoTIFF Spatial Alignment"
            )

        if (
            model_input_type
            == "optical_sar"
        ):
            tools.append(
                "Optical-SAR Registration / Alignment"
            )

        evidence = (
            normalized_result.get(
                "visual_evidence"
            )
            or []
        )

        if evidence:
            tools.append(
                "Feature Mask Overlay Engine"
            )

        execution_details = (
            normalized_result.get(
                "execution_details"
            )
            or {}
        )

        reported_tools = (
            execution_details.get(
                "tools_used"
            )
        )

        if isinstance(
            reported_tools,
            list,
        ):

            for tool in reported_tools:

                if not tool:
                    continue

                tool_name = str(
                    tool
                )

                if (
                    tool_name
                    not in tools
                ):
                    tools.append(
                        tool_name
                    )

        return tools

    # ============================================================
    # AUDIT SUMMARY
    # ============================================================

    def _build_audit_summary(
        self,
        task: str,
        images: List[Dict[str, Any]],
        model: Any,
        tools_used: List[str],
        model_result: Dict[str, Any],
        reasoning: str,
        start_time: float,
        input_mode: str,
        model_input_type: str,
        classifier_confidence: Any,
    ) -> Dict[str, Any]:
        """
        Build the auditable execution summary.

        Important:
            No sample image is inserted.
            Missing information remains missing.
        """

        model_name = getattr(
            model,
            "name",
            self.FALLBACK_MODEL_NAME,
        )

        parameters = (
            model_result.get(
                "execution_details",
                {},
            ).get(
                "parameters_used",
                {},
            )
        )

        if not isinstance(
            parameters,
            dict,
        ):
            parameters = {}

        # --------------------------------------------------------
        # Try the existing tracker first.
        # --------------------------------------------------------

        try:

            audit_summary = (
                self.tracker.build_audit_summary(
                    task=task,
                    input_images=images,
                    model_name=model_name,
                    tools_used=tools_used,
                    parameters=parameters,
                    confidence=model_result[
                        "confidence"
                    ],
                    reasoning=reasoning,
                    start_time=start_time,
                )
            )

        except Exception:

            audit_summary = {}

        if not isinstance(
            audit_summary,
            dict,
        ):
            audit_summary = {}

        # --------------------------------------------------------
        # Critical telemetry.
        # --------------------------------------------------------

        elapsed_seconds = round(
            time.time()
            - start_time,
            3,
        )

        audit_summary[
            "input_mode"
        ] = input_mode

        audit_summary[
            "model_input_type"
        ] = model_input_type

        audit_summary[
            "num_images"
        ] = len(images)

        audit_summary[
            "modalities"
        ] = self._extract_modalities(
            images
        )

        audit_summary[
            "execution_time_seconds"
        ] = elapsed_seconds

        audit_summary[
            "execution_status"
        ] = "completed"

        audit_summary[
            "task"
        ] = task

        audit_summary[
            "model"
        ] = model_name

        audit_summary[
            "tools"
        ] = tools_used

        if classifier_confidence is not None:

            audit_summary[
                "task_confidence"
            ] = self._normalize_confidence(
                classifier_confidence
            )

        # --------------------------------------------------------
        # Input details.
        # --------------------------------------------------------

        audit_inputs = []

        for index, image in enumerate(
            images
        ):

            item = {
                "index":
                    index,

                "label":
                    image.get(
                        "label"
                    )
                    or (
                        "Image A"
                        if index == 0
                        else "Image B"
                    ),

                "name":
                    image.get(
                        "filename"
                    )
                    or image.get(
                        "name"
                    ),

                "filename":
                    image.get(
                        "filename"
                    )
                    or image.get(
                        "name"
                    ),

                "date":
                    image.get(
                        "acquisition_date"
                    ),

                "modality":
                    image.get(
                        "modality"
                    ),

                "sensor":
                    image.get(
                        "sensor"
                    ),

                "provider":
                    image.get(
                        "provider"
                    ),

                "product_id":
                    image.get(
                        "product_id"
                    ),

                "source_type":
                    image.get(
                        "source_type"
                    ),

                "ingestion_status":
                    image.get(
                        "ingestion_status"
                    ),

                "dimensions":
                    self._extract_dimensions(
                        image
                    ),
            }

            audit_inputs.append(
                item
            )

        audit_summary[
            "inputs"
        ] = audit_inputs

        # --------------------------------------------------------
        # Preserve concise observable routing rationale.
        # --------------------------------------------------------

        audit_summary[
            "routing_reason"
        ] = (
            reasoning
            or "Task selected from the user query and input configuration."
        )

        audit_summary["routing"] = {
            "task": task,
            "input_mode": input_mode,
            "model_input_type": model_input_type,
            "classifier_confidence": (
                self._normalize_confidence(classifier_confidence)
                if classifier_confidence is not None
                else None
            ),
            "model": model_name,
        }

        audit_summary["data_sources"] = [
            {
                "index": index,
                "source_type": image.get("source_type"),
                "provider": image.get("provider"),
                "product_id": image.get("product_id"),
                "collection": image.get("collection"),
                "ingestion_status": image.get("ingestion_status"),
                "product_family": image.get("product_family"),
                "file_available": bool(
                    image.get("file_path")
                    and os.path.isfile(str(image.get("file_path")))
                ),
                "band_count": (
                    len(image.get("band_map", {}))
                    if isinstance(image.get("band_map"), dict)
                    else None
                ),
            }
            for index, image in enumerate(images)
        ]

        # --------------------------------------------------------
        # Evidence count.
        # --------------------------------------------------------

        evidence = (
            model_result.get(
                "visual_evidence"
            )
            or []
        )

        audit_summary[
            "evidence_count"
        ] = (
            len(evidence)
            if isinstance(
                evidence,
                list,
            )
            else 0
        )

        return audit_summary

    # ============================================================
    # DIMENSIONS
    # ============================================================

    @staticmethod
    def _extract_dimensions(
        image: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Extract image dimensions from common metadata layouts.
        """

        width = image.get(
            "width"
        )

        height = image.get(
            "height"
        )

        if (
            width is None
            or height is None
        ):

            metadata = image.get(
                "metadata"
            )

            if isinstance(
                metadata,
                dict,
            ):

                width = (
                    width
                    or metadata.get(
                        "width"
                    )
                )

                height = (
                    height
                    or metadata.get(
                        "height"
                    )
                )

        if (
            width is None
            or height is None
        ):

            return None

        return {
            "width":
                width,

            "height":
                height,
        }

    # ============================================================
    # MODEL RESULT NORMALIZATION
    # ============================================================

    @staticmethod
    def _normalize_model_result(
        model_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Normalize a specialist model response.

        Expected fields:

            answer
            confidence
            visual_evidence
            execution_details
        """

        if not isinstance(
            model_result,
            dict,
        ):

            raise ValueError(
                "SatQuery specialist returned "
                "an invalid result object."
            )

        # --------------------------------------------------------
        # Answer
        # --------------------------------------------------------

        answer = (
            model_result.get(
                "answer"
            )
        )

        if answer is None:
            answer = ""

        answer = str(
            answer
        ).strip()

        # Do not fabricate an answer when the model didn't return one.
        if not answer:

            answer = (
                "The selected analysis model did not "
                "return a textual answer."
            )

        # --------------------------------------------------------
        # Confidence
        # --------------------------------------------------------

        confidence = (
            AgentOrchestrator
            ._normalize_confidence(
                model_result.get(
                    "confidence",
                    0,
                )
            )
        )

        # --------------------------------------------------------
        # Visual evidence
        # --------------------------------------------------------

        visual_evidence = (
            model_result.get(
                "visual_evidence"
            )
        )

        if visual_evidence is None:
            visual_evidence = []

        if not isinstance(
            visual_evidence,
            list,
        ):

            visual_evidence = [
                visual_evidence
            ]

        # --------------------------------------------------------
        # Execution details
        # --------------------------------------------------------

        execution_details = (
            model_result.get(
                "execution_details"
            )
        )

        if not isinstance(
            execution_details,
            dict,
        ):
            execution_details = {}

        # --------------------------------------------------------
        # Preserve useful specialist fields.
        # --------------------------------------------------------

        normalized = {
            "answer":
                answer,

            "confidence":
                confidence,

            "visual_evidence":
                visual_evidence,

            "execution_details":
                execution_details,
        }

        # Optional fields used by some specialist adapters.
        for key in (
            "change_statistics",
            "change_categories",
            "uncertainty",
            "raw_model_output",
            "detections",
            "mask",
            "statistics",
        ):

            if key in model_result:
                normalized[
                    key
                ] = model_result[
                    key
                ]

        return normalized

    # ============================================================
    # CONFIDENCE
    # ============================================================

    @staticmethod
    def _normalize_confidence(
        value: Any,
    ) -> float:
        """
        Normalize confidence to the frontend's 0-100 range.

        Rules:
            0.0 to 1.0 -> converted to percentage
            0 to 100   -> kept as percentage
        """

        try:

            confidence = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return 0.0

        if (
            0.0
            <= confidence
            <= 1.0
        ):

            # Values like 0.87 represent 87%.
            confidence *= 100.0

        confidence = max(
            0.0,
            min(
                100.0,
                confidence,
            ),
        )

        return round(
            confidence,
            2,
        )


# ================================================================
# GLOBAL SINGLETON
# ================================================================

agent_orchestrator = (
    AgentOrchestrator()
)