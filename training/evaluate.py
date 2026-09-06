"""
SatQuery AI - BigEarthNet Model Evaluation & Verification Tool.

Evaluates an adapted checkpoint against BigEarthNet samples.
Outputs quantitative accuracy metrics (Exact Match, Keyword Match, Token F1)
and qualitative predictions with inference latency benchmarking.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional

import torch
from transformers import BlipProcessor, BlipForQuestionAnswering
from PIL import Image

from training.dataset import load_bigearthnet_manifest, split_dataset, load_raster_or_image


def compute_token_f1(pred: str, gt: str) -> float:
    """Compute token-level F1 overlap between prediction and ground truth."""
    pred_tokens = pred.lower().strip().split()
    gt_tokens = gt.lower().strip().split()
    
    if not pred_tokens or not gt_tokens:
        return 1.0 if pred_tokens == gt_tokens else 0.0

    common = set(pred_tokens) & set(gt_tokens)
    if not common:
        return 0.0

    precision = len(common) / len(pred_tokens)
    recall = len(common) / len(gt_tokens)
    f1 = (2 * precision * recall) / (precision + recall)
    return round(f1, 4)


def evaluate_checkpoint(
    checkpoint_dir: str,
    manifest_path: str = "training/data/BigEarthNet.txt",
    data_dir: str = "training/data/patches",
    task_type: str = "all",
    val_split: float = 0.2,
    seed: int = 42,
    output_report_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate a fine-tuned BigEarthNet checkpoint.
    """
    if not os.path.isdir(checkpoint_dir):
        raise FileNotFoundError(f"Checkpoint directory not found: {checkpoint_dir}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Evaluation] Loading adapted model from: {checkpoint_dir} on {device}")

    processor = BlipProcessor.from_pretrained(checkpoint_dir)
    model = BlipForQuestionAnswering.from_pretrained(checkpoint_dir)
    model.to(device)
    model.eval()

    samples = load_bigearthnet_manifest(manifest_path, data_dir, task_type=task_type)
    _, val_samples = split_dataset(samples, val_split=val_split, seed=seed)
    print(f"[Evaluation] Running evaluation on {len(val_samples)} validation samples")

    predictions: List[Dict[str, Any]] = []
    exact_matches = 0
    keyword_matches = 0
    total_f1 = 0.0
    latencies: List[float] = []

    for idx, sample in enumerate(val_samples, 1):
        if not os.path.isfile(sample.image_path):
            continue

        rgb_img = load_raster_or_image(sample.image_path)

        inputs = processor(images=rgb_img, text=sample.question, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}

        t0 = time.perf_counter()
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=32)
            predicted_answer = processor.decode(out[0], skip_special_tokens=True).strip().lower()
        latency_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(latency_ms)

        gt_answer = sample.answer.strip().lower()

        # Metrics
        is_exact = (predicted_answer == gt_answer)
        is_keyword = any(lbl.lower() in predicted_answer for lbl in sample.labels) or predicted_answer in gt_answer or gt_answer in predicted_answer
        f1 = compute_token_f1(predicted_answer, gt_answer)

        if is_exact:
            exact_matches += 1
        if is_keyword:
            keyword_matches += 1
        total_f1 += f1

        predictions.append({
            "sample_id": sample.patch_id,
            "question": sample.question,
            "ground_truth": sample.answer,
            "predicted_answer": predicted_answer,
            "exact_match": is_exact,
            "keyword_match": is_keyword,
            "token_f1": f1,
            "latency_ms": round(latency_ms, 2),
        })

    total = max(1, len(predictions))
    exact_match_acc = round((exact_matches / total) * 100.0, 2)
    keyword_match_acc = round((keyword_matches / total) * 100.0, 2)
    avg_f1 = round((total_f1 / total) * 100.0, 2)
    avg_latency = round(sum(latencies) / max(1, len(latencies)), 2) if latencies else 0.0

    report = {
        "checkpoint_dir": checkpoint_dir,
        "manifest_path": manifest_path,
        "task_type": task_type,
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "total_evaluated": len(predictions),
        "metrics": {
            "exact_match_accuracy_percent": exact_match_acc,
            "keyword_match_accuracy_percent": keyword_match_acc,
            "average_token_f1_percent": avg_f1,
            "avg_inference_latency_ms": avg_latency,
        },
        "samples": predictions,
    }

    print("\n==================================================")
    print(f"BigEarthNet Evaluation Results for {checkpoint_dir}")
    print(f"Total Evaluated: {len(predictions)}")
    print(f"Exact Match Accuracy: {exact_match_acc}%")
    print(f"Semantic/Keyword Accuracy: {keyword_match_acc}%")
    print(f"Token Overlap F1: {avg_f1}%")
    print(f"Average Latency: {avg_latency} ms")
    print("==================================================\n")

    for p in predictions[:3]:
        print(f"Sample: {p['sample_id']}")
        print(f"  Q: {p['question']}")
        print(f"  GT: {p['ground_truth']}")
        print(f"  Pred: {p['predicted_answer']}")
        print(f"  EM: {p['exact_match']} | Keyword: {p['keyword_match']} | F1: {p['token_f1']}")
        print("---")

    report_path = output_report_path or os.path.join(checkpoint_dir, "evaluation_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"[Evaluation] Saved evaluation report to: {report_path}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Adapted BigEarthNet Model")
    parser.add_argument("--checkpoint_dir", type=str, default="checkpoints/bigearthnet_blip_vqa/best")
    parser.add_argument("--dataset_manifest", type=str, default="training/data/BigEarthNet.txt")
    parser.add_argument("--data_dir", type=str, default="training/data/patches")
    parser.add_argument("--task_type", type=str, default="all")
    parser.add_argument("--output_report", type=str, default=None)

    args = parser.parse_args()
    evaluate_checkpoint(
        checkpoint_dir=args.checkpoint_dir,
        manifest_path=args.dataset_manifest,
        data_dir=args.data_dir,
        task_type=args.task_type,
        output_report_path=args.output_report,
    )
