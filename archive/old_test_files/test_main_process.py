#!/usr/bin/env python3
"""
Test the exact main process to identify where the issue occurs
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
        # Remove duplicate columns by keeping only the first occurrence
        df_cleaned = df.loc[:, ~df.columns.duplicated()]
        combined_data[i] = df_cleaned
        if len(df.columns) != len(df_cleaned.columns):
            print(f"Removed {len(df.columns) - len(df_cleaned.columns)} duplicate columns from {df['source_file'].iloc[0] if 'source_file' in df.columns else 'unknown file'}")
    
    # Combine all dataframes
    combined_df = pd.concat(combined_data, ignore_index=True)
    print(f"Combined dataset: {len(combined_df)} total contacts from {len(file_info)} files")
    
    return combined_df, file_info

def standardize_column_names(df):
    """Standardize column names across different data sources"""
    # Enhanced column mapping for multiple formats
    column_mapping = {
        'investor': 'INVESTOR',
        'firm': 'INVESTOR',
        'institution': 'INVESTOR',
        'company': 'INVESTOR',
        'organization': 'INVESTOR',
        'name': 'NAME',
        'full name': 'NAME',
        'contact name': 'NAME',
        'title': 'JOB TITLE',
        'job title': 'JOB TITLE',
        'position': 'JOB TITLE',
        'role': 'ROLE',
        'email': 'EMAIL',
        'email_address': 'EMAIL',
        'contact_id': 'CONTACT_ID',
        'id': 'CONTACT_ID'
    }
    
    # Rename columns (case insensitive)
    df_renamed = df.copy()
    for old_col in df.columns:
        if old_col.lower() in column_mapping:
            df_renamed = df_renamed.rename(columns={old_col: column_mapping[old_col.lower()]})
    
    # Handle special cases for combined name fields
    if 'NAME' not in df_renamed.columns:
        # Try to combine First Name + Last Name
        if 'First Name' in df_renamed.columns and 'Last Name' in df_renamed.columns:
            df_renamed['NAME'] = (df_renamed['First Name'].fillna('').astype(str) + ' ' + 
                                df_renamed['Last Name'].fillna('').astype(str)).apply(lambda x: x.strip())
            print("Combined 'First Name' and 'Last Name' into 'NAME' column")
        elif 'first name' in df_renamed.columns and 'last name' in df_renamed.columns:
            df_renamed['NAME'] = (df_renamed['first name'].fillna('').astype(str) + ' ' + 
                                df_renamed['last name'].fillna('').astype(str)).apply(lambda x: x.strip())
            print("Combined 'first name' and 'last name' into 'NAME' column")
    
    # Handle institution-only data (convert institution names to contact names)
    if 'NAME' not in df_renamed.columns:
        if 'INVESTOR' in df_renamed.columns:
            df_renamed['NAME'] = 'Contact at ' + df_renamed['INVESTOR'].fillna('Unknown Institution').astype(str)
            df_renamed['JOB TITLE'] = 'Institutional Contact'
            print("Created placeholder names for institution-only data (no NAME column)")
    
    # Ensure required columns exist with proper data types
    required_columns = ['INVESTOR', 'NAME', 'JOB TITLE', 'EMAIL']
    for col in required_columns:
        if col not in df_renamed.columns:
            df_renamed[col] = ''
            print(f"Added missing column: {col}")
        else:
            # Clean existing columns
            df_renamed[col] = df_renamed[col].fillna('').astype(str)
            df_renamed[col] = df_renamed[col].apply(lambda x: '' if str(x).lower().strip() in ['nan', 'none', 'null'] else str(x).strip())
    
    # Add ROLE column if missing (optional)
    if 'ROLE' not in df_renamed.columns:
        df_renamed['ROLE'] = 'Investment Team'  # Default assumption for institutional data
    else:
        df_renamed['ROLE'] = df_renamed['ROLE'].fillna('Investment Team').astype(str)
    
    # Create CONTACT_ID if missing
    if 'CONTACT_ID' not in df_renamed.columns:
        df_renamed['CONTACT_ID'] = range(1, len(df_renamed) + 1)
    
    # Remove any duplicate columns that might have been created
    df_renamed = df_renamed.loc[:, ~df_renamed.columns.duplicated()]
    
    return df_renamed

def clean_data_before_deduplication(df):
    """Clean data before deduplication to avoid issues with empty values"""
    print("Cleaning data before deduplication")
    
    # Clean NaN values in key columns
    df['NAME'] = df['NAME'].fillna('')
    df['INVESTOR'] = df['INVESTOR'].fillna('')
    
    # Remove rows where both NAME and INVESTOR are empty (these cause deduplication issues)
    initial_count = len(df)
    df = df[~((df['NAME'].str.strip() == '') & (df['INVESTOR'].str.strip() == ''))]
    removed_count = initial_count - len(df)
    
    if removed_count > 0:
        print(f"Removed {removed_count} rows with empty NAME and INVESTOR")
    
    return df

def remove_duplicates(df):
    """Remove duplicates based on name and firm combination"""
    print(f"Removing duplicates from {len(df)} contacts")
    
    if len(df) == 0:
        return df
    
    # Reset index to avoid duplicate labels issue
    df_reset = df.reset_index(drop=True)
    
    # Create normalized columns for comparison
    def normalize_text(text):
        try:
            if text is None or str(text).lower() in ['nan', 'none', '']:
                return ''
            return str(text).lower().strip()
        except:
            return ''
    
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
    print("=== TESTING MAIN PROCESS ===")
    
    # Step 1: Load and combine
    print("\n1. Loading and combining files...")
    combined_df, file_info = load_and_combine_input_files()
    
    # Step 2: Standardize column names
    print("\n2. Standardizing column names...")
    df_standardized = standardize_column_names(combined_df)
    print(f"After standardization: {len(df_standardized)} contacts")
    
    # Step 3: Clean data before deduplication
    print("\n3. Cleaning data before deduplication...")
    df_cleaned = clean_data_before_deduplication(df_standardized)
    print(f"After cleaning: {len(df_cleaned)} contacts")
    
    # Step 4: Remove duplicates
    print("\n4. Removing duplicates...")
    df_deduped = remove_duplicates(df_cleaned)
    print(f"After deduplication: {len(df_deduped)} contacts")
    
    print(f"\n=== FINAL RESULT ===")
    print(f"Original: {len(combined_df)} contacts")
    print(f"Final: {len(df_deduped)} contacts")
    print(f"Total removed: {len(combined_df) - len(df_deduped)} contacts")
