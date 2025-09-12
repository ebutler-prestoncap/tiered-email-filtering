#!/usr/bin/env python3
"""
Minimal test to isolate the deduplication issue
"""

import pandas as pd
import re
from pathlib import Path

# Load the data exactly like the main script
input_folder = Path('input')
excel_files = list(input_folder.glob('*.xlsx'))
combined_data = []

for file_path in excel_files:
    try:
        df = pd.read_excel(file_path, sheet_name='Contacts_Export')
        df['source_file'] = file_path.name
        combined_data.append(df)
    except:
        try:
            df = pd.read_excel(file_path, sheet_name='Contacts')
            df['source_file'] = file_path.name
            combined_data.append(df)
        except:
            try:
                df = pd.read_excel(file_path, sheet_name='Institution Contacts')
                df['source_file'] = file_path.name
                combined_data.append(df)
            except:
                pass

# Remove duplicate columns
for i, df in enumerate(combined_data):
    df_cleaned = df.loc[:, ~df.columns.duplicated()]
    combined_data[i] = df_cleaned

combined_df = pd.concat(combined_data, ignore_index=True)
print(f"Combined: {len(combined_df)} contacts")

# Apply column mapping
column_mapping = {
    'investor': 'INVESTOR', 'firm': 'INVESTOR', 'institution': 'INVESTOR',
    'company': 'INVESTOR', 'organization': 'INVESTOR',
    'name': 'NAME', 'full name': 'NAME', 'contact name': 'NAME',
    'title': 'JOB TITLE', 'job title': 'JOB TITLE', 'position': 'JOB TITLE',
    'role': 'ROLE', 'email': 'EMAIL', 'email_address': 'EMAIL',
    'contact_id': 'CONTACT_ID', 'id': 'CONTACT_ID'
}

df_renamed = combined_df.copy()
for old_col in combined_df.columns:
    if old_col.lower() in column_mapping:
        df_renamed = df_renamed.rename(columns={old_col: column_mapping[old_col.lower()]})

# Add required columns
required_columns = ['INVESTOR', 'NAME', 'JOB TITLE', 'EMAIL']
for col in required_columns:
    if col not in df_renamed.columns:
        df_renamed[col] = ''

print(f"After column mapping: {len(df_renamed)} contacts")

# Clean data
df_renamed['NAME'] = df_renamed['NAME'].fillna('')
df_renamed['INVESTOR'] = df_renamed['INVESTOR'].fillna('')
initial_count = len(df_renamed)
df_cleaned = df_renamed[~((df_renamed['NAME'].str.strip() == '') & (df_renamed['INVESTOR'].str.strip() == ''))]
removed_count = initial_count - len(df_cleaned)
print(f"After cleaning: {len(df_cleaned)} contacts (removed {removed_count})")

# Test deduplication
def normalize_text(text):
    try:
        if text is None or str(text).lower() in ['nan', 'none', '']:
            return ''
        return str(text).lower().strip()
    except:
        return ''

df_reset = df_cleaned.reset_index(drop=True)
normalized_names = []
normalized_firms = []

for idx, row in df_reset.iterrows():
    name_norm = normalize_text(row.get('NAME', ''))
    firm_norm = normalize_text(row.get('INVESTOR', ''))
    normalized_names.append(name_norm)
    normalized_firms.append(firm_norm)

seen_combinations = set()
rows_to_keep = []

for idx in range(len(df_reset)):
    combination = (normalized_names[idx], normalized_firms[idx])
    if combination not in seen_combinations:
        seen_combinations.add(combination)
        rows_to_keep.append(idx)

print(f"Found {len(seen_combinations)} unique combinations out of {len(df_reset)} total rows")

df_deduped = df_reset.iloc[rows_to_keep].copy()
duplicates_removed = len(df_cleaned) - len(df_deduped)
print(f"Removed {duplicates_removed} duplicates, {len(df_deduped)} unique contacts remain")
