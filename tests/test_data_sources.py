"""
Comprehensive Unit & Integration Test Suite for SatQuery AI Data Sources Architecture (Stage 1 & Stage 2).
"""

import sys
import os
import unittest
import logging
from io import StringIO
from datetime import datetime
from typing import List
from unittest.mock import MagicMock, patch

# Ensure parent directory is in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.data_sources.exceptions import (
    SatelliteProviderError,
    SatelliteSearchError,
    ProviderNotFoundError,
    InvalidSearchRequestError,
    DuplicateProviderError,
)
from app.data_sources.base_provider import (
    SearchRequest,
    SatelliteProduct,
    SatelliteDataProvider,
)
from app.data_sources.providers.copernicus_provider import (
    CopernicusProvider,
    parse_wkt_footprint,
    intersects_bbox,
)
from app.data_sources.search_service import SatelliteSearchService


class MockDataProvider(SatelliteDataProvider):
    """Mock satellite data provider for testing search service interaction."""

    @property
    def name(self) -> str:
        return "mock_provider"

    @property
    def supported_collections(self) -> List[str]:
        return ["mock-collection-1"]

    @property
    def supported_modalities(self) -> List[str]:
        return ["optical"]

    def search(self, request: SearchRequest) -> List[SatelliteProduct]:
        return [
            SatelliteProduct(
                product_id="MOCK_PRODUCT_001",
                provider=self.name,
                collection=request.collection,
                bbox=request.bbox,
                acquisition_datetime=datetime(2024, 8, 15, 10, 0, 0),
            )
        ]

    def get_product(self, product_id: str) -> SatelliteProduct:
        return SatelliteProduct(
            product_id=product_id,
            provider=self.name,
            collection="mock-collection-1",
        )

    def get_download_url(self, product_id: str) -> str:
        return f"https://mock.provider.org/download/{product_id}"


class TestDataSourcesArchitecture(unittest.TestCase):
    """Test suite for data_sources provider abstraction, Copernicus provider, and search service."""

    def test_01_valid_search_request(self):
        """Test creation of a valid search request."""
        req = SearchRequest(
            bbox=[-60.5, -3.2, -59.8, -2.5],
            start_date="2024-01-01",
            end_date="2024-08-30",
            collection="sentinel-2",
            max_cloud_cover=15.0,
            limit=10,
        )
        self.assertEqual(req.collection, "sentinel-2")
        self.assertEqual(req.limit, 10)
        self.assertEqual(req.bbox, (-60.5, -3.2, -59.8, -2.5))

    def test_02_invalid_bbox_order(self):
        """Test error when min_lon > max_lon or min_lat > max_lat."""
        with self.assertRaises(InvalidSearchRequestError) as ctx:
            SearchRequest(
                bbox=[-59.8, -3.2, -60.5, -2.5],
                start_date="2024-01-01",
                end_date="2024-08-30",
                collection="sentinel-2",
            )
        self.assertIn("min_lon", str(ctx.exception))

    def test_03_invalid_latitude(self):
        """Test error when latitude is outside [-90, 90]."""
        with self.assertRaises(InvalidSearchRequestError) as ctx:
            SearchRequest(
                bbox=[-60.5, -95.0, -59.8, -2.5],
                start_date="2024-01-01",
                end_date="2024-08-30",
                collection="sentinel-2",
            )
        self.assertIn("latitude", str(ctx.exception).lower())

    def test_04_invalid_longitude(self):
        """Test error when longitude is outside [-180, 180]."""
        with self.assertRaises(InvalidSearchRequestError) as ctx:
            SearchRequest(
                bbox=[-190.0, -3.2, -59.8, -2.5],
                start_date="2024-01-01",
                end_date="2024-08-30",
                collection="sentinel-2",
            )
        self.assertIn("longitude", str(ctx.exception).lower())

    def test_05_invalid_date_range(self):
        """Test error when start_date > end_date."""
        with self.assertRaises(InvalidSearchRequestError) as ctx:
            SearchRequest(
                bbox=[-60.5, -3.2, -59.8, -2.5],
                start_date="2024-09-01",
                end_date="2024-01-01",
                collection="sentinel-2",
            )
        self.assertIn("date range", str(ctx.exception).lower())

    def test_06_invalid_limit(self):
        """Test error when limit is non-positive."""
        with self.assertRaises(InvalidSearchRequestError) as ctx:
            SearchRequest(
                bbox=[-60.5, -3.2, -59.8, -2.5],
                start_date="2024-01-01",
                end_date="2024-08-30",
                collection="sentinel-2",
                limit=0,
            )
        self.assertIn("limit", str(ctx.exception).lower())

    def test_07_provider_registration(self):
        """Test registering a data provider with SatelliteSearchService."""
        service = SatelliteSearchService()
        mock = MockDataProvider()
        service.register_provider(mock)
        self.assertIn("mock_provider", [p["name"] for p in service.list_providers()])
        self.assertEqual(service.get_provider("mock_provider").name, "mock_provider")

    def test_08_duplicate_provider_registration(self):
        """Test that registering duplicate provider raises DuplicateProviderError unless replace=True."""
        service = SatelliteSearchService()
        mock1 = MockDataProvider()
        service.register_provider(mock1)

        mock2 = MockDataProvider()
        with self.assertRaises(DuplicateProviderError):
            service.register_provider(mock2)

        service.register_provider(mock2, replace=True)

    def test_09_unknown_provider(self):
        """Test looking up or searching with an unknown provider name."""
        service = SatelliteSearchService()
        with self.assertRaises(ProviderNotFoundError):
            service.get_provider("non_existent_provider")

        req = SearchRequest(
            bbox=[-60.5, -3.2, -59.8, -2.5],
            start_date="2024-01-01",
            end_date="2024-08-30",
            collection="sentinel-2",
        )
        with self.assertRaises(ProviderNotFoundError):
            service.search("non_existent_provider", req)

    def test_10_copernicus_provider_interface_and_capabilities(self):
        """Test CopernicusProvider properties and collection capabilities."""
        copernicus = CopernicusProvider()
        self.assertEqual(copernicus.name, "copernicus")
        self.assertIn("sentinel-1", copernicus.supported_collections)
        self.assertIn("sentinel-2", copernicus.supported_collections)
        self.assertIn("sentinel-2-l2a", copernicus.supported_collections)
        self.assertIn("optical", copernicus.supported_modalities)
        self.assertIn("sar", copernicus.supported_modalities)

    @patch("requests.Session.get")
    def test_11_copernicus_sentinel2_search_mocked(self, mock_get):
        """Test mock Sentinel-2 CDSE search execution and product normalization."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "Id": "S2_MOCK_ID_001",
                    "Name": "S2B_MSIL2A_20240829T141709_N0511_R010_T20MRC_20240829T164302.SAFE",
                    "ContentDate": {"Start": "2024-08-29T14:17:09.000Z"},
                    "Footprint": "geography'SRID=4326;POLYGON ((-60.5 -3.2, -59.8 -3.2, -59.8 -2.5, -60.5 -2.5, -60.5 -3.2))'",
                    "Attributes": [
                        {"Name": "cloudCover", "Value": 12.5},
                        {"Name": "platformShortName", "Value": "SENTINEL-2"},
                        {"Name": "platformSerialIdentifier", "Value": "B"},
                        {"Name": "instrumentShortName", "Value": "MSI"},
                        {"Name": "processingLevel", "Value": "Level-2A"}
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        copernicus = CopernicusProvider()
        req = SearchRequest(
            bbox=[-60.5, -3.2, -59.8, -2.5],
            start_date="2024-08-01",
            end_date="2024-08-30",
            collection="sentinel-2-l2a",
            limit=5
        )

        results = copernicus.search(req)
        self.assertEqual(len(results), 1)
        prod = results[0]
        self.assertEqual(prod.product_id, "S2_MOCK_ID_001")
        self.assertEqual(prod.provider, "copernicus")
        self.assertEqual(prod.platform, "Sentinel-2B")
        self.assertEqual(prod.instrument, "MSI")
        self.assertEqual(prod.modality, "optical")
        self.assertEqual(prod.cloud_cover, 12.5)
        self.assertEqual(prod.bbox, (-60.5, -3.2, -59.8, -2.5))
        self.assertIsNotNone(prod.geo_footprint)
        self.assertEqual(prod.geo_footprint["type"], "Polygon")

    @patch("requests.Session.get")
    def test_12_copernicus_sentinel1_search_mocked(self, mock_get):
        """Test mock Sentinel-1 SAR CDSE search and cloud_cover=None verification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "Id": "S1_MOCK_ID_001",
                    "Name": "S1A_IW_GRDH_1SDV_20240829T050000.SAFE",
                    "ContentDate": {"Start": "2024-08-29T05:00:00.000Z"},
                    "Footprint": "geography'SRID=4326;POLYGON ((-60.5 -3.2, -59.8 -3.2, -59.8 -2.5, -60.5 -2.5, -60.5 -3.2))'",
                    "Attributes": [
                        {"Name": "platformShortName", "Value": "SENTINEL-1"},
                        {"Name": "platformSerialIdentifier", "Value": "A"},
                        {"Name": "instrumentShortName", "Value": "C-SAR"},
                        {"Name": "productType", "Value": "GRD"}
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        copernicus = CopernicusProvider()
        req = SearchRequest(
            bbox=[-60.5, -3.2, -59.8, -2.5],
            start_date="2024-08-01",
            end_date="2024-08-30",
            collection="sentinel-1-grd"
        )

        results = copernicus.search(req)
        self.assertEqual(len(results), 1)
        prod = results[0]
        self.assertEqual(prod.modality, "sar")
        self.assertIsNone(prod.cloud_cover)

    @patch("requests.Session.get")
    def test_13_copernicus_cloud_cover_filtering(self, mock_get):
        """Test that products exceeding max_cloud_cover are filtered out."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "Id": "HIGH_CLOUD_ID",
                    "Name": "S2A_MSIL2A_HIGH_CLOUD.SAFE",
                    "ContentDate": {"Start": "2024-08-29T00:00:00.000Z"},
                    "Footprint": "geography'SRID=4326;POLYGON ((-60.5 -3.2, -59.8 -3.2, -59.8 -2.5, -60.5 -2.5, -60.5 -3.2))'",
                    "Attributes": [{"Name": "cloudCover", "Value": 85.0}]
                },
                {
                    "Id": "LOW_CLOUD_ID",
                    "Name": "S2A_MSIL2A_LOW_CLOUD.SAFE",
                    "ContentDate": {"Start": "2024-08-29T01:00:00.000Z"},
                    "Footprint": "geography'SRID=4326;POLYGON ((-60.5 -3.2, -59.8 -3.2, -59.8 -2.5, -60.5 -2.5, -60.5 -3.2))'",
                    "Attributes": [{"Name": "cloudCover", "Value": 5.0}]
                }
            ]
        }
        mock_get.return_value = mock_response

        copernicus = CopernicusProvider()
        req = SearchRequest(
            bbox=[-60.5, -3.2, -59.8, -2.5],
            start_date="2024-08-01",
            end_date="2024-08-30",
            collection="sentinel-2",
            max_cloud_cover=20.0
        )

        results = copernicus.search(req)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].product_id, "LOW_CLOUD_ID")

    @patch("requests.Session.get")
    def test_14_copernicus_missing_cloud_cover(self, mock_get):
        """Test that missing cloudCover attribute sets cloud_cover=None instead of 0."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "Id": "NO_CLOUD_ATTR_ID",
                    "Name": "S2A_MSIL2A_NO_CLOUD_ATTR.SAFE",
                    "ContentDate": {"Start": "2024-08-29T00:00:00.000Z"},
                    "Footprint": "geography'SRID=4326;POLYGON ((-60.5 -3.2, -59.8 -3.2, -59.8 -2.5, -60.5 -2.5, -60.5 -3.2))'",
                    "Attributes": []
                }
            ]
        }
        mock_get.return_value = mock_response

        copernicus = CopernicusProvider()
        req = SearchRequest(
            bbox=[-60.5, -3.2, -59.8, -2.5],
            start_date="2024-08-01",
            end_date="2024-08-30",
            collection="sentinel-2"
        )

        results = copernicus.search(req)
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0].cloud_cover)

    @patch("requests.Session.get")
    def test_15_copernicus_missing_footprint(self, mock_get):
        """Test graceful handling when CDSE item footprint is missing or empty."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "Id": "NO_FOOTPRINT_ID",
                    "Name": "S2A_NO_FOOTPRINT.SAFE",
                    "ContentDate": {"Start": "2024-08-29T00:00:00.000Z"},
                    "Footprint": None,
                    "Attributes": []
                }
            ]
        }
        mock_get.return_value = mock_response

        copernicus = CopernicusProvider()
        req = SearchRequest(
            bbox=[-60.5, -3.2, -59.8, -2.5],
            start_date="2024-08-01",
            end_date="2024-08-30",
            collection="sentinel-2"
        )

        results = copernicus.search(req)
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0].bbox)
        self.assertIsNone(results[0].geo_footprint)

    @patch("requests.Session.get")
    def test_16_copernicus_http_429_retry_and_error(self, mock_get):
        """Test retries and SatelliteSearchError on HTTP 429 rate limit errors."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        mock_get.return_value = mock_response

        copernicus = CopernicusProvider(max_retries=1, connect_timeout=1.0, read_timeout=1.0)
        req = SearchRequest(
            bbox=[-60.5, -3.2, -59.8, -2.5],
            start_date="2024-08-01",
            end_date="2024-08-30",
            collection="sentinel-2"
        )

        with self.assertRaises(SatelliteSearchError) as ctx:
            copernicus.search(req)
        self.assertIn("HTTP 429", str(ctx.exception))

    @patch("requests.Session.get")
    def test_17_copernicus_http_500_error(self, mock_get):
        """Test handling of HTTP 500 Internal Server Error from CDSE."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        copernicus = CopernicusProvider(max_retries=0)
        req = SearchRequest(
            bbox=[-60.5, -3.2, -59.8, -2.5],
            start_date="2024-08-01",
            end_date="2024-08-30",
            collection="sentinel-2"
        )

        with self.assertRaises(SatelliteSearchError):
            copernicus.search(req)

    @patch("requests.Session.get")
    def test_18_copernicus_timeout_handling(self, mock_get):
        """Test network timeout raises SatelliteSearchError."""
        import requests
        mock_get.side_effect = requests.Timeout("Connection timed out")

        copernicus = CopernicusProvider(max_retries=0)
        req = SearchRequest(
            bbox=[-60.5, -3.2, -59.8, -2.5],
            start_date="2024-08-01",
            end_date="2024-08-30",
            collection="sentinel-2"
        )

        with self.assertRaises(SatelliteSearchError) as ctx:
            copernicus.search(req)
        self.assertIn("Network error", str(ctx.exception))

    @patch("requests.Session.get")
    def test_19_copernicus_malformed_json_handling(self, mock_get):
        """Test malformed JSON response raises SatelliteSearchError."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON string")
        mock_get.return_value = mock_response

        copernicus = CopernicusProvider()
        req = SearchRequest(
            bbox=[-60.5, -3.2, -59.8, -2.5],
            start_date="2024-08-01",
            end_date="2024-08-30",
            collection="sentinel-2"
        )

        with self.assertRaises(SatelliteSearchError):
            copernicus.search(req)

    def test_20_copernicus_invalid_collection_error(self):
        """Test requesting an unsupported collection raises InvalidSearchRequestError."""
        copernicus = CopernicusProvider()
        req = SearchRequest(
            bbox=[-60.5, -3.2, -59.8, -2.5],
            start_date="2024-08-01",
            end_date="2024-08-30",
            collection="invalid-collection-xyz"
        )

        with self.assertRaises(InvalidSearchRequestError) as ctx:
            copernicus.search(req)
        self.assertIn("Unsupported collection", str(ctx.exception))

    @patch("requests.Session.get")
    def test_21_copernicus_health_check(self, mock_get):
        """Test CopernicusProvider health_check() method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        copernicus = CopernicusProvider()
        self.assertTrue(copernicus.health_check())

    def test_22_credentials_not_logged(self):
        """Verify that credentials or secrets do not appear in logger outputs."""
        log_output = StringIO()
        handler = logging.StreamHandler(log_output)
        copernicus_logger = logging.getLogger("satquery.data_sources.copernicus")
        copernicus_logger.addHandler(handler)
        copernicus_logger.setLevel(logging.INFO)

        secret_password = "SUPER_SECRET_CDSE_PASSWORD_123"
        provider = CopernicusProvider(username="user@example.com", password=secret_password)

        log_content = log_output.getvalue()
        self.assertNotIn(secret_password, log_content)
        copernicus_logger.removeHandler(handler)

    @patch("app.data_sources.providers.copernicus_provider.CopernicusProvider.search")
    def test_23_search_service_delegation(self, mock_search):
        """Verify SatelliteSearchService correctly delegates search requests to registered providers."""
        mock_search.return_value = [
            SatelliteProduct(
                product_id="DELEGATION_TEST_001",
                provider="copernicus",
                collection="sentinel-2",
            )
        ]

        service = SatelliteSearchService()
        copernicus = CopernicusProvider()
        service.register_provider(copernicus)

        results = service.search(
            "copernicus",
            {
                "bbox": [-60.5, -3.2, -59.8, -2.5],
                "start_date": "2024-01-01",
                "end_date": "2024-08-30",
                "collection": "sentinel-2",
            }
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].product_id, "DELEGATION_TEST_001")
        mock_search.assert_called_once()

    def test_24_optional_live_cdse_integration(self):
        """Optional integration test hitting real CDSE API (enabled when SATQUERY_RUN_LIVE_CDSE_TESTS=1)."""
        if os.getenv("SATQUERY_RUN_LIVE_CDSE_TESTS") != "1":
            self.skipTest("Live CDSE integration tests disabled. Set SATQUERY_RUN_LIVE_CDSE_TESTS=1 to run.")

        copernicus = CopernicusProvider()
        req = SearchRequest(
            bbox=[-60.5, -3.2, -59.8, -2.5],
            start_date="2024-08-01",
            end_date="2024-08-30",
            collection="sentinel-2",
            limit=2
        )

        results = copernicus.search(req)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].provider, "copernicus")
        self.assertIsNotNone(results[0].product_id)
        self.assertIsNotNone(results[0].acquisition_datetime)


if __name__ == "__main__":
    unittest.main()
