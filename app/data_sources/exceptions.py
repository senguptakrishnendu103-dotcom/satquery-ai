"""
Custom Exceptions for SatQuery AI Satellite Data Sources Architecture.
"""

class SatelliteProviderError(Exception):
    """Base exception for all satellite data provider errors."""
    pass

class SatelliteSearchError(SatelliteProviderError):
    """Exception raised when satellite product search fails or is not implemented."""
    pass

class ProviderNotFoundError(SatelliteProviderError):
    """Exception raised when a requested provider is not registered."""
    pass

class InvalidSearchRequestError(SatelliteProviderError):
    """Exception raised when a SearchRequest contains invalid parameters."""
    pass

class DuplicateProviderError(SatelliteProviderError):
    """Exception raised when attempting to register a duplicate provider without replacement."""
    pass
