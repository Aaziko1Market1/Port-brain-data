"""
GTI-OS Data Platform - Sample Data Generator
Creates sample Excel/CSV files for testing ingestion

Usage:
    python scripts/create_sample_data.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from etl.logging_config import setup_logging, get_logger


def generate_sample_data(num_rows: int = 1000) -> pd.DataFrame:
    """Generate sample trade data"""
    
    # Sample data lists
    countries = ['INDIA', 'USA', 'CHINA', 'GERMANY', 'UAE', 'KENYA', 'BANGLADESH']
    hs_codes = ['080610', '080711', '090111', '100630', '170111', '230120', '520100']
    goods = [
        'FRESH GRAPES',
        'FRESH WATERMELONS',
        'COFFEE BEANS',
        'RICE',
        'RAW CANE SUGAR',
        'SOYA BEAN MEAL',
        'COTTON'
    ]
    buyers = [
        'ABC TRADING LLC',
        'XYZ IMPORTS PVT LTD',
        'GLOBAL FOODS CO',
        'METRO WHOLESALE',
        'SUNRISE TRADERS',
        'OCEAN IMPORTS',
        'CONTINENTAL EXPORTS'
    ]
    suppliers = [
        'RELIABLE EXPORTS INC',
        'QUALITY PRODUCTS LLP',
        'PRIME SUPPLIERS CO',
        'AGRO EXPORTS',
        'FRESH FARMS PVT LTD',
        'TRADE SOLUTIONS',
        'EXPORT MASTERS'
    ]
    ports_india = ['NHAVA SHEVA', 'MUMBAI PORT', 'CHENNAI PORT', 'TUTICORIN']
    ports_foreign = ['MOMBASA', 'DUBAI', 'SINGAPORE', 'LOS ANGELES']
    vessels = ['MSC AURORA', 'MAERSK BOSTON', 'CMA CGM NILE', 'EVERGREEN LILY']
    
    data = []
    start_date = datetime(2023, 1, 1)
    
    for i in range(num_rows):
        hs_idx = random.randint(0, len(hs_codes) - 1)
        
        row = {
            'sl_no': i + 1,
            'shipment_date': (start_date + timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d'),
            'hs_code': hs_codes[hs_idx],
            'goods_description': goods[hs_idx],
            'buyer_name': random.choice(buyers),
            'supplier_name': random.choice(suppliers),
            'origin_country': 'INDIA',
            'destination_country': random.choice(countries),
            'quantity_kg': round(random.uniform(1000, 50000), 2),
            'unit': 'KGS',
            'fob_value_usd': round(random.uniform(5000, 200000), 2),
            'port_loading': random.choice(ports_india),
            'port_unloading': random.choice(ports_foreign),
            'vessel_name': random.choice(vessels),
            'container_id': f'MSCU{random.randint(1000000, 9999999)}',
            'bl_number': f'BL{random.randint(100000, 999999)}'
        }
        
        data.append(row)
    
    return pd.DataFrame(data)


def main():
    """Generate sample files"""
    
    setup_logging(log_level='INFO')
    logger = get_logger(__name__)
    
    logger.info("=" * 80)
    logger.info("GTI-OS Sample Data Generator")
    logger.info("=" * 80)
    
    # Create directories
    base_path = Path('data/raw')
    
    samples = [
        ('india', 'export', 2023, 1, 5000, 'xlsx'),
        ('india', 'export', 2023, 2, 3000, 'csv'),
        ('kenya', 'import', 2023, 1, 2000, 'xlsx'),
    ]
    
    for country, direction, year, month, rows, ext in samples:
        # Create directory
        dir_path = base_path / country / direction / str(year) / f'{month:02d}'
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Generate data
        logger.info(f"Generating {rows} rows for {country} {direction} {year}-{month:02d}...")
        df = generate_sample_data(rows)
        
        # Save file
        filename = f'{country}_{direction}_{year}{month:02d}.{ext}'
        file_path = dir_path / filename
        
        if ext == 'xlsx':
            df.to_excel(file_path, index=False, engine='openpyxl')
        elif ext == 'csv':
            df.to_csv(file_path, index=False)
        
        logger.info(f"  ✓ Created: {file_path}")
    
    logger.info("\n" + "=" * 80)
    logger.info("✓ Sample data generation complete!")
    logger.info(f"Files created in: {base_path.absolute()}")
    logger.info("=" * 80)
    logger.info("\nNext steps:")
    logger.info("  1. Review files in data/raw/")
    logger.info("  2. Run: python scripts/run_ingestion.py --dry-run")
    logger.info("  3. Run: python scripts/run_ingestion.py")


if __name__ == "__main__":
    main()
