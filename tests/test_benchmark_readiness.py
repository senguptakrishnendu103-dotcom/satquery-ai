"""
Tests for RSVQA, VRSBench, CDVQA, and BigEarthNet Benchmark Readiness.
"""

import json
import os
import shutil
import tempfile
import unittest

from training.benchmarks import RSVQADataset, VRSBenchDataset, CDVQADataset
from training.dataset import BigEarthNetDataset


class TestBenchmarkReadiness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="test_benchmarks_")
        cls.images_dir = os.path.join(cls.test_dir, "images")
        os.makedirs(cls.images_dir, exist_ok=True)

        # 1. Mock RSVQA JSON files
        cls.rsvqa_q_path = os.path.join(cls.test_dir, "rsvqa_questions.json")
        cls.rsvqa_a_path = os.path.join(cls.test_dir, "rsvqa_answers.json")

        rsvqa_q = {
            "questions": [
                {"id": 101, "img_id": "patch_101", "question": "Is there a river in this scene?", "type": "presence"},
                {"id": 102, "img_id": "patch_102", "question": "What is the dominant land cover?", "type": "land_cover"},
            ]
        }
        rsvqa_a = {
            "answers": [
                {"id": 1, "question_id": 101, "answer": "yes"},
                {"id": 2, "question_id": 102, "answer": "forest"},
            ]
        }
        with open(cls.rsvqa_q_path, "w", encoding="utf-8") as f:
            json.dump(rsvqa_q, f)
        with open(cls.rsvqa_a_path, "w", encoding="utf-8") as f:
            json.dump(rsvqa_a, f)

        # 2. Mock VRSBench JSON file
        cls.vrsbench_path = os.path.join(cls.test_dir, "vrsbench_annotations.json")
        vrsbench_data = [
            {
                "id": "vrs_001",
                "image": "vrs_001.tif",
                "conversations": [
                    {"from": "human", "value": "Where is the airport runway located?"},
                    {"from": "gpt", "value": "The runway is located in the central northern area."},
                ],
                "caption": "An aerial observation showing an active airport and taxiway.",
                "grounding": [{"box": [0.1, 0.2, 0.8, 0.9], "label": "runway"}],
            }
        ]
        with open(cls.vrsbench_path, "w", encoding="utf-8") as f:
            json.dump(vrsbench_data, f)

        # 3. Mock CDVQA JSON file
        cls.cdvqa_path = os.path.join(cls.test_dir, "cdvqa_pairs.json")
        cdvqa_data = [
            {
                "pair_id": "cd_pair_501",
                "image_t1": "scene_2020.tif",
                "image_t2": "scene_2024.tif",
                "question": "What change occurred in the forested area?",
                "answer": "Deforestation and newly constructed residential buildings.",
                "change_type": "urban_expansion",
            }
        ]
        with open(cls.cdvqa_path, "w", encoding="utf-8") as f:
            json.dump(cdvqa_data, f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_rsvqa_loader(self):
        dataset = RSVQADataset(
            images_dir=self.images_dir,
            questions_path=self.rsvqa_q_path,
            answers_path=self.rsvqa_a_path,
        )
        self.assertEqual(len(dataset), 2)
        sample = dataset[0]
        self.assertEqual(sample["question_id"], "101")
        self.assertEqual(sample["question"], "Is there a river in this scene?")
        self.assertEqual(sample["answer"], "yes")
        self.assertEqual(sample["question_type"], "presence")

    def test_02_vrsbench_loader(self):
        dataset = VRSBenchDataset(
            images_dir=self.images_dir,
            annotations_path=self.vrsbench_path,
        )
        self.assertEqual(len(dataset), 1)
        sample = dataset[0]
        self.assertEqual(sample["sample_id"], "vrs_001")
        self.assertEqual(sample["question"], "Where is the airport runway located?")
        self.assertIn("airport", sample["caption"])
        self.assertEqual(len(sample["grounding_boxes"]), 1)

    def test_03_cdvqa_loader(self):
        dataset = CDVQADataset(
            images_dir=self.images_dir,
            annotations_path=self.cdvqa_path,
        )
        self.assertEqual(len(dataset), 1)
        sample = dataset[0]
        self.assertEqual(sample["pair_id"], "cd_pair_501")
        self.assertIn("scene_2020.tif", sample["image_t1_path"])
        self.assertIn("scene_2024.tif", sample["image_t2_path"])
        self.assertEqual(sample["change_type"], "urban_expansion")

    def test_04_bigearthnet_loader_smoke(self):
        from training.dataset import create_sample_bigearthnet_dataset, load_bigearthnet_manifest
        manifest_path = os.path.join(self.test_dir, "BigEarthNet.txt")
        create_sample_bigearthnet_dataset(manifest_path, self.images_dir, num_samples=3)
        samples = load_bigearthnet_manifest(manifest_path, data_dir=self.images_dir)
        self.assertEqual(len(samples), 3)
        s = samples[0]
        self.assertIsNotNone(s.question)
        self.assertIsNotNone(s.answer)
        self.assertIsNotNone(s.primary_label)


if __name__ == "__main__":
    unittest.main()
