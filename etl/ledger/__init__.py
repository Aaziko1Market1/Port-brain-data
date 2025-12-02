"""
GTI-OS Data Platform - Ledger Module (EPIC 4)
==============================================
Populates the global_trades_ledger fact table from standardized shipments.

Provides:
- Incremental loading from stg_shipments_standardized
- Idempotent operation via std_id tracking
- Batch-based processing for efficiency
"""

from etl.ledger.load_global_trades import (
    load_global_trades,
    GlobalTradesLoader,
    LedgerLoadSummary,
)

__all__ = [
    'load_global_trades',
    'GlobalTradesLoader',
    'LedgerLoadSummary',
]
