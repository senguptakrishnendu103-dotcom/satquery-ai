from typing import List, Dict, Any


DEMO_SCENARIOS: List[Dict[str, Any]] = [

    # =========================================================
    # DEMO 1 — SINGLE IMAGE
    # =========================================================

    {
        "id": "demo_1",

        "title": "DEMO 1: Single-Image Land-Cover Analysis",

        "input_mode": "single_image",

        "description": (
            "Single optical remote-sensing image for natural-language "
            "question answering, scene description, and land-cover analysis."
        ),

        "default_query": (
            "Describe the major land-cover types visible."
        ),

        "suggested_queries": [
            "Describe the major land-cover types visible.",
            "What is visible in this image?",
            "Is there an urban built-up area?",
            "Estimate vegetation canopy percentage.",
            "Where are the major land-cover regions?",
        ],

        "capabilities": [
            "SINGLE_IMAGE_VQA",
            "IMAGE_CAPTIONING",
            "OBJECT_GROUNDING",
            "WATER_DETECTION",
            "BUILT_UP_ANALYSIS",
        ],

        "images": [
            {
                "id": "demo_1_image_a",

                "filename": "optical_2024.png",

                "url": "/static/assets/optical_2024.png",

                "modality": "Optical RGB",

                "sensor": "Demo Optical Sensor",

                "acquisition_date": "2024-06-15",

                "width": 800,
                "height": 600,

                "file_size_kb": 245.8,

                "format": "PNG",

                "band_count": 3,

                "bands": [
                    "Red",
                    "Green",
                    "Blue",
                ],

                "crs": None,

                "resolution_m": None,

                "bounds": None,

                "is_georeferenced": False,

                "source_type": "demo",

                "metadata_status": "Demo metadata",
            }
        ],
    },


    # =========================================================
    # DEMO 2 — TEXT GUIDED GROUNDING
    # =========================================================

    {
        "id": "demo_2",

        "title": "DEMO 2: Text-Guided Feature Grounding",

        "input_mode": "single_image",

        "description": (
            "Natural-language spatial grounding of physical features "
            "within a single optical remote-sensing image."
        ),

        "default_query": (
            "Where is the water body?"
        ),

        "suggested_queries": [
            "Where is the water body?",
            "Highlight the river and reservoir.",
            "Locate built-up infrastructure.",
            "Find agricultural fields.",
            "Locate the major vegetation regions.",
        ],

        "capabilities": [
            "OBJECT_GROUNDING",
            "WATER_DETECTION",
            "BUILT_UP_ANALYSIS",
        ],

        "images": [
            {
                "id": "demo_2_image_a",

                "filename": "optical_2024.png",

                "url": "/static/assets/optical_2024.png",

                "modality": "Optical RGB",

                "sensor": "Demo Optical Sensor",

                "acquisition_date": "2024-06-15",

                "width": 800,
                "height": 600,

                "file_size_kb": 245.8,

                "format": "PNG",

                "band_count": 3,

                "bands": [
                    "Red",
                    "Green",
                    "Blue",
                ],

                "crs": None,

                "resolution_m": None,

                "bounds": None,

                "is_georeferenced": False,

                "source_type": "demo",

                "metadata_status": "Demo metadata",
            }
        ],
    },


    # =========================================================
    # DEMO 3 — BI-TEMPORAL
    # =========================================================

    {
        "id": "demo_3",

        "title": "DEMO 3: Bi-Temporal Change Analysis",

        "input_mode": "bi_temporal",

        "description": (
            "Comparison of two optical observations acquired at "
            "different dates for natural-language change analysis."
        ),

        "default_query": (
            "What changed between these two images?"
        ),

        "suggested_queries": [
            "What changed between these two images?",
            "Has the built-up area increased?",
            "Where did vegetation decrease?",
            "Where are the major changes?",
            "Describe the spatial changes between the two dates.",
        ],

        "capabilities": [
            "CHANGE_DETECTION",
        ],

        "temporal_configuration": {
            "comparison_type": "bi_temporal",

            "registration_required": True,

            "same_area_required": True,

            "date_order": [
                "date_a",
                "date_b",
            ],
        },

        "images": [
            {
                "id": "demo_3_image_a",

                "filename": "optical_2024.png",

                "url": "/static/assets/optical_2024.png",

                "modality": "Optical RGB",

                "role": "date_a",

                "acquisition_date": "2024-06-15",

                "width": 800,
                "height": 600,

                "file_size_kb": 245.8,

                "format": "PNG",

                "band_count": 3,

                "bands": [
                    "Red",
                    "Green",
                    "Blue",
                ],

                "crs": None,

                "resolution_m": None,

                "bounds": None,

                "is_georeferenced": False,

                "source_type": "demo",

                "metadata_status": "Demo metadata",
            },

            {
                "id": "demo_3_image_b",

                "filename": "optical_2026.png",

                "url": "/static/assets/optical_2026.png",

                "modality": "Optical RGB",

                "role": "date_b",

                "acquisition_date": "2026-06-15",

                "width": 800,
                "height": 600,

                "file_size_kb": 268.4,

                "format": "PNG",

                "band_count": 3,

                "bands": [
                    "Red",
                    "Green",
                    "Blue",
                ],

                "crs": None,

                "resolution_m": None,

                "bounds": None,

                "is_georeferenced": False,

                "source_type": "demo",

                "metadata_status": "Demo metadata",
            },
        ],
    },


    # =========================================================
    # DEMO 4 — OPTICAL + SAR
    # =========================================================

    {
        "id": "demo_4",

        "title": "DEMO 4: Optical + SAR Multi-Modal Analysis",

        "input_mode": "optical_sar",

        "description": (
            "Cross-modal analysis using paired optical and SAR "
            "observations of the same area."
        ),

        "default_query": (
            "Identify built-up and water-covered regions using both images."
        ),

        "suggested_queries": [
            "Identify built-up and water-covered regions using both images.",
            "Use optical and SAR data to find water bodies.",
            "Compare optical features with SAR radar backscatter.",
            "Highlight urban areas visible in both modalities.",
            "Explain what optical and SAR reveal about this scene.",
        ],

        "capabilities": [
            "OPTICAL_SAR_ANALYSIS",
            "WATER_DETECTION",
            "BUILT_UP_ANALYSIS",
        ],

        "multimodal_configuration": {
            "pair_type": "optical_sar",

            "same_area_required": True,

            "co_registration_required": True,

            "expected_modalities": [
                "optical",
                "sar",
            ],
        },

        "images": [
            {
                "id": "demo_4_optical",

                "filename": "optical_multimodal.png",

                "url": "/static/assets/optical_multimodal.png",

                "modality": "Optical RGB",

                "role": "optical",

                "sensor": "Demo Optical Sensor",

                "acquisition_date": "2025-04-10",

                "width": 800,
                "height": 600,

                "file_size_kb": 230.1,

                "format": "PNG",

                "band_count": 3,

                "bands": [
                    "Red",
                    "Green",
                    "Blue",
                ],

                "crs": None,

                "resolution_m": None,

                "bounds": None,

                "is_georeferenced": False,

                "source_type": "demo",

                "metadata_status": "Demo metadata",
            },

            {
                "id": "demo_4_sar",

                "filename": "sar_multimodal.png",

                "url": "/static/assets/sar_multimodal.png",

                "modality": "SAR",

                "role": "sar",

                "sensor": "Demo SAR Sensor",

                "acquisition_date": "2025-04-10",

                "width": 800,
                "height": 600,

                "file_size_kb": 290.5,

                "format": "PNG",

                "band_count": 2,

                "bands": [
                    "VV",
                    "VH",
                ],

                "crs": None,

                "resolution_m": None,

                "bounds": None,

                "is_georeferenced": False,

                "source_type": "demo",

                "metadata_status": "Demo metadata",
            },
        ],
    },
]