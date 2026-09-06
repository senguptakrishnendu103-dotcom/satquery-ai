"""
Unit, Orchestrator & Integration Tests for SIH Data Resources connected to the Agentic Pipeline (Step 17E).

Verifies the common observation pipeline:
Manual Upload ─────┐
                   │
SIH Data Resource ─┤
                   ↓
          Common Observation
                   ↓
           Input Validation
                   ↓
          AgentOrchestrator
                   ↓
       Specialist Model/Tool
                   ↓
       Evidence + Confidence
                   ↓
          Audit + Result UI

Routing Verification across all 5 SIH resources:
1. BigEarthNet single sample -> SINGLE_IMAGE_VQA / WATER_DETECTION
2. BigEarthNet Sentinel-1 + Sentinel-2 pair -> OPTICAL_SAR_ANALYSIS
3. CDVQA before/after pair -> CHANGE_DETECTION
4. RSVQA sample -> SINGLE_IMAGE_VQA / BUILT_UP_ANALYSIS
5. VRSBench sample -> SINGLE_IMAGE_VQA / OBJECT_GROUNDING
6. ISRO/SAC sample -> SINGLE_IMAGE_VQA / compatible analysis
7. Invariance: AgentOrchestrator remains the sole authority for task routing; no separate analysis engine.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np

import rasterio
from rasterio.transform import from_origin

from app.agent.orchestrator import AgentOrchestrator, agent_orchestrator
from app.resources.sih_registry import (
    BigEarthNetResource,
    RSVQAResource,
    VRSBenchResource,
    CDVQAResource,
    ISROSACEvaluationResource,
)
from app.main import validate_analysis_images


def _write_geotiff(path: str, bands: int = 3, width: int = 128, height: int = 128, crs: str = "EPSG:32633", base_val: int = 100):
    transform = from_origin(13.4050, 52.5200, 10, 10)
    data = np.full((bands, height, width), base_val, dtype=np.uint8)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=bands,
        dtype=np.uint8,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(data)


class TestSIHAgenticPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orchestrator = AgentOrchestrator()
        cls.test_dir = tempfile.mkdtemp(prefix="test_sih_pipeline_")
        cls.images_dir = os.path.join(cls.test_dir, "images")
        cls.out_dir = os.path.join(cls.test_dir, "uploads")
        os.makedirs(cls.images_dir, exist_ok=True)
        os.makedirs(cls.out_dir, exist_ok=True)

        # 1. RSVQA Benchmark mock assets
        cls.rsvqa_q = os.path.join(cls.test_dir, "rsvqa_q.json")
        cls.rsvqa_a = os.path.join(cls.test_dir, "rsvqa_a.json")
        with open(cls.rsvqa_q, "w", encoding="utf-8") as f:
            json.dump({
                "questions": [
                    {"id": 201, "img_id": "rsvqa_img_01", "question": "What land cover features and objects are visible in this scene?", "type": "presence"},
                    {"id": 202, "img_id": "rsvqa_img_01", "question": "What type of area is this, rural or urban?", "type": "rural_urban"}
                ]
            }, f)
        with open(cls.rsvqa_a, "w", encoding="utf-8") as f:
            json.dump({
                "answers": [
                    {"id": 1, "question_id": 201, "answer": "forest and agricultural fields"},
                    {"id": 2, "question_id": 202, "answer": "rural"}
                ]
            }, f)
        _write_geotiff(os.path.join(cls.images_dir, "rsvqa_img_01.tif"), bands=3, base_val=75)

        # 2. VRSBench Benchmark mock assets
        cls.vrs_ann = os.path.join(cls.test_dir, "vrs_ann.json")
        with open(cls.vrs_ann, "w", encoding="utf-8") as f:
            json.dump([
                {
                    "id": "vrs_pipe_01",
                    "image": "vrs_img_01.tif",
                    "question": "What structure is visible in this high-resolution scene?",
                    "answer": "A port terminal with cargo containers.",
                    "caption": "High-resolution satellite view of an active shipping port.",
                    "grounding": [{"box": [0.1, 0.1, 0.8, 0.8], "label": "port"}]
                }
            ], f)
        _write_geotiff(os.path.join(cls.images_dir, "vrs_img_01.tif"), bands=3, base_val=90)

        # 3. CDVQA Benchmark mock assets (valid georeferenced GeoTIFF pairs)
        cls.cdvqa_ann = os.path.join(cls.test_dir, "cdvqa_ann.json")
        with open(cls.cdvqa_ann, "w", encoding="utf-8") as f:
            json.dump([
                {
                    "pair_id": "cd_pipe_01",
                    "image_t1": "cd_t1.tif",
                    "image_t2": "cd_t2.tif",
                    "question": "What changed between these two dates across the urban and forest areas?",
                    "answer": "vegetation cleared for road construction.",
                    "change_type": "deforestation"
                }
            ], f)
        _write_geotiff(os.path.join(cls.images_dir, "cd_t1.tif"), bands=3, base_val=60)
        _write_geotiff(os.path.join(cls.images_dir, "cd_t2.tif"), bands=3, base_val=180)

        # 4. BigEarthNet with SAR Pair mock assets
        cls.ben_manifest = os.path.join(cls.test_dir, "BigEarthNet.txt")
        ben_s2_name = "S2A_MSIL2A_20170613T101031_N0205_R022_T32TMR_44_12.tif"
        ben_s1_name = "S1A_MSIL2A_20170613T101031_N0205_R022_T32TMR_44_12.tif"

        _write_geotiff(os.path.join(cls.images_dir, ben_s2_name), bands=3, base_val=80)
        _write_geotiff(os.path.join(cls.images_dir, ben_s1_name), bands=2, base_val=120)

        with open(cls.ben_manifest, "w", encoding="utf-8") as f:
            f.write(f"S2A_MSIL2A_20170613T101031_N0205_R022_T32TMR_44_12 | Mixed forest, Water bodies | images/{ben_s2_name}\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. BIGEARTHNET SINGLE SAMPLE ROUTING & EXECUTION
    # -------------------------------------------------------------------------

    def test_01_bigearthnet_single_sample_vqa_routing(self):
        """Verify BigEarthNet single sample routes to SINGLE_IMAGE_VQA specialist."""
        ben = BigEarthNetResource(manifest_path=self.ben_manifest, data_dir=self.test_dir)
        samples = ben.list_samples(limit=1)
        self.assertGreater(len(samples), 0)

        obs = ben.materialize_observation(samples[0]["sample_id"], output_dir=self.out_dir)
        validated = validate_analysis_images([obs], input_mode="single_image")

        query = "What type of terrain and land cover features are present in this scene?"
        result = self.orchestrator.process_query(
            query=query,
            images=validated,
            input_mode="single_image",
        )

        self.assertEqual(result["task"], "SINGLE_IMAGE_VQA")
        self.assertEqual(result["selected_model"]["name"], "SatQuery Remote-Sensing VQA")
        self.assertIn("execution_summary", result)
        self.assertIn("visual_evidence", result)

    def test_02_bigearthnet_single_sample_water_spectral_routing(self):
        """Verify BigEarthNet single sample with water query routes to WATER_DETECTION tool."""
        ben = BigEarthNetResource(manifest_path=self.ben_manifest, data_dir=self.test_dir)
        samples = ben.list_samples(limit=1)
        obs = ben.materialize_observation(samples[0]["sample_id"], output_dir=self.out_dir)
        validated = validate_analysis_images([obs], input_mode="single_image")

        query = "Is there water in this image? Compute NDWI water detection mask"
        result = self.orchestrator.process_query(
            query=query,
            images=validated,
            input_mode="single_image",
        )

        self.assertEqual(result["task"], "WATER_DETECTION")
        self.assertEqual(result["selected_model"]["name"], "Hydro-NDWI Water Segmentation Tool")
        self.assertIn("NDWI", result["answer"])

    # -------------------------------------------------------------------------
    # 2. BIGEARTHNET SENTINEL-1 + SENTINEL-2 PAIR ROUTING & EXECUTION
    # -------------------------------------------------------------------------

    def test_03_bigearthnet_s1_s2_pair_optical_sar_routing(self):
        """Verify BigEarthNet S1+S2 pair routes to OPTICAL_SAR_ANALYSIS multimodal tool."""
        ben = BigEarthNetResource(manifest_path=self.ben_manifest, data_dir=self.test_dir)
        samples = ben.list_samples(limit=1)
        sample_id = samples[0]["sample_id"]

        pair_data = ben.materialize_observation(sample_id, output_dir=self.out_dir, pair_mode=True)
        self.assertEqual(pair_data["pair_mode"], "optical_sar")
        self.assertTrue(pair_data["both_files_verified"])

        obs_optical = pair_data["primary_observation"]
        obs_sar = pair_data["companion_observation"]
        self.assertEqual(obs_optical["modality"], "optical")
        self.assertEqual(obs_sar["modality"], "sar")

        validated = validate_analysis_images([obs_optical, obs_sar], input_mode="optical_sar")
        self.assertEqual(len(validated), 2)

        query = "Compare the optical and SAR images to verify water bodies and built-up structures"
        result = self.orchestrator.process_query(
            query=query,
            images=validated,
            input_mode="optical_sar",
        )

        self.assertEqual(result["task"], "OPTICAL_SAR_ANALYSIS")
        self.assertEqual(
            result["selected_model"]["name"],
            "Deterministic Optical+SAR Spectral-Radar Fusion Pipeline",
        )
        self.assertIn("Optical + SAR multimodal cross-analysis", result["answer"])

    # -------------------------------------------------------------------------
    # 3. CDVQA BEFORE/AFTER PAIR ROUTING & EXECUTION
    # -------------------------------------------------------------------------

    def test_04_cdvqa_bitemporal_pair_change_detection_routing(self):
        """Verify CDVQA bi-temporal pair routes to CHANGE_DETECTION specialist model."""
        cdvqa = CDVQAResource(annotations_path=self.cdvqa_ann, images_dir=self.images_dir)
        pair_data = cdvqa.materialize_observation("cd_pipe_01", output_dir=self.out_dir)

        self.assertEqual(pair_data["pair_mode"], "bi_temporal")
        obs_t1 = pair_data["primary_observation"]
        obs_t2 = pair_data["companion_observation"]
        self.assertEqual(obs_t1["order"], 1)
        self.assertEqual(obs_t2["order"], 2)

        validated = validate_analysis_images([obs_t1, obs_t2], input_mode="bi_temporal")
        self.assertEqual(len(validated), 2)

        query = pair_data["suggested_query"]
        result = self.orchestrator.process_query(
            query=query,
            images=validated,
            input_mode="bi_temporal",
        )

        self.assertEqual(result["task"], "CHANGE_DETECTION")
        self.assertEqual(result["selected_model"]["name"], "SatQuery Bi-Temporal Change Detector")
        self.assertIn("Bi-temporal", result["answer"])
        self.assertGreater(len(result["visual_evidence"]), 0)

    # -------------------------------------------------------------------------
    # 4. RSVQA SAMPLE ROUTING & EXECUTION
    # -------------------------------------------------------------------------

    def test_05_rsvqa_sample_vqa_routing(self):
        """Verify RSVQA sample routes to SINGLE_IMAGE_VQA specialist."""
        rsvqa = RSVQAResource(
            questions_path=self.rsvqa_q,
            answers_path=self.rsvqa_a,
            images_dir=self.images_dir,
        )
        obs = rsvqa.materialize_observation("201", output_dir=self.out_dir)
        validated = validate_analysis_images([obs], input_mode="single_image")

        query = obs["suggested_query"]
        result = self.orchestrator.process_query(
            query=query,
            images=validated,
            input_mode="single_image",
        )

        self.assertEqual(result["task"], "SINGLE_IMAGE_VQA")
        self.assertEqual(result["selected_model"]["name"], "SatQuery Remote-Sensing VQA")
        self.assertIn("execution_summary", result)

    # -------------------------------------------------------------------------
    # 5. VRSBENCH SAMPLE MULTI-TASK ROUTING & EXECUTION
    # -------------------------------------------------------------------------

    def test_06_vrsbench_sample_vqa_and_grounding_routing(self):
        """Verify VRSBench sample routes correctly based on query (VQA vs Grounding)."""
        vrs = VRSBenchResource(annotations_path=self.vrs_ann, images_dir=self.images_dir)
        obs = vrs.materialize_observation("vrs_pipe_01", output_dir=self.out_dir)
        validated = validate_analysis_images([obs], input_mode="single_image")

        # 1. VQA Query
        vqa_query = obs["suggested_query"]
        res_vqa = self.orchestrator.process_query(
            query=vqa_query,
            images=validated,
            input_mode="single_image",
        )
        self.assertEqual(res_vqa["task"], "SINGLE_IMAGE_VQA")

        # 2. Grounding Query
        ground_query = "Where is the port terminal located in this scene?"
        res_ground = self.orchestrator.process_query(
            query=ground_query,
            images=validated,
            input_mode="single_image",
        )
        self.assertEqual(res_ground["task"], "OBJECT_GROUNDING")
        self.assertEqual(res_ground["selected_model"]["name"], "SatQuery Text-Guided RS Grounder")

    # -------------------------------------------------------------------------
    # 6. ISRO / SAC SAMPLE ROUTING & EXECUTION
    # -------------------------------------------------------------------------

    def test_07_isro_sac_sample_routing(self):
        """Verify authentic ISRO / SAC sample routes to compatible analysis pipeline."""
        isro_res = ISROSACEvaluationResource()
        status, _, _ = isro_res.check_availability()
        self.assertEqual(status.value, "AVAILABLE")

        samples = isro_res.list_samples(limit=1)
        self.assertGreater(len(samples), 0)

        obs = isro_res.materialize_observation(samples[0]["sample_id"], output_dir=self.out_dir)
        validated = validate_analysis_images([obs], input_mode="single_image")

        query = "Identify vegetation density, water features, and built-up land use in this scene."
        result = self.orchestrator.process_query(
            query=query,
            images=validated,
            input_mode="single_image",
        )

        self.assertIn(result["task"], ["SINGLE_IMAGE_VQA", "WATER_DETECTION", "LAND_COVER_CLASSIFICATION"])
        self.assertIn("execution_summary", result)
        self.assertIn("selected_model", result)

    # -------------------------------------------------------------------------
    # 7. INVARIANCE & ARCHITECTURAL INTEGRITY
    # -------------------------------------------------------------------------

    def test_08_common_pipeline_invariance(self):
        """Verify that SIH observations and Manual Upload observations follow the exact same contract."""
        ben = BigEarthNetResource(manifest_path=self.ben_manifest, data_dir=self.test_dir)
        samples = ben.list_samples(limit=1)
        sih_obs = ben.materialize_observation(samples[0]["sample_id"], output_dir=self.out_dir)

        # Keys required by the common observation contract
        contract_keys = ["id", "filename", "file_path", "local_path", "source_type", "ingestion_status"]
        for key in contract_keys:
            self.assertIn(key, sih_obs)
            self.assertIsNotNone(sih_obs[key])

        # Verify AgentOrchestrator rejects invalid input_mode identically
        with self.assertRaises(ValueError):
            self.orchestrator.process_query(
                query="What is here?",
                images=[sih_obs],
                input_mode="invalid_unsupported_mode",
            )


if __name__ == "__main__":
    unittest.main()
