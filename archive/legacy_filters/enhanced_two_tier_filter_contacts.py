#!/usr/bin/env python3
"""
Enhanced Two-Tier Contact Filter with Flexible Sheet Detection
Extends the original two-tier filtering to handle different Excel sheet structures and adds email intelligence
"""

import pandas as pd
import re
import sys
from pathlib import Path
from typing import Tuple, Dict, Any

def detect_contact_sheet(input_file: str) -> str:
    """
    Detect the correct sheet name containing contact data
    
    Args:
        input_file: Path to Excel file
        
    Returns:
        Name of the sheet containing contact data
    """
    try:
        xls = pd.ExcelFile(input_file)
        sheet_names = xls.sheet_names
        
        # Priority order for sheet detection
        preferred_sheets = ['Contacts_Export', 'Sheet1', 'Contacts', 'Data', 'Export']
        
        for preferred in preferred_sheets:
            if preferred in sheet_names:
                return preferred
        
        # If no preferred sheet found, use the first sheet
        return sheet_names[0]
        
    except Exception as e:
        print(f"Error detecting sheet: {e}")
        return 'Sheet1'  # Default fallback

def createTier1Filter() -> Dict[str, Any]:
    """Create Tier 1 filter configuration for key contacts"""
    return {
        'name': 'Tier 1 - Key Contacts',
        'description': 'Most important key contacts: CIO, hedge/hedge fund, credit/private credit, private debt, fixed income, income, private, markets, managing director, alternatives, absolute return, head of investments, head of research, senior portfolio manager, investment director',
        'job_title_pattern': r".*\b(cio|c\.i\.o\.|c\.i\.o|chief\s+investment\s+officer|hedge|hedge\s+fund|credit|private\s+credit|private\s+debt|fixed\s+income|income|private|markets?|managing\s+director|alternatives?[\s-]?investments?|alternatives?|absolute|absolute\s+return|head\s+of\s+investments?|head\s+of\s+research|investment\s+committee|investment\s+partner|senior\s+portfolio\s+manager|investment\s+director)\b",
        'exclusion_pattern': r"^$",  # No exclusions for Tier 1
        'required_role_terms': ['investment team', 'investment', 'portfolio', 'research'],
        'priority_keywords': ['cio', 'hedge', 'hedge fund', 'credit', 'private credit', 'private debt', 'fixed income', 'income', 'private', 'markets', 'managing director', 'alternatives', 'absolute', 'absolute return', 'head of investments', 'head of research', 'senior portfolio manager', 'investment director']
    }

def createTier2Filter() -> Dict[str, Any]:
    """Create Tier 2 filter configuration for junior/less impact contacts"""
    return {
        'name': 'Tier 2 - Junior Contacts',
        'description': 'Junior investment professionals, excluding operations/HR',
        'job_title_pattern': r".*\b(research|portfolio|investment|analyst|associate|coordinator|specialist|advisor|representative|assistant\s+portfolio\s+manager|investment\s+analyst|research\s+analyst|portfolio\s+analyst|investment\s+advisor|wealth\s+advisor|trust\s+officer)\b",
        'exclusion_pattern': r".*\b(operations?|hr|human\s+resources?|investor\s+relations?|client\s+relations?|marketing|sales|compliance|technology|administrator|assistant|cio|c\.i\.o\.|c\.i\.o|chief\s+investment\s+officer|hedge|hedge\s+fund|credit|private\s+credit|private\s+debt|fixed\s+income|income|private|markets?|managing\s+director|alternatives?|absolute|absolute\s+return|head\s+of\s+investments?|head\s+of\s+research|investment\s+committee|investment\s+partner|senior\s+portfolio\s+manager|investment\s+director|president|vice\s+president|executive\s+vice\s+president|senior\s+vice\s+president|director\s+of\s+investments?|senior\s+director)\b",
        'required_role_terms': ['investment team', 'investment', 'portfolio', 'research'],
        'priority_keywords': ['research', 'portfolio', 'investment', 'analyst', 'associate']
    }

def applyTierFilter(df: pd.DataFrame, tierConfig: Dict[str, Any], maxContactsPerFirm: int = 6) -> pd.DataFrame:
    """Apply tier-specific filtering to dataframe with firm-based contact limits"""
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
            
            # Tier 1: Highest priority roles (score 100+)
            if 'cio' in job_title or 'chief investment officer' in job_title:
                priority_score += 100
            if 'head of investments' in job_title or 'head of research' in job_title:
                priority_score += 90
            if 'investment committee' in job_title or 'investment partner' in job_title:
                priority_score += 85
            if 'senior portfolio manager' in job_title or 'investment director' in job_title:
                priority_score += 80
            
            # Tier 2: High priority investment focus areas (score 70-79)
            if 'hedge fund' in job_title or 'hedge' in job_title:
                priority_score += 75
            if 'private credit' in job_title or 'private debt' in job_title:
                priority_score += 75
            if 'alternatives' in job_title or 'absolute return' in job_title:
                priority_score += 70
            if 'fixed income' in job_title:
                priority_score += 70
            
            # Tier 3: Medium priority roles (score 50-69)
            if 'managing director' in job_title:
                priority_score += 60
            if 'credit' in job_title or 'income' in job_title:
                priority_score += 55
            if 'private' in job_title or 'markets' in job_title:
                priority_score += 50
            
            # Base score for other keywords
            for keyword in tierConfig['priority_keywords']:
                if keyword.lower() in job_title and priority_score == 0:
                    priority_score += 10
            
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
    """Apply bucket overflow filtering approach"""
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
        
        # Step 2: Calculate remaining slots for Tier 2
        tier1UnusedSlots = 10 - tier1FirmCount
        tier2MaxSlots = tier1UnusedSlots + 6  # Unused Tier 1 slots + 6 Tier 2 slots
        print(f"  Tier 1 unused slots: {tier1UnusedSlots}, Tier 2 max slots: {tier2MaxSlots}")
        
        # Step 3: Get remaining contacts for Tier 2
        tier1Ids = set()
        if 'CONTACT_ID' in tier1FirmContacts.columns:
            tier1Ids = set(tier1FirmContacts['CONTACT_ID'].tolist())
        
        remainingContacts = firmGroup.copy()
        if tier1Ids:
            remainingContacts = remainingContacts[~remainingContacts['CONTACT_ID'].isin(tier1Ids)]
        
        # Step 4: Apply Tier 2 filter to remaining contacts with overflow slots
        tier2FirmContacts = applyTierFilter(remainingContacts, tier2Config, maxContactsPerFirm=tier2MaxSlots)
        tier2FirmCount = len(tier2FirmContacts)
        print(f"  Tier 2 junior contacts found: {tier2FirmCount}")
        
        # Step 5: Combine with existing results
        if not tier1FirmContacts.empty:
            tier1Df = pd.concat([tier1Df, tier1FirmContacts], ignore_index=True)
        if not tier2FirmContacts.empty:
            tier2Df = pd.concat([tier2Df, tier2FirmContacts], ignore_index=True)
    
    return tier1Df, tier2Df

def enhancedTwoTierFilterContacts(inputFile: str, outputFile: str, removeListFile: str = "remove list.csv") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Apply enhanced two-tier filtering with flexible sheet detection
    """
    try:
        # Detect the correct sheet to read
        sheet_name = detect_contact_sheet(inputFile)
        print(f"Reading Excel file: {inputFile}")
        print(f"Using sheet: {sheet_name}")
        
        # Read the detected sheet
        dfContacts = pd.read_excel(inputFile, sheet_name=sheet_name)
        print(f"{sheet_name} sheet shape: {dfContacts.shape}")
        print(f"Columns: {list(dfContacts.columns)}")
        
        originalCount = len(dfContacts)
        print(f"\nOriginal contact count: {originalCount}")
        
        # Step 0: Load and apply remove list exclusions
        print(f"\nStep 0: Loading contact IDs to exclude from {removeListFile}...")
        
        try:
            # Read the remove list CSV file
            removeDf = pd.read_csv(removeListFile, header=None, names=['CONTACT_ID'])
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
        
        # Step 1: Exclude specific firm names
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
            "Pennington Partners & Co",
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
        
        # Create exclusion pattern
        exclusionPattern = r"^(?!.*\b(?:" + "|".join(re.escape(firm) for firm in excludedFirms) + r")\b).*$"
        exclusionRegex = re.compile(exclusionPattern, re.IGNORECASE)
        
        print(f"\nStep 1: Excluding specific firms...")
        print(f"Firms to exclude: {len(excludedFirms)} firms")
        
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
        
        # Step 2: Require "Investment Team" in ROLE column (flexible)
        print(f"\nStep 2: Filtering for investment-related roles...")
        
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
        print(f"Applying {tier2Config['name']} filter (max 16 total contacts per firm)...")
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
        
        # Summary
        print(f"\n" + "="*50)
        print(f"ENHANCED BUCKET OVERFLOW FILTERING SUMMARY:")
        print(f"Original contacts: {originalCount:,}")
        print(f"After firm exclusion: {len(dfFiltered):,}")
        print(f"Tier 1 (Key Contacts): {len(tier1Df):,}")
        print(f"Tier 2 (Junior Contacts): {len(tier2Df):,}")
        print(f"Total filtered contacts: {len(tier1Df) + len(tier2Df):,}")
        
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
        
        print(f"\n✓ Enhanced filtering complete!")
        print(f"Output saved to: {outputFile}")
        
        return tier1Df, tier2Df
        
    except Exception as e:
        print(f"Error processing Excel file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    inputFile = "input/Institutional Combined_Contact_List.xlsx"
    outputFile = "output/Enhanced_Institutional_Contacts.xlsx"
    
    # Check if input file exists
    if not Path(inputFile).exists():
        print(f"Error: Input file '{inputFile}' not found!")
        sys.exit(1)
    
    print("Enhanced Two-Tier Contact Filter with Flexible Sheet Detection")
    print("=" * 70)
    print(f"Input file: {inputFile}")
    print(f"Output file: {outputFile}")
    print()
    
    enhancedTwoTierFilterContacts(inputFile, outputFile)
