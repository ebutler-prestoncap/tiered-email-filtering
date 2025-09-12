#!/usr/bin/env python3
"""
Contact comparison script to find contacts in tiered output but not in original filtering.
"""

import pandas as pd
import sys
from pathlib import Path

def main():
    try:
        print("Starting contact comparison...")
        
        # Define file paths
        tiered_file = Path('output/Two_Tier_Filtered_Family_Office_Contacts_v6.xlsx')
        original_file = Path('../email-filtering-tool/output/Filtered_Out_Contacts.xlsx')
        
        # Check if files exist
        if not tiered_file.exists():
            print(f"Error: Tiered file not found: {tiered_file}")
            return
        
        if not original_file.exists():
            print(f"Error: Original file not found: {original_file}")
            return
        
        print("Reading tiered output...")
        tiered_df = pd.read_excel(tiered_file)
        print(f"Loaded tiered output: {tiered_df.shape[0]} contacts")
        
        print("Reading original filtering output...")
        original_df = pd.read_excel(original_file)
        print(f"Loaded original filtering: {original_df.shape[0]} contacts")
        
        # Get contact IDs
        tiered_ids = set(tiered_df['CONTACT_ID'].astype(str))
        original_ids = set(original_df['CONTACT_ID'].astype(str))
        
        print(f"Unique contact IDs in tiered output: {len(tiered_ids)}")
        print(f"Unique contact IDs in original filtering: {len(original_ids)}")
        
        # Find differences
        contacts_not_in_original = tiered_ids - original_ids
        contacts_not_in_tiered = original_ids - tiered_ids
        
        print(f"\nContacts in tiered output but NOT in original filtering: {len(contacts_not_in_original)}")
        print(f"Contacts in original filtering but NOT in tiered output: {len(contacts_not_in_tiered)}")
        
        # Get details for contacts not in original
        if len(contacts_not_in_original) > 0:
            missing_contacts = tiered_df[tiered_df['CONTACT_ID'].astype(str).isin(contacts_not_in_original)]
            
            print("\n" + "="*100)
            print("CONTACTS IN LATEST TIERED OUTPUT BUT NOT IN ORIGINAL FILTERING")
            print("="*100)
            
            # Display key information for each contact
            for idx, row in missing_contacts.iterrows():
                print(f"\nContact ID: {row['CONTACT_ID']}")
                print(f"Investor: {row.get('INVESTOR', 'N/A')}")
                print(f"Firm Type: {row.get('FIRM TYPE', 'N/A')}")
                print(f"Name: {row.get('NAME', 'N/A')}")
                print(f"Title: {row.get('TITLE', 'N/A')}")
                print(f"Email: {row.get('EMAIL', 'N/A')}")
                print(f"Location: {row.get('CITY', 'N/A')}, {row.get('STATE', 'N/A')}")
                print("-" * 80)
            
            # Save to CSV
            output_file = Path('output/contacts_not_in_original_filtering.csv')
            missing_contacts.to_csv(output_file, index=False)
            print(f"\nResults saved to: {output_file}")
        else:
            print("\nNo contacts found in tiered output that are not in original filtering.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
