#!/usr/bin/env python3
"""
Script to compare contacts between latest tiered output and original filtering output.
Finds contacts that are in the latest tiered output but not in the original filtering output.
"""

import pandas as pd
import sys
from pathlib import Path

def compareContacts():
    """
    Compare contacts between latest tiered output and original filtering output.
    Returns contacts that are in tiered output but not in original filtering.
    """
    try:
        # Read the latest tiered output (v6)
        tiered_path = Path('output/Two_Tier_Filtered_Family_Office_Contacts_v6.xlsx')
        tiered_df = pd.read_excel(tiered_path)
        print(f"Loaded latest tiered output: {tiered_df.shape[0]} contacts")
        
        # Read the original filtering output
        original_path = Path('../email-filtering-tool/output/Filtered_Out_Contacts.xlsx')
        original_df = pd.read_excel(original_path)
        print(f"Loaded original filtering output: {original_df.shape[0]} contacts")
        
        # Create unique identifiers for comparison
        # Use CONTACT_ID as the primary identifier
        tiered_contact_ids = set(tiered_df['CONTACT_ID'].astype(str))
        original_contact_ids = set(original_df['CONTACT_ID'].astype(str))
        
        print(f"Unique contact IDs in tiered output: {len(tiered_contact_ids)}")
        print(f"Unique contact IDs in original filtering: {len(original_contact_ids)}")
        
        # Find contacts in tiered output but not in original filtering
        contacts_not_in_original = tiered_contact_ids - original_contact_ids
        print(f"Contacts in tiered output but not in original filtering: {len(contacts_not_in_original)}")
        
        # Get the full contact details for these contacts
        missing_contacts = tiered_df[tiered_df['CONTACT_ID'].astype(str).isin(contacts_not_in_original)]
        
        # Display the results
        print("\n" + "="*80)
        print("CONTACTS IN LATEST TIERED OUTPUT BUT NOT IN ORIGINAL FILTERING")
        print("="*80)
        
        if len(missing_contacts) > 0:
            # Select key columns for display
            display_columns = ['CONTACT_ID', 'INVESTOR', 'FIRM TYPE', 'NAME', 'TITLE', 'EMAIL', 'CITY', 'STATE']
            available_columns = [col for col in display_columns if col in missing_contacts.columns]
            
            print(f"\nFound {len(missing_contacts)} contacts:")
            print("\n" + "-"*120)
            
            for idx, row in missing_contacts.iterrows():
                print(f"\nContact ID: {row['CONTACT_ID']}")
                print(f"Investor: {row.get('INVESTOR', 'N/A')}")
                print(f"Firm Type: {row.get('FIRM TYPE', 'N/A')}")
                print(f"Name: {row.get('NAME', 'N/A')}")
                print(f"Title: {row.get('TITLE', 'N/A')}")
                print(f"Email: {row.get('EMAIL', 'N/A')}")
                print(f"Location: {row.get('CITY', 'N/A')}, {row.get('STATE', 'N/A')}")
                print("-" * 80)
        else:
            print("No contacts found in tiered output that are not in original filtering.")
        
        # Save the results to a CSV file
        if len(missing_contacts) > 0:
            output_path = Path('output/contacts_not_in_original_filtering.csv')
            missing_contacts.to_csv(output_path, index=False)
            print(f"\nResults saved to: {output_path}")
        
        return missing_contacts
        
    except Exception as e:
        print(f"Error comparing contacts: {e}")
        return None

if __name__ == "__main__":
    compareContacts()