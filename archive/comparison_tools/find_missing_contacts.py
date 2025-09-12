#!/usr/bin/env python3
"""
Script to find contacts that are in the original filtering output but NOT in the tiered output.
This is the reverse of the previous comparison.
"""

import pandas as pd
import sys
from pathlib import Path

def findMissingContacts():
    """
    Find contacts that are in original filtering but not in tiered output.
    """
    try:
        print("Finding contacts in original filtering but NOT in tiered output...")
        
        # Define file paths
        tiered_file = Path('output/Two_Tier_Filtered_Family_Office_Contacts_v6.xlsx')
        original_file = Path('../email-filtering-tool/output/Filtered_Out_Contacts.xlsx')
        
        # Check if files exist
        if not tiered_file.exists():
            print(f"Error: Tiered file not found: {tiered_file}")
            return None
        
        if not original_file.exists():
            print(f"Error: Original file not found: {original_file}")
            return None
        
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
        
        # Find contacts in original but not in tiered
        contacts_in_original_not_tiered = original_ids - tiered_ids
        contacts_in_tiered_not_original = tiered_ids - original_ids
        
        print(f"\nContacts in original filtering but NOT in tiered output: {len(contacts_in_original_not_tiered)}")
        print(f"Contacts in tiered output but NOT in original filtering: {len(contacts_in_tiered_not_original)}")
        
        # Get details for contacts in original but not in tiered
        if len(contacts_in_original_not_tiered) > 0:
            missing_contacts = original_df[original_df['CONTACT_ID'].astype(str).isin(contacts_in_original_not_tiered)]
            
            print("\n" + "="*100)
            print("CONTACTS IN ORIGINAL FILTERING BUT NOT IN TIERED OUTPUT")
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
                print(f"Filter Reason: {row.get('FILTER_REASON', 'N/A')}")
                print("-" * 80)
            
            # Save to CSV
            output_file = Path('output/contacts_in_original_but_not_tiered.csv')
            missing_contacts.to_csv(output_file, index=False)
            print(f"\nResults saved to: {output_file}")
            
            return missing_contacts
        else:
            print("\nNo contacts found in original filtering that are not in tiered output.")
            return None
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    findMissingContacts()
