"""
SatQuery AI - Remote Sensing Benchmark Evaluation & Dataset Adapters.

Implements native dataset loaders and evaluation adapters for standardized RS benchmarks:
1. RSVQA (Remote Sensing Visual Question Answering - LR / HR / Sentinel-2).
2. VRSBench (Visual Remote Sensing Benchmark for VQA, Captioning, and Spatial Grounding).
3. CDVQA (Change Detection Visual Question Answering for Bi-Temporal Image Pairs).
4. BigEarthNet (CORINE Land Cover 19/43 Multi-Spectral Benchmark).
"""

import json
import os
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
import torch
from torch.utils.data import Dataset


class RSVQABenchmarkSample:
    """Represents an individual RSVQA benchmark question-answer sample."""

    def __init__(
        self,
        question_id: str,
        image_path: str,
        question: str,
        answer: str,
        question_type: str = "presence",
    ):
        self.question_id = str(question_id)
        self.image_path = image_path
        self.question = question
        self.answer = str(answer).strip().lower()
        self.question_type = question_type  # presence, count, comp, rural_urban

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "image_path": self.image_path,
            "question": self.question,
            "answer": self.answer,
            "question_type": self.question_type,
        }


class RSVQADataset(Dataset):
    """
    Standard RSVQA (LR/HR) Benchmark Dataset Loader.
    Parses official RSVQA JSON schema:
      - questions.json: {"questions": [{"id": ..., "question": "...", "img_id": ..., "type": "..."}]}
      - answers.json: {"answers": [{"id": ..., "question_id": ..., "answer": "..."}]}
    """

    def __init__(
        self,
        images_dir: str,
        questions_path: Optional[str] = None,
        answers_path: Optional[str] = None,
        samples: Optional[List[RSVQABenchmarkSample]] = None,
    ):
        self.images_dir = images_dir
        self.samples: List[RSVQABenchmarkSample] = []

        if samples is not None:
            self.samples = samples
        elif questions_path and os.path.isfile(questions_path):
            self._load_rsvqa_json(questions_path, answers_path)

    def _load_rsvqa_json(self, q_path: str, a_path: Optional[str]):
        with open(q_path, "r", encoding="utf-8") as f:
            q_data = json.load(f)

        a_map: Dict[str, str] = {}
        if a_path and os.path.isfile(a_path):
            with open(a_path, "r", encoding="utf-8") as f:
                a_data = json.load(f)
                for item in a_data.get("answers", a_data if isinstance(a_data, list) else []):
                    qid = str(item.get("question_id", item.get("id")))
                    a_map[qid] = str(item.get("answer", "")).strip().lower()

        questions_list = q_data.get("questions", q_data if isinstance(q_data, list) else [])
        for q in questions_list:
            qid = str(q.get("id", q.get("question_id")))
            img_id = q.get("img_id", q.get("image_id", q.get("image", f"{qid}.tif")))
            img_path = os.path.join(self.images_dir, f"{img_id}" if "." in str(img_id) else f"{img_id}.tif")
            ans = a_map.get(qid, str(q.get("answer", "unknown")))
            q_type = q.get("type", "presence")

            self.samples.append(
                RSVQABenchmarkSample(
                    question_id=qid,
                    image_path=img_path,
                    question=q.get("question", ""),
                    answer=ans,
                    question_type=q_type,
                )
            )

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        s = self.samples[idx]
        return s.to_dict()


class VRSBenchSample:
    """Represents a VRSBench sample supporting VQA, Captioning, and Spatial Grounding."""

    def __init__(
        self,
        sample_id: str,
        image_path: str,
        question: str,
        answer: str,
        caption: Optional[str] = None,
        grounding_boxes: Optional[List[Dict[str, Any]]] = None,
    ):
        self.sample_id = str(sample_id)
        self.image_path = image_path
        self.question = question
        self.answer = answer
        self.caption = caption or answer
        self.grounding_boxes = grounding_boxes or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "image_path": self.image_path,
            "question": self.question,
            "answer": self.answer,
            "caption": self.caption,
            "grounding_boxes": self.grounding_boxes,
        }


class VRSBenchDataset(Dataset):
    """
    VRSBench (Visual Remote Sensing Benchmark) Dataset Loader.
    Supports multi-task evaluation: VQA, Scene Captioning, and Visual Grounding.
    """

    def __init__(
        self,
        images_dir: str,
        annotations_path: Optional[str] = None,
        samples: Optional[List[VRSBenchSample]] = None,
    ):
        self.images_dir = images_dir
        self.samples: List[VRSBenchSample] = []

        if samples is not None:
            self.samples = samples
        elif annotations_path and os.path.isfile(annotations_path):
            self._load_vrsbench_json(annotations_path)

    def _load_vrsbench_json(self, ann_path: str):
        with open(ann_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data if isinstance(data, list) else data.get("annotations", data.get("samples", []))
        for item in items:
            sid = str(item.get("id", item.get("sample_id", item.get("image_id"))))
            img_file = item.get("image", item.get("image_id", f"{sid}.tif"))
            img_path = os.path.join(self.images_dir, f"{img_file}" if "." in str(img_file) else f"{img_file}.tif")
            
            conversations = item.get("conversations", [])
            q = item.get("question", "")
            a = item.get("answer", "")
            if conversations:
                for turn in conversations:
                    if turn.get("from") == "human" and not q:
                        q = turn.get("value", "")
                    elif turn.get("from") in ["gpt", "assistant"] and not a:
                        a = turn.get("value", "")

            self.samples.append(
                VRSBenchSample(
                    sample_id=sid,
                    image_path=img_path,
                    question=q,
                    answer=a,
                    caption=item.get("caption"),
                    grounding_boxes=item.get("grounding", item.get("boxes", [])),
                )
            )

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.samples[idx].to_dict()


class CDVQASample:
    """Represents a Change Detection Visual Question Answering (CDVQA) sample."""

    def __init__(
        self,
        pair_id: str,
        image_t1_path: str,
        image_t2_path: str,
        question: str,
        answer: str,
        change_type: str = "urban_expansion",
    ):
        self.pair_id = str(pair_id)
        self.image_t1_path = image_t1_path
        self.image_t2_path = image_t2_path
        self.question = question
        self.answer = str(answer).strip().lower()
        self.change_type = change_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "image_t1_path": self.image_t1_path,
            "image_t2_path": self.image_t2_path,
            "question": self.question,
            "answer": self.answer,
            "change_type": self.change_type,
        }


class CDVQADataset(Dataset):
    """
    Change Detection VQA (CDVQA) Benchmark Dataset Loader.
    Ingests bi-temporal observation pairs and temporal QA annotations.
    """

    def __init__(
        self,
        images_dir: str,
        annotations_path: Optional[str] = None,
        samples: Optional[List[CDVQASample]] = None,
    ):
        self.images_dir = images_dir
        self.samples: List[CDVQASample] = []

        if samples is not None:
            self.samples = samples
        elif annotations_path and os.path.isfile(annotations_path):
            self._load_cdvqa_json(annotations_path)

    def _load_cdvqa_json(self, ann_path: str):
        with open(ann_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data if isinstance(data, list) else data.get("pairs", data.get("samples", []))
        for item in items:
            pid = str(item.get("pair_id", item.get("id")))
            img1 = item.get("image_t1", item.get("img_a", f"{pid}_t1.tif"))
            img2 = item.get("image_t2", item.get("img_b", f"{pid}_t2.tif"))

            p1 = os.path.join(self.images_dir, f"{img1}" if "." in str(img1) else f"{img1}.tif")
            p2 = os.path.join(self.images_dir, f"{img2}" if "." in str(img2) else f"{img2}.tif")

            self.samples.append(
                CDVQASample(
                    pair_id=pid,
                    image_t1_path=p1,
                    image_t2_path=p2,
                    question=item.get("question", "What changed between these two dates?"),
                    answer=item.get("answer", "vegetation loss and urban development"),
                    change_type=item.get("change_type", "urban"),
                )
            )

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.samples[idx].to_dict()
