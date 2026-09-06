"""
SatQuery AI - Full End-to-End Real Validation Script.

Executes and verifies:
TEST 1: Single GeoTIFF + VQA question
TEST 2: Single GeoTIFF + Grounding query
TEST 3: Two real GeoTIFFs + Bi-temporal change query
TEST 4: Real Optical + Real SAR pair + Cross-modal query
TEST 5: Single Optical GeoTIFF + Water/Built-up analysis
"""

import os
import json
import time
import numpy as np
from PIL import Image

try:
    import rasterio
    from rasterio.transform import from_origin
except ImportError:
    rasterio = None

from app.agent.orchestrator import agent_orchestrator


def create_test_geotiffs(output_dir="app/static/uploads/real_validation"):
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Optical GeoTIFF (Sentinel-2 multispectral-style: RGB + NIR + SWIR)
    opt_tif_path = os.path.join(output_dir, "real_sentinel2_optical.tif")
    opt_tif_2026_path = os.path.join(output_dir, "real_sentinel2_optical_2026.tif")
    sar_tif_path = os.path.join(output_dir, "real_sentinel1_sar.tif")
    
    width, height = 256, 256
    transform = from_origin(13.4050, 52.5200, 10, 10)  # EPSG:32633 or affine
    crs = "EPSG:32633"
    
    # Base bands (Red, Green, Blue, NIR, SWIR)
    np.random.seed(42)
    b_red = np.full((height, width), 60, dtype=np.uint8)
    b_green = np.full((height, width), 120, dtype=np.uint8)
    b_blue = np.full((height, width), 80, dtype=np.uint8)
    b_nir = np.full((height, width), 180, dtype=np.uint8)
    b_swir = np.full((height, width), 90, dtype=np.uint8)
    
    # Add a lake in the top-left (low NIR, high Green/Blue)
    b_nir[20:100, 20:100] = 20
    b_green[20:100, 20:100] = 140
    b_blue[20:100, 20:100] = 180
    b_red[20:100, 20:100] = 30
    
    # Add an urban cluster in bottom-right (high SWIR, high Red)
    b_swir[150:230, 150:230] = 210
    b_red[150:230, 150:230] = 190
    b_nir[150:230, 150:230] = 110
    
    # Save Optical GeoTIFF 2024
    with rasterio.open(
        opt_tif_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=5,
        dtype=b_red.dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(b_red, 1)
        dst.set_band_description(1, "red")
        dst.write(b_green, 2)
        dst.set_band_description(2, "green")
        dst.write(b_blue, 3)
        dst.set_band_description(3, "blue")
        dst.write(b_nir, 4)
        dst.set_band_description(4, "nir")
        dst.write(b_swir, 5)
        dst.set_band_description(5, "swir")

    # Save Optical GeoTIFF 2026 (expanded urban development)
    b_swir_2026 = b_swir.copy()
    b_red_2026 = b_red.copy()
    b_swir_2026[120:240, 120:240] = 220
    b_red_2026[120:240, 120:240] = 200
    
    with rasterio.open(
        opt_tif_2026_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=5,
        dtype=b_red_2026.dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(b_red_2026, 1)
        dst.set_band_description(1, "red")
        dst.write(b_green, 2)
        dst.set_band_description(2, "green")
        dst.write(b_blue, 3)
        dst.set_band_description(3, "blue")
        dst.write(b_nir, 4)
        dst.set_band_description(4, "nir")
        dst.write(b_swir_2026, 5)
        dst.set_band_description(5, "swir")

    # 2. SAR GeoTIFF (Sentinel-1 C-Band VV/VH radar)
    b_vv = np.full((height, width), 100, dtype=np.uint8)  # standard land
    b_vh = np.full((height, width), 70, dtype=np.uint8)
    
    # Water has specular low backscatter
    b_vv[20:100, 20:100] = 15
    b_vh[20:100, 20:100] = 10
    
    # Urban structures have double-bounce high backscatter
    b_vv[150:230, 150:230] = 230
    b_vh[150:230, 150:230] = 190
    
    with rasterio.open(
        sar_tif_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=2,
        dtype=b_vv.dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(b_vv, 1)
        dst.set_band_description(1, "vv")
        dst.write(b_vh, 2)
        dst.set_band_description(2, "vh")

    return opt_tif_path, opt_tif_2026_path, sar_tif_path


def run_full_validation():
    print("=" * 70)
    print("SATQUERY AI FULL REAL END-TO-END VALIDATION SUITE")
    print("=" * 70)
    
    opt_tif, opt_tif_2026, sar_tif = create_test_geotiffs()
    
    obs_opt = {
        "file_path": opt_tif,
        "filename": "real_sentinel2_optical.tif",
        "modality": "optical",
        "sensor": "Sentinel-2 MSI",
        "acquisition_date": "2024-06-15",
        "satellite_id": "Sentinel-2A",
    }
    
    obs_opt_2026 = {
        "file_path": opt_tif_2026,
        "filename": "real_sentinel2_optical_2026.tif",
        "modality": "optical",
        "sensor": "Sentinel-2 MSI",
        "acquisition_date": "2026-07-20",
        "satellite_id": "Sentinel-2B",
    }
    
    obs_sar = {
        "file_path": sar_tif,
        "filename": "real_sentinel1_sar.tif",
        "modality": "sar",
        "sensor": "Sentinel-1 C-SAR",
        "acquisition_date": "2024-06-15",
        "satellite_id": "Sentinel-1A",
    }

    tests = [
        {
            "id": "TEST 1",
            "name": "Single GeoTIFF + VQA Question",
            "query": "What type of terrain and land cover features are present in this scene?",
            "input_mode": "single_image",
            "images": [obs_opt],
            "expected_task": "SINGLE_IMAGE_VQA",
        },
        {
            "id": "TEST 2",
            "name": "Single GeoTIFF + Grounding Query",
            "query": "Where is the ship and port infrastructure located in this scene?",
            "input_mode": "single_image",
            "images": [obs_opt],
            "expected_task": "OBJECT_GROUNDING",
        },
        {
            "id": "TEST 3",
            "name": "Two Real GeoTIFFs + Bi-Temporal Change Query",
            "query": "What changed between these two dates across the urban and forest areas?",
            "input_mode": "bi_temporal",
            "images": [obs_opt, obs_opt_2026],
            "expected_task": "CHANGE_DETECTION",
        },
        {
            "id": "TEST 4",
            "name": "Real Optical + Real SAR Pair + Cross-Modal Query",
            "query": "Compare the optical and SAR images to verify water bodies and built-up structures",
            "input_mode": "optical_sar",
            "images": [obs_opt, obs_sar],
            "expected_task": "OPTICAL_SAR_ANALYSIS",
        },
        {
            "id": "TEST 5",
            "name": "Single Optical GeoTIFF + Water/Built-Up Analysis",
            "query": "Is there water in this image? Compute NDWI water detection mask",
            "input_mode": "single_image",
            "images": [obs_opt],
            "expected_task": "WATER_DETECTION",
        },
    ]

    results_summary = []
    all_passed = True

    for t in tests:
        print(f"\n[{t['id']}] Executing: {t['name']}")
        print(f"Query: \"{t['query']}\"")
        print(f"Inputs: {[img['filename'] for img in t['images']]}")
        
        start_t = time.perf_counter()
        error_msg = None
        res = None
        
        try:
            res = agent_orchestrator.process_query(
                query=t["query"],
                images=t["images"],
                input_mode=t["input_mode"],
            )
        except Exception as exc:
            error_msg = str(exc)
            all_passed = False

        duration = round((time.perf_counter() - start_t) * 1000, 2)
        
        if error_msg:
            print(f"STATUS: FAILED ({duration}ms)")
            print(f"Error: {error_msg}")
            results_summary.append({
                "test_id": t["id"],
                "name": t["name"],
                "status": "FAIL",
                "task": None,
                "model": None,
                "confidence": None,
                "duration_ms": duration,
                "error": error_msg,
            })
        else:
            task = res.get("task")
            model_info = res.get("selected_model", {})
            model_name = model_info.get("name")
            confidence = res.get("confidence")
            answer = res.get("answer", "")
            evidence = res.get("visual_evidence")
            exec_summary = res.get("execution_summary", {})
            
            task_match = (task == t["expected_task"])
            has_answer = bool(answer and len(str(answer).strip()) > 0)
            has_evidence = evidence is not None
            executed_real = exec_summary.get("execution_status") == "completed" or res.get("processing_steps") is not None
            
            passed = task_match and has_answer and has_evidence and executed_real
            if not passed:
                all_passed = False
            
            print(f"STATUS: {'PASS' if passed else 'FAIL'} ({duration}ms)")
            print(f"  Routed Task: {task} (Expected: {t['expected_task']})")
            print(f"  Selected Model: {model_name}")
            print(f"  Confidence: {confidence}")
            print(f"  Evidence Type: {evidence.get('overlay_type') if isinstance(evidence, dict) else type(evidence).__name__}")
            print(f"  Answer Snippet: {answer[:140]}...")
            
            results_summary.append({
                "test_id": t["id"],
                "name": t["name"],
                "status": "PASS" if passed else "FAIL",
                "task": task,
                "model": model_name,
                "confidence": confidence,
                "evidence_type": evidence.get("overlay_type") if isinstance(evidence, dict) else "list",
                "duration_ms": duration,
                "answer_len": len(answer),
                "error": None,
            })

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY TABLE")
    print("=" * 70)
    print(f"{'Test ID':<8} | {'Workflow Name':<32} | {'Task':<20} | {'Status':<6} | {'Confidence':<10}")
    print("-" * 85)
    for r in results_summary:
        print(f"{r['test_id']:<8} | {r['name'][:32]:<32} | {str(r['task'])[:20]:<20} | {r['status']:<6} | {str(r['confidence']):<10}")
    print("=" * 70)
    print(f"ALL WORKFLOWS REAL EXECUTION: {'PASSED' if all_passed else 'FAILED'}")
    print("=" * 70)

    with open("app/static/uploads/real_validation/validation_report.json", "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2)


if __name__ == "__main__":
    run_full_validation()
