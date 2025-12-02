# GTI-OS Setup Guide for Windows

Complete step-by-step setup guide for Windows 10/11.

---

## Prerequisites Installation

### 1. Install Python 3.10+

**Download:**
- Visit: https://www.python.org/downloads/
- Download Python 3.10 or newer (3.11 recommended)

**Install:**
- ✅ Check "Add Python to PATH"
- Choose "Customize installation"
- ✅ Enable "pip"
- ✅ Enable "py launcher"
- Install

**Verify:**
```powershell
python --version
# Should show: Python 3.10.x or 3.11.x
```

### 2. Install PostgreSQL 13+

**Download:**
- Visit: https://www.postgresql.org/download/windows/
- Download installer (version 13, 14, 15, or 16)

**Install:**
- Note your password for `postgres` user
- Port: 5432 (default)
- Locale: English, United States

**Verify:**
```powershell
# Check service is running
Get-Service -Name postgresql*

# Should show: Running
```

**Test Connection:**
```powershell
# Open SQL Shell (psql) from Start Menu
# Press Enter for defaults, enter your password
psql -U postgres

# You should see:
# postgres=#
```

### 3. Install Git (Optional)

**Download:**
- Visit: https://git-scm.com/download/win
- Download and install

---

## Project Setup

### Step 1: Navigate to Project

```powershell
# Open PowerShell
# Navigate to project directory
cd "e:\Port Data Brain"

# List files to verify
ls
```

### Step 2: Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1
```

**If you get execution policy error:**
```powershell
# Run this first (as Administrator):
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try activate again:
.\venv\Scripts\Activate.ps1
```

**Your prompt should change to:**
```
(venv) PS E:\Port Data Brain>
```

### Step 3: Install Dependencies

```powershell
# Ensure pip is updated
python -m pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt
```

**This will install:**
- polars (data processing)
- pandas (data processing)
- sqlalchemy (database ORM)
- psycopg2-binary (PostgreSQL driver)
- pyyaml (config files)
- openpyxl (Excel support)
- And more...

**Wait 2-5 minutes for installation.**

### Step 4: Create Configuration Files

```powershell
# Copy example configs
Copy-Item config\db_config.example.yml config\db_config.yml
Copy-Item config\ingestion_config.example.yml config\ingestion_config.yml
```

### Step 5: Edit Database Config

**Open `config\db_config.yml` in Notepad or VS Code:**

```powershell
notepad config\db_config.yml
```

**Update password:**
```yaml
database:
  host: localhost
  port: 5432
  database: aaziko_trade
  user: postgres
  password: YOUR_POSTGRES_PASSWORD_HERE  # ← Change this!
```

**Save and close.**

### Step 6: Setup Database

```powershell
# This will:
# 1. Create 'aaziko_trade' database
# 2. Apply all schemas (15+ tables)
python scripts\setup_database.py
```

**Expected output:**
```
============================================================
GTI-OS Data Platform - Database Setup
============================================================
Step 1: Creating database 'aaziko_trade' if not exists...
Database 'aaziko_trade' created successfully
Step 2: Applying schema from db/schema_v1.sql...
Schema applied from db/schema_v1.sql
============================================================
✓ Database setup completed successfully!
============================================================
```

### Step 7: Verify Setup

```powershell
python scripts\verify_setup.py
```

**Expected output:**
```
============================================================
GTI-OS Data Platform - Setup Verification
============================================================
✓ Database connection successful

Checking tables...
  ✓ file_registry                   (         0 rows)
  ✓ stg_shipments_raw               (         0 rows)
  ✓ stg_shipments_standardized      (         0 rows)
  ...
  
✓ All expected tables exist!
============================================================
```

---

## Testing with Sample Data

### Step 1: Generate Sample Files

```powershell
python scripts\create_sample_data.py
```

**This creates:**
- `data/raw/india/export/2023/01/india_export_202301.xlsx` (5000 rows)
- `data/raw/india/export/2023/02/india_export_202302.csv` (3000 rows)
- `data/raw/kenya/import/2023/01/kenya_import_202301.xlsx` (2000 rows)

### Step 2: Dry Run (Scan Only)

```powershell
python scripts\run_ingestion.py --dry-run
```

**Output shows discovered files without ingesting:**
```
Scanning directory: e:/Port Data Brain/data/raw
Found 3 file(s) to process
DRY RUN MODE - Files discovered:
  - india_export_202301.xlsx
  - india_export_202302.csv
  - kenya_import_202301.xlsx
```

### Step 3: Run Ingestion

```powershell
python scripts\run_ingestion.py
```

**Expected output:**
```
[1/3] Processing: india_export_202301.xlsx
Processing chunk 1/1 (5000 rows)
✓ Ingested 5000 rows

[2/3] Processing: india_export_202302.csv
Processing chunk 1/1 (3000 rows)
✓ Ingested 3000 rows

[3/3] Processing: kenya_import_202301.xlsx
Processing chunk 1/1 (2000 rows)
✓ Ingested 2000 rows

============================================================
INGESTION SUMMARY
============================================================
Total files processed:  3
  ✓ Successfully ingested: 3
  ⊗ Duplicates skipped:    0
  ✗ Failed:                0
Total rows ingested:    10,000
Duration:               12.34 seconds
Throughput:             810 rows/sec
============================================================
```

### Step 4: Verify Data in Database

```powershell
# Connect to database
psql -U postgres -d aaziko_trade
```

**Run queries:**
```sql
-- Check file registry
SELECT * FROM file_registry;

-- Count raw rows
SELECT COUNT(*) FROM stg_shipments_raw;

-- Sample data
SELECT 
    raw_file_name, 
    reporting_country, 
    direction,
    raw_data->>'hs_code' as hs_code,
    raw_data->>'buyer_name' as buyer
FROM stg_shipments_raw
LIMIT 5;

-- Exit
\q
```

---

## Common Issues & Solutions

### Issue 1: "python: command not found"

**Solution:**
```powershell
# Check if python is in PATH
$env:Path

# If not, add manually or reinstall Python with "Add to PATH"
```

### Issue 2: "Activate.ps1 cannot be loaded"

**Solution:**
```powershell
# Run as Administrator:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate:
.\venv\Scripts\Activate.ps1
```

### Issue 3: "ModuleNotFoundError: No module named 'polars'"

**Solution:**
```powershell
# Ensure venv is activated (should see (venv) in prompt)
.\venv\Scripts\Activate.ps1

# Reinstall requirements
pip install -r requirements.txt
```

### Issue 4: "psycopg2.OperationalError: could not connect"

**Solution:**
1. Check PostgreSQL is running:
   ```powershell
   Get-Service postgresql*
   ```

2. If stopped, start it:
   ```powershell
   Start-Service postgresql-x64-13  # Adjust version
   ```

3. Check credentials in `config\db_config.yml`

### Issue 5: "FileNotFoundError: config/db_config.yml"

**Solution:**
```powershell
# Copy from example
Copy-Item config\db_config.example.yml config\db_config.yml

# Edit with your password
notepad config\db_config.yml
```

### Issue 6: "Permission denied" on data/raw

**Solution:**
```powershell
# Create directories manually
mkdir data\raw\india\export\2023\01 -Force
```

---

## Daily Workflow

### Activate Environment
```powershell
cd "e:\Port Data Brain"
.\venv\Scripts\Activate.ps1
```

### Run Ingestion
```powershell
# Add new files to data/raw/{country}/{direction}/{year}/{month}/
# Then run:
python scripts\run_ingestion.py
```

### Check Logs
```powershell
# View recent logs
Get-Content logs\ingestion.log -Tail 50

# Search errors
Select-String -Path logs\ingestion.log -Pattern "ERROR"
```

### Query Database
```powershell
psql -U postgres -d aaziko_trade
```

---

## Next Steps

✅ **EPIC 0-1 Complete!**

**Next task:** EPIC 2 – Standardization Engine
- Country-specific column mapping
- Data normalization (HS codes, dates, currencies)
- Populate `stg_shipments_standardized`

---

## Support Checklist

If something doesn't work:

- [ ] Python 3.10+ installed and in PATH?
- [ ] PostgreSQL running? (`Get-Service postgresql*`)
- [ ] Virtual environment activated? (see `(venv)` in prompt)
- [ ] Dependencies installed? (`pip list | Select-String polars`)
- [ ] Config files created? (`ls config\db_config.yml`)
- [ ] Database created? (check with pgAdmin or psql)
- [ ] Logs checked? (`logs\ingestion.log`)

---

**Ready to ingest trade data! 🚀**
