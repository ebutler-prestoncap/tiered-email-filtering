#!/usr/bin/env python3
"""
Analyze remaining contacts from specified firms to identify all variations
"""

import pandas as pd
import re
from pathlib import Path

def analyzeRemainingFirms(inputFile: str, firmsToCheck: list) -> None:
    """
    Analyze which contacts from specified firms still remain in the data
    
    Args:
        inputFile: Path to input Excel file with tiered results
        firmsToCheck: List of firm names to check for
    """
    try:
        print(f"Analyzing remaining contacts from specified firms in: {inputFile}")
        
        # Read both tier sheets
        tier1Df = pd.read_excel(inputFile, sheet_name="Tier1_Key_Contacts")
        tier2Df = pd.read_excel(inputFile, sheet_name="Tier2_Junior_Contacts")
        
        print(f"Tier 1 contacts: {len(tier1Df)}")
        print(f"Tier 2 contacts: {len(tier2Df)}")
        
        # Combine both tiers for analysis
        allContacts = pd.concat([tier1Df, tier2Df], ignore_index=True)
        
        print(f"\nAnalyzing {len(firmsToCheck)} specified firms...")
        print("=" * 60)
        
        remainingFirms = {}
        
        for firm in firmsToCheck:
            print(f"\nChecking for: '{firm}'")
            
            # Create multiple search patterns for this firm
            patterns = [
                firm.lower(),
                firm.replace(" ", "").lower(),
                firm.replace(" ", "-").lower(),
                firm.replace(" ", "_").lower(),
                firm.replace(" ", ".").lower(),
            ]
            
            # Also check for partial matches
            words = firm.split()
            if len(words) > 1:
                patterns.extend([word.lower() for word in words])
            
            foundContacts = []
            
            if 'INVESTOR' in allContacts.columns:
                for idx, row in allContacts.iterrows():
                    investor = str(row.get('INVESTOR', '')).lower()
                    
                    # Check if any pattern matches
                    for pattern in patterns:
                        if pattern in investor:
                            foundContacts.append({
                                'Tier': 'Tier1' if idx < len(tier1Df) else 'Tier2',
                                'INVESTOR': row.get('INVESTOR', ''),
                                'NAME': row.get('NAME', ''),
                                'JOB TITLE': row.get('JOB TITLE', ''),
                                'EMAIL': row.get('EMAIL', ''),
                                'Pattern Matched': pattern
                            })
                            break  # Only count once per contact
            
            if foundContacts:
                remainingFirms[firm] = foundContacts
                print(f"  Found {len(foundContacts)} remaining contacts:")
                for contact in foundContacts[:5]:  # Show first 5
                    print(f"    - {contact['INVESTOR']} | {contact['NAME']} | {contact['JOB TITLE']}")
                if len(foundContacts) > 5:
                    print(f"    ... and {len(foundContacts) - 5} more")
            else:
                print(f"  ✓ No remaining contacts found")
        
        # Summary
        print(f"\n" + "="*60)
        print(f"SUMMARY OF REMAINING CONTACTS:")
        print(f"="*60)
        
        totalRemaining = 0
        for firm, contacts in remainingFirms.items():
            print(f"\n{firm}: {len(contacts)} contacts")
            totalRemaining += len(contacts)
            
            # Show all unique investor names for this firm
            uniqueInvestors = set(contact['INVESTOR'] for contact in contacts)
            print(f"  Unique investor names found:")
            for investor in sorted(uniqueInvestors):
                count = sum(1 for c in contacts if c['INVESTOR'] == investor)
                print(f"    - '{investor}' ({count} contacts)")
        
        print(f"\nTotal remaining contacts from specified firms: {totalRemaining}")
        
        # Create detailed report
        if remainingFirms:
            reportFile = "output/remaining_contacts_analysis.csv"
            allRemainingContacts = []
            for firm, contacts in remainingFirms.items():
                for contact in contacts:
                    contact['Target_Firm'] = firm
                    allRemainingContacts.append(contact)
            
            if allRemainingContacts:
                reportDf = pd.DataFrame(allRemainingContacts)
                reportDf.to_csv(reportFile, index=False)
                print(f"\nDetailed report saved to: {reportFile}")
        
    except Exception as e:
        print(f"Error analyzing file: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to analyze remaining contacts"""
    inputFile = "output/Two_Tier_Filtered_Family_Office_Contacts_v7.xlsx"
    
    # Firms to check (same as specified by user)
    firmsToCheck = [
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
        return
    
    print("Analyze Remaining Contacts from Specified Firms")
    print("=" * 60)
    print(f"Input file: {inputFile}")
    print(f"Firms to check: {len(firmsToCheck)}")
    print()
    
    analyzeRemainingFirms(inputFile, firmsToCheck)

if __name__ == "__main__":
    main()
