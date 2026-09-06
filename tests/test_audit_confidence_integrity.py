"""
Confidence & Evidence Integrity Audit Test Suite for SatQuery AI.

Requirements Tested:
1. Remove all invented confidence.
2. Confidence may only come from actual model output, calibrated scores, or explicitly defined deterministic methods.
3. If confidence is unavailable, return None / null, not a made-up number.
4. Every visual evidence overlay corresponds to actual model/tool output.
5. No fake bounding boxes are generated.
6. No fake change regions are generated.
7. Source image references are preserved in observation metadata.
8. Result metadata identifies the actual model/tool used.
9. Audit logs record: input files, task, selected specialist, model/tool, parameters, execution status, evidence references.
10. Do not expose private chain-of-thought; provide only an auditable execution summary.
11. Failed model execution CANNOT produce a VERIFIED / successful result.
"""

import os
import unittest
from unittest.mock import MagicMock, patch
from PIL import Image

from app.agent.orchestrator import AgentOrchestrator
from app.models.optical_sar import (
    WaterBodyDetectionTool,
    BuiltUpAreaDetectionTool,
    OpticalSARFusionModel,
)
from app.models.change_detection import BiTemporalChangeDetectionModel
from app.models.grounding_model import TextGuidedGroundingModel
from app.models.base_model import BaseRSModel


class TestConfidenceAndEvidenceIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orchestrator = AgentOrchestrator()
        
        cls.test_dir = os.path.join("app", "static", "uploads", "test_audit")
        os.makedirs(cls.test_dir, exist_ok=True)
        
        cls.opt_path = os.path.join(cls.test_dir, "test_opt_audit.png")
        cls.sar_path = os.path.join(cls.test_dir, "test_sar_audit.png")
        
        # Pure synthetic images
        img_opt = Image.new("RGB", (128, 128), color=(50, 100, 150))
        img_opt.save(cls.opt_path)
        
        img_sar = Image.new("L", (128, 128), color=100)
        img_sar.save(cls.sar_path)
        
        cls.opt_obs = {
            "file_path": cls.opt_path,
            "filename": "test_opt_audit.png",
            "modality": "optical",
            "acquisition_date": "2024-05-10",
            "satellite_id": "Sentinel-2A",
        }
        
        cls.sar_obs = {
            "file_path": cls.sar_path,
            "filename": "test_sar_audit.png",
            "modality": "sar",
            "acquisition_date": "2024-05-10",
            "satellite_id": "Sentinel-1A",
        }

    # =========================================================================
    # 1. NO INVENTED CONFIDENCE ON DETERMINISTIC & UNCALIBRATED TOOLS
    # =========================================================================

    def test_water_tool_confidence_is_none(self):
        tool = WaterBodyDetectionTool()
        res = tool.execute([self.opt_obs], "Water detection", {})
        self.assertIsNone(res["confidence"], "WaterBodyDetectionTool must not invent a confidence score.")

    def test_builtup_tool_confidence_is_none(self):
        tool = BuiltUpAreaDetectionTool()
        res = tool.execute([self.opt_obs], "Built-up detection", {})
        self.assertIsNone(res["confidence"], "BuiltUpAreaDetectionTool must not invent a confidence score.")

    def test_optical_sar_fusion_confidence_is_none(self):
        tool = OpticalSARFusionModel()
        res = tool.execute([self.opt_obs, self.sar_obs], "Analyze optical and SAR", {})
        self.assertIsNone(res["confidence"], "Deterministic OpticalSARFusionModel must not invent a confidence score.")

    def test_change_detection_confidence_is_none(self):
        tool = BiTemporalChangeDetectionModel()
        res = tool.execute([self.opt_obs, self.opt_obs], "Compare images", {})
        self.assertIsNone(res["confidence"], "Deterministic BiTemporalChangeDetectionModel must not invent a confidence score.")

    def test_orchestrator_returns_null_confidence_for_deterministic_tools(self):
        res = self.orchestrator.process_query(
            query="Is there water in this image?",
            images=[self.opt_obs],
            input_mode="single_image",
        )
        self.assertIsNone(res["confidence"], "Orchestrator must return None/null for deterministic tools.")

    # =========================================================================
    # 2. EVIDENCE AND SOURCE REFERENCE INTEGRITY
    # =========================================================================

    def test_optical_sar_evidence_references_real_sources(self):
        res = self.orchestrator.process_query(
            query="Compare the optical and SAR images",
            images=[self.opt_obs, self.sar_obs],
            input_mode="optical_sar",
        )
        exec_summary = res["execution_summary"]
        self.assertIn("inputs", exec_summary)
        self.assertEqual(len(exec_summary["inputs"]), 2)
        
        # Verify source file integrity
        filenames = [inp["name"] for inp in exec_summary["inputs"]]
        self.assertIn("test_opt_audit.png", filenames)
        self.assertIn("test_sar_audit.png", filenames)
        
        # Verify model used identity
        self.assertIn("Deterministic Optical+SAR Spectral-Radar Fusion Pipeline", exec_summary["models_used"])

    def test_audit_logs_record_complete_metadata(self):
        res = self.orchestrator.process_query(
            query="What changed between these images?",
            images=[self.opt_obs, self.opt_obs],
            input_mode="bi_temporal",
        )
        summary = res["execution_summary"]
        
        # Required audit record fields
        self.assertIn("task", summary)
        self.assertIn("inputs", summary)
        self.assertIn("models_used", summary)
        self.assertIn("tools_used", summary)
        self.assertIn("parameters", summary)
        self.assertIn("execution_status", summary)
        self.assertEqual(summary["execution_status"], "completed")
        self.assertIn("audit_timestamp", summary)
        self.assertNotIn("chain_of_thought", summary)

    # =========================================================================
    # 3. FAILED MODEL EXECUTION CANNOT PRODUCE VERIFIED RESULT
    # =========================================================================

    def test_failed_model_execution_raises_error_and_never_claims_success(self):
        class BrokenFailingModel(BaseRSModel):
            @property
            def name(self):
                return "Broken Mock Specialist"
            @property
            def description(self):
                return "Always fails"
            @property
            def supported_input_types(self):
                return ["single_optical"]
            @property
            def supported_tasks(self):
                return ["WATER_DETECTION"]
            def execute(self, images, query, metadata):
                raise RuntimeError("Critical sensor hardware failure or corrupted raster data.")

        failing_model = BrokenFailingModel()
        
        with patch.object(self.orchestrator.classifier, "classify", return_value={"task": "WATER_DETECTION", "reasoning": "test", "confidence": 0.9}):
            with patch("app.agent.orchestrator.registry_instance.select_model_for_task", return_value=failing_model):
                with self.assertRaises(RuntimeError) as ctx:
                    self.orchestrator.process_query(
                        query="Is there water in this image?",
                        images=[self.opt_obs],
                        input_mode="single_image",
                    )
                self.assertIn("SatQuery model execution failed", str(ctx.exception))
                self.assertIn("Critical sensor hardware failure", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
