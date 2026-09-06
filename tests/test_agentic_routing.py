"""
Unit and Integration Tests for SatQuery AI Agentic Orchestration and Routing.

Validates:
1. Input validation before routing.
2. Single-image vs pair-input discrimination.
3. Optical vs SAR vs multimodal vs temporal modality detection.
4. Correct model and tool selection across all specialist categories:
   - "Is there water in this image?" -> WATER_DETECTION (WaterBodyDetectionTool)
   - "What is in this image?" -> SINGLE_IMAGE_VQA (RemoteSensingVQAModel)
   - "Where is the ship?" -> OBJECT_GROUNDING (TextGuidedGroundingModel)
   - "What changed between these images?" -> CHANGE_DETECTION (BiTemporalChangeDetectionModel)
   - "Compare the optical and SAR images" -> OPTICAL_SAR_ANALYSIS (OpticalSARFusionModel)
5. Execution metadata audit trail and error handling.
"""

import os
import unittest
import numpy as np
from PIL import Image

from app.agent.query_classifier import QueryClassifier
from app.agent.orchestrator import AgentOrchestrator, agent_orchestrator
from app.models.registry import ModelRegistry, registry_instance


class TestAgenticRoutingAndOrchestration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classifier = QueryClassifier()
        cls.orchestrator = AgentOrchestrator()
        
        # Create test assets
        cls.test_dir = os.path.join("app", "static", "uploads", "test_routing")
        os.makedirs(cls.test_dir, exist_ok=True)
        
        cls.optical_path = os.path.join(cls.test_dir, "test_optical.png")
        cls.sar_path = os.path.join(cls.test_dir, "test_sar.png")
        
        # Synthetic optical image
        img_opt = Image.new("RGB", (256, 256), color=(60, 140, 70))
        img_opt.save(cls.optical_path)
        
        # Synthetic SAR image
        img_sar = Image.new("L", (256, 256), color=128)
        img_sar.save(cls.sar_path)
        
        cls.optical_obs = {
            "file_path": cls.optical_path,
            "modality": "optical",
            "acquisition_date": "2024-01-15",
            "satellite_id": "Sentinel-2A",
        }
        
        cls.optical_obs_2026 = {
            "file_path": cls.optical_path,
            "modality": "optical",
            "acquisition_date": "2026-03-20",
            "satellite_id": "Sentinel-2B",
        }
        
        cls.sar_obs = {
            "file_path": cls.sar_path,
            "modality": "sar",
            "acquisition_date": "2024-01-15",
            "satellite_id": "Sentinel-1A",
        }

    # =========================================================================
    # 1. INPUT VALIDATION TESTS
    # =========================================================================

    def test_validate_empty_query(self):
        with self.assertRaises(ValueError):
            self.orchestrator.process_query(
                query="",
                images=[self.optical_obs],
                input_mode="single_image",
            )

    def test_validate_empty_images(self):
        with self.assertRaises(ValueError):
            self.orchestrator.process_query(
                query="What is in this image?",
                images=[],
                input_mode="single_image",
            )

    def test_validate_invalid_input_mode(self):
        with self.assertRaises(ValueError):
            self.orchestrator.process_query(
                query="What is in this image?",
                images=[self.optical_obs],
                input_mode="invalid_mode_xyz",
            )

    def test_validate_mismatched_observation_count_bi_temporal(self):
        # Bi-temporal requires 2 observations
        with self.assertRaises(ValueError):
            self.orchestrator.process_query(
                query="What changed between these images?",
                images=[self.optical_obs],
                input_mode="bi_temporal",
            )

    def test_validate_mismatched_observation_count_optical_sar(self):
        # Optical + SAR requires 2 observations
        with self.assertRaises(ValueError):
            self.orchestrator.process_query(
                query="Compare optical and SAR images",
                images=[self.optical_obs],
                input_mode="optical_sar",
            )

    # =========================================================================
    # 2. QUERY CLASSIFICATION ROUTING EXAMPLES
    # =========================================================================

    def test_routing_water_detection(self):
        # "Is there water in this image?" -> WATER_DETECTION
        res = self.classifier.classify(
            query="Is there water in this image?",
            num_images=1,
            modalities=["optical"],
            input_mode="single_image",
        )
        self.assertEqual(res["task"], "WATER_DETECTION")

    def test_routing_vqa(self):
        # "What is in this image?" -> SINGLE_IMAGE_VQA
        res = self.classifier.classify(
            query="What is in this image?",
            num_images=1,
            modalities=["optical"],
            input_mode="single_image",
        )
        self.assertEqual(res["task"], "SINGLE_IMAGE_VQA")

    def test_routing_grounding(self):
        # "Where is the ship?" -> OBJECT_GROUNDING
        res = self.classifier.classify(
            query="Where is the ship?",
            num_images=1,
            modalities=["optical"],
            input_mode="single_image",
        )
        self.assertEqual(res["task"], "OBJECT_GROUNDING")

    def test_routing_change_detection(self):
        # "What changed between these images?" -> CHANGE_DETECTION
        res = self.classifier.classify(
            query="What changed between these images?",
            num_images=2,
            modalities=["optical", "optical"],
            input_mode="bi_temporal",
        )
        self.assertEqual(res["task"], "CHANGE_DETECTION")

    def test_routing_optical_sar_analysis(self):
        # "Compare the optical and SAR images" -> OPTICAL_SAR_ANALYSIS
        res = self.classifier.classify(
            query="Compare the optical and SAR images",
            num_images=2,
            modalities=["optical", "sar"],
            input_mode="optical_sar",
        )
        self.assertEqual(res["task"], "OPTICAL_SAR_ANALYSIS")

    # =========================================================================
    # 3. END-TO-END ORCHESTRATION & TOOL SELECTION
    # =========================================================================

    def test_orchestration_water_specialist_execution(self):
        res = self.orchestrator.process_query(
            query="Is there water in this image?",
            images=[self.optical_obs],
            input_mode="single_image",
        )
        self.assertEqual(res["task"], "WATER_DETECTION")
        self.assertEqual(res["selected_model"]["name"], "Hydro-NDWI Water Segmentation Tool")
        self.assertIn("NDWI", res["answer"])
        self.assertIn("execution_summary", res)
        self.assertIn("visual_evidence", res)

    def test_orchestration_grounding_specialist_execution(self):
        res = self.orchestrator.process_query(
            query="Where is the ship?",
            images=[self.optical_obs],
            input_mode="single_image",
        )
        self.assertEqual(res["task"], "OBJECT_GROUNDING")
        self.assertEqual(res["selected_model"]["name"], "SatQuery Text-Guided RS Grounder")
        self.assertIn("visual_evidence", res)
        self.assertIn("execution_summary", res)

    def test_orchestration_change_detection_execution(self):
        res = self.orchestrator.process_query(
            query="What changed between these images?",
            images=[self.optical_obs, self.optical_obs_2026],
            input_mode="bi_temporal",
        )
        self.assertEqual(res["task"], "CHANGE_DETECTION")
        self.assertEqual(res["selected_model"]["name"], "SatQuery Bi-Temporal Change Detector")
        self.assertIn("Bi-temporal", res["answer"])
        self.assertIn("execution_summary", res)

    def test_orchestration_optical_sar_execution(self):
        res = self.orchestrator.process_query(
            query="Compare the optical and SAR images",
            images=[self.optical_obs, self.sar_obs],
            input_mode="optical_sar",
        )
        self.assertEqual(res["task"], "OPTICAL_SAR_ANALYSIS")
        self.assertEqual(res["selected_model"]["name"], "Deterministic Optical+SAR Spectral-Radar Fusion Pipeline")
        self.assertIn("Optical + SAR", res["answer"])
        self.assertIn("execution_summary", res)

    def test_orchestration_preserves_contract_fields(self):
        res = self.orchestrator.process_query(
            query="What is in this image?",
            images=[self.optical_obs],
            input_mode="single_image",
        )
        required_keys = [
            "query",
            "task",
            "input_mode",
            "selected_model",
            "processing_steps",
            "answer",
            "confidence",
            "visual_evidence",
            "execution_summary",
        ]
        for key in required_keys:
            self.assertIn(key, res, f"Missing required response key: {key}")
            
        self.assertIsInstance(res["processing_steps"], list)
        self.assertIsInstance(res["selected_model"], dict)
        self.assertIsInstance(res["execution_summary"], dict)
        if res["confidence"] is not None:
            self.assertGreaterEqual(res["confidence"], 0.0)
            self.assertLessEqual(res["confidence"], 100.0)


if __name__ == "__main__":
    unittest.main()
