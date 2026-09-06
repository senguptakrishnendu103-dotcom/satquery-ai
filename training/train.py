"""
SatQuery AI - BigEarthNet Model Adaptation Trainer.

Executes real fine-tuning / adaptation of remote-sensing VLM models.
Saves model checkpoints, evaluation metrics, processor, optimizer/scheduler states,
and auditable metadata.
"""

import os
import sys
import time
import argparse
import json
from datetime import datetime
from typing import Dict, Any, Optional

import torch
from torch.utils.data import DataLoader
from transformers import (
    BlipProcessor,
    BlipForQuestionAnswering,
    get_cosine_schedule_with_warmup,
)

from training.config import TrainingConfig
from training.dataset import (
    BigEarthNetDataset,
    load_bigearthnet_manifest,
    split_dataset,
    create_sample_bigearthnet_dataset,
)


class BigEarthNetTrainer:
    """
    Handles model fine-tuning, metric evaluation, and resumable checkpoint saving.
    """

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() and config.device == "cuda" else "cpu"
        )
        print(f"[Trainer] Initializing BigEarthNet adaptation on device: {self.device}")

        # 1. Load Processor and Model
        print(f"[Trainer] Loading base VLM: {config.base_model_id}")
        self.processor = BlipProcessor.from_pretrained(config.base_model_id)
        self.model = BlipForQuestionAnswering.from_pretrained(config.base_model_id)

        # Apply adaptation mode
        self._apply_adaptation_mode(config.adaptation_mode)
        self.model.to(self.device)

        # 2. Prepare Datasets
        if not os.path.isfile(config.dataset_manifest):
            print(f"[Trainer] Manifest {config.dataset_manifest} not found. Creating sample BigEarthNet manifest...")
            create_sample_bigearthnet_dataset(
                manifest_path=config.dataset_manifest,
                data_dir=config.data_dir,
                num_samples=config.smoke_samples if config.smoke_test else 6,
            )

        samples = load_bigearthnet_manifest(
            manifest_path=config.dataset_manifest,
            data_dir=config.data_dir,
            task_type=config.task_type,
            filter_classes=config.filter_classes,
        )
        print(f"[Trainer] Loaded {len(samples)} samples from {config.dataset_manifest}")

        if config.smoke_test and len(samples) > config.smoke_samples:
            samples = samples[:config.smoke_samples]
            print(f"[Trainer] Smoke test mode: limited to {len(samples)} samples.")

        train_samples, val_samples = split_dataset(
            samples,
            val_split=config.val_split,
            seed=config.seed,
        )
        print(f"[Trainer] Dataset split: {len(train_samples)} train, {len(val_samples)} validation")

        self.train_dataset = BigEarthNetDataset(train_samples, self.processor, config.max_length)
        self.val_dataset = BigEarthNetDataset(val_samples, self.processor, config.max_length)

        self.train_loader = DataLoader(
            self.train_dataset,
            batch_size=config.batch_size,
            shuffle=True,
        )
        self.val_loader = DataLoader(
            self.val_dataset,
            batch_size=config.batch_size,
            shuffle=False,
        )

        # 3. Optimizer & Scheduler (trainable params only)
        trainable_params = [p for p in self.model.parameters() if p.requires_grad]
        print(f"[Trainer] Trainable parameters: {len(trainable_params)} tensors")

        self.optimizer = torch.optim.AdamW(
            trainable_params,
            lr=config.learning_rate,
            weight_decay=config.weight_decay,
        )

        total_training_steps = (len(self.train_loader) // config.gradient_accumulation_steps) * config.num_epochs
        warmup_steps = int(total_training_steps * config.warmup_ratio)

        self.scheduler = get_cosine_schedule_with_warmup(
            self.optimizer,
            num_warmup_steps=warmup_steps,
            num_training_steps=max(1, total_training_steps),
        )

        self.start_epoch = 1
        self.best_val_loss = float("inf")
        self.history: Dict[str, Any] = {
            "train_loss": [],
            "val_loss": [],
            "epochs": [],
        }

        # 4. Resume if requested
        if config.resume_from_checkpoint:
            self._resume_checkpoint(config.resume_from_checkpoint)

    def _apply_adaptation_mode(self, mode: str):
        """Apply parameter adaptation mode (full, qa_head, or lora)."""
        if mode == "qa_head":
            print("[Trainer] Adaptation Mode: QA Head only (freezing vision encoder & text encoder)")
            if hasattr(self.model, "vision_model"):
                for param in self.model.vision_model.parameters():
                    param.requires_grad = False
            if hasattr(self.model, "text_encoder"):
                for param in self.model.text_encoder.parameters():
                    param.requires_grad = False
        elif mode == "lora":
            try:
                from peft import LoraConfig, get_peft_model
                print("[Trainer] Adaptation Mode: PEFT LoRA")
                lora_config = LoraConfig(
                    r=self.config.lora_r,
                    lora_alpha=self.config.lora_alpha,
                    lora_dropout=self.config.lora_dropout,
                    bias="none",
                )
                self.model = get_peft_model(self.model, lora_config)
            except ImportError:
                print("[Trainer] PEFT library not installed. Falling back to full fine-tuning.")
        else:
            print("[Trainer] Adaptation Mode: Full model fine-tuning")

    def _resume_checkpoint(self, checkpoint_path: str):
        print(f"[Trainer] Resuming from checkpoint: {checkpoint_path}")
        state_file = os.path.join(checkpoint_path, "training_state.json")
        if os.path.isfile(state_file):
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                self.start_epoch = state.get("epoch", 1) + 1
                self.best_val_loss = state.get("best_val_loss", float("inf"))
                self.history = state.get("history", self.history)
                print(f"[Trainer] Resuming at epoch {self.start_epoch} (previous best val loss: {self.best_val_loss:.4f})")

        opt_file = os.path.join(checkpoint_path, "optimizer.pt")
        if os.path.isfile(opt_file):
            try:
                self.optimizer.load_state_dict(torch.load(opt_file, map_location=self.device))
                print("[Trainer] Restored optimizer state.")
            except Exception as e:
                print(f"[Trainer] Warning: Could not restore optimizer state: {e}")

        sched_file = os.path.join(checkpoint_path, "scheduler.pt")
        if os.path.isfile(sched_file):
            try:
                self.scheduler.load_state_dict(torch.load(sched_file, map_location=self.device))
                print("[Trainer] Restored scheduler state.")
            except Exception as e:
                print(f"[Trainer] Warning: Could not restore scheduler state: {e}")

    def train_epoch(self, epoch: int) -> float:
        self.model.train()
        total_loss = 0.0
        steps = 0
        start_time = time.perf_counter()

        for batch_idx, batch in enumerate(self.train_loader, 1):
            batch = {k: v.to(self.device) for k, v in batch.items()}

            outputs = self.model(**batch)
            loss = outputs.loss

            if loss is None:
                continue

            loss = loss / self.config.gradient_accumulation_steps
            loss.backward()

            if batch_idx % self.config.gradient_accumulation_steps == 0 or batch_idx == len(self.train_loader):
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.max_grad_norm)
                self.optimizer.step()
                self.scheduler.step()
                self.optimizer.zero_grad()

            total_loss += loss.item() * self.config.gradient_accumulation_steps
            steps += 1

        avg_loss = total_loss / max(1, steps)
        elapsed = time.perf_counter() - start_time
        print(f"[Epoch {epoch}/{self.config.num_epochs}] Train Loss: {avg_loss:.4f} | Time: {elapsed:.2f}s")
        return avg_loss

    def validate(self, epoch: int) -> float:
        self.model.eval()
        total_loss = 0.0
        steps = 0

        with torch.no_grad():
            for batch in self.val_loader:
                batch = {k: v.to(self.device) for k, v in batch.items()}
                outputs = self.model(**batch)
                loss = outputs.loss
                if loss is not None:
                    total_loss += loss.item()
                    steps += 1

        avg_loss = total_loss / max(1, steps)
        print(f"[Epoch {epoch}/{self.config.num_epochs}] Val Loss: {avg_loss:.4f}")
        return avg_loss

    def save_checkpoint(self, epoch: int, val_loss: float, is_best: bool = False):
        epoch_dir = os.path.join(self.config.output_dir, f"epoch_{epoch}")
        os.makedirs(epoch_dir, exist_ok=True)

        # Save Hugging Face model & processor
        self.model.save_pretrained(epoch_dir)
        self.processor.save_pretrained(epoch_dir)

        # Save optimizer & scheduler for resumability
        torch.save(self.optimizer.state_dict(), os.path.join(epoch_dir, "optimizer.pt"))
        torch.save(self.scheduler.state_dict(), os.path.join(epoch_dir, "scheduler.pt"))

        # Save training state
        training_state = {
            "epoch": epoch,
            "val_loss": val_loss,
            "best_val_loss": self.best_val_loss,
            "history": self.history,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        with open(os.path.join(epoch_dir, "training_state.json"), "w", encoding="utf-8") as f:
            json.dump(training_state, f, indent=2)

        # Save comprehensive training metadata
        metadata = {
            "base_model_id": self.config.base_model_id,
            "adapted_checkpoint": epoch_dir,
            "dataset": {
                "manifest": self.config.dataset_manifest,
                "data_dir": self.config.data_dir,
                "task_type": self.config.task_type,
                "train_samples": len(self.train_dataset),
                "val_samples": len(self.val_dataset),
            },
            "training_config": self.config.to_dict(),
            "metrics": {
                "epoch": epoch,
                "val_loss": val_loss,
                "train_loss": self.history["train_loss"][-1] if self.history["train_loss"] else None,
            },
            "created_at": datetime.utcnow().isoformat() + "Z",
            "model_type": "BigEarthNet-Adapted-BLIP-VQA",
        }
        with open(os.path.join(epoch_dir, "training_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # If best model, save to best directory
        if is_best:
            best_dir = os.path.join(self.config.output_dir, "best")
            os.makedirs(best_dir, exist_ok=True)
            self.model.save_pretrained(best_dir)
            self.processor.save_pretrained(best_dir)
            with open(os.path.join(best_dir, "training_metadata.json"), "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            print(f"[Trainer] New best model saved to {best_dir} (Val Loss: {val_loss:.4f})")

    def run(self):
        print(f"\n==================================================")
        print(f"Starting BigEarthNet VLM Adaptation Pipeline")
        print(f"Base Model: {self.config.base_model_id}")
        print(f"Output Dir: {self.config.output_dir}")
        print(f"Epochs: {self.config.num_epochs} | Batch: {self.config.batch_size} | LR: {self.config.learning_rate}")
        print(f"==================================================\n")

        for epoch in range(self.start_epoch, self.config.num_epochs + 1):
            train_loss = self.train_epoch(epoch)
            val_loss = self.validate(epoch)

            self.history["train_loss"].append(train_loss)
            self.history["val_loss"].append(val_loss)
            self.history["epochs"].append(epoch)

            is_best = val_loss < self.best_val_loss
            if is_best:
                self.best_val_loss = val_loss

            if self.config.save_every_epoch or is_best:
                self.save_checkpoint(epoch, val_loss, is_best=is_best)

        print("\n==================================================")
        print(f"BigEarthNet Adaptation Complete! Best Val Loss: {self.best_val_loss:.4f}")
        print(f"Adapted Checkpoint available at: {os.path.join(self.config.output_dir, 'best')}")
        print("==================================================\n")


def parse_args() -> TrainingConfig:
    parser = argparse.ArgumentParser(description="BigEarthNet VLM Model Adaptation Trainer")
    parser.add_argument("--base_model_id", type=str, default="Salesforce/blip-vqa-base")
    parser.add_argument("--dataset_manifest", type=str, default="training/data/BigEarthNet.txt")
    parser.add_argument("--data_dir", type=str, default="training/data/patches")
    parser.add_argument("--output_dir", type=str, default="checkpoints/bigearthnet_blip_vqa")
    parser.add_argument("--adaptation_mode", type=str, default="full", choices=["full", "qa_head", "lora"])
    parser.add_argument("--task_type", type=str, default="all", choices=["all", "land_cover", "terrain", "water_detection", "urban_detection"])
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--num_epochs", type=int, default=2)
    parser.add_argument("--learning_rate", type=float, default=5e-5)
    parser.add_argument("--smoke_test", action="store_true", help="Run quick verification with small subset")
    parser.add_argument("--smoke_samples", type=int, default=6)
    parser.add_argument("--resume", type=str, default=None, help="Path to checkpoint directory to resume from")

    args = parser.parse_args()
    return TrainingConfig(
        base_model_id=args.base_model_id,
        dataset_manifest=args.dataset_manifest,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        adaptation_mode=args.adaptation_mode,
        task_type=args.task_type,
        batch_size=args.batch_size,
        num_epochs=args.num_epochs,
        learning_rate=args.learning_rate,
        smoke_test=args.smoke_test,
        smoke_samples=args.smoke_samples,
        resume_from_checkpoint=args.resume,
    )


if __name__ == "__main__":
    config = parse_args()
    trainer = BigEarthNetTrainer(config)
    trainer.run()
