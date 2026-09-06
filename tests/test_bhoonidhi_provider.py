"""
Comprehensive Unit & Integration Test Suite for ISRO Bhoonidhi Provider and Web Data Ingestion.
"""

import io
import json
import os
import shutil
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.providers import (
    BhoonidhiProvider,
    InvalidSearchRequestError,
    ProductNotAvailableError,
    ProductNotFoundError,
    ProviderAuthError,
    ProviderNetworkError,
    ProviderRateLimitError,
    SearchRequest,
    get_provider,
    list_providers,
)
from app.utils.metadata_extractor import MetadataExtractor
from app.agent.orchestrator import AgentOrchestrator, agent_orchestrator


class TestBhoonidhiProvider(unittest.TestCase):
    """Test suite for ISRO Bhoonidhi satellite data provider."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_bhoonidhi_"))
        self.provider = BhoonidhiProvider(
            base_url="https://bhoonidhi.nrsc.gov.in/api/v1",
            username="test_isro_user",
            password="test_secret_password_123",
            timeout_seconds=5.0,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_provider_properties_and_registry(self):
        """Verify provider metadata and factory registration."""
        self.assertEqual(self.provider.name, "bhoonidhi")
        self.assertIn("ISRO", self.provider.display_name)
        self.assertIn("RESOURCESAT-2A", self.provider.supported_collections)
        self.assertIn("EOS-04", self.provider.supported_collections)

        # Factory lookup
        factory_prov = get_provider("bhoonidhi")
        self.assertEqual(factory_prov.name, "bhoonidhi")
        providers = list_providers()
        self.assertTrue(any(p["id"] == "bhoonidhi" for p in providers))

    @patch("urllib.request.urlopen")
    def test_02_authentication_and_token_caching(self, mock_urlopen):
        """Test successful token retrieval and in-memory caching."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "access_token": "isro_jwt_token_abc123",
            "expires_in": 3600,
        }).encode("utf-8")
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # First call hits auth endpoint
        success = self.provider.authenticate()
        self.assertTrue(success)
        self.assertEqual(self.provider._access_token, "isro_jwt_token_abc123")
        self.assertEqual(mock_urlopen.call_count, 1)

        # Second call should reuse valid cached token without HTTP request
        success2 = self.provider.authenticate()
        self.assertTrue(success2)
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("urllib.request.urlopen")
    def test_03_authentication_failure(self, mock_urlopen):
        """Test authentication rejection with invalid credentials."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://bhoonidhi.nrsc.gov.in/api/v1/auth/token",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(b'{"error": "Invalid credentials"}'),
        )
        with self.assertRaises(ProviderAuthError):
            self.provider.authenticate(force_refresh=True)

    @patch("urllib.request.urlopen")
    def test_04_search_request_and_normalization(self, mock_urlopen):
        """Test spatial and temporal search query normalization."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "total_matched": 2,
            "features": [
                {
                    "id": "RS2A_L4_20240615_T32TMR_001",
                    "collection": "RESOURCESAT-2A",
                    "bbox": [77.45, 12.85, 77.75, 13.15],
                    "properties": {
                        "platform": "RESOURCESAT-2A",
                        "instrument": "LISS-4",
                        "datetime": "2024-06-15T05:30:00Z",
                        "cloud_cover": 2.5,
                        "online": True,
                        "is_downloadable": True,
                    },
                },
                {
                    "id": "EOS04_CSAR_20240720_002",
                    "collection": "EOS-04",
                    "bbox": [77.45, 12.85, 77.75, 13.15],
                    "properties": {
                        "platform": "EOS-04",
                        "instrument": "C-SAR",
                        "datetime": "2024-07-20T10:15:00Z",
                        "cloud_cover": None,
                        "online": True,
                        "is_downloadable": True,
                    },
                },
            ],
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Set fake token
        self.provider._access_token = "valid_token"
        self.provider._token_expiry_timestamp = 9999999999.0

        req = SearchRequest(
            provider="bhoonidhi",
            collections=["RESOURCESAT-2A", "EOS-04"],
            bbox=(77.45, 12.85, 77.75, 13.15),
            datetime_range="2024-01-01/2026-08-30",
            limit=5,
        )

        resp = self.provider.search(req)
        self.assertEqual(resp.provider, "bhoonidhi")
        self.assertEqual(len(resp.items), 2)
        self.assertEqual(resp.items[0].product_id, "RS2A_L4_20240615_T32TMR_001")
        self.assertEqual(resp.items[0].platform, "RESOURCESAT-2A")
        self.assertEqual(resp.items[0].instrument, "LISS-4")
        self.assertEqual(resp.items[0].cloud_cover, 2.5)
        self.assertTrue(resp.items[0].is_downloadable)
        self.assertEqual(resp.items[1].product_id, "EOS04_CSAR_20240720_002")

    def test_05_search_validation_errors(self):
        """Test invalid search boundaries and parameters."""
        # Invalid bbox lat/lon
        with self.assertRaises(ValueError):
            req = SearchRequest(provider="bhoonidhi", bbox=(190.0, 10.0, 80.0, 20.0))
            req.validate()

        # Inverted bbox
        with self.assertRaises(ValueError):
            req = SearchRequest(provider="bhoonidhi", bbox=(80.0, 20.0, 70.0, 10.0))
            req.validate()

        # Invalid limit
        with self.assertRaises(ValueError):
            req = SearchRequest(provider="bhoonidhi", limit=500)
            req.validate()

    @patch("urllib.request.urlopen")
    def test_06_download_execution_and_caching(self, mock_urlopen):
        """Test product download and subsequent cache reuse."""
        fake_content = b"PK\x03\x04FAKE_ZIP_HEADER_CONTENT_BYTES"
        mock_response = MagicMock()
        mock_response.headers.get.return_value = "application/zip"
        mock_response.read.side_effect = [fake_content, b""]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Set fake token
        self.provider._access_token = "valid_token"
        self.provider._token_expiry_timestamp = 9999999999.0

        product_id = "RS2A_L4_BAND_20240615"
        dl_res = self.provider.download(
            product_id=product_id,
            destination_dir=self.test_dir,
            collection="RESOURCESAT-2A",
        )

        self.assertEqual(dl_res.product_id, product_id)
        self.assertFalse(dl_res.cached)
        self.assertTrue(os.path.isfile(dl_res.local_path))
        self.assertEqual(dl_res.file_size_bytes, len(fake_content))

        # Second download should use local cached file without network request
        dl_res_cached = self.provider.download(
            product_id=product_id,
            destination_dir=self.test_dir,
            collection="RESOURCESAT-2A",
        )
        self.assertTrue(dl_res_cached.cached)
        self.assertEqual(dl_res_cached.local_path, dl_res.local_path)

    def test_07_path_traversal_sanitization(self):
        """Test defense against malicious product ID directory traversal."""
        with self.assertRaises(InvalidSearchRequestError):
            self.provider.download(
                product_id="../../etc/passwd",
                destination_dir=self.test_dir,
            )

        with self.assertRaises(InvalidSearchRequestError):
            self.provider.download(
                product_id="/root/malicious_script.sh",
                destination_dir=self.test_dir,
            )

    @patch("urllib.request.urlopen")
    def test_08_error_handling_codes(self, mock_urlopen):
        """Test standard error code mappings."""
        # 429 Rate Limit
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=429, msg="Too Many Requests", hdrs={}, fp=io.BytesIO(b"")
        )
        with self.assertRaises(ProviderRateLimitError):
            req = SearchRequest(provider="bhoonidhi")
            self.provider.search(req)

        # 404 Not Found
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=404, msg="Not Found", hdrs={}, fp=io.BytesIO(b"")
        )
        prod = self.provider.get_product("NON_EXISTENT_PRODUCT")
        self.assertIsNone(prod)

        # 412 Order Only / Restricted
        self.provider._access_token = "mock_active_token"
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=412, msg="Precondition Failed", hdrs={}, fp=io.BytesIO(b"")
        )
        with self.assertRaises(ProductNotAvailableError):
            self.provider.download("RESTRICTED_PRODUCT_001", self.test_dir)

    def test_09_common_ingestion_and_orchestrator(self):
        """Verify downloaded web product passes through common ingestion into AgentOrchestrator."""
        # Create a sample GeoTIFF representing a fetched ISRO product
        sample_path = os.path.join(self.test_dir, "RESOURCESAT2A_LISS4_20240615.tif")
        import numpy as np
        import rasterio
        w, h = 64, 64
        transform = rasterio.transform.from_origin(77.59, 12.97, 0.0001, 0.0001)
        r = np.full((h, w), 100, dtype=np.uint16)
        g = np.full((h, w), 150, dtype=np.uint16)
        b = np.full((h, w), 80, dtype=np.uint16)

        with rasterio.open(
            sample_path,
            "w",
            driver="GTiff",
            height=h,
            width=w,
            count=3,
            dtype=r.dtype,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(r, 1)
            dst.write(g, 2)
            dst.write(b, 3)

        # Common ingestion
        meta = MetadataExtractor.extract_metadata(sample_path, os.path.basename(sample_path))
        self.assertEqual(meta["platform"].upper(), "RESOURCESAT-2A")
        self.assertEqual(meta["sensor"], "LISS-4")

        # Ingested observation contract
        obs = {
            "id": "fetch_isro_001",
            "provider": "bhoonidhi",
            "product_id": "RESOURCESAT2A_LISS4_20240615",
            "source_type": "web_fetch",
            "file_path": sample_path,
            "local_path": sample_path,
            "modality": "optical",
            "metadata": meta,
        }

        # Run through AgentOrchestrator
        orchestrator = AgentOrchestrator()
        result = orchestrator.process_query(
            query="Analyze vegetation cover and land use in this ISRO observation.",
            images=[obs],
            input_mode="single_image",
        )

        self.assertIn("answer", result)
        self.assertIn("selected_model", result)
        self.assertIn("visual_evidence", result)
        self.assertIn("task", result)
        self.assertIn("execution_summary", result)
        self.assertEqual(result["execution_summary"]["data_sources"][0]["provider"], "bhoonidhi")
        self.assertEqual(result["execution_summary"]["data_sources"][0]["source_type"], "web_fetch")

    def test_10_optional_live_bhoonidhi_integration(self):
        """Optional live test hitting Bhoonidhi (skipped cleanly when credentials absent)."""
        if not os.getenv("BHOONIDHI_USERNAME") or not os.getenv("BHOONIDHI_PASSWORD"):
            self.skipTest("Live Bhoonidhi credentials not set in environment. Skipping live test.")

        prov = BhoonidhiProvider()
        health = prov.health_check()
        self.assertTrue(health)


if __name__ == "__main__":
    unittest.main()
