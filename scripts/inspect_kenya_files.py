"""
Inspect Kenya Excel files to check if HS 690721 exists
"""
import pandas as pd
import os

files = [
    r"e:\Port Data Brain\data\reference\port_real\Kenya Import F.xlsx",
    r"e:\Port Data Brain\data\reference\port_real\Kenya Import S.xlsx",
    r"e:\Port Data Brain\data\reference\port_real\Kenya Export F.xlsx",
    r"e:\Port Data Brain\data\reference\port_real\Kenya Export S.xlsx",
]

print("=" * 80)
print("KENYA FILE INSPECTION - Looking for HS 690721")
print("=" * 80)

for filepath in files:
    print(f"\n### {os.path.basename(filepath)} ###")
    if not os.path.exists(filepath):
        print(f"  FILE NOT FOUND: {filepath}")
        continue
    
    try:
        # Read Excel file
        df = pd.read_excel(filepath, sheet_name=0, header=None, nrows=20)
        print(f"  First 5 rows preview:")
        print(df.head().to_string())
        
        # Find header row (look for common column names)
        header_row = None
        for i in range(min(10, len(df))):
            row_str = ' '.join([str(x).lower() for x in df.iloc[i].values if pd.notna(x)])
            if 'hs' in row_str or 'code' in row_str or 'product' in row_str:
                header_row = i
                break
        
        if header_row is not None:
            print(f"\n  Detected header row: {header_row}")
            df_full = pd.read_excel(filepath, sheet_name=0, header=header_row)
            print(f"  Columns: {list(df_full.columns)}")
            print(f"  Total rows: {len(df_full)}")
            
            # Find HS code column
            hs_col = None
            for col in df_full.columns:
                col_lower = str(col).lower()
                if 'hs' in col_lower or 'code' in col_lower:
                    hs_col = col
                    break
            
            if hs_col:
                print(f"\n  HS Code column: {hs_col}")
                # Check for 690721
                df_full[hs_col] = df_full[hs_col].astype(str)
                hs_690721 = df_full[df_full[hs_col].str.contains('690721', na=False)]
                print(f"  Rows with HS 690721: {len(hs_690721)}")
                
                if len(hs_690721) > 0:
                    print(f"  FOUND HS 690721 in this file!")
                    print(hs_690721.head())
                else:
                    print(f"  NO HS 690721 found in this file")
                
                # Show unique HS codes (first 6 digits)
                unique_hs = df_full[hs_col].str[:6].unique()[:20]
                print(f"\n  Sample unique HS codes (first 20): {list(unique_hs)}")
            else:
                print("  Could not identify HS code column")
        else:
            print("  Could not detect header row")
            
    except Exception as e:
        print(f"  ERROR reading file: {e}")

print("\n" + "=" * 80)
print("INSPECTION COMPLETE")
print("=" * 80)
