"""
Comprehensive Unit & Integration Test Suite for CDSE (Copernicus Data Space Ecosystem) Provider.
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
    CDSEProvider,
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


class TestCDSEProvider(unittest.TestCase):
    """Test suite for CDSE satellite data provider."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_cdse_"))
        self.provider = CDSEProvider(
            token_url="https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            catalogue_url="https://catalogue.dataspace.copernicus.eu",
            download_url="https://zipper.dataspace.copernicus.eu/odata/v1/Products",
            username="test_cdse_user",
            password="test_cdse_password",
            timeout_seconds=5.0,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_provider_properties_and_registry(self):
        """Verify CDSE provider metadata and registry auto-registration."""
        self.assertEqual(self.provider.name, "cdse")
        self.assertIn("Copernicus Data Space Ecosystem", self.provider.display_name)
        self.assertIn("SENTINEL-2", self.provider.supported_collections)
        self.assertIn("S2MSI2A", self.provider.supported_collections)
        self.assertIn("SENTINEL-1", self.provider.supported_collections)

        # Factory & list_providers lookup
        factory_prov = get_provider("cdse")
        self.assertEqual(factory_prov.name, "cdse")
        providers = list_providers()
        self.assertTrue(any(p["id"] == "cdse" for p in providers))

    def test_02_credential_configuration_check(self):
        """Verify credential presence and placeholder detection."""
        # Configured provider
        self.assertTrue(self.provider.has_configured_credentials())

        # Unconfigured / placeholder provider
        empty_provider = CDSEProvider(
            username="your_cdse_username",
            password="your_cdse_password",
        )
        self.assertFalse(empty_provider.has_configured_credentials())

    @patch("urllib.request.urlopen")
    def test_03_oauth2_authentication(self, mock_urlopen):
        """Verify OAuth2 password grant authentication flow and token caching."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "access_token": "mock_jwt_token_12345",
            "expires_in": 3600,
            "token_type": "Bearer",
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Authenticate
        res = self.provider.authenticate(force_refresh=True)
        self.assertTrue(res)
        self.assertEqual(self.provider._access_token, "mock_jwt_token_12345")

        # Second call should use cached token without additional network request
        mock_urlopen.reset_mock()
        res_cached = self.provider.authenticate()
        self.assertTrue(res_cached)
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_04_odata_search(self, mock_urlopen):
        """Verify OData search API query and item normalization."""
        # CDSE OData search item mock
        odata_response = {
            "value": [
                {
                    "Id": "S2B_MSIL2A_20240520T051659_N0510_R062_T43QDA_20240520T073719",
                    "Name": "S2B_MSIL2A_20240520T051659_N0510_R062_T43QDA_20240520T073719.SAFE",
                    "ContentDate": {"Start": "2024-05-20T05:16:59.000Z"},
                    "Online": True,
                    "Attributes": [
                        {"Name": "cloudCover", "Value": "4.25"}
                    ],
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(odata_response).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Execute Search
        search_req = SearchRequest(
            provider="cdse",
            collections=["SENTINEL-2"],
            bbox=(77.45, 12.85, 77.75, 13.15),
            datetime_range="2024-05-01/2024-05-30",
            limit=10,
            filters={"max_cloud_cover": 10.0},
        )

        resp = self.provider.search(search_req)
        self.assertEqual(resp.provider, "cdse")
        self.assertEqual(resp.total_matched, 1)
        self.assertEqual(len(resp.items), 1)

        item = resp.items[0]
        self.assertEqual(item.product_id, "S2B_MSIL2A_20240520T051659_N0510_R062_T43QDA_20240520T073719")
        self.assertEqual(item.cloud_cover, 4.25)
        self.assertEqual(item.platform, "Sentinel-2")
        self.assertEqual(len(item.assets), 1)

    @patch("urllib.request.urlopen")
    def test_05_download_product_caching(self, mock_urlopen):
        """Verify file download streaming and local caching."""
        # 1. Mock token auth
        token_resp = MagicMock()
        token_resp.status = 200
        token_resp.read.return_value = json.dumps({"access_token": "valid_token"}).encode("utf-8")

        # 2. Mock download stream
        dl_resp = MagicMock()
        dl_resp.status = 200
        dl_resp.read.side_effect = [b"PK\x03\x04" + b"x" * 100, b""]

        mock_urlopen.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=token_resp)),
            MagicMock(__enter__=MagicMock(return_value=dl_resp)),
        ]

        pid = "S2B_TEST_PRODUCT_001"
        result = self.provider.download(
            product_id=pid,
            destination_dir=self.test_dir,
            collection="SENTINEL-2",
        )

        self.assertEqual(result.product_id, pid)
        self.assertFalse(result.cached)
        self.assertTrue(Path(result.local_path).exists())
        self.assertGreater(result.file_size_bytes, 0)

        # Re-downloading should return cached result
        cached_result = self.provider.download(
            product_id=pid,
            destination_dir=self.test_dir,
            collection="SENTINEL-2",
        )
        self.assertTrue(cached_result.cached)


if __name__ == "__main__":
    unittest.main()
