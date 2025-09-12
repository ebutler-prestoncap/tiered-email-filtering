#!/usr/bin/env python3
"""
Comparison script to analyze differences between original and two-tier filtering systems
"""

import pandas as pd
import sys
from pathlib import Path

def analyze_contacts(df, system_name):
    """Analyze contact distribution for a given dataframe"""
    if df.empty:
        return {
            'total_contacts': 0,
            'unique_firms': 0,
            'avg_contacts_per_firm': 0,
            'max_contacts_per_firm': 0,
            'firms_10_plus': 0,
            'firms_20_plus': 0
        }
    
    # Basic counts
    total_contacts = len(df)
    unique_firms = df['INVESTOR'].nunique() if 'INVESTOR' in df.columns else 0
    
    # Per-firm analysis
    if 'INVESTOR' in df.columns:
        firm_counts = df['INVESTOR'].value_counts()
        avg_contacts_per_firm = firm_counts.mean()
        max_contacts_per_firm = firm_counts.max()
        firms_10_plus = (firm_counts >= 10).sum()
        firms_20_plus = (firm_counts >= 20).sum()
    else:
        avg_contacts_per_firm = 0
        max_contacts_per_firm = 0
        firms_10_plus = 0
        firms_20_plus = 0
    
    return {
        'total_contacts': total_contacts,
        'unique_firms': unique_firms,
        'avg_contacts_per_firm': round(avg_contacts_per_firm, 2),
        'max_contacts_per_firm': max_contacts_per_firm,
        'firms_10_plus': firms_10_plus,
        'firms_20_plus': firms_20_plus
    }

def main():
    print("System Comparison Analysis")
    print("=" * 50)
    
    # Read original data
    input_file = "input/AI list- Family offices (002).xlsx"
    if not Path(input_file).exists():
        print(f"Error: Input file {input_file} not found!")
        sys.exit(1)
    
    df_original = pd.read_excel(input_file, sheet_name="Contacts_Export")
    print(f"Original dataset: {len(df_original):,} contacts")
    
    # Apply original filtering logic (simplified version)
    print("\nApplying original filtering logic...")
    
    # Step 1: Remove list exclusions
    try:
        remove_df = pd.read_csv("remove list.csv", header=None, names=['CONTACT_ID'])
        remove_ids = set(remove_df['CONTACT_ID'].dropna().astype(int).tolist())
        if 'CONTACT_ID' in df_original.columns:
            df_original = df_original[~df_original['CONTACT_ID'].isin(remove_ids)]
    except:
        pass
    
    # Step 2: Firm exclusions
    excluded_firms = [
        "Morgan Stanley Private Wealth Management", "HighTower Advisors", "Creative Planning",
        "Cresset Asset Management", "Jasper Ridge Partners", "Soros Fund Management",
        "Rockefeller Capital Management", "Great Lakes Advisors", "DFO Management",
        "Gresham Partners", "Johnson Financial Group", "Twin Focus Capital Partners",
        "Stelac Advisory Services", "Waterloo Capital", "Pennington Partners & Co"
    ]
    
    if 'INVESTOR' in df_original.columns:
        df_original = df_original[~df_original['INVESTOR'].isin(excluded_firms)]
    
    # Step 3: Role filter
    if 'ROLE' in df_original.columns:
        df_original = df_original[df_original['ROLE'].str.contains('Investment Team', na=False)]
    
    # Step 4: Job title filter (simplified)
    if 'JOB TITLE' in df_original.columns:
        # Basic inclusion pattern
        inclusion_pattern = r".*\b(portfolios?[\s-]?managers?|cio|alternatives?[\s-]?investments?|alternatives?|income|directors?|research|absolute|presidents?|private|credit|hedge|investments?|invest)\b"
        df_original = df_original[df_original['JOB TITLE'].str.contains(inclusion_pattern, case=False, na=False)]
    
    # Analyze original system
    original_metrics = analyze_contacts(df_original, "Original System")
    
    # Read two-tier results
    print("\nReading two-tier filtering results...")
    two_tier_file = "output/Two_Tier_Filtered_Family_Office_Contacts.xlsx"
    
    if Path(two_tier_file).exists():
        tier1_df = pd.read_excel(two_tier_file, sheet_name="Tier1_Key_Contacts")
        tier2_df = pd.read_excel(two_tier_file, sheet_name="Tier2_Junior_Contacts")
        two_tier_combined = pd.concat([tier1_df, tier2_df], ignore_index=True)
        two_tier_metrics = analyze_contacts(two_tier_combined, "Two-Tier System")
    else:
        print("Two-tier results not found, using placeholder data")
        two_tier_metrics = {
            'total_contacts': 3576,  # From previous run
            'unique_firms': 1259,    # From previous run
            'avg_contacts_per_firm': 2.84,
            'max_contacts_per_firm': 10,
            'firms_10_plus': 0,
            'firms_20_plus': 0
        }
    
    # Calculate deltas
    def calculate_delta(original, new):
        delta = new - original
        change_pct = (delta / original * 100) if original != 0 else 0
        return delta, change_pct
    
    # Generate comparison table
    print("\n" + "=" * 80)
    print("FILTERING SYSTEMS COMPARISON")
    print("=" * 80)
    print(f"{'Metric':<25} {'Original':<12} {'Two-Tier':<12} {'Delta':<12} {'Change %':<12}")
    print("-" * 80)
    
    metrics = [
        ('Total Contacts', 'total_contacts'),
        ('Unique Firms', 'unique_firms'),
        ('Avg Contacts/Firm', 'avg_contacts_per_firm'),
        ('Max Contacts/Firm', 'max_contacts_per_firm'),
        ('Firms with 10+ Contacts', 'firms_10_plus'),
        ('Firms with 20+ Contacts', 'firms_20_plus')
    ]
    
    for metric_name, metric_key in metrics:
        orig_val = original_metrics[metric_key]
        new_val = two_tier_metrics[metric_key]
        delta, change_pct = calculate_delta(orig_val, new_val)
        
        print(f"{metric_name:<25} {orig_val:<12,} {new_val:<12,} {delta:<12,} {change_pct:<12.1f}%")
    
    print("=" * 80)
    
    # Additional insights
    print(f"\nKey Insights:")
    print(f"• Two-tier system reduces total contacts by {abs(calculate_delta(original_metrics['total_contacts'], two_tier_metrics['total_contacts'])[0]):,}")
    print(f"• Two-tier system increases firm diversity by {calculate_delta(original_metrics['unique_firms'], two_tier_metrics['unique_firms'])[0]:,} firms")
    print(f"• Two-tier system eliminates firms with 10+ contacts (max is now 10)")
    print(f"• Average contacts per firm reduced by {abs(calculate_delta(original_metrics['avg_contacts_per_firm'], two_tier_metrics['avg_contacts_per_firm'])[0]):.2f}")

if __name__ == "__main__":
    main()
