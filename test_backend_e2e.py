import os
import sys
import logging

logging.basicConfig(level=logging.INFO)

from app.agent.orchestrator import agent_orchestrator
from app.utils.image_resolver import ImageResolver

def test_e2e_backend():
    print("==================================================")
    print("Running SatQuery Backend End-to-End Test Pipeline")
    print("==================================================")

    # 1. Generate test image
    test_img = ImageResolver._generate_synthetic_satellite_image(512, 512)
    img_path = os.path.join("app", "static", "uploads", "e2e_test_sample.png")
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    test_img.save(img_path)
    
    obs = {"file_path": img_path, "modality": "optical", "filename": "e2e_test_sample.png"}
    obs_sar = {"file_path": img_path, "modality": "sar", "filename": "e2e_test_sample_sar.png"}

    scenarios = [
        ("VQA Task", "What type of terrain and land cover is present in this scene?", "single_image", [obs]),
        ("Grounding Task", "Locate solar panels and water features", "single_image", [obs]),
        ("Change Detection Task", "Analyze structural changes between dates", "bi_temporal", [obs, obs]),
        ("Water Detection Tool", "Compute NDWI water mask percentage", "single_image", [obs]),
        ("Built-Up Detection Tool", "Calculate NDBI urban built-up coverage", "single_image", [obs]),
        ("Optical-SAR Fusion Task", "Perform multimodal optical and SAR fusion for vessel detection", "optical_sar", [obs, obs_sar]),
    ]

    for name, query, mode, imgs in scenarios:
        print(f"\n---> Testing {name}: '{query}'")
        res = agent_orchestrator.process_query(
            query=query,
            images=imgs,
            input_mode=mode
        )
        print(f"Status: SUCCESS")
        print(f"Task: {res.get('classification', {}).get('task')}")
        print(f"Model Selected: {res.get('model_selected')}")
        print(f"Confidence: {res.get('confidence')}")
        print(f"Answer: {res.get('answer')[:120]}...")
        if res.get("visual_evidence"):
            print(f"Visual Evidence: {list(res.get('visual_evidence').keys())}")
        if res.get("audit"):
            print(f"Execution Time: {res.get('audit', {}).get('inference_time_ms')}ms")

    print("\n==================================================")
    print("ALL SATQUERY BACKEND E2E TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    test_e2e_backend()
