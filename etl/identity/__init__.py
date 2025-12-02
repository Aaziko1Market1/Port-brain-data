"""
GTI-OS Data Platform - Identity Engine Module (EPIC 3)
=======================================================
Organization identity resolution for buyers and suppliers.

Provides:
- Name normalization for de-duplication
- Exact and fuzzy matching against organizations_master
- Incremental UUID assignment to standardized shipments
"""

from etl.identity.name_normalization import (
    normalize_org_name,
    normalize_country_for_org,
    get_org_country,
)

from etl.identity.resolve_organizations import (
    IdentityResolutionEngine,
    run_identity_resolution,
    OrganizationCandidate,
    ResolutionResult,
    IdentityResolutionSummary,
)

__all__ = [
    'normalize_org_name',
    'normalize_country_for_org',
    'get_org_country',
    'IdentityResolutionEngine',
    'run_identity_resolution',
    'OrganizationCandidate',
    'ResolutionResult',
    'IdentityResolutionSummary',
]
