#!/usr/bin/env python3
"""
Test the main script with debugging
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from consolidated_tiered_filter import ConsolidatedTieredFilter

def main():
    print("=== TESTING MAIN SCRIPT ===")
    
    # Create filter instance
    filter_tool = ConsolidatedTieredFilter()
    
    # Test the process step by step
    print("\n1. Loading and combining files...")
    combined_df, file_info = filter_tool.load_and_combine_input_files()
    print(f"   Combined: {len(combined_df)} contacts")
    
    print("\n2. Removing duplicates (immediately after combination)...")
    df_deduped = filter_tool.remove_duplicates(combined_df)
    print(f"   After deduplication: {len(df_deduped)} contacts")
    
    print("\n3. Standardizing column names...")
    df_standardized = filter_tool.standardize_column_names(df_deduped)
    print(f"   After standardization: {len(df_standardized)} contacts")
    
    print("\n4. Cleaning data...")
    df_cleaned = filter_tool.clean_data_after_standardization(df_standardized)
    print(f"   After cleaning: {len(df_cleaned)} contacts")
    
    print(f"\n=== DEDUPLICATION RESULT ===")
    print(f"Original: {len(combined_df)} contacts")
    print(f"Final: {len(df_deduped)} contacts")
    print(f"Removed: {len(combined_df) - len(df_deduped)} contacts")
    
    if len(df_deduped) > 1000:
        print("✅ SUCCESS: Deduplication is working correctly!")
    else:
        print("❌ ISSUE: Still only finding very few unique contacts")
        print("This explains why the output is blank - no contacts to filter!")

if __name__ == "__main__":
    main()
