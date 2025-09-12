#!/usr/bin/env python3
"""
Debug script to test the combination and deduplication process
"""

import pandas as pd
import re
from pathlib import Path
from collections import Counter, defaultdict

def load_and_combine_input_files(input_folder="input"):
    """Load all Excel files from input folder and combine them"""
    input_folder = Path(input_folder)
    excel_files = list(input_folder.glob("*.xlsx"))
    print(f"Found {len(excel_files)} Excel files: {[f.name for f in excel_files]}")
    
    combined_data = []
    file_info = []
    
    for file_path in excel_files:
        try:
            # Get available sheets first
            excel_file = pd.ExcelFile(file_path)
            available_sheets = excel_file.sheet_names
            
            # Try common sheet names in priority order
            df = None
            sheet_priority = [
                'Contacts_Export',  # Standard contact export
                'Contacts',         # Contact data
                'Institution Contacts',  # Institution contact data
                'Sheet1',           # Default sheet
                available_sheets[0] if available_sheets else None  # First available sheet
            ]
            
            for sheet_name in sheet_priority:
                if sheet_name and sheet_name in available_sheets:
                    try:
                        df = pd.read_excel(file_path, sheet_name=sheet_name)
                        print(f"Loaded {file_path.name} from sheet '{sheet_name}': {len(df)} rows")
                        break
                    except Exception as e:
                        print(f"Failed to load sheet '{sheet_name}' from {file_path.name}: {e}")
                        continue
            
            if df is None:
                print(f"Could not load any sheet from {file_path.name}")
                continue
            
            # Add source file column
            df['source_file'] = file_path.name
            combined_data.append(df)
            file_info.append({'file': file_path.name, 'contacts': len(df)})
            
        except Exception as e:
            print(f"Error loading {file_path.name}: {e}")
            continue
    
    if not combined_data:
        raise Exception("No files could be loaded successfully")
    
    # Check for duplicate columns before combining
    for i, df in enumerate(combined_data):
        original_cols = len(df.columns)
        # Remove duplicate columns by keeping only the first occurrence
        df_cleaned = df.loc[:, ~df.columns.duplicated()]
        combined_data[i] = df_cleaned
        if original_cols != len(df_cleaned.columns):
            print(f"Removed {original_cols - len(df_cleaned.columns)} duplicate columns from {file_path.name}")
    
    # Combine all dataframes
    combined_df = pd.concat(combined_data, ignore_index=True)
    print(f"Combined dataset: {len(combined_df)} total contacts from {len(file_info)} files")
    
    return combined_df, file_info

def normalize_text(text):
    """Normalize text for duplicate detection"""
    try:
        if text is None or str(text).lower() in ['nan', 'none', '']:
            return ''
        return str(text).lower().strip()
    except:
        return ''

def remove_duplicates(df):
    """Remove duplicates based on name and firm combination"""
    print(f"Removing duplicates from {len(df)} contacts")
    
    if len(df) == 0:
        return df
    
    # Reset index to avoid duplicate labels issue
    df_reset = df.reset_index(drop=True)
    
    # Create normalized versions for duplicate detection
    normalized_names = []
    normalized_firms = []
    
    for idx, row in df_reset.iterrows():
        name_norm = normalize_text(row.get('NAME', ''))
        firm_norm = normalize_text(row.get('INVESTOR', ''))
        normalized_names.append(name_norm)
        normalized_firms.append(firm_norm)
    
    # Track which rows to keep (first occurrence of each name+firm combination)
    seen_combinations = set()
    rows_to_keep = []
    
    # Debug: Check first few combinations
    print(f"Sample normalized combinations (first 10):")
    for i in range(min(10, len(normalized_names))):
        print(f"  {i}: ('{normalized_names[i]}', '{normalized_firms[i]}')")
    
    for idx in range(len(df_reset)):
        combination = (normalized_names[idx], normalized_firms[idx])
        if combination not in seen_combinations:
            seen_combinations.add(combination)
            rows_to_keep.append(idx)
    
    print(f"Found {len(seen_combinations)} unique combinations out of {len(df_reset)} total rows")
    
    # Create deduplicated dataframe
    df_deduped = df_reset.iloc[rows_to_keep].copy()
    
    duplicates_removed = len(df) - len(df_deduped)
    print(f"Removed {duplicates_removed} duplicates, {len(df_deduped)} unique contacts remain")
    
    return df_deduped

if __name__ == "__main__":
    print("=== DEBUGGING COMBINATION AND DEDUPLICATION ===")
    
    # Test combination
    print("\n1. Testing file combination...")
    combined_df, file_info = load_and_combine_input_files()
    
    print(f"\nCombined DataFrame info:")
    print(f"  Shape: {combined_df.shape}")
    print(f"  Columns: {list(combined_df.columns)}")
    print(f"  Duplicate columns: {combined_df.columns.duplicated().sum()}")
    
    # Check key columns
    if 'NAME' in combined_df.columns and 'INVESTOR' in combined_df.columns:
        print(f"\nKey columns analysis:")
        print(f"  NAME column - Non-null: {combined_df['NAME'].notna().sum()}, Null: {combined_df['NAME'].isna().sum()}")
        print(f"  INVESTOR column - Non-null: {combined_df['INVESTOR'].notna().sum()}, Null: {combined_df['INVESTOR'].isna().sum()}")
        
        # Show sample data
        print(f"\nSample NAME values:")
        print(combined_df['NAME'].head(5).tolist())
        print(f"\nSample INVESTOR values:")
        print(combined_df['INVESTOR'].head(5).tolist())
    
    # Test deduplication
    print(f"\n2. Testing deduplication...")
    deduped_df = remove_duplicates(combined_df)
    
    print(f"\nDeduplication result:")
    print(f"  Original: {len(combined_df)} contacts")
    print(f"  After dedup: {len(deduped_df)} contacts")
    print(f"  Removed: {len(combined_df) - len(deduped_df)} duplicates")
