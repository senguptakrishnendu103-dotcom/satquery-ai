"""
Satellite Data Provider Registry & Factory.
"""

from typing import Any, Dict, List, Optional
from app.providers.base import SatelliteDataProvider
from app.providers.bhoonidhi import BhoonidhiProvider
from app.providers.exceptions import ProviderError

_PROVIDERS: Dict[str, SatelliteDataProvider] = {}


def register_provider(provider: SatelliteDataProvider) -> None:
    """Register a provider instance."""
    _PROVIDERS[provider.name.lower()] = provider


def get_provider(name: str) -> SatelliteDataProvider:
    """Retrieve a registered provider by key."""
    key = (name or "bhoonidhi").lower().strip()
    if key not in _PROVIDERS:
        if key == "bhoonidhi":
            _PROVIDERS["bhoonidhi"] = BhoonidhiProvider()
        else:
            raise ProviderError(f"Unsupported satellite data provider: '{name}'. Available: {list_providers()}")
    return _PROVIDERS[key]


def list_providers() -> List[Dict[str, Any]]:
    """List all registered providers and their supported collections."""
    if "bhoonidhi" not in _PROVIDERS:
        _PROVIDERS["bhoonidhi"] = BhoonidhiProvider()

    return [
        {
            "id": p.name,
            "name": p.display_name,
            "supported_collections": p.supported_collections,
        }
        for p in _PROVIDERS.values()
    ]


# Auto-register default provider
register_provider(BhoonidhiProvider())
