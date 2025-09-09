#!/usr/bin/env python3
"""
Bucket Overflow Excel Contact Filter Script
Creates two tiers of filtered contacts with bucket overflow approach:
- Tier 1: Key contacts (CIO, Hedge fund, private credit, fixed income, private debt, alternatives, head of investments, head of research) - max 10 per firm
- Tier 2: Junior contacts (research, portfolio, investment, analyst, associate) - max 6 total per firm
"""

import pandas as pd
import re
import sys
from pathlib import Path
from typing import Tuple, Dict, Any

def createTier1Filter() -> Dict[str, Any]:
    """
    Create Tier 1 filter configuration for key contacts (bucket approach)
    
    Returns:
        Dict containing filter configuration for Tier 1
    """
    return {
        'name': 'Tier 1 - Key Contacts',
        'description': 'Most important key contacts: CIO, Hedge fund, private credit, fixed income, private debt, alternatives, head of investments, head of research',
        'job_title_pattern': r".*\b(cio|c\.i\.o\.|c\.i\.o|chief\s+investment\s+officer|hedge\s+fund|private\s+credit|private\s+debt|fixed\s+income|alternatives?[\s-]?investments?|alternatives?|head\s+of\s+investments?|head\s+of\s+research|investment\s+committee|investment\s+partner)\b",
        'exclusion_pattern': r".*\b(operations?|hr|human\s+resources?|investor\s+relations?|client\s+relations?|marketing|sales|compliance|technology|administrator|assistant|associate\s+director|associate\s+vice\s+president|managing\s+director)\b",
        'required_role_terms': ['investment team', 'investment', 'portfolio', 'research'],
        'priority_keywords': ['cio', 'hedge fund', 'private credit', 'private debt', 'fixed income', 'alternatives', 'head of investments', 'head of research']
    }

def createTier2Filter() -> Dict[str, Any]:
    """
    Create Tier 2 filter configuration for junior/less impact contacts
    
    Returns:
        Dict containing filter configuration for Tier 2
    """
    return {
        'name': 'Tier 2 - Junior Contacts',
        'description': 'Junior investment professionals, excluding operations/HR',
        'job_title_pattern': r".*\b(research|portfolio|investment|analyst|associate|coordinator|specialist|advisor|representative|assistant\s+portfolio\s+manager|investment\s+analyst|research\s+analyst|portfolio\s+analyst|investment\s+advisor|wealth\s+advisor|trust\s+officer)\b",
        'exclusion_pattern': r".*\b(operations?|hr|human\s+resources?|investor\s+relations?|client\s+relations?|marketing|sales|compliance|technology|administrator|assistant|cio|chief\s+investment\s+officer|hedge\s+fund|private\s+credit|private\s+debt|fixed\s+income|alternatives?|head\s+of\s+investments?|head\s+of\s+research|managing\s+director|investment\s+director|president|vice\s+president|executive\s+vice\s+president|senior\s+vice\s+president|director\s+of\s+investments?|senior\s+director)\b",
        'required_role_terms': ['investment team', 'investment', 'portfolio', 'research'],
        'priority_keywords': ['research', 'portfolio', 'investment', 'analyst', 'associate']
    }

def applyTierFilter(df: pd.DataFrame, tierConfig: Dict[str, Any], maxContactsPerFirm: int = 6) -> pd.DataFrame:
    """
    Apply tier-specific filtering to dataframe with firm-based contact limits
    
    Args:
        df: Input dataframe
        tierConfig: Tier configuration dictionary
        maxContactsPerFirm: Maximum number of contacts per firm
        
    Returns:
        Filtered dataframe for the tier
    """
    filtered_df = df.copy()
    
    # Apply job title regex filter
    if 'JOB TITLE' in filtered_df.columns:
        job_title_regex = re.compile(tierConfig['job_title_pattern'], re.IGNORECASE)
        exclusion_regex = re.compile(tierConfig['exclusion_pattern'], re.IGNORECASE)
        
        def matchesTierCriteria(row):
            job_title = str(row.get('JOB TITLE', '')).lower()
            role = str(row.get('ROLE', '')).lower()
            
            # Check job title matches (must contain at least one positive term)
            if not job_title_regex.search(job_title):
                return False
                
            # Check exclusions (must NOT contain any exclusion terms)
            if exclusion_regex.search(job_title):
                return False
                
            # Check role requirements (role must contain at least one required term)
            if tierConfig['required_role_terms']:
                role_matches = any(term in role for term in tierConfig['required_role_terms'])
                if not role_matches:
                    return False
                    
            return True
        
        tier_filter = filtered_df.apply(matchesTierCriteria, axis=1)
        filtered_df = filtered_df[tier_filter]
    
    # Apply firm-based contact limits
    if 'INVESTOR' in filtered_df.columns and len(filtered_df) > 0:
        # Sort by priority keywords to ensure best contacts are selected first
        def calculatePriority(row):
            job_title = str(row.get('JOB TITLE', '')).lower()
            priority_score = 0
            
            # Higher priority for more senior terms
            for keyword in tierConfig['priority_keywords']:
                if keyword.lower() in job_title:
                    priority_score += 10
            
            # Additional priority for specific high-value terms
            high_value_terms = ['cio', 'chief investment officer', 'managing director', 'president', 'vice president']
            for term in high_value_terms:
                if term in job_title:
                    priority_score += 5
            
            return priority_score
        
        # Add priority score and sort
        filtered_df = filtered_df.copy()
        filtered_df['_priority_score'] = filtered_df.apply(calculatePriority, axis=1)
        filtered_df = filtered_df.sort_values(['INVESTOR', '_priority_score'], ascending=[True, False])
        
        # Limit contacts per firm
        limited_contacts = []
        for firm, group in filtered_df.groupby('INVESTOR'):
            # Take up to maxContactsPerFirm contacts from this firm
            firm_contacts = group.head(maxContactsPerFirm)
            limited_contacts.append(firm_contacts)
        
        if limited_contacts:
            filtered_df = pd.concat(limited_contacts, ignore_index=True)
            # Remove the temporary priority score column
            filtered_df = filtered_df.drop('_priority_score', axis=1)
    
    return filtered_df

def applyBucketOverflowFilter(df: pd.DataFrame, tier1Config: Dict[str, Any], tier2Config: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Apply bucket overflow filtering approach:
    - Tier 1: Key contacts only (max 10 per firm, don't fill if fewer match)
    - Tier 2: Tier 1 overflow + junior contacts (max 6 total per firm)
    
    Args:
        df: Input dataframe
        tier1Config: Tier 1 configuration for key contacts
        tier2Config: Tier 2 configuration for junior contacts
        
    Returns:
        Tuple of (tier1_df, tier2_df) - filtered dataframes for each tier
    """
    tier1Df = pd.DataFrame()
    tier2Df = pd.DataFrame()
    
    if 'INVESTOR' not in df.columns:
        print("Warning: INVESTOR column not found, cannot apply firm-based filtering")
        return tier1Df, tier2Df
    
    # Process each firm separately
    for firm, firmGroup in df.groupby('INVESTOR'):
        print(f"Processing firm: {firm}")
        
        # Step 1: Get Tier 1 key contacts (max 10, don't fill if fewer match)
        tier1FirmContacts = applyTierFilter(firmGroup, tier1Config, maxContactsPerFirm=10)
        tier1FirmCount = len(tier1FirmContacts)
        print(f"  Tier 1 key contacts found: {tier1FirmCount}")
        
        # Step 2: Get remaining contacts for Tier 2
        tier1Ids = set()
        if 'CONTACT_ID' in tier1FirmContacts.columns:
            tier1Ids = set(tier1FirmContacts['CONTACT_ID'].tolist())
        
        remainingContacts = firmGroup.copy()
        if tier1Ids:
            remainingContacts = remainingContacts[~remainingContacts['CONTACT_ID'].isin(tier1Ids)]
        
        # Step 3: Apply Tier 2 filter to remaining contacts
        tier2FirmContacts = applyTierFilter(remainingContacts, tier2Config, maxContactsPerFirm=6)
        tier2FirmCount = len(tier2FirmContacts)
        print(f"  Tier 2 junior contacts found: {tier2FirmCount}")
        
        # Step 4: Combine with existing results
        if not tier1FirmContacts.empty:
            tier1Df = pd.concat([tier1Df, tier1FirmContacts], ignore_index=True)
        if not tier2FirmContacts.empty:
            tier2Df = pd.concat([tier2Df, tier2FirmContacts], ignore_index=True)
    
    return tier1Df, tier2Df

def twoTierFilterContacts(inputFile: str, outputFile: str, removeListFile: str = "remove list.csv") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Apply two-tier filtering to contacts in Excel file
    
    Args:
        inputFile: Path to input Excel file
        outputFile: Path to output filtered Excel file
        removeListFile: Path to CSV file containing contact IDs to exclude
        
    Returns:
        Tuple of (tier1_df, tier2_df) - filtered dataframes for each tier
    """
    try:
        # Read the Excel file
        print(f"Reading Excel file: {inputFile}")
        
        # Read the Contacts_Export sheet specifically
        dfContacts = pd.read_excel(inputFile, sheet_name="Contacts_Export")
        print(f"Contacts_Export sheet shape: {dfContacts.shape}")
        print(f"Columns: {list(dfContacts.columns)}")
        
        originalCount = len(dfContacts)
        print(f"\nOriginal contact count: {originalCount}")
        
        # Step 0: Load and apply remove list exclusions
        print(f"\nStep 0: Loading contact IDs to exclude from {removeListFile}...")
        
        try:
            # Read the remove list CSV file
            removeDf = pd.read_csv(removeListFile, header=None, names=['CONTACT_ID'])
            # Remove any empty rows and convert to integers
            removeIds = set(removeDf['CONTACT_ID'].dropna().astype(int).tolist())
            print(f"Loaded {len(removeIds)} contact IDs to exclude")
            
            # Apply remove list filter
            if 'CONTACT_ID' in dfContacts.columns:
                beforeRemoveFilter = len(dfContacts)
                dfContacts = dfContacts[~dfContacts['CONTACT_ID'].isin(removeIds)]
                excludedByRemoveList = beforeRemoveFilter - len(dfContacts)
                print(f"Contacts excluded by remove list: {excludedByRemoveList}")
                print(f"Remaining after remove list filter: {len(dfContacts)}")
            else:
                print("CONTACT_ID column not found, skipping remove list filter")
                
        except FileNotFoundError:
            print(f"Warning: Remove list file '{removeListFile}' not found, skipping remove list filter")
        except Exception as e:
            print(f"Warning: Error processing remove list file: {e}")
            print("Continuing without remove list filter")
        
        # Step 1: Exclude specific firm names (same as before)
        excludedFirms = [
            "Morgan Stanley Private Wealth Management",
            "HighTower Advisors", 
            "Creative Planning",
            "Cresset Asset Management",
            "Jasper Ridge Partners",
            "Soros Fund Management",
            "Rockefeller Capital Management",
            "Great Lakes Advisors",
            "DFO Management",
            "Gresham Partners",
            "Johnson Financial Group",
            "Twin Focus Capital Partners",
            "Stelac Advisory Services",
            "Waterloo Capital",
            "Pennington Partners & Co"
        ]
        
        # Create exclusion pattern
        exclusionPattern = r"^(?!.*\b(?:" + "|".join(re.escape(firm) for firm in excludedFirms) + r")\b).*$"
        exclusionRegex = re.compile(exclusionPattern, re.IGNORECASE)
        
        print(f"\nStep 1: Excluding specific firms...")
        print(f"Firms to exclude: {excludedFirms}")
        
        # Apply firm exclusion filter to INVESTOR column
        if 'INVESTOR' in dfContacts.columns:
            firmFilter = dfContacts['INVESTOR'].apply(
                lambda x: bool(exclusionRegex.match(str(x))) if pd.notna(x) else True
            )
            dfFiltered = dfContacts[firmFilter]
            excludedByFirm = originalCount - len(dfFiltered)
            print(f"Contacts excluded by firm filter: {excludedByFirm}")
            print(f"Remaining after firm filter: {len(dfFiltered)}")
        else:
            dfFiltered = dfContacts.copy()
            print("INVESTOR column not found, skipping firm filter")
        
        # Step 2: Require "Investment Team" in ROLE column
        print(f"\nStep 2: Filtering for 'Investment Team' in ROLE column...")
        
        if 'ROLE' in dfFiltered.columns:
            roleFilter = dfFiltered['ROLE'].apply(
                lambda x: 'Investment Team' in str(x) if pd.notna(x) else False
            )
            dfFiltered = dfFiltered[roleFilter]
            afterRoleFilter = len(dfFiltered)
            print(f"Contacts with 'Investment Team' in ROLE: {afterRoleFilter}")
        else:
            print("ROLE column not found, skipping role filter")
            afterRoleFilter = len(dfFiltered)
        
        # Step 3: Apply bucket overflow filtering approach
        print(f"\nStep 3: Applying bucket overflow filtering approach...")
        
        # Create tier configurations
        tier1Config = createTier1Filter()
        tier2Config = createTier2Filter()
        
        # Apply bucket overflow filtering
        print(f"\nApplying {tier1Config['name']} filter (max 10 key contacts per firm)...")
        print(f"Applying {tier2Config['name']} filter (max 6 total contacts per firm)...")
        tier1Df, tier2Df = applyBucketOverflowFilter(dfFiltered, tier1Config, tier2Config)
        print(f"Tier 1 key contacts: {len(tier1Df)}")
        print(f"Tier 2 junior contacts: {len(tier2Df)}")
        
        # Final verification: ensure no duplicates between tiers
        if 'CONTACT_ID' in tier1Df.columns and 'CONTACT_ID' in tier2Df.columns:
            tier1Ids = set(tier1Df['CONTACT_ID'].tolist())
            tier2Ids = set(tier2Df['CONTACT_ID'].tolist())
            duplicates = tier1Ids.intersection(tier2Ids)
            if duplicates:
                print(f"Warning: Found {len(duplicates)} duplicates between tiers - removing from Tier 2")
                tier2Df = tier2Df[~tier2Df['CONTACT_ID'].isin(duplicates)]
                print(f"Tier 2 contacts after removing duplicates: {len(tier2Df)}")
            else:
                print("✓ No duplicates between tiers confirmed")
        else:
            print("Warning: CONTACT_ID column not found, cannot verify no duplicates between tiers")
        
        # Summary
        print(f"\n" + "="*50)
        print(f"BUCKET OVERFLOW FILTERING SUMMARY:")
        print(f"Original contacts: {originalCount:,}")
        print(f"After firm exclusion: {len(dfFiltered):,}")
        print(f"Tier 1 (Key Contacts): {len(tier1Df):,} (max 10 per firm, key titles only)")
        print(f"Tier 2 (Junior Contacts): {len(tier2Df):,} (max 6 total per firm)")
        print(f"Total filtered contacts: {len(tier1Df) + len(tier2Df):,}")
        print(f"Duplicates between tiers: 0 (ensured)")
        
        # Firm-based statistics
        if 'INVESTOR' in tier1Df.columns and 'INVESTOR' in tier2Df.columns:
            tier1Firms = tier1Df['INVESTOR'].nunique()
            tier2Firms = tier2Df['INVESTOR'].nunique()
            totalFirms = len(set(tier1Df['INVESTOR'].tolist() + tier2Df['INVESTOR'].tolist()))
            print(f"Tier 1 firms: {tier1Firms:,}")
            print(f"Tier 2 firms: {tier2Firms:,}")
            print(f"Total unique firms: {totalFirms:,}")
            
            # Show firms with most contacts
            if len(tier1Df) > 0:
                tier1FirmCounts = tier1Df['INVESTOR'].value_counts().head(5)
                print(f"\nTop 5 Tier 1 firms by contact count:")
                for firm, count in tier1FirmCounts.items():
                    print(f"  {firm}: {count} contacts")
            
            if len(tier2Df) > 0:
                tier2FirmCounts = tier2Df['INVESTOR'].value_counts().head(5)
                print(f"\nTop 5 Tier 2 firms by contact count:")
                for firm, count in tier2FirmCounts.items():
                    print(f"  {firm}: {count} contacts")
        
        # Show sample of filtered results
        if not tier1Df.empty:
            print(f"\nSample Tier 1 Key Contacts:")
            print("-" * 30)
            sampleSize = min(5, len(tier1Df))
            sampleDf = tier1Df.head(sampleSize)
            
            for idx, row in sampleDf.iterrows():
                print(f"\nTier 1 Contact {idx + 1}:")
                print(f"  Firm: {row.get('INVESTOR', 'N/A')}")
                print(f"  Name: {row.get('NAME', 'N/A')}")
                print(f"  Job Title: {row.get('JOB TITLE', 'N/A')}")
                print(f"  Role: {row.get('ROLE', 'N/A')}")
                print(f"  Email: {row.get('EMAIL', 'N/A')}")
        
        if not tier2Df.empty:
            print(f"\nSample Tier 2 Junior Contacts:")
            print("-" * 30)
            sampleSize = min(5, len(tier2Df))
            sampleDf = tier2Df.head(sampleSize)
            
            for idx, row in sampleDf.iterrows():
                print(f"\nTier 2 Contact {idx + 1}:")
                print(f"  Firm: {row.get('INVESTOR', 'N/A')}")
                print(f"  Name: {row.get('NAME', 'N/A')}")
                print(f"  Job Title: {row.get('JOB TITLE', 'N/A')}")
                print(f"  Role: {row.get('ROLE', 'N/A')}")
                print(f"  Email: {row.get('EMAIL', 'N/A')}")
        
        # Save to new Excel file with separate sheets
        with pd.ExcelWriter(outputFile, engine='xlsxwriter') as writer:
            tier1Df.to_excel(writer, sheet_name="Tier1_Key_Contacts", index=False)
            tier2Df.to_excel(writer, sheet_name="Tier2_Junior_Contacts", index=False)
            
            # Create summary sheet
            summaryData = {
                'Metric': [
                    'Original Contacts',
                    'After Firm Exclusion',
                    'Tier 1 (Key Contacts)',
                    'Tier 2 (Junior Contacts)',
                    'Total Filtered',
                    'Duplicates Between Tiers'
                ],
                'Count': [
                    originalCount,
                    len(dfFiltered),
                    len(tier1Df),
                    len(tier2Df),
                    len(tier1Df) + len(tier2Df),
                    0
                ]
            }
            summaryDf = pd.DataFrame(summaryData)
            summaryDf.to_excel(writer, sheet_name="Filtering_Summary", index=False)
        
        print(f"\n✓ Bucket overflow filtering complete!")
        print(f"Output saved to: {outputFile}")
        print(f"  - Tier 1 (Key Contacts): {len(tier1Df)} contacts")
        print(f"  - Tier 2 (Junior Contacts): {len(tier2Df)} contacts")
        
        return tier1Df, tier2Df
        
    except Exception as e:
        print(f"Error processing Excel file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Main function to execute the two-tier filtering"""
    inputFile = "AI list- Family offices (002).xlsx"
    outputFile = "Two_Tier_Filtered_Family_Office_Contacts.xlsx"
    
    # Check if input file exists
    if not Path(inputFile).exists():
        print(f"Error: Input file '{inputFile}' not found!")
        sys.exit(1)
    
    print("Bucket Overflow Contact Filter Script")
    print("=" * 50)
    print(f"Input file: {inputFile}")
    print(f"Output file: {outputFile}")
    print("\nFiltering criteria:")
    print("0. EXCLUDE contact IDs from remove list")
    print("1. EXCLUDE specific firm names")
    print("2. REQUIRE 'Investment Team' in ROLE column")
    print("3. APPLY bucket overflow filtering:")
    print("   - Tier 1: Key contacts (CIO, Hedge fund, private credit, fixed income, private debt, alternatives, head of investments, head of research) - max 10 per firm")
    print("   - Tier 2: Junior contacts (research, portfolio, investment, analyst, associate) - max 6 total per firm")
    print("4. ENSURE no duplicates between tiers")
    print()
    
    twoTierFilterContacts(inputFile, outputFile)

if __name__ == "__main__":
    main()
