#!/usr/bin/env python3
"""
Remove Additional Firms from Tiered Filtering Results
Removes contacts from specified firms from the existing tiered filtering results
"""

import pandas as pd
import sys
from pathlib import Path
from typing import List

def removeFirmsFromTieredResults(inputFile: str, outputFile: str, firmsToRemove: List[str]) -> None:
    """
    Remove contacts from specified firms from tiered filtering results
    
    Args:
        inputFile: Path to input Excel file with tiered results
        outputFile: Path to output Excel file with firms removed
        firmsToRemove: List of firm names to remove
    """
    try:
        print(f"Reading tiered filtering results from: {inputFile}")
        
        # Read both tier sheets
        tier1Df = pd.read_excel(inputFile, sheet_name="Tier1_Key_Contacts")
        tier2Df = pd.read_excel(inputFile, sheet_name="Tier2_Junior_Contacts")
        
        print(f"Original Tier 1 contacts: {len(tier1Df)}")
        print(f"Original Tier 2 contacts: {len(tier2Df)}")
        
        # Create exclusion pattern for the firms to remove
        exclusionPattern = r"^(?!.*\b(?:" + "|".join(re.escape(firm) for firm in firmsToRemove) + r")\b).*$"
        exclusionRegex = re.compile(exclusionPattern, re.IGNORECASE)
        
        print(f"\nFirms to remove: {firmsToRemove}")
        
        # Filter Tier 1 contacts
        if 'INVESTOR' in tier1Df.columns:
            tier1Filter = tier1Df['INVESTOR'].apply(
                lambda x: bool(exclusionRegex.match(str(x))) if pd.notna(x) else True
            )
            tier1Filtered = tier1Df[tier1Filter]
            tier1Removed = len(tier1Df) - len(tier1Filtered)
            print(f"Tier 1 contacts removed: {tier1Removed}")
            print(f"Tier 1 contacts remaining: {len(tier1Filtered)}")
        else:
            tier1Filtered = tier1Df.copy()
            print("INVESTOR column not found in Tier 1, skipping filter")
        
        # Filter Tier 2 contacts
        if 'INVESTOR' in tier2Df.columns:
            tier2Filter = tier2Df['INVESTOR'].apply(
                lambda x: bool(exclusionRegex.match(str(x))) if pd.notna(x) else True
            )
            tier2Filtered = tier2Df[tier2Filter]
            tier2Removed = len(tier2Df) - len(tier2Filtered)
            print(f"Tier 2 contacts removed: {tier2Removed}")
            print(f"Tier 2 contacts remaining: {len(tier2Filtered)}")
        else:
            tier2Filtered = tier2Df.copy()
            print("INVESTOR column not found in Tier 2, skipping filter")
        
        # Show which firms were removed
        if 'INVESTOR' in tier1Df.columns:
            removedFirmsTier1 = set(tier1Df['INVESTOR'].tolist()) - set(tier1Filtered['INVESTOR'].tolist())
            if removedFirmsTier1:
                print(f"\nFirms removed from Tier 1: {sorted(removedFirmsTier1)}")
        
        if 'INVESTOR' in tier2Df.columns:
            removedFirmsTier2 = set(tier2Df['INVESTOR'].tolist()) - set(tier2Filtered['INVESTOR'].tolist())
            if removedFirmsTier2:
                print(f"Firms removed from Tier 2: {sorted(removedFirmsTier2)}")
        
        # Summary
        print(f"\n" + "="*50)
        print(f"FIRM REMOVAL SUMMARY:")
        print(f"Original Tier 1 contacts: {len(tier1Df):,}")
        print(f"After firm removal: {len(tier1Filtered):,}")
        print(f"Tier 1 contacts removed: {len(tier1Df) - len(tier1Filtered):,}")
        print(f"Original Tier 2 contacts: {len(tier2Df):,}")
        print(f"After firm removal: {len(tier2Filtered):,}")
        print(f"Tier 2 contacts removed: {len(tier2Df) - len(tier2Filtered):,}")
        print(f"Total contacts removed: {(len(tier1Df) - len(tier1Filtered)) + (len(tier2Df) - len(tier2Filtered)):,}")
        print(f"Total remaining contacts: {len(tier1Filtered) + len(tier2Filtered):,}")
        
        # Save to new Excel file
        with pd.ExcelWriter(outputFile, engine='xlsxwriter') as writer:
            tier1Filtered.to_excel(writer, sheet_name="Tier1_Key_Contacts", index=False)
            tier2Filtered.to_excel(writer, sheet_name="Tier2_Junior_Contacts", index=False)
            
            # Create summary sheet
            summaryData = {
                'Metric': [
                    'Original Tier 1 Contacts',
                    'After Firm Removal (Tier 1)',
                    'Tier 1 Contacts Removed',
                    'Original Tier 2 Contacts',
                    'After Firm Removal (Tier 2)',
                    'Tier 2 Contacts Removed',
                    'Total Contacts Removed',
                    'Total Remaining Contacts'
                ],
                'Count': [
                    len(tier1Df),
                    len(tier1Filtered),
                    len(tier1Df) - len(tier1Filtered),
                    len(tier2Df),
                    len(tier2Filtered),
                    len(tier2Df) - len(tier2Filtered),
                    (len(tier1Df) - len(tier1Filtered)) + (len(tier2Df) - len(tier2Filtered)),
                    len(tier1Filtered) + len(tier2Filtered)
                ]
            }
            summaryDf = pd.DataFrame(summaryData)
            summaryDf.to_excel(writer, sheet_name="Firm_Removal_Summary", index=False)
        
        print(f"\n✓ Firm removal complete!")
        print(f"Output saved to: {outputFile}")
        
    except Exception as e:
        print(f"Error processing Excel file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Main function to remove specified firms from tiered results"""
    inputFile = "output/Two_Tier_Filtered_Family_Office_Contacts_v6.xlsx"
    outputFile = "output/Two_Tier_Filtered_Family_Office_Contacts_v7.xlsx"
    
    # Firms to remove as specified by user
    firmsToRemove = [
        "Mariner Wealth Advisors",
        "Bessemer Trust", 
        "Bitterroot",
        "CM wealth advisors",
        "Cerity Partners",
        "Goldman Sachs",
        "Halbert",
        "Jefferson River Capital",
        "Northern Trust",
        "Pin Oak",
        "Sanctuary Wealth",
        "Turtle Creek",
        "Waycrosse"
    ]
    
    # Check if input file exists
    if not Path(inputFile).exists():
        print(f"Error: Input file '{inputFile}' not found!")
        sys.exit(1)
    
    print("Remove Additional Firms from Tiered Filtering Results")
    print("=" * 60)
    print(f"Input file: {inputFile}")
    print(f"Output file: {outputFile}")
    print(f"Firms to remove: {len(firmsToRemove)}")
    for firm in firmsToRemove:
        print(f"  - {firm}")
    print()
    
    removeFirmsFromTieredResults(inputFile, outputFile, firmsToRemove)

if __name__ == "__main__":
    import re
    main()
