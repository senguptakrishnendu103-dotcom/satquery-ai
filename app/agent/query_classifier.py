import re
from typing import Dict, Any, List


class QueryClassifier:
    """
    Query Classification Layer for SatQuery AI.

    Determines the most appropriate remote-sensing task from:
    - natural-language query
    - number of observations
    - observation modalities
    - explicit frontend input mode

    Compatibility:
    - Existing classify() signature is preserved.
    - Existing TASK_CATEGORIES are preserved.
    - Existing task names are preserved.
    - Existing return keys (task, reasoning, confidence) are preserved.
    - Additional metadata is included only as non-breaking fields.

    The classifier is intentionally deterministic and lightweight for now.
    It can later be replaced/augmented by an ML/LLM intent classifier
    without changing the orchestrator contract.
    """

    TASK_CATEGORIES = [
        "SINGLE_IMAGE_VQA",
        "IMAGE_CAPTIONING",
        "OBJECT_GROUNDING",
        "CHANGE_DETECTION",
        "OPTICAL_SAR_ANALYSIS",
        "WATER_DETECTION",
        "BUILT_UP_ANALYSIS",
        "UNKNOWN",
    ]

    # ------------------------------------------------------------------
    # Query vocabulary
    # ------------------------------------------------------------------

    CHANGE_TERMS = (
        "change",
        "changed",
        "changes",
        "difference",
        "differences",
        "compare",
        "comparison",
        "before and after",
        "growth",
        "grown",
        "increase",
        "increased",
        "decrease",
        "decreased",
        "expanded",
        "expansion",
        "loss",
        "gain",
        "newly developed",
        "new development",
        "temporal",
        "over time",
        "between dates",
        "between years",
    )

    WATER_TERMS = (
        "water",
        "water body",
        "water bodies",
        "river",
        "rivers",
        "lake",
        "lakes",
        "reservoir",
        "reservoirs",
        "pond",
        "ponds",
        "stream",
        "streams",
        "canal",
        "canals",
        "flood",
        "flooded",
        "flooding",
        "hydro",
    )

    BUILT_UP_TERMS = (
        "built-up",
        "built up",
        "builtup",
        "building",
        "buildings",
        "urban",
        "urban area",
        "city",
        "cities",
        "infrastructure",
        "residential",
        "settlement",
        "settlements",
        "impervious",
        "construction",
        "developed area",
        "developed areas",
    )

    CAPTION_TERMS = (
        "describe",
        "description",
        "caption",
        "scene description",
        "scene overview",
        "overview",
        "summarize",
        "summary",
        "tell me about",
        "what does this image show",
        "what is shown",
    )

    SAR_TERMS = (
        "sar",
        "radar",
        "backscatter",
        "vv",
        "vh",
        "hh",
        "hv",
    )

    SPECTRAL_INDEX_TERMS = (
        "ndwi",
        "ndbi",
        "spectral index",
        "water index",
        "built-up index",
        "built up index",
    )

    GROUNDING_TERMS = (
        "where is",
        "where are",
        "locate",
        "location of",
        "highlight",
        "mark",
        "bounding box",
        "bounding boxes",
        "draw box",
        "draw boxes",
        "outline",
        "show where",
        "point out",
        "spatially locate",
    )

    VQA_TERMS = (
        "what",
        "which",
        "who",
        "how many",
        "how much",
        "is there",
        "are there",
        "visible",
        "detect",
        "identify",
        "land cover",
        "landcover",
        "class",
        "classification",
        "type",
        "present",
        "seen",
    )

    # ------------------------------------------------------------------
    # Public classifier
    # ------------------------------------------------------------------

    def classify(
        self,
        query: str,
        num_images: int,
        modalities: List[str],
        input_mode: str,
    ) -> Dict[str, Any]:
        """
        Classify a SatQuery request.

        Priority is deliberately ordered around the SatQuery problem:
            1. Optical + SAR cross-modal analysis
            2. Bi-temporal/change analysis
            3. Domain-specific single-image analysis
            4. Grounding
            5. Captioning
            6. General VQA
            7. Safe fallback

        Existing return fields remain:
            task
            reasoning
            confidence

        Additional fields:
            detected_intent
            target
            temporal
            modalities
            observation_count
            input_mode
        """

        q = self._normalize_query(query)
        mode = self._normalize_input_mode(input_mode)
        normalized_modalities = self._normalize_modalities(
            modalities
        )

        try:
            observation_count = max(
                0,
                int(num_images or 0),
            )
        except (TypeError, ValueError):
            observation_count = 0

        has_optical = self._has_modality(
            normalized_modalities,
            "optical",
        )

        has_multispectral = self._has_modality(
            normalized_modalities,
            "multispectral",
        )

        has_sar = self._has_modality(
            normalized_modalities,
            "sar",
        )

        has_optical_family = (
            has_optical
            or has_multispectral
        )

        # ==============================================================
        # 1. CROSS-MODAL OPTICAL + SAR
        # ==============================================================

        explicit_optical_sar = (
            mode == "optical_sar"
            or (
                has_optical_family
                and has_sar
            )
            or (
                self._contains_any(
                    q,
                    (
                        "optical sar",
                        "optical and sar",
                        "optical + sar",
                        "sar and optical",
                        "sar with optical",
                        "cross modal",
                        "cross-modal",
                        "multimodal",
                        "multi-modal",
                        "radar and optical",
                    ),
                )
            )
        )

        if explicit_optical_sar:
            return self._result(
                task="OPTICAL_SAR_ANALYSIS",
                reasoning=(
                    "Detected an Optical + SAR cross-modal "
                    "configuration or an explicit cross-modal "
                    "remote-sensing request."
                ),
                confidence=0.97,
                detected_intent="CROSS_MODAL_ANALYSIS",
                target=self._detect_target(q),
                temporal=False,
                modalities=normalized_modalities,
                observation_count=observation_count,
                input_mode=mode,
            )

        # ==============================================================
        # 2. BI-TEMPORAL / CHANGE DETECTION
        # ==============================================================

        explicit_temporal_mode = (
            mode == "bi_temporal"
        )

        multiple_observations = (
            observation_count >= 2
        )

        change_query = self._contains_any(
            q,
            self.CHANGE_TERMS,
        )

        temporal_language = self._has_temporal_language(
            q
        )

        if (
            explicit_temporal_mode
            or multiple_observations
            or change_query
            or temporal_language
        ):
            temporal_reason = []

            if explicit_temporal_mode:
                temporal_reason.append(
                    "bi-temporal input mode"
                )

            if multiple_observations:
                temporal_reason.append(
                    f"{observation_count} observations supplied"
                )

            if change_query:
                temporal_reason.append(
                    "change/comparison intent detected"
                )

            if temporal_language:
                temporal_reason.append(
                    "temporal language detected"
                )

            return self._result(
                task="CHANGE_DETECTION",
                reasoning=(
                    "Detected "
                    + ", ".join(temporal_reason)
                    + "."
                ),
                confidence=0.96 if (
                    explicit_temporal_mode
                    or (
                        multiple_observations
                        and change_query
                    )
                ) else 0.91,
                detected_intent="BI_TEMPORAL_CHANGE_ANALYSIS",
                target=self._detect_target(q),
                temporal=True,
                modalities=normalized_modalities,
                observation_count=observation_count,
                input_mode=mode,
            )

        # ==============================================================
        # 3. EXPLICIT SPECTRAL-INDEX REQUESTS
        # ==============================================================
        #
        # Explicit NDWI/NDBI requests should route directly to their
        # deterministic spectral tools, regardless of whether the query also
        # contains generic words such as "what" or "compare".
        #

        if self._contains_any(q, ("ndwi", "water index")):
            if not has_optical_family:
                return self._result(
                    task="WATER_DETECTION",
                    reasoning=(
                        "Detected an explicit NDWI/water-index request; "
                        "an optical or multispectral observation is required."
                    ),
                    confidence=0.98,
                    detected_intent="NDWI_WATER_ANALYSIS",
                    target="water bodies",
                    temporal=False,
                    modalities=normalized_modalities,
                    observation_count=observation_count,
                    input_mode=mode,
                )

            return self._result(
                task="WATER_DETECTION",
                reasoning="Detected an explicit NDWI/water-index request.",
                confidence=0.99,
                detected_intent="NDWI_WATER_ANALYSIS",
                target="water bodies",
                temporal=False,
                modalities=normalized_modalities,
                observation_count=observation_count,
                input_mode=mode,
            )

        if self._contains_any(q, ("ndbi", "built-up index", "built up index")):
            return self._result(
                task="BUILT_UP_ANALYSIS",
                reasoning="Detected an explicit NDBI/built-up-index request.",
                confidence=0.99,
                detected_intent="NDBI_BUILT_UP_ANALYSIS",
                target="built-up / urban regions",
                temporal=False,
                modalities=normalized_modalities,
                observation_count=observation_count,
                input_mode=mode,
            )

        # ==============================================================
        # 4. WATER DETECTION
        #
        # Water is checked before generic grounding/VQA so:
        #
        # "Highlight water bodies"
        #
        # routes to WATER_DETECTION rather than generic grounding.
        # ==============================================================

        water_target = self._contains_any(
            q,
            self.WATER_TERMS,
        )

        water_spatial_intent = (
            self._contains_any(
                q,
                self.GROUNDING_TERMS,
            )
            or self._contains_any(
                q,
                (
                    "detect",
                    "identify",
                    "find",
                    "extract",
                    "map",
                    "delineate",
                    "area",
                    "extent",
                ),
            )
        )

        if water_target and water_spatial_intent:
            return self._result(
                task="WATER_DETECTION",
                reasoning=(
                    "Detected a water-related remote-sensing "
                    "target with detection, extraction or "
                    "spatial localization intent."
                ),
                confidence=0.95,
                detected_intent="WATER_BODY_DETECTION",
                target="water bodies",
                temporal=False,
                modalities=normalized_modalities,
                observation_count=observation_count,
                input_mode=mode,
            )

        # ==============================================================
        # 5. BUILT-UP / URBAN ANALYSIS
        # ==============================================================

        builtup_target = self._contains_any(
            q,
            self.BUILT_UP_TERMS,
        )

        builtup_spatial_intent = (
            self._contains_any(
                q,
                self.GROUNDING_TERMS,
            )
            or self._contains_any(
                q,
                (
                    "detect",
                    "identify",
                    "find",
                    "extract",
                    "map",
                    "delineate",
                    "area",
                    "extent",
                ),
            )
        )

        if (
            builtup_target
            and builtup_spatial_intent
        ):
            return self._result(
                task="BUILT_UP_ANALYSIS",
                reasoning=(
                    "Detected a built-up, urban or "
                    "infrastructure extraction request."
                ),
                confidence=0.94,
                detected_intent="BUILT_UP_ANALYSIS",
                target="built-up / urban regions",
                temporal=False,
                modalities=normalized_modalities,
                observation_count=observation_count,
                input_mode=mode,
            )

        # ==============================================================
        # 6. OBJECT GROUNDING
        # ==============================================================

        if self._contains_any(
            q,
            self.GROUNDING_TERMS,
        ):
            return self._result(
                task="OBJECT_GROUNDING",
                reasoning=(
                    "Detected a spatial localization request "
                    "for an object, feature or region."
                ),
                confidence=0.93,
                detected_intent="OBJECT_GROUNDING",
                target=self._detect_target(q),
                temporal=False,
                modalities=normalized_modalities,
                observation_count=observation_count,
                input_mode=mode,
            )

        # ==============================================================
        # 7. IMAGE CAPTIONING / SCENE DESCRIPTION
        # ==============================================================

        if self._contains_any(
            q,
            self.CAPTION_TERMS,
        ):
            return self._result(
                task="IMAGE_CAPTIONING",
                reasoning=(
                    "Detected scene description, captioning "
                    "or observation overview intent."
                ),
                confidence=0.93,
                detected_intent="SCENE_DESCRIPTION",
                target="scene",
                temporal=False,
                modalities=normalized_modalities,
                observation_count=observation_count,
                input_mode=mode,
            )

        # ==============================================================
        # 8. GENERAL SINGLE-IMAGE VQA
        # ==============================================================

        if self._contains_any(
            q,
            self.VQA_TERMS,
        ):
            return self._result(
                task="SINGLE_IMAGE_VQA",
                reasoning=(
                    "Detected a visual question about the "
                    "contents or properties of a remote-sensing scene."
                ),
                confidence=0.90,
                detected_intent="SINGLE_IMAGE_VQA",
                target=self._detect_target(q),
                temporal=False,
                modalities=normalized_modalities,
                observation_count=observation_count,
                input_mode=mode,
            )

        # ==============================================================
        # 9. SAFE DEFAULT
        # ==============================================================

        return self._result(
            task="SINGLE_IMAGE_VQA",
            reasoning=(
                "No specialized intent was confidently detected; "
                "defaulted to Remote Sensing VQA for a general "
                "natural-language observation query."
            ),
            confidence=0.75,
            detected_intent="GENERAL_REMOTE_SENSING_QUERY",
            target=None,
            temporal=False,
            modalities=normalized_modalities,
            observation_count=observation_count,
            input_mode=mode,
        )

    # ==================================================================
    # RESULT BUILDER
    # ==================================================================

    @staticmethod
    def _result(
        task: str,
        reasoning: str,
        confidence: float,
        detected_intent: str,
        target: Any,
        temporal: bool,
        modalities: List[str],
        observation_count: int,
        input_mode: str,
    ) -> Dict[str, Any]:
        """
        Build a consistent classifier response.

        The original three keys are retained exactly.
        """

        return {
            # Existing contract
            "task": task,
            "reasoning": reasoning,
            "confidence": confidence,

            # New non-breaking metadata
            "detected_intent": detected_intent,
            "target": target,
            "temporal": temporal,
            "modalities": modalities,
            "observation_count": observation_count,
            "input_mode": input_mode,
        }

    # ==================================================================
    # NORMALIZATION
    # ==================================================================

    @staticmethod
    def _normalize_query(
        query: Any,
    ) -> str:
        if query is None:
            return ""

        # Collapse repeated whitespace while preserving the query meaning.
        return re.sub(
            r"\s+",
            " ",
            str(query),
        ).strip().lower()

    @staticmethod
    def _normalize_input_mode(
        input_mode: Any,
    ) -> str:
        if not input_mode:
            return "single_image"

        return str(
            input_mode
        ).strip().lower()

    @staticmethod
    def _normalize_modalities(
        modalities: Any,
    ) -> List[str]:
        if not modalities:
            return ["optical"]

        if not isinstance(
            modalities,
            (list, tuple),
        ):
            modalities = [modalities]

        normalized = []

        for modality in modalities:
            value = str(
                modality
            ).strip().lower()

            if not value:
                continue

            if value not in normalized:
                normalized.append(value)

        return normalized or ["optical"]

    # ==================================================================
    # KEYWORD DETECTION
    # ==================================================================

    @staticmethod
    def _contains_any(
        query: str,
        terms: tuple,
    ) -> bool:
        """
        Match terms safely.

        Short terms such as 'what' are treated as words rather than
        arbitrary substrings.
        """

        for term in terms:
            term = term.strip().lower()

            if not term:
                continue

            # Multi-word expressions can be matched directly.
            if " " in term or "-" in term or "+" in term:
                if term in query:
                    return True
                continue

            # Single words use word boundaries.
            if re.search(
                rf"\b{re.escape(term)}\b",
                query,
            ):
                return True

        return False

    @staticmethod
    def _has_modality(
        modalities: List[str],
        target: str,
    ) -> bool:
        target = target.lower()

        return any(
            target == modality.lower()
            or target in modality.lower()
            for modality in modalities
        )

    # ==================================================================
    # TEMPORAL LANGUAGE
    # ==================================================================

    @staticmethod
    def _has_temporal_language(
        query: str,
    ) -> bool:
        """
        Detect explicit temporal references such as:
            2024 and 2026
            between 2024 and 2026
            earlier/later
            before/after
            first/second observation
        """

        year_matches = re.findall(
            r"\b(?:19|20)\d{2}\b",
            query,
        )

        if len(set(year_matches)) >= 2:
            return True

        temporal_phrases = (
            "before",
            "after",
            "earlier",
            "later",
            "previous",
            "current",
            "first observation",
            "second observation",
            "two dates",
            "two times",
            "different dates",
            "different times",
            "over time",
            "between dates",
            "between years",
            "across time",
            "historical",
            "recent",
            "latest",
            "then and now",
            "pre-event",
            "post-event",
            "pre event",
            "post event",
            "from 2024",
            "from 2025",
            "from 2026",
        )

        return QueryClassifier._contains_any(
            query,
            temporal_phrases,
        )

    # ==================================================================
    # TARGET EXTRACTION
    # ==================================================================

    def _detect_target(
        self,
        query: str,
    ) -> Any:
        """
        Return a lightweight target label for routing/UI metadata.

        This does not replace the actual model's interpretation.
        """

        if self._contains_any(
            query,
            self.WATER_TERMS,
        ):
            return "water bodies"

        if self._contains_any(
            query,
            self.BUILT_UP_TERMS,
        ):
            return "built-up / urban regions"

        if self._contains_any(
            query,
            (
                "vegetation",
                "crop",
                "crops",
                "forest",
                "forests",
                "agriculture",
                "agricultural",
                "green cover",
            ),
        ):
            return "vegetation / agricultural areas"

        if self._contains_any(
            query,
            (
                "road",
                "roads",
                "highway",
                "highways",
                "bridge",
                "bridges",
            ),
        ):
            return "transport infrastructure"

        if self._contains_any(
            query,
            (
                "building",
                "buildings",
            ),
        ):
            return "buildings"

        if self._contains_any(
            query,
            (
                "ship",
                "ships",
                "vessel",
                "vessels",
                "boat",
                "boats",
            ),
        ):
            return "ships / vessels"

        if self._contains_any(
            query,
            (
                "solar",
                "solar panel",
                "solar panels",
                "panel",
                "panels",
            ),
        ):
            return "solar infrastructure"

        return None


# No singleton is created here.
# The existing AgentOrchestrator creates QueryClassifier() itself,
# preserving the current application architecture.
