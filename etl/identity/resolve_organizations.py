"""
EPIC 3 - Identity Engine: Organization Resolution
==================================================
Implements batch-based, incremental identity resolution for organizations
(buyers and suppliers) across trade data.

Key Features:
- Batch processing for efficiency
- Exact matching on (name_normalized, country_iso)
- Fuzzy matching with pg_trgm for unmatched names
- Incremental processing (only NULL UUIDs)
- MIXED type handling for orgs appearing in both roles

Part of GTI-OS Data Platform Architecture v1.0
"""

import logging
import uuid
import json
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values, execute_batch

from etl.db_utils import DatabaseManager
from etl.identity.name_normalization import (
    normalize_org_name, 
    normalize_country_for_org,
    get_org_country
)

logger = logging.getLogger(__name__)

# Configuration constants
FUZZY_MATCH_THRESHOLD = 0.8  # pg_trgm similarity threshold
DEFAULT_BATCH_SIZE = 5000
SUPPORTED_COUNTRIES = ('INDIA', 'KENYA', 'INDONESIA')


@dataclass
class OrganizationCandidate:
    """Represents a candidate organization to be resolved"""
    raw_name: str
    name_normalized: str
    country_iso: str
    role: str  # BUYER or SUPPLIER
    source_std_ids: Set[int] = field(default_factory=set)
    
    def __hash__(self):
        return hash((self.name_normalized, self.country_iso))
    
    def __eq__(self, other):
        return (self.name_normalized == other.name_normalized and 
                self.country_iso == other.country_iso)


@dataclass
class ResolutionResult:
    """Result of identity resolution"""
    org_uuid: uuid.UUID
    name_normalized: str
    country_iso: str
    org_type: str
    is_new: bool
    match_type: str  # 'exact', 'fuzzy', 'new'
    raw_name_variants: List[str] = field(default_factory=list)


@dataclass
class IdentityResolutionSummary:
    """Summary statistics from identity resolution run"""
    total_buyers_processed: int = 0
    total_suppliers_processed: int = 0
    new_organizations_created: int = 0
    existing_orgs_matched_exact: int = 0
    existing_orgs_matched_fuzzy: int = 0
    type_updates_to_mixed: int = 0
    shipments_updated_buyer_uuid: int = 0
    shipments_updated_supplier_uuid: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_buyers_processed': self.total_buyers_processed,
            'total_suppliers_processed': self.total_suppliers_processed,
            'new_organizations_created': self.new_organizations_created,
            'existing_orgs_matched_exact': self.existing_orgs_matched_exact,
            'existing_orgs_matched_fuzzy': self.existing_orgs_matched_fuzzy,
            'type_updates_to_mixed': self.type_updates_to_mixed,
            'shipments_updated_buyer_uuid': self.shipments_updated_buyer_uuid,
            'shipments_updated_supplier_uuid': self.shipments_updated_supplier_uuid,
            'errors': self.errors
        }


class IdentityResolutionEngine:
    """
    Main engine for resolving organization identities.
    
    Process:
    1. Extract distinct buyer/supplier names from standardized shipments lacking UUIDs
    2. Normalize names
    3. Match against existing organizations (exact then fuzzy)
    4. Insert new organizations
    5. Update type to MIXED if org appears in both roles
    6. Write back UUIDs to shipments
    """
    
    def __init__(
        self, 
        db_manager: DatabaseManager,
        batch_size: int = DEFAULT_BATCH_SIZE,
        fuzzy_threshold: float = FUZZY_MATCH_THRESHOLD,
        enable_fuzzy: bool = True
    ):
        self.db_manager = db_manager
        self.batch_size = batch_size
        self.fuzzy_threshold = fuzzy_threshold
        self.enable_fuzzy = enable_fuzzy
        self.summary = IdentityResolutionSummary()
        
        # Cache for resolved organizations
        self._org_cache: Dict[Tuple[str, str], uuid.UUID] = {}
        
    def run(self) -> IdentityResolutionSummary:
        """
        Execute the full identity resolution pipeline.
        
        Returns:
            IdentityResolutionSummary with statistics
        """
        logger.info("=" * 60)
        logger.info("EPIC 3: Identity Resolution Engine - Starting")
        logger.info("=" * 60)
        
        try:
            # Step 1: Extract candidates
            logger.info("Step 1: Extracting organization candidates...")
            buyer_candidates = self._extract_buyer_candidates()
            supplier_candidates = self._extract_supplier_candidates()
            
            self.summary.total_buyers_processed = len(buyer_candidates)
            self.summary.total_suppliers_processed = len(supplier_candidates)
            
            logger.info(f"  Found {len(buyer_candidates)} distinct buyers to resolve")
            logger.info(f"  Found {len(supplier_candidates)} distinct suppliers to resolve")
            
            # Combine all candidates for processing
            all_candidates = list(buyer_candidates.values()) + list(supplier_candidates.values())
            
            if not all_candidates:
                logger.info("No organizations to process. All UUIDs already assigned.")
                return self.summary
            
            # Step 2: Resolve organizations
            logger.info("Step 2: Resolving organizations...")
            resolution_map = self._resolve_organizations(all_candidates)
            
            # Step 3: Update organization types to MIXED where needed
            logger.info("Step 3: Checking for MIXED type updates...")
            self._update_mixed_types(buyer_candidates, supplier_candidates, resolution_map)
            
            # Step 4: Write back UUIDs to shipments
            logger.info("Step 4: Writing UUIDs back to shipments...")
            self._update_shipment_uuids(buyer_candidates, supplier_candidates, resolution_map)
            
            logger.info("=" * 60)
            logger.info("Identity Resolution Complete!")
            logger.info(f"  New orgs created: {self.summary.new_organizations_created}")
            logger.info(f"  Exact matches: {self.summary.existing_orgs_matched_exact}")
            logger.info(f"  Fuzzy matches: {self.summary.existing_orgs_matched_fuzzy}")
            logger.info(f"  Type→MIXED updates: {self.summary.type_updates_to_mixed}")
            logger.info(f"  Shipments updated (buyer): {self.summary.shipments_updated_buyer_uuid}")
            logger.info(f"  Shipments updated (supplier): {self.summary.shipments_updated_supplier_uuid}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Identity resolution failed: {e}", exc_info=True)
            self.summary.errors.append(str(e))
            
        return self.summary
    
    def _extract_buyer_candidates(self) -> Dict[Tuple[str, str], OrganizationCandidate]:
        """
        Extract distinct buyer names from shipments missing buyer_uuid.
        
        Returns:
            Dict mapping (normalized_name, country) to OrganizationCandidate
        """
        candidates = {}
        
        query = """
            SELECT 
                std_id,
                buyer_name_raw,
                destination_country,
                reporting_country,
                direction
            FROM stg_shipments_standardized
            WHERE reporting_country IN %s
              AND buyer_name_raw IS NOT NULL
              AND buyer_uuid IS NULL
        """
        
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (SUPPORTED_COUNTRIES,))
                rows = cur.fetchall()
                
                for row in rows:
                    std_id, raw_name, dest_country, reporting_country, direction = row
                    
                    normalized = normalize_org_name(raw_name)
                    if not normalized:
                        continue
                    
                    # Buyer country is destination country for exports, 
                    # or reporting country for imports
                    country = get_org_country(
                        'BUYER', direction, 
                        None, dest_country, reporting_country
                    )
                    if not country:
                        country = normalize_country_for_org(dest_country or reporting_country)
                    
                    if not country:
                        continue
                    
                    key = (normalized, country)
                    if key not in candidates:
                        candidates[key] = OrganizationCandidate(
                            raw_name=raw_name,
                            name_normalized=normalized,
                            country_iso=country,
                            role='BUYER',
                            source_std_ids=set()
                        )
                    candidates[key].source_std_ids.add(std_id)
        
        return candidates
    
    def _extract_supplier_candidates(self) -> Dict[Tuple[str, str], OrganizationCandidate]:
        """
        Extract distinct supplier names from shipments missing supplier_uuid.
        
        Returns:
            Dict mapping (normalized_name, country) to OrganizationCandidate
        """
        candidates = {}
        
        query = """
            SELECT 
                std_id,
                supplier_name_raw,
                origin_country,
                reporting_country,
                direction
            FROM stg_shipments_standardized
            WHERE reporting_country IN %s
              AND supplier_name_raw IS NOT NULL
              AND supplier_uuid IS NULL
        """
        
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (SUPPORTED_COUNTRIES,))
                rows = cur.fetchall()
                
                for row in rows:
                    std_id, raw_name, origin_country, reporting_country, direction = row
                    
                    normalized = normalize_org_name(raw_name)
                    if not normalized:
                        continue
                    
                    # Supplier country is origin country for imports,
                    # or reporting country for exports
                    country = get_org_country(
                        'SUPPLIER', direction, 
                        origin_country, None, reporting_country
                    )
                    if not country:
                        country = normalize_country_for_org(origin_country or reporting_country)
                    
                    if not country:
                        continue
                    
                    key = (normalized, country)
                    if key not in candidates:
                        candidates[key] = OrganizationCandidate(
                            raw_name=raw_name,
                            name_normalized=normalized,
                            country_iso=country,
                            role='SUPPLIER',
                            source_std_ids=set()
                        )
                    candidates[key].source_std_ids.add(std_id)
        
        return candidates
    
    def _resolve_organizations(
        self, 
        candidates: List[OrganizationCandidate]
    ) -> Dict[Tuple[str, str], ResolutionResult]:
        """
        Resolve organization candidates against existing master data.
        
        Process:
        1. Batch exact matching
        2. Fuzzy matching for unmatched (if enabled)
        3. Insert new organizations for remaining unmatched
        
        Returns:
            Dict mapping (normalized_name, country) to ResolutionResult
        """
        resolution_map: Dict[Tuple[str, str], ResolutionResult] = {}
        unmatched: List[OrganizationCandidate] = []
        
        # Step 1: Bulk exact match
        logger.info("  Performing bulk exact matching...")
        exact_matched, unmatched = self._bulk_exact_match(candidates)
        resolution_map.update(exact_matched)
        self.summary.existing_orgs_matched_exact = len(exact_matched)
        logger.info(f"    Exact matches: {len(exact_matched)}")
        
        # Step 2: Fuzzy match for unmatched
        if self.enable_fuzzy and unmatched:
            logger.info(f"  Performing fuzzy matching for {len(unmatched)} unmatched...")
            fuzzy_matched, still_unmatched = self._bulk_fuzzy_match(unmatched)
            resolution_map.update(fuzzy_matched)
            self.summary.existing_orgs_matched_fuzzy = len(fuzzy_matched)
            unmatched = still_unmatched
            logger.info(f"    Fuzzy matches: {len(fuzzy_matched)}")
        
        # Step 3: Insert new organizations for remaining unmatched
        if unmatched:
            logger.info(f"  Creating {len(unmatched)} new organizations...")
            new_orgs = self._insert_new_organizations(unmatched)
            resolution_map.update(new_orgs)
            self.summary.new_organizations_created = len(new_orgs)
        
        return resolution_map
    
    def _bulk_exact_match(
        self, 
        candidates: List[OrganizationCandidate]
    ) -> Tuple[Dict[Tuple[str, str], ResolutionResult], List[OrganizationCandidate]]:
        """
        Perform bulk exact matching against organizations_master.
        
        Returns:
            Tuple of (matched_results, unmatched_candidates)
        """
        matched = {}
        unmatched = []
        
        if not candidates:
            return matched, unmatched
        
        # Build lookup sets
        names = list(set(c.name_normalized for c in candidates))
        countries = list(set(c.country_iso for c in candidates))
        
        # Query existing organizations
        query = """
            SELECT org_uuid, name_normalized, country_iso, type, raw_name_variants
            FROM organizations_master
            WHERE country_iso = ANY(%s)
              AND name_normalized = ANY(%s)
        """
        
        existing_orgs: Dict[Tuple[str, str], Tuple] = {}
        
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (countries, names))
                for row in cur.fetchall():
                    org_uuid, name_norm, country, org_type, variants = row
                    existing_orgs[(name_norm, country)] = (org_uuid, org_type, variants)
        
        # Match candidates
        for candidate in candidates:
            key = (candidate.name_normalized, candidate.country_iso)
            if key in existing_orgs:
                org_uuid, org_type, variants = existing_orgs[key]
                matched[key] = ResolutionResult(
                    org_uuid=org_uuid,
                    name_normalized=candidate.name_normalized,
                    country_iso=candidate.country_iso,
                    org_type=org_type,
                    is_new=False,
                    match_type='exact',
                    raw_name_variants=variants if variants else []
                )
                # Update cache
                self._org_cache[key] = org_uuid
            else:
                unmatched.append(candidate)
        
        return matched, unmatched
    
    def _bulk_fuzzy_match(
        self, 
        candidates: List[OrganizationCandidate]
    ) -> Tuple[Dict[Tuple[str, str], ResolutionResult], List[OrganizationCandidate]]:
        """
        Perform fuzzy matching using pg_trgm similarity.
        
        This queries each candidate individually but uses prepared statements
        for efficiency. In a future version, could be optimized with lateral joins.
        
        Returns:
            Tuple of (matched_results, still_unmatched_candidates)
        """
        matched = {}
        still_unmatched = []
        
        query = """
            SELECT org_uuid, name_normalized, country_iso, type, raw_name_variants,
                   similarity(name_normalized, %s) AS sim
            FROM organizations_master
            WHERE country_iso = %s
              AND similarity(name_normalized, %s) >= %s
            ORDER BY sim DESC
            LIMIT 1
        """
        
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                for candidate in candidates:
                    cur.execute(
                        query, 
                        (candidate.name_normalized, candidate.country_iso,
                         candidate.name_normalized, self.fuzzy_threshold)
                    )
                    row = cur.fetchone()
                    
                    if row:
                        org_uuid, name_norm, country, org_type, variants, sim = row
                        key = (candidate.name_normalized, candidate.country_iso)
                        
                        # Use the matched org's key for resolution
                        matched[key] = ResolutionResult(
                            org_uuid=org_uuid,
                            name_normalized=name_norm,  # Keep original name
                            country_iso=country,
                            org_type=org_type,
                            is_new=False,
                            match_type='fuzzy',
                            raw_name_variants=variants if variants else []
                        )
                        
                        # Update variants with new raw name if different
                        self._add_name_variant(
                            cur, org_uuid, candidate.raw_name, candidate.role
                        )
                        
                        self._org_cache[key] = org_uuid
                    else:
                        still_unmatched.append(candidate)
        
        return matched, still_unmatched
    
    def _add_name_variant(
        self, 
        cur, 
        org_uuid: uuid.UUID, 
        raw_name: str, 
        role: str
    ) -> None:
        """Add a new raw name variant to an existing organization."""
        # Fetch current variants
        cur.execute(
            "SELECT raw_name_variants FROM organizations_master WHERE org_uuid = %s",
            (str(org_uuid),)
        )
        row = cur.fetchone()
        if not row:
            return
        
        variants = row[0] if row[0] else {}
        if isinstance(variants, list):
            # Convert old list format to dict format
            variants = {'variants': variants}
        
        role_key = role.lower()
        if role_key not in variants:
            variants[role_key] = []
        
        if raw_name not in variants[role_key]:
            variants[role_key].append(raw_name)
            
            cur.execute(
                """
                UPDATE organizations_master 
                SET raw_name_variants = %s, updated_at = CURRENT_TIMESTAMP
                WHERE org_uuid = %s
                """,
                (json.dumps(variants), str(org_uuid))
            )
    
    def _insert_new_organizations(
        self, 
        candidates: List[OrganizationCandidate]
    ) -> Dict[Tuple[str, str], ResolutionResult]:
        """
        Insert new organizations for unmatched candidates.
        
        Returns:
            Dict mapping (normalized_name, country) to ResolutionResult
        """
        results = {}
        
        if not candidates:
            return results
        
        # Prepare bulk insert data
        insert_data = []
        for candidate in candidates:
            new_uuid = uuid.uuid4()
            variants = {candidate.role.lower(): [candidate.raw_name]}
            
            insert_data.append((
                str(new_uuid),
                candidate.name_normalized,
                candidate.country_iso,
                candidate.role,  # Initial type matches role
                json.dumps(variants)
            ))
            
            key = (candidate.name_normalized, candidate.country_iso)
            results[key] = ResolutionResult(
                org_uuid=new_uuid,
                name_normalized=candidate.name_normalized,
                country_iso=candidate.country_iso,
                org_type=candidate.role,
                is_new=True,
                match_type='new',
                raw_name_variants=variants
            )
            self._org_cache[key] = new_uuid
        
        # Bulk insert
        insert_query = """
            INSERT INTO organizations_master 
            (org_uuid, name_normalized, country_iso, type, raw_name_variants, created_at, updated_at)
            VALUES %s
            ON CONFLICT (name_normalized, country_iso) DO NOTHING
        """
        
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    execute_values(
                        cur, 
                        insert_query,
                        [(d[0], d[1], d[2], d[3], d[4]) for d in insert_data],
                        template="(%s, %s, %s, %s, %s, NOW(), NOW())"
                    )
                    logger.info(f"    Inserted {len(insert_data)} new organizations")
                except Exception as e:
                    logger.error(f"Failed to insert organizations: {e}")
                    raise
        
        return results
    
    def _update_mixed_types(
        self,
        buyer_candidates: Dict[Tuple[str, str], OrganizationCandidate],
        supplier_candidates: Dict[Tuple[str, str], OrganizationCandidate],
        resolution_map: Dict[Tuple[str, str], ResolutionResult]
    ) -> None:
        """
        Update organization type to MIXED if org appears in both buyer and supplier roles.
        """
        # Find organizations that appear in both roles
        buyer_keys = set(buyer_candidates.keys())
        supplier_keys = set(supplier_candidates.keys())
        both_roles = buyer_keys & supplier_keys
        
        if not both_roles:
            logger.info("    No organizations need MIXED type update")
            return
        
        # Get UUIDs that need updating to MIXED
        uuids_to_update = []
        for key in both_roles:
            if key in resolution_map:
                result = resolution_map[key]
                if result.org_type != 'MIXED':
                    uuids_to_update.append(str(result.org_uuid))
        
        if not uuids_to_update:
            return
        
        # Bulk update type to MIXED
        update_query = """
            UPDATE organizations_master
            SET type = 'MIXED', updated_at = CURRENT_TIMESTAMP
            WHERE org_uuid = ANY(%s::uuid[])
              AND type != 'MIXED'
        """
        
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(update_query, (uuids_to_update,))
                updated = cur.rowcount
            self.summary.type_updates_to_mixed = updated
            logger.info(f"    Updated {updated} organizations to MIXED type")
    
    def _update_shipment_uuids(
        self,
        buyer_candidates: Dict[Tuple[str, str], OrganizationCandidate],
        supplier_candidates: Dict[Tuple[str, str], OrganizationCandidate],
        resolution_map: Dict[Tuple[str, str], ResolutionResult]
    ) -> None:
        """
        Write back resolved UUIDs to shipments in stg_shipments_standardized.
        """
        # Update buyer UUIDs
        logger.info("    Updating buyer UUIDs...")
        buyer_updates = self._prepare_uuid_updates(buyer_candidates, resolution_map)
        if buyer_updates:
            updated = self._bulk_update_uuids(buyer_updates, 'buyer_uuid')
            self.summary.shipments_updated_buyer_uuid = updated
            logger.info(f"      Updated {updated} shipments with buyer_uuid")
        
        # Update supplier UUIDs
        logger.info("    Updating supplier UUIDs...")
        supplier_updates = self._prepare_uuid_updates(supplier_candidates, resolution_map)
        if supplier_updates:
            updated = self._bulk_update_uuids(supplier_updates, 'supplier_uuid')
            self.summary.shipments_updated_supplier_uuid = updated
            logger.info(f"      Updated {updated} shipments with supplier_uuid")
    
    def _prepare_uuid_updates(
        self,
        candidates: Dict[Tuple[str, str], OrganizationCandidate],
        resolution_map: Dict[Tuple[str, str], ResolutionResult]
    ) -> List[Tuple[List[int], str]]:
        """
        Prepare (std_ids, uuid) pairs for bulk update.
        
        Returns:
            List of (std_id_list, org_uuid_str) tuples
        """
        updates = []
        
        for key, candidate in candidates.items():
            if key in resolution_map:
                result = resolution_map[key]
                if candidate.source_std_ids:
                    updates.append((
                        list(candidate.source_std_ids),
                        str(result.org_uuid)
                    ))
        
        return updates
    
    def _bulk_update_uuids(
        self, 
        updates: List[Tuple[List[int], str]], 
        uuid_column: str
    ) -> int:
        """
        Bulk update UUID column in stg_shipments_standardized.
        
        Args:
            updates: List of (std_id_list, org_uuid) tuples
            uuid_column: 'buyer_uuid' or 'supplier_uuid'
            
        Returns:
            Total number of rows updated
        """
        if not updates:
            return 0
        
        total_updated = 0
        
        # Process in batches
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    for std_ids, org_uuid in updates:
                        # Batch the std_ids updates
                        for i in range(0, len(std_ids), self.batch_size):
                            batch_ids = std_ids[i:i + self.batch_size]
                            
                            query = f"""
                                UPDATE stg_shipments_standardized
                                SET {uuid_column} = %s
                                WHERE std_id = ANY(%s)
                                  AND {uuid_column} IS NULL
                            """
                            
                            cur.execute(query, (org_uuid, batch_ids))
                            total_updated += cur.rowcount
                except Exception as e:
                    logger.error(f"Failed to update {uuid_column}: {e}")
                    raise
        
        return total_updated


def run_identity_resolution(
    db_config_path: str = "config/db_config.yml",
    batch_size: int = DEFAULT_BATCH_SIZE,
    enable_fuzzy: bool = True,
    fuzzy_threshold: float = FUZZY_MATCH_THRESHOLD
) -> Dict[str, Any]:
    """
    Main entry point for identity resolution.
    
    Args:
        db_config_path: Path to database configuration file
        batch_size: Number of records to process per batch
        enable_fuzzy: Whether to enable fuzzy matching
        fuzzy_threshold: Similarity threshold for fuzzy matching (0.0-1.0)
        
    Returns:
        Summary dictionary with resolution statistics
    """
    logger.info(f"Initializing Identity Resolution Engine")
    logger.info(f"  Config: {db_config_path}")
    logger.info(f"  Batch size: {batch_size}")
    logger.info(f"  Fuzzy matching: {'enabled' if enable_fuzzy else 'disabled'}")
    if enable_fuzzy:
        logger.info(f"  Fuzzy threshold: {fuzzy_threshold}")
    
    db_manager = DatabaseManager(db_config_path)
    
    try:
        engine = IdentityResolutionEngine(
            db_manager=db_manager,
            batch_size=batch_size,
            fuzzy_threshold=fuzzy_threshold,
            enable_fuzzy=enable_fuzzy
        )
        
        summary = engine.run()
        return summary.to_dict()
        
    finally:
        db_manager.close()


# CLI entrypoint
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='EPIC 3: Identity Resolution Engine')
    parser.add_argument('--config', default='config/db_config.yml', help='Database config path')
    parser.add_argument('--batch-size', type=int, default=5000, help='Batch size')
    parser.add_argument('--no-fuzzy', action='store_true', help='Disable fuzzy matching')
    parser.add_argument('--fuzzy-threshold', type=float, default=0.8, help='Fuzzy match threshold')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    result = run_identity_resolution(
        db_config_path=args.config,
        batch_size=args.batch_size,
        enable_fuzzy=not args.no_fuzzy,
        fuzzy_threshold=args.fuzzy_threshold
    )
    
    print("\n" + "=" * 60)
    print("Identity Resolution Summary")
    print("=" * 60)
    for key, value in result.items():
        print(f"  {key}: {value}")
