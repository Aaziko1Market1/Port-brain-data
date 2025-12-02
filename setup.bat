@echo off
REM GTI-OS Data Platform - Automated Setup Script for Windows
REM This script automates the setup process

echo ============================================================
echo GTI-OS Data Platform - Automated Setup
echo ============================================================
echo.

REM Check Python installation
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)
python --version
echo.

REM Create virtual environment
echo [2/6] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists, skipping creation
) else (
    python -m venv venv
    echo Virtual environment created
)
echo.

REM Activate and install dependencies
echo [3/6] Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo Dependencies installed
echo.

REM Copy config files
echo [4/6] Creating configuration files...
if not exist config\db_config.yml (
    copy config\db_config.example.yml config\db_config.yml >nul
    echo Created config\db_config.yml
    echo IMPORTANT: Edit config\db_config.yml and set your PostgreSQL password
) else (
    echo config\db_config.yml already exists
)

if not exist config\ingestion_config.yml (
    copy config\ingestion_config.example.yml config\ingestion_config.yml >nul
    echo Created config\ingestion_config.yml
) else (
    echo config\ingestion_config.yml already exists
)
echo.

REM Setup database
echo [5/6] Setting up database...
echo This will create the aaziko_trade database and apply schema
echo.
python scripts\setup_database.py
if errorlevel 1 (
    echo.
    echo ERROR: Database setup failed
    echo Please check:
    echo   1. PostgreSQL is running
    echo   2. config\db_config.yml has correct credentials
    pause
    exit /b 1
)
echo.

REM Verify setup
echo [6/6] Verifying setup...
python scripts\verify_setup.py
if errorlevel 1 (
    echo.
    echo WARNING: Setup verification found issues
    echo Please review the output above
) else (
    echo.
    echo ============================================================
    echo SUCCESS: GTI-OS setup completed!
    echo ============================================================
    echo.
    echo Next steps:
    echo   1. Edit config\db_config.yml if you haven't already
    echo   2. Generate sample data: python scripts\create_sample_data.py
    echo   3. Run ingestion: python scripts\run_ingestion.py
    echo.
    echo To activate the virtual environment in future sessions:
    echo   venv\Scripts\activate.bat
    echo.
)

pause
