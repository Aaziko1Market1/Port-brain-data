"""
Inspect Kenya Excel files for QA purposes
"""
import pandas as pd
from pathlib import Path

def main():
    # Kenya Import S.xlsx - SHORT format
    print("=" * 70)
    print("KENYA IMPORT S.xlsx (SHORT FORMAT)")
    print("=" * 70)
    
    df_short = pd.read_excel(
        'data/raw/kenya/import/2023/01/Kenya Import S.xlsx', 
        header=0
    )
    
    print(f"\nTotal rows: {len(df_short)}")
    print(f"Total value (USD): ${df_short['TOTALVALUEUSD'].sum():,.2f}")
    
    # Find DAVITA
    davita_rows = df_short[df_short['IMPORTER_NAME'].str.contains('DAVITA', case=False, na=False)]
    print(f"\nDAVITA SOLUTIONS LIMITED:")
    for idx, row in davita_rows.iterrows():
        print(f"  Row {idx}: HS={row['HS_CODE']}, Value=${row['TOTALVALUEUSD']:.2f}, "
              f"Origin={row['ORIGIN_COUNTRY']}, Month={row['MONTHYEAR']}")
    davita_total = davita_rows['TOTALVALUEUSD'].sum()
    print(f"  TOTAL DAVITA VALUE: ${davita_total:.2f}")
    
    # Find MARBLE INN
    marble_rows = df_short[df_short['IMPORTER_NAME'].str.contains('MARBLE INN', case=False, na=False)]
    print(f"\nMARBLE INN DEVELOPERS LIMITED:")
    for idx, row in marble_rows.iterrows():
        print(f"  Row {idx}: HS={row['HS_CODE']}, Value=${row['TOTALVALUEUSD']:.2f}, "
              f"Origin={row['ORIGIN_COUNTRY']}, Month={row['MONTHYEAR']}")
    marble_total = marble_rows['TOTALVALUEUSD'].sum() if len(marble_rows) > 0 else 0
    print(f"  TOTAL MARBLE INN VALUE: ${marble_total:.2f}")
    
    # HS 690721 stats for import SHORT
    hs_690721_rows = df_short[df_short['HS_CODE'].astype(str).str.startswith('690721')]
    print(f"\nHS 690721 (Tiles) Summary:")
    print(f"  Total rows: {len(hs_690721_rows)}")
    print(f"  Total value: ${hs_690721_rows['TOTALVALUEUSD'].sum():,.2f}")
    print(f"  Unique buyers: {hs_690721_rows['IMPORTER_NAME'].nunique()}")
    
    # Kenya Import F.xlsx - FULL format
    print("\n" + "=" * 70)
    print("KENYA IMPORT F.xlsx (FULL FORMAT)")
    print("=" * 70)
    
    df_full = pd.read_excel(
        'data/raw/kenya/import/2023/01/Kenya Import F.xlsx', 
        header=5
    )
    
    print(f"\nTotal rows: {len(df_full)}")
    print(f"Total value (USD): ${df_full['TOTAL_VALUE_USD'].sum():,.2f}")
    
    # HS 690721 stats for import FULL
    hs_690721_full = df_full[df_full['HS_CODE'].astype(str).str.startswith('690721')]
    print(f"\nHS 690721 (Tiles) Summary:")
    print(f"  Total rows: {len(hs_690721_full)}")
    print(f"  Total value: ${hs_690721_full['TOTAL_VALUE_USD'].sum():,.2f}")
    print(f"  Unique buyers: {hs_690721_full['IMPORTER_NAME'].nunique()}")
    
    # Kenya Export Files
    print("\n" + "=" * 70)
    print("KENYA EXPORT S.xlsx (SHORT FORMAT)")
    print("=" * 70)
    
    df_export_short = pd.read_excel(
        'data/raw/kenya/export/2023/01/Kenya Export S.xlsx', 
        header=0
    )
    
    print(f"\nTotal rows: {len(df_export_short)}")
    print(f"Total value: ${df_export_short['TOTALVALUE'].sum():,.2f}")
    
    print("\n" + "=" * 70)
    print("KENYA EXPORT F.xlsx (FULL FORMAT)")
    print("=" * 70)
    
    df_export_full = pd.read_excel(
        'data/raw/kenya/export/2023/01/Kenya Export F.xlsx', 
        header=5
    )
    
    print(f"\nTotal rows: {len(df_export_full)}")
    print(f"Total value (USD): ${df_export_full['TOTAL_VALUE_USD'].sum():,.2f}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY - ALL KENYA FILES")
    print("=" * 70)
    print(f"Import SHORT: {len(df_short):,} rows, ${df_short['TOTALVALUEUSD'].sum():,.2f}")
    print(f"Import FULL:  {len(df_full):,} rows, ${df_full['TOTAL_VALUE_USD'].sum():,.2f}")
    print(f"Export SHORT: {len(df_export_short):,} rows, ${df_export_short['TOTALVALUE'].sum():,.2f}")
    print(f"Export FULL:  {len(df_export_full):,} rows, ${df_export_full['TOTAL_VALUE_USD'].sum():,.2f}")

if __name__ == "__main__":
    main()
