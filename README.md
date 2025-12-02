# GTI-OS Data Platform v1.0

**Global Trade Intelligence – Data Platform**  
Production-grade trade data ingestion, standardization, and analytics system.

---

## 🎯 Current Implementation Status

✅ **EPIC 0 – Foundation & Environment** (Complete)  
✅ **EPIC 1 – Bulk Ingestion (Staging)** (Complete)  
✅ **EPIC 2 – Standardization Engine** (Complete)  
⏳ **EPIC 3-9** (Pending future implementation)

---

## 📋 Architecture Overview

GTI-OS is a 9-phase data platform designed to:

1. **Ingest** 47+ countries' import/export data (8+ years, Excel/CSV)
2. **Standardize** disparate formats into unified schema
3. **Resolve** buyer/supplier identities with UUIDs
4. **Build** global trades ledger fact table
5. **Unmask** hidden buyers via Global Mirror Algorithm
6. **Generate** analytics: buyer profiles, price corridors, risk scores
7. **Serve** clean data to LLMs and APIs

### Current Implementation (EPIC 0-2)

```
data/raw/{country}/{direction}/{year}/{month}/*.xlsx
    ↓
[File Registry + Checksum Deduplication]
    ↓
[Chunked Reading (Polars)]
    ↓
[Bulk Insert (PostgreSQL COPY)]
    ↓
stg_shipments_raw (JSON + metadata)
    ↓
[Country-Specific YAML Mapping]
    ↓
[Column Mapping + Unit Conversions]
    ↓
[HS Normalization + Date Parsing]
    ↓
stg_shipments_standardized (normalized schema)
```

---

## 🚀 Quick Start (Windows)

### Prerequisites

- **Python 3.10+** installed and in PATH
- **PostgreSQL 13+** installed and running
- **Git** (optional, for version control)

### Step 1: Clone/Setup Project

```powershell
# Navigate to project directory
cd "e:\Port Data Brain"

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If execution policy error, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Database

1. **Copy example configs:**
   ```powershell
   Copy-Item config\db_config.example.yml config\db_config.yml
   Copy-Item config\ingestion_config.example.yml config\ingestion_config.yml
   ```

2. **Edit `config/db_config.yml`:**
   ```yaml
   database:
     host: localhost
     port: 5432
     database: aaziko_trade
     user: postgres
     password: YOUR_PASSWORD_HERE  # ← Change this
   ```

3. **Edit `config/ingestion_config.yml`:**
   ```yaml
   ingestion:
     raw_data_root: "e:/Port Data Brain/data/raw"  # ← Adjust if needed
     chunk_size: 50000
   ```

### Step 3: Setup Database

```powershell
# Create database and apply schema
python scripts\setup_database.py

# Verify setup
python scripts\verify_setup.py
```

**Expected output:**
```
✓ Database connection successful
✓ file_registry                   (0 rows)
✓ stg_shipments_raw               (0 rows)
✓ stg_shipments_standardized      (0 rows)
...
✓ All expected tables exist!
```

### Step 4: Prepare Sample Data

Create sample data directory structure:

```powershell
# Create sample data folders
mkdir -p data\raw\india\export\2023\01
mkdir -p data\raw\kenya\import\2023\01
```

Place your Excel/CSV files in appropriate folders:
- `data/raw/india/export/2023/01/india_exports_jan2023.xlsx`
- `data/raw/kenya/import/2023/01/kenya_imports_jan2023.csv`

### Step 5: Run Ingestion

```powershell
# Dry run (scan only, no ingestion)
python scripts\run_ingestion.py --dry-run

# Full ingestion
python scripts\run_ingestion.py
```

**Expected output:**
```
[1/2] Processing: india_exports_jan2023.xlsx
Processing chunk 1/3 (50000 rows)
Processing chunk 2/3 (50000 rows)
Processing chunk 3/3 (15234 rows)
✓ Ingested 115234 rows

[2/2] Processing: kenya_imports_jan2023.csv
Processing chunk 1/1 (23451 rows)
✓ Ingested 23451 rows

============================================================
INGESTION SUMMARY
============================================================
Total files processed:  2
  ✓ Successfully ingested: 2
  ⊗ Duplicates skipped:    0
  ✗ Failed:                0
Total rows ingested:    138,685
Duration:               45.23 seconds
Throughput:             3066 rows/sec
============================================================
```

### Step 6: Run Standardization (EPIC 2)

After ingestion, standardize the raw data:

```powershell
# Run standardization pipeline
python scripts\run_standardization.py
```

**Expected output:**
```
============================================================
GTI-OS Data Platform - Standardization Pipeline Started
============================================================
Database connection established
Raw rows in staging: 10,000
Already standardized rows: 0
Rows to standardize: 10,000

Processing: INDIA EXPORT (FULL)
Standardizing 5000 rows for INDIA EXPORT
Standardization complete: 5000 rows processed
Inserted 5000 standardized rows

Processing: KENYA IMPORT (FULL)
Standardizing 2000 rows for KENYA IMPORT
Standardization complete: 2000 rows processed
Inserted 2000 standardized rows

============================================================
STANDARDIZATION SUMMARY
============================================================
Groups processed:          2
Groups skipped:            0
Total rows standardized:   10,000
Duration:                  8.45 seconds
Throughput:                1183 rows/sec
============================================================
```

**Verify standardization:**
```powershell
psql -U postgres -d aaziko_trade
```

```sql
-- Check standardized counts
SELECT COUNT(*) FROM stg_shipments_standardized;

-- Sample normalized data
SELECT 
    hs_code_raw, 
    hs_code_6, 
    qty_raw, 
    qty_kg, 
    customs_value_usd, 
    price_usd_per_kg
FROM stg_shipments_standardized
LIMIT 10;

-- Check standardization progress
SELECT 
    reporting_country,
    direction,
    COUNT(*) as rows,
    AVG(price_usd_per_kg) as avg_price
FROM stg_shipments_standardized
WHERE price_usd_per_kg IS NOT NULL
GROUP BY reporting_country, direction;
```

---

## 📁 Project Structure

```
Port Data Brain/
├── config/                              # Configuration files
│   ├── db_config.yml                   # Database credentials
│   ├── ingestion_config.yml            # Ingestion settings
│   ├── india_export.yml                # EPIC 2: India export mapping
│   └── kenya_import.yml                # EPIC 2: Kenya import mapping
├── data/
│   └── raw/                            # Raw data files
│       └── {country}/
│           └── {direction}/
│               └── {year}/
│                   └── {month}/
│                       └── *.xlsx, *.csv
├── db/
│   ├── schema_v1.sql                   # PostgreSQL schema DDL
│   ├── useful_queries.sql              # EPIC 0-1 queries
│   └── epic2_verification_queries.sql  # EPIC 2 validation queries
├── etl/                                # Python ETL package
│   ├── __init__.py
│   ├── db_utils.py                     # Database connection & bulk ops
│   ├── logging_config.py               # Structured logging
│   ├── ingestion/                      # EPIC 1: File ingestion
│   │   ├── __init__.py
│   │   └── ingest_files.py             # Core ingestion engine
│   ├── standardization/                # EPIC 2: Standardization ✅
│   │   ├── __init__.py
│   │   └── standardize_shipments.py    # Mapping & normalization
│   ├── identity/                       # EPIC 3: PLACEHOLDER
│   └── analytics/                      # EPIC 6+: PLACEHOLDER
├── logs/                               # Application logs
│   ├── ingestion.log
│   └── standardization.log
├── scripts/                            # Executable scripts
│   ├── setup_database.py               # Create DB + apply schema
│   ├── verify_setup.py                 # Check DB health
│   ├── run_ingestion.py                # EPIC 1: Ingestion orchestrator
│   ├── run_standardization.py          # EPIC 2: Standardization orchestrator
│   └── create_sample_data.py           # Generate test data
├── requirements.txt                    # Python dependencies
└── README.md                           # This file
```

---

## 🗄️ Database Schema (Phase 0-2)

### Operational Tables

#### `file_registry`
Tracks all ingested files with checksums for deduplication.

| Column | Type | Description |
|--------|------|-------------|
| file_id | SERIAL | Primary key |
| file_name | TEXT | Original filename |
| file_checksum | TEXT | SHA256 checksum (unique) |
| reporting_country | TEXT | Extracted from path |
| direction | TEXT | EXPORT / IMPORT |
| year, month | INTEGER | Extracted from path |
| status | TEXT | PENDING / INGESTED / FAILED |
| total_rows | INTEGER | Rows ingested |
| ingested_at | TIMESTAMP | Completion timestamp |

#### `stg_shipments_raw`
Raw data staging table with full JSON storage.

| Column | Type | Description |
|--------|------|-------------|
| raw_id | BIGSERIAL | Primary key |
| raw_file_name | TEXT | Source file |
| reporting_country | TEXT | Country code |
| direction | TEXT | EXPORT / IMPORT |
| raw_row_number | INTEGER | Original row number |
| raw_data | JSONB | Full row as JSON |
| hs_code_raw | TEXT | Pre-extracted (optional) |
| buyer_name_raw | TEXT | Pre-extracted (optional) |
| supplier_name_raw | TEXT | Pre-extracted (optional) |

---

## 🔧 Key Features (EPIC 0-1)

### ✅ Idempotent Ingestion
- SHA256 checksum prevents duplicate file ingestion
- Re-running ingestion on same files = **no duplicates**

### ✅ Efficient Bulk Loading
- **Polars** for fast data reading (10x faster than pandas)
- **PostgreSQL COPY** for bulk insert (50k+ rows/sec)
- **Chunked processing** handles files with 1M+ rows

### ✅ Robust Error Handling
- Failed files logged in `file_registry` with error messages
- Partial ingestion tracked by chunk
- Comprehensive logging to console + file

### ✅ Flexible File Formats
- `.xlsx` (Excel 2007+)
- `.xls` (Legacy Excel)
- `.csv` (UTF-8 encoded)

### ✅ Automatic Metadata Detection
- Extracts country/direction/year/month from path structure
- Configurable via YAML for custom structures

---

## 📊 Monitoring & Verification

### Check Ingestion Status

```sql
-- Total files ingested
SELECT status, COUNT(*) as count, SUM(total_rows) as total_rows
FROM file_registry
GROUP BY status;

-- Recent ingestions
SELECT file_name, reporting_country, direction, total_rows, ingested_at
FROM file_registry
WHERE status = 'INGESTED'
ORDER BY ingested_at DESC
LIMIT 10;

-- Sample raw data
SELECT raw_file_name, reporting_country, direction, raw_data
FROM stg_shipments_raw
LIMIT 5;
```

### Check Logs

```powershell
# View recent logs
Get-Content logs\ingestion.log -Tail 50

# Search for errors
Select-String -Path logs\ingestion.log -Pattern "ERROR"
```

---

## 🔐 Database Access

### psql (PostgreSQL CLI)

```powershell
# Connect to database
psql -h localhost -U postgres -d aaziko_trade

# Run queries
SELECT COUNT(*) FROM stg_shipments_raw;
SELECT * FROM file_registry;
```

### pgAdmin (GUI)

1. Open pgAdmin
2. Add server: `localhost:5432`
3. Connect to `aaziko_trade` database
4. Browse tables in `public` schema

---

## 🛠️ Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'polars'`

**Solution:**
```powershell
# Ensure venv is activated
.\venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: `psycopg2.OperationalError: connection refused`

**Solution:**
1. Check PostgreSQL is running:
   ```powershell
   Get-Service -Name postgresql*
   ```
2. Start if stopped:
   ```powershell
   Start-Service postgresql-x64-13  # Adjust version
   ```
3. Verify credentials in `config/db_config.yml`

### Issue: `FileNotFoundError: config/db_config.yml`

**Solution:**
```powershell
Copy-Item config\db_config.example.yml config\db_config.yml
# Edit config/db_config.yml with your credentials
```

### Issue: Files not being ingested

**Solution:**
1. Check file path structure matches:
   ```
   data/raw/{country}/{direction}/{year}/{month}/*.xlsx
   ```
2. Run dry-run to see detected files:
   ```powershell
   python scripts\run_ingestion.py --dry-run
   ```
3. Check `file_registry` for duplicates:
   ```sql
   SELECT * FROM file_registry WHERE status = 'DUPLICATE';
   ```

---

## 🎓 Implementation Notes

### Design Principles

1. **Modular Architecture**  
   Each phase is isolated in its own module (`ingestion`, `standardization`, etc.)

2. **Vectorized Operations**  
   No Python row-by-row loops—all transforms use Polars/Pandas vectorized ops

3. **Bulk Loading**  
   PostgreSQL `COPY` for maximum throughput (vs. individual INSERTs)

4. **Incremental Processing**  
   Checksum-based deduplication ensures idempotency

5. **Production-Ready**  
   - Connection pooling
   - Logging with rotation
   - Error handling with rollback
   - Progress tracking

### Extensibility (Next Steps)

**EPIC 2 – Standardization Engine** ✅ (Complete):
- Country-specific YAML configs (`config/india_export.yml`, `config/kenya_import.yml`)
- Column mapping: raw → standardized fields
- Data normalization: HS codes, dates, weights, currencies
- Unit conversions: weight to KG, currency to USD
- Price per kg calculation
- Populates `stg_shipments_standardized`

**EPIC 3 – Identity Engine** (Next Task):
- Batch fuzzy matching for buyer/supplier names
- UUID assignment via `organizations_master`
- Trigram similarity indexing

**EPIC 4 – Global Trades Ledger**:
- Promote standardized data to `global_trades_ledger` fact table
- Single source of truth for all queries

**EPIC 5+ – Analytics & Serving**:
- Mirror algorithm for hidden buyers
- Buyer/exporter profiles
- Price corridors, risk scores
- LLM-ready views and APIs

---

## 📚 Additional Resources

### Database Schema Reference

Full schema: `db/schema_v1.sql`

Key tables for Phase 0-2:
- `file_registry` – File tracking
- `stg_shipments_raw` – Raw staging with JSON
- `stg_shipments_standardized` – Normalized data
- (15+ additional tables for future phases)

### Configuration Reference

**Database Config** (`config/db_config.yml`):
```yaml
database:
  host: localhost
  port: 5432
  database: aaziko_trade
  user: postgres
  password: <your-password>
  pool_size: 5
  max_overflow: 10
```

**Ingestion Config** (`config/ingestion_config.yml`):
```yaml
ingestion:
  raw_data_root: "e:/Port Data Brain/data/raw"
  chunk_size: 50000
  supported_extensions:
    - .xlsx
    - .xls
    - .csv
logging:
  level: INFO
  file: "logs/ingestion.log"
```

---

## 👥 Development Team

**Built by:** Aaziko Data Engineering Team  
**Architecture:** GTI-OS Data Platform v1.0  
**License:** Proprietary

---

## 📞 Support

For issues or questions:
1. Check logs: `logs/ingestion.log`, `logs/standardization.log`
2. Verify setup: `python scripts/verify_setup.py`
3. Review this README
4. Check database with `psql` or pgAdmin
5. Run verification queries: `db/epic2_verification_queries.sql`

---

## ✅ Phase 0-2 Checklist

**EPIC 0 - Foundation:**
- [x] PostgreSQL database created (`aaziko_trade`)
- [x] Schema applied (15+ tables, views, indexes)
- [x] Python environment setup (venv + requirements)
- [x] Configuration files created (`db_config.yml`, `ingestion_config.yml`)

**EPIC 1 - Ingestion:**
- [x] File scanning implemented
- [x] Checksum-based deduplication
- [x] Chunked file reading (Polars)
- [x] Bulk insert via COPY
- [x] File registry tracking
- [x] Logging with rotation
- [x] Error handling & rollback
- [x] Verification scripts
- [ ] Sample data prepared *(user action)*
- [ ] First successful ingestion run *(user action)*

**EPIC 2 - Standardization:**
- [x] Country-specific YAML mapping configs created
- [x] HS code normalization (6-digit extraction)
- [x] Country name normalization
- [x] Date parsing with multiple formats
- [x] Weight conversion to KG
- [x] Currency conversion to USD
- [x] Price per kg calculation
- [x] TEU estimation
- [x] Bulk insert to stg_shipments_standardized
- [x] Standardization orchestrator script
- [x] Verification SQL queries
- [ ] First successful standardization run *(user action)*

---

**Ready to proceed to EPIC 3 – Identity Engine!**


# run control tower
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
npm run dev