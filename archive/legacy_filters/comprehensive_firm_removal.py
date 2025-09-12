#!/usr/bin/env python3
"""
Comprehensive Firm Removal Script
Uses more sophisticated pattern matching to remove all contacts from specified firms
"""

import pandas as pd
import re
from pathlib import Path
from typing import List, Set

def createComprehensiveFirmPatterns(firmsToRemove: List[str]) -> List[re.Pattern]:
    """
    Create comprehensive regex patterns for firm removal
    
    Args:
        firmsToRemove: List of firm names to remove
        
    Returns:
        List of compiled regex patterns
    """
    patterns = []
    
    for firm in firmsToRemove:
        # Create multiple variations of the firm name
        variations = []
        
        # Original firm name
        variations.append(re.escape(firm))
        
        # Common variations
        if " " in firm:
            # Replace spaces with common separators
            variations.append(re.escape(firm.replace(" ", "")))
            variations.append(re.escape(firm.replace(" ", "-")))
            variations.append(re.escape(firm.replace(" ", "_")))
            variations.append(re.escape(firm.replace(" ", ".")))
        
        # Handle specific known variations
        if firm.lower() == "goldman sachs":
            variations.extend([
                r"goldman\s+sachs\s+private\s+wealth\s+management",
                r"goldman\s+sachs\s+asset\s+management",
                r"goldman\s+sachs\s+investment\s+management"
            ])
        elif firm.lower() == "northern trust":
            variations.extend([
                r"northern\s+trust\s+investments?",
                r"northern\s+trust\s+wealth\s+management",
                r"northern\s+trust\s+company"
            ])
        elif firm.lower() == "bessemer trust":
            variations.extend([
                r"bessemer\s+trust\s+company",
                r"bessemer\s+trust\s+investments?"
            ])
        elif firm.lower() == "mariner wealth advisors":
            variations.extend([
                r"mariner\s+wealth\s+advisors?",
                r"mariner\s+wealth\s+management"
            ])
        elif firm.lower() == "cerity partners":
            variations.extend([
                r"cerity\s+partners?",
                r"cerity\s+capital\s+partners?"
            ])
        elif firm.lower() == "halbert":
            variations.extend([
                r"halbert\s+hargrove",
                r"halbert\s+wealth\s+management",
                r"halbert\s+global\s+advisors?"
            ])
        elif firm.lower() == "jefferson river capital":
            variations.extend([
                r"jefferson\s+river\s+capital",
                r"jefferson\s+river\s+investments?"
            ])
        elif firm.lower() == "pin oak":
            variations.extend([
                r"pin\s+oak\s+investment\s+advisors?",
                r"pin\s+oak\s+capital",
                r"pin\s+oak\s+wealth"
            ])
        elif firm.lower() == "sanctuary wealth":
            variations.extend([
                r"sanctuary\s+wealth",
                r"sanctuary\s+capital"
            ])
        elif firm.lower() == "turtle creek":
            variations.extend([
                r"turtle\s+creek\s+investment\s+advisors?",
                r"turtle\s+creek\s+capital",
                r"turtle\s+creek\s+wealth"
            ])
        elif firm.lower() == "waycrosse":
            variations.extend([
                r"waycrosse",
                r"way\s+crosse"
            ])
        elif firm.lower() == "bitterroot":
            variations.extend([
                r"bitterroot\s+capital\s+advisors?",
                r"bitterroot\s+investments?"
            ])
        elif firm.lower() == "cm wealth advisors":
            variations.extend([
                r"cm\s+wealth\s+advisors?",
                r"c\.m\.\s+wealth\s+advisors?",
                r"cm\s+capital\s+advisors?"
            ])
        
        # Create pattern that matches any of the variations
        pattern = r"\b(?:" + "|".join(variations) + r")\b"
        patterns.append(re.compile(pattern, re.IGNORECASE))
    
    return patterns

def removeFirmsComprehensively(inputFile: str, outputFile: str, firmsToRemove: List[str]) -> None:
    """
    Comprehensively remove contacts from specified firms using advanced pattern matching
    
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
        
        # Create comprehensive patterns
        patterns = createComprehensiveFirmPatterns(firmsToRemove)
        
        print(f"\nCreated {len(patterns)} comprehensive patterns for firm removal")
        print("Firms to remove:")
        for firm in firmsToRemove:
            print(f"  - {firm}")
        
        # Filter Tier 1 contacts
        if 'INVESTOR' in tier1Df.columns:
            def shouldRemoveContact(investorName):
                if pd.isna(investorName):
                    return False
                investorStr = str(investorName)
                return any(pattern.search(investorStr) for pattern in patterns)
            
            tier1Filter = ~tier1Df['INVESTOR'].apply(shouldRemoveContact)
            tier1Filtered = tier1Df[tier1Filter]
            tier1Removed = len(tier1Df) - len(tier1Filtered)
            print(f"\nTier 1 contacts removed: {tier1Removed}")
            print(f"Tier 1 contacts remaining: {len(tier1Filtered)}")
        else:
            tier1Filtered = tier1Df.copy()
            print("INVESTOR column not found in Tier 1, skipping filter")
        
        # Filter Tier 2 contacts
        if 'INVESTOR' in tier2Df.columns:
            def shouldRemoveContact(investorName):
                if pd.isna(investorName):
                    return False
                investorStr = str(investorName)
                return any(pattern.search(investorStr) for pattern in patterns)
            
            tier2Filter = ~tier2Df['INVESTOR'].apply(shouldRemoveContact)
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
                print(f"\nFirms removed from Tier 1 ({len(removedFirmsTier1)} unique firms):")
                for firm in sorted(removedFirmsTier1):
                    count = sum(1 for x in tier1Df['INVESTOR'] if x == firm)
                    print(f"  - '{firm}' ({count} contacts)")
        
        if 'INVESTOR' in tier2Df.columns:
            removedFirmsTier2 = set(tier2Df['INVESTOR'].tolist()) - set(tier2Filtered['INVESTOR'].tolist())
            if removedFirmsTier2:
                print(f"\nFirms removed from Tier 2 ({len(removedFirmsTier2)} unique firms):")
                for firm in sorted(removedFirmsTier2):
                    count = sum(1 for x in tier2Df['INVESTOR'] if x == firm)
                    print(f"  - '{firm}' ({count} contacts)")
        
        # Summary
        print(f"\n" + "="*60)
        print(f"COMPREHENSIVE FIRM REMOVAL SUMMARY:")
        print(f"="*60)
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
                    'After Comprehensive Firm Removal (Tier 1)',
                    'Tier 1 Contacts Removed',
                    'Original Tier 2 Contacts',
                    'After Comprehensive Firm Removal (Tier 2)',
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
            summaryDf.to_excel(writer, sheet_name="Comprehensive_Removal_Summary", index=False)
        
        print(f"\n✓ Comprehensive firm removal complete!")
        print(f"Output saved to: {outputFile}")
        
    except Exception as e:
        print(f"Error processing Excel file: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to comprehensively remove specified firms"""
    inputFile = "output/Two_Tier_Filtered_Family_Office_Contacts_v6.xlsx"  # Start from v6
    outputFile = "output/Two_Tier_Filtered_Family_Office_Contacts_v8.xlsx"
    
    # Firms to remove (same as specified by user)
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
        return
    
    print("Comprehensive Firm Removal from Tiered Filtering Results")
    print("=" * 70)
    print(f"Input file: {inputFile}")
    print(f"Output file: {outputFile}")
    print(f"Firms to remove: {len(firmsToRemove)}")
    print()
    
    removeFirmsComprehensively(inputFile, outputFile, firmsToRemove)

if __name__ == "__main__":
    main()
