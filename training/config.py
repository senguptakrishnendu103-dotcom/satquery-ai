"""
SatQuery AI - BigEarthNet Model Adaptation Configuration.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List


@dataclass
class TrainingConfig:
    """
    Configuration parameters for BigEarthNet Remote-Sensing VLM Adaptation.
    """
    # Model configuration
    base_model_id: str = "Salesforce/blip-vqa-base"
    task: str = "image-text-to-text"
    adaptation_mode: str = "full"  # 'full', 'qa_head', or 'lora'
    
    # Dataset configuration
    dataset_manifest: str = "training/data/BigEarthNet.txt"
    data_dir: str = "training/data/patches"
    task_type: str = "all"  # 'all', 'land_cover', 'terrain', 'water_detection', 'urban_detection'
    filter_classes: Optional[List[str]] = None
    val_split: float = 0.2
    max_length: int = 64
    seed: int = 42
    
    # Training hyperparameters
    batch_size: int = 2
    num_epochs: int = 3
    learning_rate: float = 5e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    gradient_accumulation_steps: int = 1
    max_grad_norm: float = 1.0
    
    # PEFT / LoRA options (used if adaptation_mode == 'lora')
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: Optional[List[str]] = None
    
    # Execution & Checkpointing
    output_dir: str = "checkpoints/bigearthnet_blip_vqa"
    save_every_epoch: bool = True
    save_best_only: bool = False
    device: str = "cuda"  # Auto-falls back to cpu if cuda unavailable
    resume_from_checkpoint: Optional[str] = None
    
    # Smoke test mode for quick verification
    smoke_test: bool = False
    smoke_samples: int = 6

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save_json(self, path: str):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_json(cls, path: str) -> "TrainingConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
