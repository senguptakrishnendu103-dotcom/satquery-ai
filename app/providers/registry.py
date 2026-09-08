"""
Satellite Data Provider Registry & Factory.
"""

from typing import Any, Dict, List, Optional
from app.providers.base import SatelliteDataProvider
from app.providers.bhoonidhi import BhoonidhiProvider
from app.providers.cdse import CDSEProvider
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
        elif key == "cdse":
            _PROVIDERS["cdse"] = CDSEProvider()
        else:
            raise ProviderError(f"Unsupported satellite data provider: '{name}'. Available: {[p['id'] for p in list_providers()]}")
    return _PROVIDERS[key]


def list_providers() -> List[Dict[str, Any]]:
    """List all registered providers and their supported collections with genuine availability status."""
    if "bhoonidhi" not in _PROVIDERS:
        _PROVIDERS["bhoonidhi"] = BhoonidhiProvider()
    if "cdse" not in _PROVIDERS:
        _PROVIDERS["cdse"] = CDSEProvider()

    results = []
    for p in _PROVIDERS.values():
        has_creds = getattr(p, "has_configured_credentials", lambda: False)()
        results.append({
            "id": p.name,
            "name": p.display_name,
            "supported_collections": p.supported_collections,
            "is_configured": bool(has_creds),
            "is_available": bool(has_creds),
            "status": "CONFIGURED" if has_creds else "NOT_CONFIGURED",
            "message": (
                "Provider is configured and ready."
                if has_creds
                else f"Credentials not configured on backend. Set {p.name.upper()}_USERNAME and {p.name.upper()}_PASSWORD in environment to authenticate."
            ),
        })
    return results


# Auto-register default providers
register_provider(BhoonidhiProvider())
register_provider(CDSEProvider())
