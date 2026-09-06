# BigEarthNet Model Adaptation Pipeline

SatQuery AI provides a **real, reproducible, and resumable** model adaptation and fine-tuning pipeline for Earth Observation / Remote Sensing Vision-Language Models (VLMs).

---

## 🛰️ Overview

The adaptation pipeline fine-tunes base Vision-Language Models (such as `Salesforce/blip-vqa-base`) on multi-label land-cover satellite observations from **BigEarthNet** (CORINE Land Cover nomenclature).

```
   BigEarthNet Manifest (BigEarthNet.txt)
                     │
                     ▼
  ┌──────────────────────────────────────┐
  │   BigEarthNet Dataset Loader         │
  │   - GeoTIFF 2%-98% band normalization│
  │   - Remote-Sensing QA synthesis      │
  │   - Deterministic Train/Val split    │
  └──────────────────┬───────────────────┘
                     │
                     ▼
  ┌──────────────────────────────────────┐
  │   BigEarthNet Trainer Engine         │
  │   - Full / QA-Head / LoRA modes      │
  │   - Cosine LR & Warmup schedule      │
  │   - Resumable state persistence      │
  └──────────────────┬───────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
  ┌──────────────┐        ┌──────────────┐
  │ Checkpoints  │        │  Evaluation  │
  │ & Metadata   │        │  & Metrics   │
  └──────┬───────┘        └──────────────┘
         │
         ▼
  ┌──────────────────────────────────────┐
  │  SatQuery AI Inference Engine        │
  │  (app/models/vqa_model.py)           │
  └──────────────────────────────────────┘
```

---

## 📁 Dataset Manifest (`BigEarthNet.txt`)

The dataset manifest file is located at `training/data/BigEarthNet.txt`.

### Format
Lines starting with `#` are comments. Each entry is pipe-delimited (`|`):
```text
<Patch_ID> | <CLC_Labels_Comma_Separated> | <Relative_Path_To_GeoTIFF>
```

### Example Manifest Entries
```text
S2A_MSIL2A_20170613T101031_N0205_R022_T32TMR_44_12 | Coniferous forest, Natural grasslands | patches/S2A_MSIL2A_20170613T101031_N0205_R022_T32TMR_44_12.tif
S2A_MSIL2A_20170613T101031_N0205_R022_T32TMR_56_24 | Inland waters, Water bodies | patches/S2A_MSIL2A_20170613T101031_N0205_R022_T32TMR_56_24.tif
S2B_MSIL2A_20170718T102021_N0205_R065_T32TNR_12_88 | Urban fabric, Industrial units | patches/S2B_MSIL2A_20170718T102021_N0205_R065_T32TNR_12_88.tif
```

---

## ⚡ Quickstart: Local Smoke Test

You can run a local smoke-test in a few seconds on CPU or GPU without downloading the full multi-gigabyte dataset:

```bash
python -m training.train --smoke_test --num_epochs 1 --batch_size 2
```

This will:
1. Verify the manifest and patch assets.
2. Load the base VLM processor and weights.
3. Execute genuine gradient updates.
4. Save the trained checkpoint to `checkpoints/bigearthnet_blip_vqa/epoch_1` and `checkpoints/bigearthnet_blip_vqa/best`.
5. Write `training_metadata.json` and `training_state.json`.

---

## 🚀 Running Full Adaptation

### Standard Full Fine-Tuning
```bash
python -m training.train \
  --base_model_id Salesforce/blip-vqa-base \
  --dataset_manifest training/data/BigEarthNet.txt \
  --data_dir training/data/patches \
  --output_dir checkpoints/bigearthnet_blip_vqa \
  --adaptation_mode full \
  --num_epochs 5 \
  --batch_size 4 \
  --learning_rate 5e-5
```

### Lightweight Head-Only Adaptation
Freezes the vision and text backbones and only adapts the cross-attention and answer decoder:
```bash
python -m training.train \
  --adaptation_mode qa_head \
  --num_epochs 3 \
  --batch_size 4
```

### Task-Specific Filtering
Target specific land-cover tasks (e.g. water detection, terrain, urban classification):
```bash
python -m training.train \
  --task_type water_detection \
  --num_epochs 3
```

---

## 🔄 Resuming Training from Checkpoint

The trainer saves full optimizer states (`optimizer.pt`), learning rate scheduler states (`scheduler.pt`), and training loss trajectories (`training_state.json`) at each epoch.

To resume an interrupted run:
```bash
python -m training.train \
  --resume checkpoints/bigearthnet_blip_vqa/epoch_1 \
  --num_epochs 3
```

---

## 📊 Evaluating an Adapted Checkpoint

Run the validation tool to calculate Exact Match (EM) %, Semantic / Keyword Match %, Token F1 Overlap %, and average latency:

```bash
python -m training.evaluate \
  --checkpoint_dir checkpoints/bigearthnet_blip_vqa/best
```

### Sample Output
```text
==================================================
BigEarthNet Evaluation Results for checkpoints/bigearthnet_blip_vqa/best
Total Evaluated: 1
Exact Match Accuracy: 100.0%
Semantic/Keyword Accuracy: 100.0%
Token Overlap F1: 100.0%
Average Latency: 320.15 ms
==================================================
```
The detailed evaluation report is saved to `checkpoints/bigearthnet_blip_vqa/best/evaluation_report.json`.

---

## 🔌 Using the Adapted Model in SatQuery AI Backend

The SatQuery AI inference engine (`app/models/vqa_model.py`) is fully decoupled from training. To use your fine-tuned checkpoint for real-time visual question answering:

Set the environment variable:
```bash
# Windows PowerShell
$env:SATQUERY_VQA_MODEL_ID = "checkpoints/bigearthnet_blip_vqa/best"

# Linux / macOS
export SATQUERY_VQA_MODEL_ID="checkpoints/bigearthnet_blip_vqa/best"
```

Start the SatQuery backend:
```bash
uvicorn app.main:app --reload --port 8000
```

When an observation is queried, SatQuery AI will automatically:
1. Load the locally adapted checkpoint weights and processor.
2. Audit the `training_metadata.json` to attribute the dataset reference.
3. Provide generative Earth Observation insights.
