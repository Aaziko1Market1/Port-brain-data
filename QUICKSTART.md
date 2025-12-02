# GTI-OS Quick Start Guide

**Get up and running in 10 minutes.**

---

## ⚡ Prerequisites

- ✅ Python 3.10+ installed
- ✅ PostgreSQL 13+ running
- ✅ PowerShell or Command Prompt

---

## 🚀 5-Step Setup

### 1️⃣ Create Virtual Environment

```powershell
cd "e:\Port Data Brain"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2️⃣ Configure Database

```powershell
# Copy configs
Copy-Item config\db_config.example.yml config\db_config.yml
Copy-Item config\ingestion_config.example.yml config\ingestion_config.yml

# Edit db_config.yml - change YOUR_PASSWORD
notepad config\db_config.yml
```

### 3️⃣ Setup Database

```powershell
python scripts\setup_database.py
python scripts\verify_setup.py
```

### 4️⃣ Generate Sample Data

```powershell
python scripts\create_sample_data.py
```

### 5️⃣ Run Ingestion

```powershell
python scripts\run_ingestion.py
```

---

## ✅ Verify Success

```powershell
# Connect to database
psql -U postgres -d aaziko_trade

# Run query
SELECT COUNT(*) FROM stg_shipments_raw;
# Should show: 10000 (from sample data)

# Exit
\q
```

---

## 📁 Add Your Own Data

Place files in:
```
data/raw/{country}/{direction}/{year}/{month}/file.xlsx
```

Example:
```
data/raw/india/export/2024/01/my_data.xlsx
data/raw/usa/import/2024/02/shipments.csv
```

Then run:
```powershell
python scripts\run_ingestion.py
```

---

## 🔧 Common Commands

**View logs:**
```powershell
Get-Content logs\ingestion.log -Tail 50
```

**Query database:**
```powershell
psql -U postgres -d aaziko_trade
```

**Re-run setup:**
```powershell
python scripts\setup_database.py
python scripts\verify_setup.py
```

**Check what will be ingested:**
```powershell
python scripts\run_ingestion.py --dry-run
```

---

## 📊 Useful SQL Queries

See `db/useful_queries.sql` for comprehensive query examples.

**Quick check:**
```sql
-- Files ingested
SELECT status, COUNT(*) FROM file_registry GROUP BY status;

-- Total rows
SELECT COUNT(*) FROM stg_shipments_raw;

-- Sample data
SELECT * FROM stg_shipments_raw LIMIT 5;
```

---

## 🆘 Troubleshooting

**Problem:** Can't activate venv  
**Solution:** Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`

**Problem:** Can't connect to database  
**Solution:** Check PostgreSQL is running with `Get-Service postgresql*`

**Problem:** Module not found  
**Solution:** Ensure venv is activated, run `pip install -r requirements.txt`

**Full guide:** See `SETUP_WINDOWS.md`

---

## 📚 Documentation

- **Full Setup:** `SETUP_WINDOWS.md`
- **Architecture:** `README.md`
- **SQL Queries:** `db/useful_queries.sql`

---

## ✨ What's Next?

**Current Status:** EPIC 0-1 Complete ✅

**Next Phase:** EPIC 2 – Standardization Engine
- Column mapping via YAML configs
- Data normalization
- Populate `stg_shipments_standardized`

---

**Happy ingesting! 🚀**
