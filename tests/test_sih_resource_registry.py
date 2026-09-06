"""
Unit & Integration Tests for SIH Data Resource Registry & Real Sample Materializer (Step 17D).

Tests:
1. Resource discovery (5 explicit SIH26167 resources)
2. Resource types distinction (training dataset, benchmark, ISRO evaluation)
3. Metadata normalization & schema compliance
4. Valid sample -> real file path on disk + materialization state (newly_materialized vs cached vs existing_local)
5. Missing sample -> SampleNotFoundError
6. Missing/unconfigured dataset -> ResourceNotConfiguredError
7. Invalid sample file (0-byte / unreadable) -> InvalidSampleFileError
8. Paired data (CDVQA bi-temporal) -> preserves both T1 & T2 files, ordering, modalities, annotations
9. BigEarthNet pairing & annotations preservation (CORINE labels, query, answer)
10. RSVQA & VRSBench question, caption, and grounding box preservation
11. ISRO / SAC authentic product detection and payload metadata preservation
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from app.resources.sih_registry import (
    ResourceAvailability,
    ResourceType,
    SIHResourceRegistry,
    BigEarthNetResource,
    RSVQAResource,
    VRSBenchResource,
    CDVQAResource,
    ISROSACEvaluationResource,
    SIHResourceError,
    ResourceNotConfiguredError,
    SampleNotFoundError,
    InvalidSampleFileError,
    _materialize_file,
)


class TestSIHResourceMaterialization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="test_sih_mat_")
        cls.images_dir = os.path.join(cls.test_dir, "images")
        cls.mat_output_dir = os.path.join(cls.test_dir, "output")
        os.makedirs(cls.images_dir, exist_ok=True)
        os.makedirs(cls.mat_output_dir, exist_ok=True)

        # 1. Create a mock RSVQA benchmark set
        cls.rsvqa_q = os.path.join(cls.test_dir, "rsvqa_q.json")
        cls.rsvqa_a = os.path.join(cls.test_dir, "rsvqa_a.json")
        with open(cls.rsvqa_q, "w", encoding="utf-8") as f:
            json.dump({
                "questions": [
                    {"id": 101, "img_id": "rsvqa_test_01", "question": "Is there water here?", "type": "presence"}
                ]
            }, f)
        with open(cls.rsvqa_a, "w", encoding="utf-8") as f:
            json.dump({
                "answers": [
                    {"id": 1, "question_id": 101, "answer": "yes"}
                ]
            }, f)

        img1 = Image.new("RGB", (64, 64), color=(50, 100, 150))
        img1.save(os.path.join(cls.images_dir, "rsvqa_test_01.tif"))

        # 2. Create a mock VRSBench benchmark set
        cls.vrs_ann = os.path.join(cls.test_dir, "vrs_ann.json")
        with open(cls.vrs_ann, "w", encoding="utf-8") as f:
            json.dump([
                {
                    "id": "vrs_test_01",
                    "image": "vrs_test_01.tif",
                    "question": "What structure is visible?",
                    "answer": "A bridge over a river.",
                    "caption": "Satellite view of a highway bridge.",
                    "grounding": [{"box": [0.2, 0.2, 0.7, 0.7], "label": "bridge"}]
                }
            ], f)
        img2 = Image.new("RGB", (64, 64), color=(80, 120, 60))
        img2.save(os.path.join(cls.images_dir, "vrs_test_01.tif"))

        # 3. Create a mock CDVQA bi-temporal pair
        cls.cdvqa_ann = os.path.join(cls.test_dir, "cdvqa_pairs.json")
        with open(cls.cdvqa_ann, "w", encoding="utf-8") as f:
            json.dump([
                {
                    "pair_id": "cd_test_01",
                    "image_t1": "cd_t1.tif",
                    "image_t2": "cd_t2.tif",
                    "question": "What changed between T1 and T2?",
                    "answer": "Forest cleared for new construction.",
                    "change_type": "urban_expansion"
                }
            ], f)
        img3_t1 = Image.new("RGB", (64, 64), color=(30, 150, 40))
        img3_t2 = Image.new("RGB", (64, 64), color=(180, 150, 120))
        img3_t1.save(os.path.join(cls.images_dir, "cd_t1.tif"))
        img3_t2.save(os.path.join(cls.images_dir, "cd_t2.tif"))

        # 4. Create an invalid (0-byte) image and a corrupted image
        cls.empty_img = os.path.join(cls.images_dir, "empty_sample.tif")
        with open(cls.empty_img, "wb") as f:
            pass  # 0 bytes

        cls.corrupt_img = os.path.join(cls.images_dir, "corrupt_sample.tif")
        with open(cls.corrupt_img, "wb") as f:
            f.write(b"NOT_A_VALID_TIFF_HEADER_XYZ")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # 1. REGISTRY DISCOVERY & STRUCTURE
    # ------------------------------------------------------------------

    def test_01_registry_discovery(self):
        """Test that exactly the 5 SIH26167 resources are registered."""
        registry = SIHResourceRegistry()
        resources = registry.list_resources()
        self.assertEqual(len(resources), 5)
        resource_ids = {r["resource_id"] for r in resources}
        self.assertEqual(
            resource_ids,
            {"bigearthnet", "vrsbench", "rsvqa", "cdvqa", "isro_sac_evaluation"},
        )

    def test_02_resource_types_distinction(self):
        """Test proper distinction between training datasets, benchmarks, and ISRO resources."""
        registry = SIHResourceRegistry()
        self.assertEqual(
            registry.get_resource("bigearthnet").resource_type,
            ResourceType.TRAINING_ADAPTATION_DATASET,
        )
        self.assertEqual(
            registry.get_resource("vrsbench").resource_type,
            ResourceType.EVALUATION_BENCHMARK,
        )
        self.assertEqual(
            registry.get_resource("rsvqa").resource_type,
            ResourceType.EVALUATION_BENCHMARK,
        )
        self.assertEqual(
            registry.get_resource("cdvqa").resource_type,
            ResourceType.EVALUATION_BENCHMARK,
        )
        self.assertEqual(
            registry.get_resource("isro_sac_evaluation").resource_type,
            ResourceType.ISRO_SAC_EVALUATION_RESOURCE,
        )

    # ------------------------------------------------------------------
    # 2. VALID SAMPLE -> REAL FILE PATH & MATERIALIZATION STATES
    # ------------------------------------------------------------------

    def test_03_valid_sample_to_real_file_path(self):
        """Test that materializing a valid sample produces a real, non-empty file on disk."""
        ben = BigEarthNetResource()
        samples = ben.list_samples(limit=1)
        self.assertGreater(len(samples), 0)

        sample_id = samples[0]["sample_id"]
        obs = ben.materialize_observation(sample_id, output_dir=self.mat_output_dir)

        # Validate real file path exists and is non-empty
        real_path = obs.get("file_path")
        self.assertIsNotNone(real_path)
        self.assertTrue(os.path.isfile(real_path), f"File {real_path} does not exist on disk.")
        self.assertGreater(os.path.getsize(real_path), 0)
        self.assertEqual(obs["source_type"], "sih_resource")
        self.assertEqual(obs["dataset_name"], "BigEarthNet")
        self.assertEqual(obs["sample_id"], sample_id)

    def test_04_materialization_state_distinction(self):
        """Test distinction among 'newly_materialized', 'cached', and 'existing_local'."""
        sample_src = os.path.join(self.images_dir, "rsvqa_test_01.tif")
        isolated_dir = os.path.join(self.test_dir, "state_test")
        os.makedirs(isolated_dir, exist_ok=True)

        # 1. First copy: newly_materialized
        dest_1, state_1 = _materialize_file(sample_src, output_dir=isolated_dir)
        self.assertEqual(state_1, "newly_materialized")
        self.assertTrue(dest_1.exists())

        # 2. Second copy to same target: cached
        dest_2, state_2 = _materialize_file(sample_src, output_dir=isolated_dir)
        self.assertEqual(state_2, "cached")
        self.assertEqual(dest_1, dest_2)

        # 3. Source equals destination: existing_local
        dest_3, state_3 = _materialize_file(str(dest_1), output_dir=isolated_dir)
        self.assertEqual(state_3, "existing_local")

    # ------------------------------------------------------------------
    # 3. MISSING SAMPLE -> ERROR
    # ------------------------------------------------------------------

    def test_05_missing_sample_raises_error(self):
        """Test that requesting a non-existent sample raises SampleNotFoundError."""
        ben = BigEarthNetResource()
        with self.assertRaises(SampleNotFoundError):
            ben.materialize_observation("non_existent_patch_xyz_99999", output_dir=self.mat_output_dir)

        vrs = VRSBenchResource(annotations_path=self.vrs_ann, images_dir=self.images_dir)
        with self.assertRaises(SampleNotFoundError):
            vrs.materialize_observation("unknown_vrs_id_123", output_dir=self.mat_output_dir)

    # ------------------------------------------------------------------
    # 4. MISSING DATASET -> CLEAR CONFIGURATION ERROR
    # ------------------------------------------------------------------

    def test_06_missing_dataset_raises_configuration_error(self):
        """Test that unconfigured or missing datasets raise ResourceNotConfiguredError."""
        unconf_rsvqa = RSVQAResource(
            questions_path="/path/does/not/exist/questions.json",
            answers_path="/path/does/not/exist/answers.json",
            images_dir="/path/does/not/exist/images",
        )
        status, reason, _ = unconf_rsvqa.check_availability()
        self.assertEqual(status, ResourceAvailability.NOT_CONFIGURED)

        with self.assertRaises(ResourceNotConfiguredError) as ctx:
            unconf_rsvqa.materialize_observation("any_id", output_dir=self.mat_output_dir)
        self.assertIn("not available", str(ctx.exception).lower())

        unconf_cdvqa = CDVQAResource(
            annotations_path="/invalid/cdvqa_pairs.json",
            images_dir="/invalid/images",
        )
        with self.assertRaises(ResourceNotConfiguredError):
            unconf_cdvqa.materialize_observation("any_id", output_dir=self.mat_output_dir)

    # ------------------------------------------------------------------
    # 5. INVALID FILE -> REJECTION
    # ------------------------------------------------------------------

    def test_07_invalid_or_zero_byte_file_rejected(self):
        """Test that zero-byte or nonexistent files are rejected with InvalidSampleFileError."""
        # Non-existent file path
        with self.assertRaises(InvalidSampleFileError):
            _materialize_file("/non_existent/path/sample.tif", output_dir=self.mat_output_dir)

        # 0-byte file
        with self.assertRaises(InvalidSampleFileError):
            _materialize_file(self.empty_img, output_dir=self.mat_output_dir)

    # ------------------------------------------------------------------
    # 6. PAIRED INPUT PRESERVES BOTH FILES (CDVQA BI-TEMPORAL)
    # ------------------------------------------------------------------

    def test_08_pair_input_preserves_both_files_and_ordering(self):
        """Test that CDVQA bi-temporal materialization preserves both T1 & T2, ordering, and metadata."""
        cdvqa = CDVQAResource(
            annotations_path=self.cdvqa_ann,
            images_dir=self.images_dir,
        )
        status, _, details = cdvqa.check_availability()
        self.assertEqual(status, ResourceAvailability.AVAILABLE)
        self.assertEqual(details["valid_pairs"], 1)

        pair_obs = cdvqa.materialize_observation("cd_test_01", output_dir=self.mat_output_dir)

        # Validate pair structure
        self.assertEqual(pair_obs["pair_mode"], "bi_temporal")
        self.assertEqual(pair_obs["sample_id"], "cd_test_01")
        self.assertTrue(pair_obs["both_files_verified"])
        self.assertEqual(pair_obs["change_type"], "urban_expansion")
        self.assertEqual(pair_obs["suggested_query"], "What changed between T1 and T2?")
        self.assertEqual(pair_obs["ground_truth_answer"], "forest cleared for new construction.")

        # Validate primary (T1 / pre_change)
        t1 = pair_obs["primary_observation"]
        self.assertEqual(t1["temporal_role"], "pre_change")
        self.assertEqual(t1["order"], 1)
        self.assertTrue(os.path.isfile(t1["file_path"]))
        self.assertGreater(os.path.getsize(t1["file_path"]), 0)

        # Validate companion (T2 / post_change)
        t2 = pair_obs["companion_observation"]
        self.assertEqual(t2["temporal_role"], "post_change")
        self.assertEqual(t2["order"], 2)
        self.assertTrue(os.path.isfile(t2["file_path"]))
        self.assertGreater(os.path.getsize(t2["file_path"]), 0)

        # Verify distinct files
        self.assertNotEqual(t1["file_path"], t2["file_path"])

    # ------------------------------------------------------------------
    # 7. BIGEARTHNET ANNOTATION & SAR PAIRING PRESERVATION
    # ------------------------------------------------------------------

    def test_09_bigearthnet_metadata_and_sar_pairing(self):
        """Test BigEarthNet preserves CORINE labels, question/answer, and SAR pairing flags."""
        ben = BigEarthNetResource()
        samples = ben.list_samples()
        self.assertGreater(len(samples), 0)

        sample = samples[0]
        self.assertIn("labels", sample)
        self.assertIsInstance(sample["labels"], list)
        self.assertGreater(len(sample["labels"]), 0)
        self.assertIn("primary_label", sample)
        self.assertIn("has_s1_sar_pair", sample)
        self.assertIn("suggested_query", sample)

        obs = ben.materialize_observation(sample["sample_id"], output_dir=self.mat_output_dir)
        self.assertEqual(obs["labels"], sample["labels"])
        self.assertEqual(obs["primary_label"], sample["primary_label"])
        self.assertEqual(obs["suggested_query"], sample["suggested_query"])
        self.assertEqual(obs["ground_truth_answer"], sample["ground_truth_answer"])

    # ------------------------------------------------------------------
    # 8. RSVQA & VRSBENCH ANNOTATIONS PRESERVATION
    # ------------------------------------------------------------------

    def test_10_rsvqa_and_vrsbench_annotation_preservation(self):
        """Test that RSVQA questions and VRSBench captions/grounding boxes are fully preserved."""
        # RSVQA
        rsvqa = RSVQAResource(
            questions_path=self.rsvqa_q,
            answers_path=self.rsvqa_a,
            images_dir=self.images_dir,
        )
        obs_rsvqa = rsvqa.materialize_observation("101", output_dir=self.mat_output_dir)
        self.assertEqual(obs_rsvqa["suggested_query"], "Is there water here?")
        self.assertEqual(obs_rsvqa["ground_truth_answer"], "yes")
        self.assertEqual(obs_rsvqa["question_type"], "presence")

        # VRSBench
        vrs = VRSBenchResource(
            annotations_path=self.vrs_ann,
            images_dir=self.images_dir,
        )
        obs_vrs = vrs.materialize_observation("vrs_test_01", output_dir=self.mat_output_dir)
        self.assertEqual(obs_vrs["suggested_query"], "What structure is visible?")
        self.assertEqual(obs_vrs["ground_truth_answer"], "A bridge over a river.")
        self.assertEqual(obs_vrs["caption"], "Satellite view of a highway bridge.")
        self.assertEqual(len(obs_vrs["grounding_boxes"]), 1)

    # ------------------------------------------------------------------
    # 9. ISRO / SAC ADAPTER INTEGRATION & METADATA PRESERVATION
    # ------------------------------------------------------------------

    def test_11_isro_evaluation_resource_materialization(self):
        """Test ISRO / SAC adapter detects genuine GeoTIFF and preserves mission payload headers."""
        isro_res = ISROSACEvaluationResource()
        status, reason, details = isro_res.check_availability()
        self.assertEqual(status, ResourceAvailability.AVAILABLE)
        self.assertGreaterEqual(details["files_found"], 1)

        samples = isro_res.list_samples()
        self.assertGreaterEqual(len(samples), 1)
        sample = samples[0]

        obs = isro_res.materialize_observation(sample["sample_id"], output_dir=self.mat_output_dir)
        self.assertTrue(os.path.isfile(obs["file_path"]))
        self.assertEqual(obs["source_type"], "sih_resource")
        self.assertEqual(obs["dataset_name"], "ISRO / SAC Evaluation Resource")
        self.assertIn("isro_metadata", obs)


    # ------------------------------------------------------------------
    # 10. MATERIALIZATION -> AGENT OBSERVATION VALIDATION
    # ------------------------------------------------------------------

    def test_12_materialized_sih_observation_compatible_with_agent(self):
        """Test that a materialized SIH observation is recognized by validate_analysis_images."""
        from app.main import validate_analysis_images
        ben = BigEarthNetResource()
        samples = ben.list_samples(limit=1)
        self.assertGreater(len(samples), 0)

        obs = ben.materialize_observation(samples[0]["sample_id"], output_dir=self.mat_output_dir)
        validated = validate_analysis_images([obs], input_mode="single_image")
        self.assertEqual(len(validated), 1)
        self.assertTrue(os.path.isfile(validated[0]["file_path"]))


if __name__ == "__main__":
    unittest.main()
