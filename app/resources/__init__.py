"""
SatQuery AI - SIH Data Resources Package.
"""

from app.resources.sih_registry import (
    ResourceAvailability,
    ResourceType,
    SIHResource,
    BigEarthNetResource,
    RSVQAResource,
    VRSBenchResource,
    CDVQAResource,
    ISROSACEvaluationResource,
    SIHResourceRegistry,
    sih_resource_registry,
)

__all__ = [
    "ResourceAvailability",
    "ResourceType",
    "SIHResource",
    "BigEarthNetResource",
    "RSVQAResource",
    "VRSBenchResource",
    "CDVQAResource",
    "ISROSACEvaluationResource",
    "SIHResourceRegistry",
    "sih_resource_registry",
]
