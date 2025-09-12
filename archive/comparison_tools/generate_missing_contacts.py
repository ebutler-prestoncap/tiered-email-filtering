#!/usr/bin/env python3
"""
Generate Missing Contacts Analysis
Compare unfiltered list vs enhanced tiered list
"""

import pandas as pd
import sys

def main():
    print("🔍 GENERATING MISSING CONTACTS ANALYSIS")
    print("=" * 60)
    
    try:
        # Load both datasets
        print("Loading unfiltered list...")
        unfiltered_df = pd.read_excel('output/Unfiltered_Combined_Institutional_List.xlsx', sheet_name='All_Contacts')
        
        print("Loading enhanced tiered list...")
        tiered_df = pd.read_excel('output/Tiered_Institutional_Contacts_20250911_123451.xlsx', sheet_name='All_Filtered_Contacts')
        
        print(f"📊 DATA OVERVIEW:")
        print(f"  Unfiltered list: {len(unfiltered_df):,} contacts")
        print(f"  Enhanced tiered list: {len(tiered_df):,} contacts")
        
        # Find missing contacts using Record_ID
        unfiltered_ids = set(unfiltered_df['Record_ID'].values)
        tiered_ids = set(tiered_df['Record_ID'].values)
        missing_ids = unfiltered_ids - tiered_ids
        
        missing_contacts_df = unfiltered_df[unfiltered_df['Record_ID'].isin(missing_ids)]
        
        print(f"  Missing from enhanced tiered: {len(missing_contacts_df):,} contacts")
        print(f"  Filtering efficiency: {len(tiered_df)/len(unfiltered_df)*100:.1f}%")
        
        # Source breakdown
        print(f"\n📂 SOURCE BREAKDOWN OF MISSING CONTACTS:")
        source_counts = missing_contacts_df['Source_File'].value_counts()
        for source, count in source_counts.items():
            print(f"  {source}: {count:,} contacts")
        
        # Institution breakdown
        missing_institutions = missing_contacts_df.groupby('Institution_Name').size().sort_values(ascending=False)
        print(f"\n🏢 TOP 20 MISSING INSTITUTIONS:")
        for i, (institution, count) in enumerate(missing_institutions.head(20).items(), 1):
            print(f"  {i:2d}. {institution}: {count} contacts")
        
        # Check for high-value contacts still missing
        high_value_missing = missing_contacts_df[missing_contacts_df['Job_Title'].str.contains(
            'cio|chief investment officer|managing director.*private|head.*private|executive director.*private', 
            case=False, na=False
        )]
        
        print(f"\n🔍 HIGH-VALUE CONTACTS STILL MISSING:")
        print(f"  High-value missing contacts: {len(high_value_missing)}")
        
        if len(high_value_missing) > 0:
            print(f"  Sample high-value missing contacts:")
            for idx, row in high_value_missing.head(10).iterrows():
                print(f"    • {row['Full_Name']} - {row['Job_Title']} at {row['Institution_Name']}")
        
        # Email coverage
        emails = missing_contacts_df['Email'].notna() & (missing_contacts_df['Email'] != '')
        print(f"\n📧 EMAIL COVERAGE OF MISSING CONTACTS:")
        print(f"  Contacts with emails: {emails.sum():,}/{len(missing_contacts_df):,} ({emails.sum()/len(missing_contacts_df)*100:.1f}%)")
        
        # Save files
        print(f"\n💾 SAVING FILES:")
        missing_contacts_df.to_csv('output/Enhanced_Missing_Contacts_Detailed.csv', index=False)
        print(f"  ✅ Detailed list: output/Enhanced_Missing_Contacts_Detailed.csv")
        
        # Create summary
        missing_summary = missing_institutions.reset_index()
        missing_summary.columns = ['Institution_Name', 'Contact_Count']
        missing_summary.to_csv('output/Enhanced_Missing_Contacts_Summary.csv', index=False)
        print(f"  ✅ Summary: output/Enhanced_Missing_Contacts_Summary.csv")
        
        print(f"\n🎯 ANALYSIS COMPLETE!")
        print(f"  Total missing contacts: {len(missing_contacts_df):,}")
        print(f"  Missing institutions: {len(missing_institutions):,}")
        print(f"  High-value missing: {len(high_value_missing):,}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
