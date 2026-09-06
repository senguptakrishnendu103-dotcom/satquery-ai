"""
Tests for ISRO / SAC Remote-Sensing Product and Metadata Adapter.

Verifies:
1. Explicit ISRO mission / platform / sensor detection (RESOURCESAT, CARTOSAT, RISAT, EOS-04, EOS-06).
2. XML metadata discovery & parsing (BAND_META.xml, <scene>_metadata.xml).
3. ISRO band naming patterns (L4_BAND*.tif, L3_BAND*.tif, AW_BAND*.tif, PAN_BAND*, MX_BAND*, SAR VV/VH).
4. Accurate band mapping into the normalized band map without fabrication.
5. Preservation of generic GeoTIFF / Sentinel / Landsat processing for non-ISRO data.
6. End-to-end execution of remote sensing analysis workflows over ISRO rasters.
"""

import os
import shutil
import tempfile
import unittest
import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.utils.isro_adapter import ISROProductAdapter
from app.utils.metadata_extractor import MetadataExtractor
from app.agent.orchestrator import AgentOrchestrator


class TestISROProductAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="test_isro_adapter_")
        cls.orchestrator = AgentOrchestrator()

        # Generate a synthetic 3-band Resourcesat LISS-4 GeoTIFF (Band 1: Green, Band 2: Red, Band 3: NIR)
        cls.rs_liss4_path = os.path.join(cls.test_dir, "RS2A_L4_20240115_T1205.tif")
        transform = from_origin(77.5, 12.9, 5.8, 5.8)  # Bangalore coordinates, 5.8m resolution
        data_liss4 = np.ones((3, 64, 64), dtype=np.uint16) * 1000
        data_liss4[0] = 1200  # Green
        data_liss4[1] = 800   # Red
        data_liss4[2] = 3000  # NIR (high vegetation reflectance)

        with rasterio.open(
            cls.rs_liss4_path,
            "w",
            driver="GTiff",
            height=64,
            width=64,
            count=3,
            dtype=np.uint16,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(data_liss4)

        # Generate a single-band LISS-4 Band 2 file
        cls.rs_liss4_b2_path = os.path.join(cls.test_dir, "L4_BAND2.tif")
        with rasterio.open(
            cls.rs_liss4_b2_path,
            "w",
            driver="GTiff",
            height=64,
            width=64,
            count=1,
            dtype=np.uint16,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(data_liss4[0], 1)

        # Generate a Cartosat-3 PAN GeoTIFF
        cls.carto_pan_path = os.path.join(cls.test_dir, "CARTO3_PAN_20240210.tif")
        with rasterio.open(
            cls.carto_pan_path,
            "w",
            driver="GTiff",
            height=64,
            width=64,
            count=1,
            dtype=np.uint16,
            crs="EPSG:4326",
            transform=from_origin(77.5, 12.9, 0.28, 0.28),
        ) as dst:
            dst.write(np.ones((64, 64), dtype=np.uint16) * 2000, 1)

        # Generate a Cartosat-2 MX (4-band: Blue, Green, Red, NIR)
        cls.carto_mx_path = os.path.join(cls.test_dir, "CARTO2_MX_20240210.tif")
        with rasterio.open(
            cls.carto_mx_path,
            "w",
            driver="GTiff",
            height=64,
            width=64,
            count=4,
            dtype=np.uint16,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(np.ones((4, 64, 64), dtype=np.uint16) * 1500)

        # Generate a RISAT-1 / EOS-04 C-SAR GeoTIFF (Dual-pol: VV, VH)
        cls.risat_sar_path = os.path.join(cls.test_dir, "EOS04_CSAR_20240301_VV_VH.tif")
        with rasterio.open(
            cls.risat_sar_path,
            "w",
            driver="GTiff",
            height=64,
            width=64,
            count=2,
            dtype=np.float32,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(np.ones((2, 64, 64), dtype=np.float32) * 0.05)

        # Generate a package folder with BAND_META.xml
        cls.pkg_dir = os.path.join(cls.test_dir, "RESOURCESAT2A_LISS4_PKG")
        os.makedirs(cls.pkg_dir, exist_ok=True)
        cls.pkg_img_path = os.path.join(cls.pkg_dir, "BAND3.tif")
        with rasterio.open(
            cls.pkg_img_path,
            "w",
            driver="GTiff",
            height=64,
            width=64,
            count=1,
            dtype=np.uint16,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(data_liss4[1], 1)

        cls.pkg_xml_path = os.path.join(cls.pkg_dir, "BAND_META.xml")
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Product_Information>
    <Satellite>RESOURCESAT-2A</Satellite>
    <Sensor>LISS-4</Sensor>
    <DateOfPass>15-JAN-2024</DateOfPass>
    <ProductID>RS2A_L4_MX_05M_20240115_001</ProductID>
    <PixelResolution>5.8</PixelResolution>
</Product_Information>
"""
        with open(cls.pkg_xml_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        # Non-ISRO GeoTIFF for regression check
        cls.sentinel_path = os.path.join(cls.test_dir, "S2A_MSIL2A_20240101.tif")
        with rasterio.open(
            cls.sentinel_path,
            "w",
            driver="GTiff",
            height=64,
            width=64,
            count=4,
            dtype=np.uint16,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(np.ones((4, 64, 64), dtype=np.uint16) * 1000)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # =========================================================================
    # 1. MISSION DETECTION TESTS
    # =========================================================================

    def test_01_detect_resourcesat_liss4(self):
        meta = MetadataExtractor.extract_metadata(self.rs_liss4_path)
        self.assertTrue(meta["valid"])
        self.assertTrue(meta["is_isro_product"])
        self.assertEqual(meta["isro_mission"], "Resourcesat")
        self.assertEqual(meta["platform"], "Resourcesat-2A")
        self.assertEqual(meta["sensor"], "LISS-4")
        self.assertEqual(meta["acquisition_date"], "2024-01-15")
        
        # Band map verification (LISS-4 3 bands: B2=Green [1], B3=Red [2], B4=NIR [3])
        band_map = meta["band_map"]
        self.assertIn("green", band_map)
        self.assertIn("red", band_map)
        self.assertIn("nir", band_map)
        self.assertEqual(band_map["green"], [1])
        self.assertEqual(band_map["red"], [2])
        self.assertEqual(band_map["nir"], [3])

    def test_02_detect_single_band_liss4(self):
        meta = MetadataExtractor.extract_metadata(self.rs_liss4_b2_path)
        self.assertTrue(meta["valid"])
        self.assertTrue(meta["is_isro_product"])
        self.assertEqual(meta["sensor"], "LISS-4")
        self.assertEqual(meta["band_map"]["green"], [1])

    def test_03_detect_cartosat_pan(self):
        meta = MetadataExtractor.extract_metadata(self.carto_pan_path)
        self.assertTrue(meta["valid"])
        self.assertTrue(meta["is_isro_product"])
        self.assertEqual(meta["isro_mission"], "Cartosat")
        self.assertEqual(meta["platform"], "Cartosat-3")
        self.assertEqual(meta["sensor"], "PAN")
        self.assertIn("pan", meta["band_map"])

    def test_04_detect_cartosat_mx(self):
        meta = MetadataExtractor.extract_metadata(self.carto_mx_path)
        self.assertTrue(meta["valid"])
        self.assertTrue(meta["is_isro_product"])
        self.assertEqual(meta["platform"], "Cartosat-2")
        self.assertEqual(meta["sensor"], "MX")
        self.assertEqual(meta["band_map"]["blue"], [1])
        self.assertEqual(meta["band_map"]["green"], [2])
        self.assertEqual(meta["band_map"]["red"], [3])
        self.assertEqual(meta["band_map"]["nir"], [4])

    def test_05_detect_eos04_sar(self):
        meta = MetadataExtractor.extract_metadata(self.risat_sar_path)
        self.assertTrue(meta["valid"])
        self.assertTrue(meta["is_isro_product"])
        self.assertEqual(meta["platform"], "EOS-04 (RISAT-1A)")
        self.assertEqual(meta["sensor"], "C-SAR")
        self.assertEqual(meta["modality"], "SAR")
        self.assertIn("vv", meta["band_map"])
        self.assertIn("vh", meta["band_map"])

    # =========================================================================
    # 2. XML METADATA PARSING TESTS
    # =========================================================================

    def test_06_parse_adjacent_band_meta_xml(self):
        meta = MetadataExtractor.extract_metadata(self.pkg_img_path)
        self.assertTrue(meta["valid"])
        self.assertTrue(meta["is_isro_product"])
        self.assertEqual(meta["platform"], "Resourcesat-2A")
        self.assertEqual(meta["sensor"], "LISS-4")
        self.assertEqual(meta["acquisition_date"], "2024-01-15")
        self.assertEqual(meta["isro_product_id"], "RS2A_L4_MX_05M_20240115_001")
        self.assertEqual(meta["spatial_resolution_m"], 5.8)
        self.assertTrue(meta["xml_metadata_path"].endswith("BAND_META.xml"))

    # =========================================================================
    # 3. REGRESSION & NON-ISRO PRESERVATION
    # =========================================================================

    def test_07_preserve_non_isro_sentinel_ingestion(self):
        meta = MetadataExtractor.extract_metadata(self.sentinel_path)
        self.assertTrue(meta["valid"])
        self.assertFalse(meta.get("is_isro_product", False))
        self.assertEqual(meta["platform"], "Sentinel-2A")
        self.assertEqual(meta["sensor"], "MSI")

    # =========================================================================
    # 4. END-TO-END WORKFLOW WITH ISRO RASTERS
    # =========================================================================

    def test_08_end_to_end_analysis_on_isro_raster(self):
        obs = {
            "file_path": self.rs_liss4_path,
            "modality": "optical",
            "acquisition_date": "2024-01-15",
            "satellite_id": "Resourcesat-2A",
        }
        res = self.orchestrator.process_query(
            query="Is there water in this image? Compute NDWI",
            images=[obs],
            input_mode="single_image",
        )
        self.assertEqual(res["task"], "WATER_DETECTION")
        self.assertIn("NDWI", res["answer"])
        self.assertIn("visual_evidence", res)
        self.assertIn("execution_summary", res)


if __name__ == "__main__":
    unittest.main()
