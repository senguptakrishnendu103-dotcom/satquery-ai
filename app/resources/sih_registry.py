"""
SatQuery AI - SIH Data Resource Registry & Real Sample Materializer.

Implements the backend workflow that converts a selected SIH dataset sample
into real, verified image files usable by SatQuery:

    SELECT
       ↓
    MATERIALIZE
       ↓
    REAL LOCAL IMAGE FILE(S)
       ↓
    existing RasterIngestor / MetadataExtractor processing
       ↓
    normalized observation

Core Principles:
1. Use actual dataset files exclusively.
2. Never create synthetic imagery.
3. Never create fake sample IDs.
4. Never fabricate image paths.
5. Validate that every selected image actually exists on disk.
6. For paired data preserve: image 1, image 2, temporal ordering, modality, sample ID.
7. Preserve original dataset metadata/annotations (CORINE labels, VQA questions, grounding boxes, ISRO headers).
8. Distinguish materialization state: 'existing_local' | 'cached' | 'newly_materialized'.
9. Isolate strictly from external satellite download APIs (no CDSE, no Bhoonidhi).
"""

import os
import shutil
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.utils.isro_adapter import ISROProductAdapter
from app.utils.metadata_extractor import MetadataExtractor
from app.utils.image_resolver import ImageResolver


# ============================================================
# EXCEPTIONS
# ============================================================

class SIHResourceError(Exception):
    """Base exception for SIH data resource errors."""
    pass


class ResourceNotConfiguredError(SIHResourceError):
    """Raised when a requested resource is not configured or unavailable."""
    pass


class SampleNotFoundError(SIHResourceError):
    """Raised when a requested sample ID cannot be found in the dataset."""
    pass


class InvalidSampleFileError(SIHResourceError):
    """Raised when a physical sample raster is missing, unreadable, or invalid."""
    pass


# ============================================================
# CONSTANTS & ENUMS
# ============================================================

class ResourceAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"              # Configured and verified readable on disk
    CONFIGURED = "CONFIGURED"            # Path provided but files missing or unreadable
    NOT_CONFIGURED = "NOT_CONFIGURED"    # No local path or environment variable configured
    UNAVAILABLE = "UNAVAILABLE"          # Explicitly disabled or unsupported environment


class ResourceType(str, Enum):
    TRAINING_ADAPTATION_DATASET = "training_adaptation_dataset"
    EVALUATION_BENCHMARK = "evaluation_benchmark"
    ISRO_SAC_EVALUATION_RESOURCE = "isro_sac_evaluation_resource"


# ============================================================
# MATERIALIZATION HELPER
# ============================================================

def _materialize_file(
    source_path: str,
    output_dir: Optional[str] = None,
    subfolder: str = "sih_materialized",
) -> Tuple[Path, str]:
    """
    Ensure the physical raster file exists and materialize into target working directory.

    Returns:
        (materialized_path, materialization_state)
        Where state is one of:
            - 'existing_local': file already resides at destination
            - 'cached': destination file already exists and is identical
            - 'newly_materialized': freshly copied to workspace upload dir
    """
    if not source_path or not os.path.isfile(source_path):
        raise InvalidSampleFileError(f"Physical sample file not found on disk: '{source_path}'")

    if os.path.getsize(source_path) == 0:
        raise InvalidSampleFileError(f"Physical sample file is empty (0 bytes): '{source_path}'")

    source = Path(source_path).resolve()

    if output_dir:
        target_dir = Path(output_dir).resolve()
    else:
        target_dir = Path(__file__).resolve().parent.parent / "static" / "uploads" / subfolder

    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / source.name

    if source == destination:
        return destination, "existing_local"

    if destination.exists() and destination.is_file():
        if destination.stat().st_size == source.stat().st_size:
            return destination, "cached"

    shutil.copy2(str(source), str(destination))
    return destination, "newly_materialized"


# ============================================================
# BASE SIH RESOURCE
# ============================================================

class SIHResource:
    """
    Abstract Base Class for SIH26167 Data Resources.
    """

    def __init__(
        self,
        resource_id: str,
        name: str,
        resource_type: ResourceType,
        official_reference: str,
        description: str,
        supported_modalities: List[str],
        supported_tasks: List[str],
        local_dataset_root: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
    ):
        self.resource_id = resource_id.strip()
        self.name = name.strip()
        self.resource_type = resource_type
        self.official_reference = official_reference.strip()
        self.description = description.strip()
        self.supported_modalities = [m.lower() for m in supported_modalities]
        self.supported_tasks = list(supported_tasks)
        self.local_dataset_root = local_dataset_root
        self.configuration = configuration or {}
        self.materialization_capability = True

    def check_availability(self) -> Tuple[ResourceAvailability, str, Dict[str, Any]]:
        """
        Verify whether the resource is genuinely available on disk.
        Returns (Status, Diagnostic Message, Metadata Details).
        """
        raise NotImplementedError("Subclasses must implement check_availability")

    def get_metadata(self) -> Dict[str, Any]:
        """
        Return normalized metadata for discovery and API exposure.
        """
        status, reason, details = self.check_availability()
        return {
            "resource_id": self.resource_id,
            "name": self.name,
            "resource_type": self.resource_type.value,
            "official_reference": self.official_reference,
            "description": self.description,
            "supported_modalities": self.supported_modalities,
            "supported_tasks": self.supported_tasks,
            "local_dataset_root": self.local_dataset_root,
            "configuration": self.configuration,
            "materialization_capability": self.materialization_capability,
            "availability": status.value,
            "availability_reason": reason,
            "details": details,
        }

    def list_samples(
        self,
        limit: Optional[int] = None,
        filter_task: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List available samples with questions, labels, and metadata.
        """
        raise NotImplementedError("Subclasses must implement list_samples")

    def get_sample(self, sample_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single sample by ID.
        """
        samples = self.list_samples()
        for s in samples:
            if s.get("sample_id") == str(sample_id) or s.get("id") == str(sample_id):
                return s
        return None

    def materialize_observation(
        self,
        sample_id: str,
        output_dir: Optional[str] = None,
        pair_mode: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Materialize a real sample into the standard SatQuery Observation contract.
        """
        raise NotImplementedError("Subclasses must implement materialize_observation")


# ============================================================
# 1. BIGEARTHNET RESOURCE (Training / Adaptation Dataset)
# ============================================================

class BigEarthNetResource(SIHResource):
    """
    BigEarthNet Multi-Spectral Land Cover Training / Adaptation Dataset.
    Manifest format: BigEarthNet.txt (<patch_id> | <clc_labels> | <rel_path>)
    """

    def __init__(
        self,
        manifest_path: Optional[str] = None,
        data_dir: Optional[str] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent.parent
        default_manifest = base_dir / "training" / "data" / "BigEarthNet.txt"
        default_data_dir = base_dir / "training" / "data"

        resolved_manifest = manifest_path or os.getenv(
            "SATQUERY_BIGEARTHNET_MANIFEST", str(default_manifest)
        )
        resolved_data_dir = data_dir or os.getenv(
            "SATQUERY_BIGEARTHNET_DIR", str(default_data_dir)
        )

        super().__init__(
            resource_id="bigearthnet",
            name="BigEarthNet (CORINE Land Cover)",
            resource_type=ResourceType.TRAINING_ADAPTATION_DATASET,
            official_reference=(
                "BigEarthNet: A Large-Scale Benchmark Archive for Remote Sensing "
                "Image Understanding (Sumbul et al., IEEE IGARSS 2019 / CVPRW)"
            ),
            description=(
                "Multi-spectral Sentinel-2 satellite image patches annotated with "
                "CORINE Land Cover (CLC) nomenclature classes for VLM adaptation."
            ),
            supported_modalities=["optical", "multispectral"],
            supported_tasks=[
                "SINGLE_IMAGE_VQA",
                "IMAGE_CAPTIONING",
                "LAND_COVER_CLASSIFICATION",
                "WATER_DETECTION",
                "BUILT_UP_ANALYSIS",
            ],
            local_dataset_root=str(resolved_data_dir),
            configuration={
                "manifest_path": str(resolved_manifest),
                "data_dir": str(resolved_data_dir),
                "manifest_filename": "BigEarthNet.txt",
                "nomenclature": "CORINE Land Cover (CLC 19/43 classes)",
            },
        )
        self.manifest_path = resolved_manifest
        self.data_dir = resolved_data_dir

    def check_availability(self) -> Tuple[ResourceAvailability, str, Dict[str, Any]]:
        if not os.path.exists(self.manifest_path):
            return (
                ResourceAvailability.NOT_CONFIGURED,
                f"BigEarthNet manifest not found at '{self.manifest_path}'.",
                {"sample_count": 0, "valid_patches": 0},
            )

        try:
            from training.dataset import load_bigearthnet_manifest
            samples = load_bigearthnet_manifest(self.manifest_path, self.data_dir)
            if not samples:
                return (
                    ResourceAvailability.CONFIGURED,
                    f"Manifest exists at '{self.manifest_path}' but contains no valid entries.",
                    {"sample_count": 0, "valid_patches": 0},
                )

            valid_count = sum(1 for s in samples if os.path.isfile(s.image_path) and os.path.getsize(s.image_path) > 0)
            if valid_count == 0:
                return (
                    ResourceAvailability.CONFIGURED,
                    f"Manifest references {len(samples)} patches, but no image files exist on disk.",
                    {"sample_count": len(samples), "valid_patches": 0},
                )

            return (
                ResourceAvailability.AVAILABLE,
                f"BigEarthNet manifest verified with {valid_count}/{len(samples)} valid patch files on disk.",
                {
                    "sample_count": len(samples),
                    "valid_patches": valid_count,
                    "manifest_path": self.manifest_path,
                },
            )
        except Exception as exc:
            return (
                ResourceAvailability.UNAVAILABLE,
                f"Error validating BigEarthNet manifest: {exc}",
                {"error": str(exc)},
            )

    def list_samples(
        self,
        limit: Optional[int] = None,
        filter_task: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        status, _, _ = self.check_availability()
        if status != ResourceAvailability.AVAILABLE:
            return []

        from training.dataset import load_bigearthnet_manifest
        raw_samples = load_bigearthnet_manifest(self.manifest_path, self.data_dir)
        results = []
        for s in raw_samples:
            if not os.path.isfile(s.image_path) or os.path.getsize(s.image_path) == 0:
                continue

            # Check for paired Sentinel-1 SAR counterpart if available
            s1_pair_path = None
            s1_filename = s.patch_id.replace("S2A_", "S1A_").replace("S2B_", "S1B_") + ".tif"
            potential_s1 = Path(s.image_path).parent / s1_filename
            if potential_s1.exists() and potential_s1.is_file():
                s1_pair_path = str(potential_s1.resolve())

            item = {
                "sample_id": s.patch_id,
                "id": s.patch_id,
                "dataset": "bigearthnet",
                "filename": os.path.basename(s.image_path),
                "file_path": str(s.image_path),
                "labels": s.labels,
                "primary_label": s.primary_label,
                "suggested_query": s.question,
                "ground_truth_answer": s.answer,
                "modality": "optical",
                "has_s1_sar_pair": s1_pair_path is not None,
                "s1_pair_path": s1_pair_path,
                "task_compatibility": [
                    "SINGLE_IMAGE_VQA",
                    "IMAGE_CAPTIONING",
                    "LAND_COVER_CLASSIFICATION",
                ],
            }
            results.append(item)
            if limit and len(results) >= limit:
                break
        return results

    def materialize_observation(
        self,
        sample_id: str,
        output_dir: Optional[str] = None,
        pair_mode: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        status, reason, _ = self.check_availability()
        if status != ResourceAvailability.AVAILABLE:
            raise ResourceNotConfiguredError(f"BigEarthNet dataset is not available: {reason}")

        sample = self.get_sample(sample_id)
        if not sample:
            raise SampleNotFoundError(f"BigEarthNet sample '{sample_id}' not found in manifest.")

        source_file = sample["file_path"]
        dest_file, mat_state = _materialize_file(source_file, output_dir=output_dir, subfolder="sih_materialized")

        clean_name = dest_file.name
        metadata = MetadataExtractor.extract_metadata(str(dest_file), clean_name)
        if not metadata.get("valid", True):
            raise InvalidSampleFileError(f"Invalid BigEarthNet raster '{clean_name}': {metadata.get('error')}")

        obs_id = f"sih_ben_{sample_id}"
        preview_url = ImageResolver.ensure_displayable_preview(str(dest_file))

        metadata.update({
            "id": obs_id,
            "filename": clean_name,
            "name": f"BigEarthNet — {sample['primary_label']} ({clean_name})",
            "url": preview_url,
            "image_url": preview_url,
            "imageUrl": preview_url,
            "thumbnailUrl": preview_url,
            "thumbnail_url": preview_url,
            "file_path": str(dest_file.resolve()),
            "local_path": str(dest_file.resolve()),
            "source_type": "sih_resource",
            "resource_id": "bigearthnet",
            "dataset_name": "BigEarthNet",
            "sample_id": sample_id,
            "modality": "optical",
            "materialization_state": mat_state,
            "isDemo": False,
            "ingestion_status": "ready",
            "suggested_query": sample.get("suggested_query"),
            "ground_truth_answer": sample.get("ground_truth_answer"),
            "labels": sample.get("labels", []),
            "primary_label": sample.get("primary_label"),
            "has_s1_sar_pair": sample.get("has_s1_sar_pair", False),
        })

        if pair_mode and sample.get("has_s1_sar_pair") and sample.get("s1_pair_path"):
            s1_source = sample["s1_pair_path"]
            s1_dest, mat_state_s1 = _materialize_file(s1_source, output_dir=output_dir, subfolder="sih_materialized")
            meta_s1 = MetadataExtractor.extract_metadata(str(s1_dest), s1_dest.name)
            s1_preview = ImageResolver.ensure_displayable_preview(str(s1_dest))
            meta_s1.update({
                "id": f"sih_ben_s1_{sample_id}",
                "filename": s1_dest.name,
                "name": f"BigEarthNet S1 (SAR) — {sample['primary_label']} ({s1_dest.name})",
                "url": s1_preview,
                "image_url": s1_preview,
                "imageUrl": s1_preview,
                "thumbnailUrl": s1_preview,
                "thumbnail_url": s1_preview,
                "file_path": str(s1_dest.resolve()),
                "local_path": str(s1_dest.resolve()),
                "source_type": "sih_resource",
                "resource_id": "bigearthnet",
                "dataset_name": "BigEarthNet",
                "sample_id": sample_id,
                "modality": "sar",
                "order": 2,
                "materialization_state": mat_state_s1,
                "isDemo": False,
                "ingestion_status": "ready",
            })
            return {
                "primary_observation": metadata,
                "companion_observation": meta_s1,
                "pair_mode": "optical_sar",
                "sample_id": sample_id,
                "suggested_query": sample.get("suggested_query"),
                "ground_truth_answer": sample.get("ground_truth_answer"),
                "ordering": ["optical (Sentinel-2)", "sar (Sentinel-1)"],
                "both_files_verified": True,
            }

        return metadata


# ============================================================
# 2. VRSBENCH RESOURCE (Evaluation Benchmark)
# ============================================================

class VRSBenchResource(SIHResource):
    """
    VRSBench Visual Remote Sensing Benchmark for VQA, Captioning, and Visual Grounding.
    """

    def __init__(
        self,
        annotations_path: Optional[str] = None,
        images_dir: Optional[str] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent.parent
        default_dir = base_dir / "training" / "data" / "vrsbench"
        default_ann = default_dir / "vrsbench_annotations.json"
        default_img = default_dir / "images"

        resolved_ann = annotations_path or os.getenv("SATQUERY_VRSBENCH_ANN", str(default_ann))
        resolved_img = images_dir or os.getenv("SATQUERY_VRSBENCH_DIR", str(default_img))

        super().__init__(
            resource_id="vrsbench",
            name="VRSBench (VQA, Captioning, Grounding)",
            resource_type=ResourceType.EVALUATION_BENCHMARK,
            official_reference=(
                "VRSBench: A Versatile Visual Remote Sensing Benchmark for Visual "
                "Question Answering, Captioning, and Visual Grounding (Chen et al., 2024)"
            ),
            description=(
                "Standardized high-resolution benchmark supporting conversational VQA, "
                "detailed multi-sentence scene captioning, and bounding box visual grounding."
            ),
            supported_modalities=["optical", "high_resolution_rgb"],
            supported_tasks=[
                "SINGLE_IMAGE_VQA",
                "IMAGE_CAPTIONING",
                "OBJECT_GROUNDING",
            ],
            local_dataset_root=str(resolved_img),
            configuration={
                "annotations_path": str(resolved_ann),
                "images_dir": str(resolved_img),
                "supported_features": ["vqa", "captioning", "spatial_grounding_boxes"],
            },
        )
        self.annotations_path = resolved_ann
        self.images_dir = resolved_img

    def check_availability(self) -> Tuple[ResourceAvailability, str, Dict[str, Any]]:
        if not os.path.exists(self.annotations_path):
            return (
                ResourceAvailability.NOT_CONFIGURED,
                f"VRSBench annotations JSON not found at '{self.annotations_path}'.",
                {"annotations_found": False, "images_dir_exists": os.path.isdir(self.images_dir)},
            )

        try:
            from training.benchmarks import VRSBenchDataset
            dataset = VRSBenchDataset(
                images_dir=self.images_dir,
                annotations_path=self.annotations_path,
            )
            if len(dataset) == 0:
                return (
                    ResourceAvailability.CONFIGURED,
                    f"VRSBench annotation file at '{self.annotations_path}' contains 0 items.",
                    {"sample_count": 0, "valid_images": 0},
                )

            valid_count = sum(1 for s in dataset.samples if os.path.isfile(s.image_path) and os.path.getsize(s.image_path) > 0)
            if valid_count == 0:
                return (
                    ResourceAvailability.CONFIGURED,
                    f"VRSBench annotations parsed ({len(dataset)} items), but no referenced image files found in '{self.images_dir}'.",
                    {"sample_count": len(dataset), "valid_images": 0},
                )

            return (
                ResourceAvailability.AVAILABLE,
                f"VRSBench verified with {valid_count}/{len(dataset)} valid benchmark samples on disk.",
                {
                    "sample_count": len(dataset),
                    "valid_images": valid_count,
                    "annotations_path": self.annotations_path,
                },
            )
        except Exception as exc:
            return (
                ResourceAvailability.UNAVAILABLE,
                f"Error validating VRSBench benchmark: {exc}",
                {"error": str(exc)},
            )

    def list_samples(
        self,
        limit: Optional[int] = None,
        filter_task: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        status, _, _ = self.check_availability()
        if status != ResourceAvailability.AVAILABLE:
            return []

        from training.benchmarks import VRSBenchDataset
        dataset = VRSBenchDataset(
            images_dir=self.images_dir,
            annotations_path=self.annotations_path,
        )
        results = []
        for s in dataset.samples:
            if not os.path.isfile(s.image_path) or os.path.getsize(s.image_path) == 0:
                continue
            item = {
                "sample_id": s.sample_id,
                "id": s.sample_id,
                "dataset": "vrsbench",
                "filename": os.path.basename(s.image_path),
                "file_path": str(s.image_path),
                "suggested_query": s.question,
                "ground_truth_answer": s.answer,
                "caption": s.caption,
                "grounding_boxes": s.grounding_boxes,
                "modality": "optical",
                "task_compatibility": ["SINGLE_IMAGE_VQA", "IMAGE_CAPTIONING", "OBJECT_GROUNDING"],
            }
            results.append(item)
            if limit and len(results) >= limit:
                break
        return results

    def materialize_observation(
        self,
        sample_id: str,
        output_dir: Optional[str] = None,
        pair_mode: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        status, reason, _ = self.check_availability()
        if status != ResourceAvailability.AVAILABLE:
            raise ResourceNotConfiguredError(f"VRSBench benchmark is not available: {reason}")

        sample = self.get_sample(sample_id)
        if not sample:
            raise SampleNotFoundError(f"VRSBench sample '{sample_id}' not found.")

        source_file = sample["file_path"]
        dest_file, mat_state = _materialize_file(source_file, output_dir=output_dir, subfolder="sih_materialized")

        clean_name = dest_file.name
        metadata = MetadataExtractor.extract_metadata(str(dest_file), clean_name)
        if not metadata.get("valid", True):
            raise InvalidSampleFileError(f"Invalid VRSBench raster '{clean_name}': {metadata.get('error')}")

        public_url = ImageResolver.ensure_displayable_preview(str(dest_file))
        metadata.update({
            "id": f"sih_vrs_{sample_id}",
            "filename": clean_name,
            "name": f"VRSBench — {sample_id} ({clean_name})",
            "url": public_url,
            "image_url": public_url,
            "imageUrl": public_url,
            "thumbnailUrl": public_url,
            "thumbnail_url": public_url,
            "file_path": str(dest_file.resolve()),
            "local_path": str(dest_file.resolve()),
            "source_type": "sih_resource",
            "resource_id": "vrsbench",
            "dataset_name": "VRSBench",
            "sample_id": sample_id,
            "materialization_state": mat_state,
            "isDemo": False,
            "ingestion_status": "ready",
            "suggested_query": sample.get("suggested_query"),
            "ground_truth_answer": sample.get("ground_truth_answer"),
            "caption": sample.get("caption"),
            "grounding_boxes": sample.get("grounding_boxes", []),
        })
        return metadata


# ============================================================
# 3. RSVQA RESOURCE (Evaluation Benchmark)
# ============================================================

class RSVQAResource(SIHResource):
    """
    RSVQA (Remote Sensing Visual Question Answering) Benchmark Dataset.
    Official schema: questions.json & answers.json.
    """

    def __init__(
        self,
        questions_path: Optional[str] = None,
        answers_path: Optional[str] = None,
        images_dir: Optional[str] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent.parent
        default_dir = base_dir / "training" / "data" / "rsvqa"
        default_q = default_dir / "questions.json"
        default_a = default_dir / "answers.json"
        default_img = default_dir / "images"

        resolved_q = questions_path or os.getenv("SATQUERY_RSVQA_QUESTIONS", str(default_q))
        resolved_a = answers_path or os.getenv("SATQUERY_RSVQA_ANSWERS", str(default_a))
        resolved_img = images_dir or os.getenv("SATQUERY_RSVQA_DIR", str(default_img))

        super().__init__(
            resource_id="rsvqa",
            name="RSVQA (Remote Sensing VQA)",
            resource_type=ResourceType.EVALUATION_BENCHMARK,
            official_reference=(
                "RSVQA: Visual Question Answering for Remote Sensing Data "
                "(Lobry et al., IEEE Transactions on Geoscience and Remote Sensing 2020)"
            ),
            description=(
                "Standardized benchmark for remote-sensing question answering across "
                "presence, count, comparison, and rural/urban land cover queries."
            ),
            supported_modalities=["optical", "multispectral"],
            supported_tasks=[
                "SINGLE_IMAGE_VQA",
                "LAND_COVER_CLASSIFICATION",
                "WATER_DETECTION",
                "BUILT_UP_ANALYSIS",
            ],
            local_dataset_root=str(resolved_img),
            configuration={
                "questions_path": str(resolved_q),
                "answers_path": str(resolved_a),
                "images_dir": str(resolved_img),
                "categories": ["presence", "count", "comparison", "rural_urban"],
            },
        )
        self.questions_path = resolved_q
        self.answers_path = resolved_a
        self.images_dir = resolved_img

    def check_availability(self) -> Tuple[ResourceAvailability, str, Dict[str, Any]]:
        if not os.path.exists(self.questions_path):
            return (
                ResourceAvailability.NOT_CONFIGURED,
                f"RSVQA questions JSON not found at '{self.questions_path}'.",
                {"questions_found": False, "images_dir_exists": os.path.isdir(self.images_dir)},
            )

        try:
            from training.benchmarks import RSVQADataset
            dataset = RSVQADataset(
                images_dir=self.images_dir,
                questions_path=self.questions_path,
                answers_path=self.answers_path,
            )
            if len(dataset) == 0:
                return (
                    ResourceAvailability.CONFIGURED,
                    f"RSVQA questions parsed but contain 0 question items.",
                    {"sample_count": 0, "valid_images": 0},
                )

            valid_count = sum(1 for s in dataset.samples if os.path.isfile(s.image_path) and os.path.getsize(s.image_path) > 0)
            if valid_count == 0:
                return (
                    ResourceAvailability.CONFIGURED,
                    f"RSVQA parsed {len(dataset)} questions, but no images found in '{self.images_dir}'.",
                    {"sample_count": len(dataset), "valid_images": 0},
                )

            return (
                ResourceAvailability.AVAILABLE,
                f"RSVQA benchmark verified with {valid_count}/{len(dataset)} valid samples on disk.",
                {
                    "sample_count": len(dataset),
                    "valid_images": valid_count,
                    "questions_path": self.questions_path,
                },
            )
        except Exception as exc:
            return (
                ResourceAvailability.UNAVAILABLE,
                f"Error validating RSVQA benchmark: {exc}",
                {"error": str(exc)},
            )

    def list_samples(
        self,
        limit: Optional[int] = None,
        filter_task: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        status, _, _ = self.check_availability()
        if status != ResourceAvailability.AVAILABLE:
            return []

        from training.benchmarks import RSVQADataset
        dataset = RSVQADataset(
            images_dir=self.images_dir,
            questions_path=self.questions_path,
            answers_path=self.answers_path,
        )
        results = []
        for s in dataset.samples:
            if not os.path.isfile(s.image_path) or os.path.getsize(s.image_path) == 0:
                continue
            item = {
                "sample_id": s.question_id,
                "id": s.question_id,
                "dataset": "rsvqa",
                "filename": os.path.basename(s.image_path),
                "file_path": str(s.image_path),
                "suggested_query": s.question,
                "ground_truth_answer": s.answer,
                "question_type": s.question_type,
                "modality": "optical",
                "task_compatibility": ["SINGLE_IMAGE_VQA", "LAND_COVER_CLASSIFICATION"],
            }
            results.append(item)
            if limit and len(results) >= limit:
                break
        return results

    def materialize_observation(
        self,
        sample_id: str,
        output_dir: Optional[str] = None,
        pair_mode: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        status, reason, _ = self.check_availability()
        if status != ResourceAvailability.AVAILABLE:
            raise ResourceNotConfiguredError(f"RSVQA benchmark is not available: {reason}")

        sample = self.get_sample(sample_id)
        if not sample:
            raise SampleNotFoundError(f"RSVQA sample '{sample_id}' not found.")

        source_file = sample["file_path"]
        dest_file, mat_state = _materialize_file(source_file, output_dir=output_dir, subfolder="sih_materialized")

        clean_name = dest_file.name
        metadata = MetadataExtractor.extract_metadata(str(dest_file), clean_name)
        if not metadata.get("valid", True):
            raise InvalidSampleFileError(f"Invalid RSVQA raster '{clean_name}': {metadata.get('error')}")

        public_url = ImageResolver.ensure_displayable_preview(str(dest_file))
        metadata.update({
            "id": f"sih_rsvqa_{sample_id}",
            "filename": clean_name,
            "name": f"RSVQA — {sample_id} ({clean_name})",
            "url": public_url,
            "image_url": public_url,
            "imageUrl": public_url,
            "thumbnailUrl": public_url,
            "thumbnail_url": public_url,
            "file_path": str(dest_file.resolve()),
            "local_path": str(dest_file.resolve()),
            "source_type": "sih_resource",
            "resource_id": "rsvqa",
            "dataset_name": "RSVQA",
            "sample_id": sample_id,
            "materialization_state": mat_state,
            "isDemo": False,
            "ingestion_status": "ready",
            "suggested_query": sample.get("suggested_query"),
            "ground_truth_answer": sample.get("ground_truth_answer"),
            "question_type": sample.get("question_type"),
        })
        return metadata


# ============================================================
# 4. CDVQA RESOURCE (Evaluation Benchmark)
# ============================================================

class CDVQAResource(SIHResource):
    """
    CDVQA (Change Detection Visual Question Answering) Benchmark Dataset.
    Bi-temporal observation pairs and change queries.
    """

    def __init__(
        self,
        annotations_path: Optional[str] = None,
        images_dir: Optional[str] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent.parent
        default_dir = base_dir / "training" / "data" / "cdvqa"
        default_ann = default_dir / "cdvqa_pairs.json"
        default_img = default_dir / "images"

        resolved_ann = annotations_path or os.getenv("SATQUERY_CDVQA_ANN", str(default_ann))
        resolved_img = images_dir or os.getenv("SATQUERY_CDVQA_DIR", str(default_img))

        super().__init__(
            resource_id="cdvqa",
            name="CDVQA (Change Detection VQA)",
            resource_type=ResourceType.EVALUATION_BENCHMARK,
            official_reference=(
                "Change Detection Visual Question Answering on Bi-Temporal Remote "
                "Sensing Images (Yuan et al., IEEE TGRS)"
            ),
            description=(
                "Bi-temporal satellite observation benchmark evaluating natural-language "
                "reasoning over structural, agricultural, and urban environmental changes."
            ),
            supported_modalities=["optical", "bi_temporal"],
            supported_tasks=[
                "CHANGE_DETECTION",
                "BI_TEMPORAL_VQA",
            ],
            local_dataset_root=str(resolved_img),
            configuration={
                "annotations_path": str(resolved_ann),
                "images_dir": str(resolved_img),
                "pair_mode": "bi_temporal (T1 + T2)",
            },
        )
        self.annotations_path = resolved_ann
        self.images_dir = resolved_img

    def check_availability(self) -> Tuple[ResourceAvailability, str, Dict[str, Any]]:
        if not os.path.exists(self.annotations_path):
            return (
                ResourceAvailability.NOT_CONFIGURED,
                f"CDVQA pairs JSON not found at '{self.annotations_path}'.",
                {"annotations_found": False, "images_dir_exists": os.path.isdir(self.images_dir)},
            )

        try:
            from training.benchmarks import CDVQADataset
            dataset = CDVQADataset(
                images_dir=self.images_dir,
                annotations_path=self.annotations_path,
            )
            if len(dataset) == 0:
                return (
                    ResourceAvailability.CONFIGURED,
                    f"CDVQA pairs file parsed but contains 0 items.",
                    {"sample_count": 0, "valid_pairs": 0},
                )

            valid_count = sum(
                1 for s in dataset.samples
                if os.path.isfile(s.image_t1_path) and os.path.isfile(s.image_t2_path)
                and os.path.getsize(s.image_t1_path) > 0 and os.path.getsize(s.image_t2_path) > 0
            )
            if valid_count == 0:
                return (
                    ResourceAvailability.CONFIGURED,
                    f"CDVQA parsed {len(dataset)} pair definitions, but no image pairs found on disk in '{self.images_dir}'.",
                    {"sample_count": len(dataset), "valid_pairs": 0},
                )

            return (
                ResourceAvailability.AVAILABLE,
                f"CDVQA benchmark verified with {valid_count}/{len(dataset)} valid bi-temporal pairs on disk.",
                {
                    "sample_count": len(dataset),
                    "valid_pairs": valid_count,
                    "annotations_path": self.annotations_path,
                },
            )
        except Exception as exc:
            return (
                ResourceAvailability.UNAVAILABLE,
                f"Error validating CDVQA benchmark: {exc}",
                {"error": str(exc)},
            )

    def list_samples(
        self,
        limit: Optional[int] = None,
        filter_task: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        status, _, _ = self.check_availability()
        if status != ResourceAvailability.AVAILABLE:
            return []

        from training.benchmarks import CDVQADataset
        dataset = CDVQADataset(
            images_dir=self.images_dir,
            annotations_path=self.annotations_path,
        )
        results = []
        for s in dataset.samples:
            if not os.path.isfile(s.image_t1_path) or not os.path.isfile(s.image_t2_path):
                continue
            item = {
                "sample_id": s.pair_id,
                "id": s.pair_id,
                "dataset": "cdvqa",
                "image_t1_path": str(s.image_t1_path),
                "image_t2_path": str(s.image_t2_path),
                "suggested_query": s.question,
                "ground_truth_answer": s.answer,
                "change_type": s.change_type,
                "modality": "optical",
                "task_compatibility": ["CHANGE_DETECTION", "BI_TEMPORAL_VQA"],
            }
            results.append(item)
            if limit and len(results) >= limit:
                break
        return results

    def materialize_observation(
        self,
        sample_id: str,
        output_dir: Optional[str] = None,
        pair_mode: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        For bi-temporal CDVQA, materializes real observation pair (T1 + T2) preserving
        ordering, modality, sample ID, and temporal QA metadata.
        """
        status, reason, _ = self.check_availability()
        if status != ResourceAvailability.AVAILABLE:
            raise ResourceNotConfiguredError(f"CDVQA benchmark is not available: {reason}")

        sample = self.get_sample(sample_id)
        if not sample:
            raise SampleNotFoundError(f"CDVQA pair '{sample_id}' not found.")

        t1_source = sample["image_t1_path"]
        t2_source = sample["image_t2_path"]

        t1_dest, mat_state_t1 = _materialize_file(t1_source, output_dir=output_dir, subfolder="sih_materialized")
        t2_dest, mat_state_t2 = _materialize_file(t2_source, output_dir=output_dir, subfolder="sih_materialized")

        meta_t1 = MetadataExtractor.extract_metadata(str(t1_dest), t1_dest.name)
        meta_t2 = MetadataExtractor.extract_metadata(str(t2_dest), t2_dest.name)

        if not meta_t1.get("valid", True):
            raise InvalidSampleFileError(f"Invalid CDVQA T1 raster '{t1_dest.name}': {meta_t1.get('error')}")
        if not meta_t2.get("valid", True):
            raise InvalidSampleFileError(f"Invalid CDVQA T2 raster '{t2_dest.name}': {meta_t2.get('error')}")

        preview_t1 = ImageResolver.ensure_displayable_preview(str(t1_dest))
        preview_t2 = ImageResolver.ensure_displayable_preview(str(t2_dest))

        obs_t1 = {
            **meta_t1,
            "id": f"sih_cd_{sample_id}_t1",
            "filename": t1_dest.name,
            "name": f"CDVQA T1 (Pre-Change) — {sample_id} ({t1_dest.name})",
            "url": preview_t1,
            "image_url": preview_t1,
            "imageUrl": preview_t1,
            "thumbnailUrl": preview_t1,
            "thumbnail_url": preview_t1,
            "file_path": str(t1_dest.resolve()),
            "local_path": str(t1_dest.resolve()),
            "source_type": "sih_resource",
            "resource_id": "cdvqa",
            "dataset_name": "CDVQA",
            "sample_id": sample_id,
            "temporal_role": "pre_change",
            "order": 1,
            "materialization_state": mat_state_t1,
            "isDemo": False,
            "ingestion_status": "ready",
            "suggested_query": sample.get("suggested_query"),
            "ground_truth_answer": sample.get("ground_truth_answer"),
        }

        obs_t2 = {
            **meta_t2,
            "id": f"sih_cd_{sample_id}_t2",
            "filename": t2_dest.name,
            "name": f"CDVQA T2 (Post-Change) — {sample_id} ({t2_dest.name})",
            "url": preview_t2,
            "image_url": preview_t2,
            "imageUrl": preview_t2,
            "thumbnailUrl": preview_t2,
            "thumbnail_url": preview_t2,
            "file_path": str(t2_dest.resolve()),
            "local_path": str(t2_dest.resolve()),
            "source_type": "sih_resource",
            "resource_id": "cdvqa",
            "dataset_name": "CDVQA",
            "sample_id": sample_id,
            "temporal_role": "post_change",
            "order": 2,
            "materialization_state": mat_state_t2,
            "isDemo": False,
            "ingestion_status": "ready",
            "suggested_query": sample.get("suggested_query"),
            "ground_truth_answer": sample.get("ground_truth_answer"),
        }

        return {
            "primary_observation": obs_t1,
            "companion_observation": obs_t2,
            "pair_mode": "bi_temporal",
            "sample_id": sample_id,
            "change_type": sample.get("change_type"),
            "suggested_query": sample.get("suggested_query"),
            "ground_truth_answer": sample.get("ground_truth_answer"),
            "ordering": ["pre_change (T1)", "post_change (T2)"],
            "both_files_verified": True,
        }


# ============================================================
# 5. ISRO / SAC EVALUATION RESOURCE
# ============================================================

class ISROSACEvaluationResource(SIHResource):
    """
    Indian Space Research Organisation (ISRO) & Space Applications Centre (SAC)
    Dedicated Evaluation Resource (Resourcesat LISS-4/3, Cartosat, RISAT/EOS-04 SAR).
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent.parent
        default_dir = base_dir / "sample_data"
        resolved_dir = data_dir or os.getenv("SATQUERY_ISRO_DIR", str(default_dir))

        super().__init__(
            resource_id="isro_sac_evaluation",
            name="ISRO / SAC Mission Evaluation Resource",
            resource_type=ResourceType.ISRO_SAC_EVALUATION_RESOURCE,
            official_reference=(
                "ISRO / Space Applications Centre (SAC) Earth Observation Standard Products "
                "& In-Flight Sensor Payloads (Resourcesat, Cartosat, RISAT / EOS-04 SAR, EOS-06)"
            ),
            description=(
                "Genuine ISRO / SAC multi-spectral and radar satellite rasters and XML metadata "
                "conforming to Indian National Remote Sensing Centre (NRSC) format specifications."
            ),
            supported_modalities=["optical", "multispectral", "sar"],
            supported_tasks=[
                "SINGLE_IMAGE_VQA",
                "WATER_DETECTION",
                "BUILT_UP_ANALYSIS",
                "OPTICAL_SAR_ANALYSIS",
                "ISRO_PAYLOAD_VALIDATION",
            ],
            local_dataset_root=str(resolved_dir),
            configuration={
                "data_dir": str(resolved_dir),
                "supported_missions": [
                    "Resourcesat (LISS-4, LISS-3, AWiFS)",
                    "Cartosat (Panchromatic, MX)",
                    "RISAT / EOS-04 (C-Band Radar SAR)",
                    "EOS-06 (Ocean Colour Monitor)",
                ],
                "adapter": "ISROProductAdapter",
            },
        )
        self.data_dir = resolved_dir

    def check_availability(self) -> Tuple[ResourceAvailability, str, Dict[str, Any]]:
        if not os.path.exists(self.data_dir) or not os.path.isdir(self.data_dir):
            return (
                ResourceAvailability.NOT_CONFIGURED,
                f"ISRO evaluation data directory not found at '{self.data_dir}'.",
                {"files_found": 0},
            )

        try:
            isro_files = self._scan_isro_files()
            if not isro_files:
                return (
                    ResourceAvailability.CONFIGURED,
                    f"Directory '{self.data_dir}' exists, but contains no recognized ISRO GeoTIFF rasters.",
                    {"files_found": 0},
                )

            return (
                ResourceAvailability.AVAILABLE,
                f"ISRO / SAC Evaluation Resource verified with {len(isro_files)} authentic mission product(s) on disk.",
                {
                    "files_found": len(isro_files),
                    "isro_products": [f["filename"] for f in isro_files],
                    "data_dir": self.data_dir,
                },
            )
        except Exception as exc:
            return (
                ResourceAvailability.UNAVAILABLE,
                f"Error scanning ISRO evaluation resource: {exc}",
                {"error": str(exc)},
            )

    def _scan_isro_files(self) -> List[Dict[str, Any]]:
        isro_products = []
        if not os.path.isdir(self.data_dir):
            return isro_products

        for root, _, files in os.walk(self.data_dir):
            for file in files:
                if not file.lower().endswith((".tif", ".tiff", ".jp2")):
                    continue
                full_path = os.path.join(root, file)
                if not os.path.isfile(full_path) or os.path.getsize(full_path) == 0:
                    continue
                # Detect using ISROProductAdapter
                isro_info = ISROProductAdapter.detect_isro_product(full_path, filename=file)
                if isro_info:
                    isro_products.append({
                        "file_path": full_path,
                        "filename": file,
                        "isro_info": isro_info,
                    })
        return isro_products

    def list_samples(
        self,
        limit: Optional[int] = None,
        filter_task: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        status, _, _ = self.check_availability()
        if status != ResourceAvailability.AVAILABLE:
            return []

        isro_files = self._scan_isro_files()
        results = []
        for item in isro_files:
            file_path = item["file_path"]
            filename = item["filename"]
            info = item["isro_info"]

            sample_id = (
                info.get("product_id")
                or info.get("isro_product_id")
                or os.path.splitext(filename)[0]
            )
            mission = (
                info.get("mission")
                or info.get("isro_mission")
                or info.get("platform")
                or "ISRO"
            )
            sensor = (
                info.get("sensor")
                or info.get("isro_sensor")
                or "Optical"
            )
            modality = (
                info.get("modality")
                or info.get("isro_modality")
                or "optical"
            )

            suggested_query = (
                f"Identify vegetation density, water features, and built-up land use in this {mission} {sensor} observation."
            )

            results.append({
                "sample_id": sample_id,
                "id": sample_id,
                "dataset": "isro_sac_evaluation",
                "filename": filename,
                "file_path": file_path,
                "mission": mission,
                "sensor": sensor,
                "modality": modality,
                "suggested_query": suggested_query,
                "isro_metadata": info,
                "task_compatibility": [
                    "SINGLE_IMAGE_VQA",
                    "WATER_DETECTION",
                    "BUILT_UP_ANALYSIS",
                    "ISRO_PAYLOAD_VALIDATION",
                ],
            })
            if limit and len(results) >= limit:
                break
        return results

    def materialize_observation(
        self,
        sample_id: str,
        output_dir: Optional[str] = None,
        pair_mode: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        status, reason, _ = self.check_availability()
        if status != ResourceAvailability.AVAILABLE:
            raise ResourceNotConfiguredError(f"ISRO / SAC Evaluation Resource is not available: {reason}")

        sample = self.get_sample(sample_id)
        if not sample:
            raise SampleNotFoundError(f"ISRO product '{sample_id}' not found.")

        source_file = sample["file_path"]
        dest_file, mat_state = _materialize_file(source_file, output_dir=output_dir, subfolder="sih_materialized")

        clean_name = dest_file.name
        metadata = MetadataExtractor.extract_metadata(str(dest_file), clean_name)
        if not metadata.get("valid", True):
            raise InvalidSampleFileError(f"Invalid ISRO GeoTIFF raster '{clean_name}': {metadata.get('error')}")

        public_url = ImageResolver.ensure_displayable_preview(str(dest_file))
        metadata.update({
            "id": f"sih_isro_{sample_id}",
            "filename": clean_name,
            "name": f"ISRO {sample['mission']} ({sample['sensor']})",
            "url": public_url,
            "image_url": public_url,
            "imageUrl": public_url,
            "thumbnailUrl": public_url,
            "thumbnail_url": public_url,
            "file_path": str(dest_file.resolve()),
            "local_path": str(dest_file.resolve()),
            "source_type": "sih_resource",
            "resource_id": "isro_sac_evaluation",
            "dataset_name": "ISRO / SAC Evaluation Resource",
            "sample_id": sample_id,
            "materialization_state": mat_state,
            "isDemo": False,
            "ingestion_status": "ready",
            "suggested_query": sample.get("suggested_query"),
            "isro_metadata": sample.get("isro_metadata", {}),
        })
        return metadata


# ============================================================
# SIH RESOURCE REGISTRY (Singleton)
# ============================================================

class SIHResourceRegistry:
    """
    Central Registry for SIH26167 Data Resources and Evaluation Benchmarks.
    """

    def __init__(self):
        self._resources: Dict[str, SIHResource] = {}
        self._register_default_resources()

    def _register_default_resources(self) -> None:
        """Register the 5 standardized SIH26167 resources."""
        self.register(BigEarthNetResource())
        self.register(VRSBenchResource())
        self.register(RSVQAResource())
        self.register(CDVQAResource())
        self.register(ISROSACEvaluationResource())

    def register(self, resource: SIHResource) -> None:
        """Register a resource instance."""
        self._resources[resource.resource_id.lower().strip()] = resource

    def unregister(self, resource_id: str) -> Optional[SIHResource]:
        """Unregister a resource by ID."""
        return self._resources.pop(resource_id.lower().strip(), None)

    def get_resource(self, resource_id: str) -> Optional[SIHResource]:
        """Retrieve a registered resource by ID."""
        return self._resources.get(resource_id.lower().strip())

    def list_resources(
        self,
        resource_type: Optional[str] = None,
        available_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """List registered resources with normalized metadata."""
        results = []
        for r in self._resources.values():
            if resource_type and r.resource_type.value != resource_type:
                continue

            meta = r.get_metadata()
            if available_only and meta["availability"] != ResourceAvailability.AVAILABLE.value:
                continue

            results.append(meta)
        return results

    def get_summary(self) -> Dict[str, Any]:
        """Generate high-level status summary across all SIH resources."""
        all_meta = [r.get_metadata() for r in self._resources.values()]
        available_count = sum(1 for m in all_meta if m["availability"] == ResourceAvailability.AVAILABLE.value)
        return {
            "total_registered": len(self._resources),
            "available_count": available_count,
            "resources": all_meta,
        }


# Global Singleton Instance
sih_resource_registry = SIHResourceRegistry()
