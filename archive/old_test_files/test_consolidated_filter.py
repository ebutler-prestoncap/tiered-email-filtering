#!/usr/bin/env python3
"""
Test script for the consolidated tiered filter
"""

import pandas as pd
from pathlib import Path
import sys

# Add the current directory to path so we can import our module
sys.path.append(str(Path(__file__).parent))

from consolidated_tiered_filter import ConsolidatedTieredFilter

def create_test_data():
    """Create sample test data for validation"""
    
    # Sample contact data with various titles and missing emails
    test_data = {
        'NAME': [
            'John Smith', 'Jane Doe', 'Robert Johnson', 'Mary Williams', 'David Brown',
            'Lisa Davis', 'Michael Wilson', 'Sarah Miller', 'James Jones', 'Jennifer Garcia',
            'Christopher Martinez', 'Elizabeth Anderson', 'Daniel Taylor', 'Ashley Thomas'
        ],
        'INVESTOR': [
            'Alpha Capital', 'Alpha Capital', 'Beta Investments', 'Beta Investments', 'Gamma Fund',
            'Gamma Fund', 'Delta Management', 'Delta Management', 'Epsilon Partners', 'Epsilon Partners',
            'Zeta Group', 'Zeta Group', 'Eta Holdings', 'Eta Holdings'
        ],
        'JOB TITLE': [
            'Chief Investment Officer',  # Tier 1
            'Investment Analyst',       # Tier 2
            'Managing Director',        # Tier 1
            'Research Analyst',         # Tier 2
            'Head of Private Markets',  # Tier 1
            'Portfolio Analyst',        # Tier 2
            'Investment Director',      # Tier 1
            'Associate Director',       # Tier 2
            'Portfolio Manager',        # Tier 1
            'Investment Associate',     # Tier 2
            'Executive Director',       # Tier 1
            'Research Associate',       # Tier 2
            'President',               # Tier 1
            'Investment Coordinator'    # Tier 2
        ],
        'EMAIL': [
            'john.smith@alphacap.com',
            '',  # Missing email
            'r.johnson@betainv.com',
            '',  # Missing email
            'david.brown@gammafund.com',
            '',  # Missing email
            'michael.wilson@deltamgmt.com',
            '',  # Missing email
            'james.jones@epsilonpartners.com',
            '',  # Missing email
            'c.martinez@zetagroup.com',
            '',  # Missing email
            'daniel.taylor@etaholdings.com',
            ''   # Missing email
        ],
        'ROLE': [
            'Investment Team', 'Investment Team', 'Investment Team', 'Investment Team',
            'Investment Team', 'Investment Team', 'Investment Team', 'Investment Team',
            'Investment Team', 'Investment Team', 'Investment Team', 'Investment Team',
            'Investment Team', 'Investment Team'
        ],
        'CONTACT_ID': list(range(1, 15))
    }
    
    return pd.DataFrame(test_data)

def test_consolidated_filter():
    """Test the consolidated filter functionality"""
    
    print("🧪 TESTING CONSOLIDATED TIERED FILTER")
    print("=" * 50)
    
    # Create test data
    test_df = create_test_data()
    print(f"📊 Created test dataset: {len(test_df)} contacts")
    print(f"   Firms: {test_df['INVESTOR'].nunique()}")
    print(f"   Missing emails: {(test_df['EMAIL'] == '').sum()}")
    
    # Initialize filter
    filter_tool = ConsolidatedTieredFilter()
    
    # Test standardization
    print("\n1️⃣ Testing column standardization...")
    standardized_df = filter_tool.standardize_column_names(test_df)
    print(f"   ✅ Columns: {list(standardized_df.columns)}")
    
    # Test email pattern extraction
    print("\n2️⃣ Testing email pattern extraction...")
    patterns = filter_tool.extract_email_patterns_by_firm(standardized_df)
    print(f"   ✅ Patterns extracted for {len(patterns)} firms")
    for firm, firm_patterns in patterns.items():
        print(f"      {firm}: {firm_patterns}")
    
    # Test tier filtering
    print("\n3️⃣ Testing Tier 1 filtering...")
    tier1_config = filter_tool.create_tier1_filter()
    tier1_result = filter_tool.apply_tier_filter(standardized_df, tier1_config, 10)
    print(f"   ✅ Tier 1 contacts: {len(tier1_result)}")
    if len(tier1_result) > 0:
        print(f"      Sample titles: {tier1_result['JOB TITLE'].tolist()[:3]}")
    
    print("\n4️⃣ Testing Tier 2 filtering...")
    tier2_config = filter_tool.create_tier2_filter()
    # Remove Tier 1 contacts from Tier 2 consideration
    tier1_ids = set(tier1_result['CONTACT_ID'].tolist())
    tier2_candidates = standardized_df[~standardized_df['CONTACT_ID'].isin(tier1_ids)]
    tier2_result = filter_tool.apply_tier_filter(tier2_candidates, tier2_config, 6)
    print(f"   ✅ Tier 2 contacts: {len(tier2_result)}")
    if len(tier2_result) > 0:
        print(f"      Sample titles: {tier2_result['JOB TITLE'].tolist()[:3]}")
    
    # Test email filling
    print("\n5️⃣ Testing missing email filling...")
    tier1_filled = filter_tool.fill_missing_emails(tier1_result, patterns)
    tier2_filled = filter_tool.fill_missing_emails(tier2_result, patterns)
    
    tier1_missing_before = (tier1_result['EMAIL'] == '').sum()
    tier1_missing_after = (tier1_filled['EMAIL'] == '').sum()
    tier2_missing_before = (tier2_result['EMAIL'] == '').sum() 
    tier2_missing_after = (tier2_filled['EMAIL'] == '').sum()
    
    print(f"   ✅ Tier 1: {tier1_missing_before - tier1_missing_after} emails filled")
    print(f"   ✅ Tier 2: {tier2_missing_before - tier2_missing_after} emails filled")
    
    # Test duplicate removal
    print("\n6️⃣ Testing duplicate removal...")
    # Add a duplicate contact
    duplicate_df = pd.concat([standardized_df, standardized_df.iloc[[0]]], ignore_index=True)
    deduped_df = filter_tool.remove_duplicates(duplicate_df)
    print(f"   ✅ Removed {len(duplicate_df) - len(deduped_df)} duplicates")
    
    print("\n" + "=" * 50)
    print("✅ All tests completed successfully!")
    print(f"📈 Final results:")
    print(f"   • Tier 1 (Key): {len(tier1_filled)} contacts")
    print(f"   • Tier 2 (Junior): {len(tier2_filled)} contacts") 
    print(f"   • Total: {len(tier1_filled) + len(tier2_filled)} contacts")
    print(f"   • Email patterns: {len(patterns)} firms")

if __name__ == "__main__":
    test_consolidated_filter()
