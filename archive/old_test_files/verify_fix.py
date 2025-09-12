#!/usr/bin/env python3
"""
Verify that the deduplication fix is working
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from consolidated_tiered_filter import ConsolidatedTieredFilter

def main():
    print("=== VERIFYING DEDUPLICATION FIX ===")
    
    # Create filter instance
    filter_tool = ConsolidatedTieredFilter()
    
    # Test just the combination and deduplication steps
    print("\n1. Loading and combining files...")
    combined_df, file_info = filter_tool.load_and_combine_input_files()
    print(f"   Combined: {len(combined_df)} contacts")
    
    print("\n2. Standardizing column names...")
    df_standardized = filter_tool.standardize_column_names(combined_df)
    print(f"   After standardization: {len(df_standardized)} contacts")
    
    print("\n3. Cleaning data...")
    df_cleaned = filter_tool.clean_data_before_deduplication(df_standardized)
    print(f"   After cleaning: {len(df_cleaned)} contacts")
    
    print("\n4. Removing duplicates...")
    df_deduped = filter_tool.remove_duplicates(df_cleaned)
    print(f"   After deduplication: {len(df_deduped)} contacts")
    
    print(f"\n=== RESULT ===")
    print(f"Original: {len(combined_df)} contacts")
    print(f"Final: {len(df_deduped)} contacts")
    print(f"Removed: {len(combined_df) - len(df_deduped)} contacts")
    
    if len(df_deduped) > 1000:
        print("✅ SUCCESS: Deduplication is working correctly!")
    else:
        print("❌ ISSUE: Still only finding very few unique contacts")

if __name__ == "__main__":
    main()
