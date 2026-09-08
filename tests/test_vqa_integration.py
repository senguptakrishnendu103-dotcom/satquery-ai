import os
import unittest
from PIL import Image
import tempfile

from app.agent.orchestrator import agent_orchestrator
from app.models.vqa_model import RemoteSensingVQAModel
from app.utils.metadata_extractor import MetadataExtractor


class TestVQAIntegration(unittest.TestCase):
    def setUp(self):
        # Create a simple test image
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img = Image.new("RGB", (128, 128), color=(34, 139, 34)) # Forest green
        img.save(self.temp_file.name, format="PNG")
        self.temp_file.close()

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_vqa_model_direct_execution(self):
        model = RemoteSensingVQAModel()
        obs = {
            "file_path": self.temp_file.name,
            "filename": os.path.basename(self.temp_file.name),
            "modality": "optical",
        }
        res = model.execute(
            images=[obs],
            query="What color is dominant in this scene?",
            metadata={},
        )
        self.assertIn("answer", res)
        self.assertIsInstance(res["answer"], str)
        self.assertTrue(len(res["answer"].strip()) > 0)
        self.assertIn("### Remote-Sensing Intelligence & Insights", res["answer"])
        self.assertIn("* **Primary Feature Observed**", res["answer"])
        self.assertIn("* **Spectral & Visual Evidence**", res["answer"])
        self.assertIn("execution_details", res)
        self.assertEqual(res["execution_details"]["execution_status"], "success")
        self.assertEqual(res["execution_details"]["model_id"], model._runtime.model_id)

    def test_vqa_orchestrator_integration(self):
        obs = {
            "file_path": self.temp_file.name,
            "filename": os.path.basename(self.temp_file.name),
            "modality": "optical",
        }
        res = agent_orchestrator.process_query(
            query="What features are present in this satellite scene?",
            images=[obs],
            input_mode="single_image",
        )
        self.assertEqual(res["task"], "SINGLE_IMAGE_VQA")
        self.assertIn("answer", res)
        self.assertTrue(len(res["answer"].strip()) > 0)
        self.assertIn("selected_model", res)
        self.assertIn("execution_summary", res)
        self.assertEqual(res["execution_summary"]["execution_status"], "completed")

    def test_vqa_missing_image_fails_explicitly(self):
        model = RemoteSensingVQAModel()
        obs = {
            "file_path": "non_existent_file_path.tif",
            "filename": "non_existent.tif",
            "modality": "optical",
        }
        with self.assertRaises(Exception):
            model.execute(
                images=[obs],
                query="What is in this image?",
                metadata={},
            )


if __name__ == "__main__":
    unittest.main()
