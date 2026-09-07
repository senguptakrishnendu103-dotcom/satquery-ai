import os
import sys
import json
import tempfile
import zipfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.providers import get_provider, list_providers, SearchRequest
from app.utils.raster_ingestor import RasterIngestor
from app.utils.metadata_extractor import MetadataExtractor
from app.utils.image_resolver import ImageResolver


class TestSatellitePipelineFlow(unittest.TestCase):
    """
    Validates the end-to-end flow:
    Provider selection -> Search -> Download -> Raster Ingestion -> Observation Creation -> Real Local Analysis Asset
    """

    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="pipeline_test_"))
        self.storage_dir = self.tmp_dir / "storage"
        self.storage_dir.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_provider_selection(self):
        """Step 1: Provider selection from real registry"""
        providers = list_providers()
        self.assertIsInstance(providers, list)
        self.assertGreater(len(providers), 0)
        
        bhoonidhi = next((p for p in providers if p["id"] == "bhoonidhi"), None)
        self.assertIsNotNone(bhoonidhi)
        self.assertIn("RESOURCESAT-2A", bhoonidhi["supported_collections"])
        self.assertIn("is_configured", bhoonidhi)
        self.assertIn("is_available", bhoonidhi)
        self.assertIn("status", bhoonidhi)

    def test_02_satellite_search_validation_and_results(self):
        """Step 2: Satellite search with genuine parameters"""
        prov = get_provider("bhoonidhi")
        
        # Inverted BBox should be rejected
        req_invalid = SearchRequest(
            provider="bhoonidhi",
            collections=["RESOURCESAT-2A"],
            bbox=(80.0, 20.0, 70.0, 10.0),
        )
        with self.assertRaises(ValueError):
            req_invalid.validate()

        # Genuine search with mock network response
        req_valid = SearchRequest(
            provider="bhoonidhi",
            collections=["RESOURCESAT-2A"],
            bbox=(77.45, 12.85, 77.75, 13.15),
            datetime_range="2024-01-01/2026-08-30",
            limit=5,
        )
        req_valid.validate()

        fake_catalogue_response = {
            "total_matched": 1,
            "features": [
                {
                    "id": "RS2A_L4_TEST_20240615",
                    "collection": "RESOURCESAT-2A",
                    "bbox": [77.45, 12.85, 77.75, 13.15],
                    "properties": {
                        "platform": "RESOURCESAT-2A",
                        "instrument": "LISS-4",
                        "datetime": "2024-06-15T05:30:00Z",
                        "cloud_cover": 1.2,
                        "online": True,
                        "is_downloadable": True,
                    },
                }
            ],
        }

        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(fake_catalogue_response).encode("utf-8")
            mock_url.return_value.__enter__.return_value = mock_resp

            search_res = prov.search(req_valid)
            self.assertEqual(search_res.total_matched, 1)
            self.assertEqual(len(search_res.items), 1)
            item = search_res.items[0]
            self.assertEqual(item.product_id, "RS2A_L4_TEST_20240615")
            self.assertEqual(item.platform, "RESOURCESAT-2A")
            self.assertEqual(item.instrument, "LISS-4")
            self.assertEqual(item.cloud_cover, 1.2)

    def test_03_download_raster_ingestion_and_local_asset(self):
        """Steps 3, 4, 5, 6: Download -> Ingest -> Observation -> Real Local Analysis Asset"""
        # Create a genuine GeoTIFF
        tif_path = self.tmp_dir / "RS2A_L4_TEST_BAND.tif"
        w, h = 128, 128
        transform = from_origin(77.59, 12.97, 0.0001, 0.0001)
        data = np.full((3, h, w), 120, dtype=np.uint16)
        
        with rasterio.open(
            tif_path,
            "w",
            driver="GTiff",
            height=h,
            width=w,
            count=3,
            dtype=data.dtype,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(data)

        # Package into a product archive (simulating real provider download)
        zip_path = self.tmp_dir / "RS2A_L4_TEST_20240615.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            # Add with Sentinel-2 / ISRO naming conventions
            zf.write(tif_path, arcname="GRANULE/L1C_TEST/IMG_DATA/B04.jp2")
            zf.write(tif_path, arcname="GRANULE/L1C_TEST/IMG_DATA/B03.jp2")
            zf.write(tif_path, arcname="GRANULE/L1C_TEST/IMG_DATA/B02.jp2")
            zf.write(tif_path, arcname="GRANULE/L1C_TEST/IMG_DATA/B08.jp2")

        # Step 4: Raster Ingestion
        ingestor = RasterIngestor(self.storage_dir)
        manifest = ingestor.ingest_archive(
            zip_path,
            product_id="RS2A_L4_TEST_20240615",
            collection="RESOURCESAT-2A",
        )

        self.assertEqual(manifest["status"], "success")
        candidate_asset = (
            manifest.get("model_file_path")
            or manifest.get("local_path")
            or (manifest.get("analysis_asset") if isinstance(manifest.get("analysis_asset"), str) else None)
            or (manifest.get("analysis_asset", {}).get("path") if isinstance(manifest.get("analysis_asset"), dict) else None)
            or manifest.get("raster_path")
        )
        self.assertIsNotNone(candidate_asset)
        analysis_asset = Path(candidate_asset)
        
        # Step 6: Real local analysis asset check
        self.assertTrue(analysis_asset.exists(), f"Local asset {analysis_asset} must exist on disk")
        self.assertGreater(analysis_asset.stat().st_size, 0, "Local asset must not be empty")

        # Step 5: Extract real metadata and construct Observation
        metadata = MetadataExtractor.extract_metadata(str(analysis_asset), analysis_asset.name)
        metadata["provider"] = "bhoonidhi"
        metadata["product_id"] = "RS2A_L4_TEST_20240615"
        metadata["collection"] = "RESOURCESAT-2A"
        metadata["analysis_asset"] = str(analysis_asset)
        metadata["analysisAsset"] = str(analysis_asset)
        metadata["file_path"] = str(analysis_asset)
        metadata["local_path"] = str(analysis_asset)

        # Verify real metadata fields
        self.assertIsNotNone(metadata.get("crs"))
        self.assertIsNotNone(metadata.get("bounds"))
        self.assertIsNotNone(metadata.get("resolution"))
        self.assertIsNotNone(metadata.get("bands"))
        self.assertIsNotNone(metadata.get("dimensions"))

        # Verify preview generation from local analysis asset
        preview_url = ImageResolver.ensure_displayable_preview(str(analysis_asset))
        self.assertTrue(preview_url.startswith("/static/uploads/"))
        preview_file = Path("app" + preview_url)
        self.assertTrue(preview_file.exists(), f"Preview file {preview_file} must exist on disk")


if __name__ == "__main__":
    unittest.main()
