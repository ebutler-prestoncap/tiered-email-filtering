#!/usr/bin/env python3
"""
Enhanced Tiered Filtering with Email Intelligence
Combines the existing two-tier filtering system with advanced email finding and analysis capabilities
"""

import pandas as pd
import sys
from pathlib import Path
from email_finder import EmailFinder, enhance_tiered_filtering_with_emails

def main():
    """Main function to execute enhanced tiered filtering with email intelligence"""
    
    # Configuration
    input_file = "input/AI list- Family offices (002).xlsx"
    output_file = "output/Enhanced_Tiered_Filtered_Contacts_with_Emails.xlsx"
    
    # Email domain filters (customize as needed)
    domain_filters = {
        'exclude': [
            # Exclude common personal email domains to focus on business emails
            'gmail.com', 'yahoo.com', 'hotmail.com', 'aol.com',
            'outlook.com', 'icloud.com', 'comcast.net', 'verizon.net',
            # Exclude temporary/suspicious domains
            '10minutemail.com', 'guerrillamail.com', 'mailinator.com',
            'tempmail.org', 'throwaway.email'
        ]
        # Uncomment to include only specific domains:
        # 'include': ['company1.com', 'company2.com', 'targetfirm.com']
    }
    
    # Check if input file exists
    if not Path(input_file).exists():
        print(f"❌ Error: Input file '{input_file}' not found!")
        print("Please ensure the input file exists in the correct location.")
        sys.exit(1)
    
    print("🚀 Enhanced Tiered Contact Filter with Email Intelligence")
    print("=" * 70)
    print(f"📁 Input file: {input_file}")
    print(f"📁 Output file: {output_file}")
    print("\n🎯 Enhanced filtering features:")
    print("✅ Two-tier contact filtering (Key vs Junior professionals)")
    print("✅ Email validation and quality analysis")
    print("✅ Email domain filtering and analysis") 
    print("✅ Duplicate email detection")
    print("✅ Email normalization and cleaning")
    print("✅ Comprehensive email reporting")
    print("✅ Business vs personal email classification")
    
    if domain_filters.get('exclude'):
        print(f"\n🚫 Domain exclusions: {len(domain_filters['exclude'])} domains")
        print(f"   Sample exclusions: {', '.join(domain_filters['exclude'][:3])}...")
    
    if domain_filters.get('include'):
        print(f"\n✅ Domain inclusions: {len(domain_filters['include'])} domains")
        print(f"   Included domains: {', '.join(domain_filters['include'])}")
    
    print("\n" + "="*70)
    
    try:
        # Run enhanced filtering with email intelligence
        enhance_tiered_filtering_with_emails(
            input_file=input_file,
            output_file=output_file,
            email_analysis=True,
            domain_filters=domain_filters
        )
        
        print("\n" + "="*70)
        print("🎉 SUCCESS! Enhanced filtering completed successfully.")
        print(f"📊 Results saved to: {output_file.replace('.xlsx', '_with_email_analysis.xlsx')}")
        print("\n📈 Output includes:")
        print("   • Tier1_Key_Contacts sheet (senior professionals)")
        print("   • Tier2_Junior_Contacts sheet (junior professionals)")  
        print("   • Email_Analysis_Summary sheet (quality metrics)")
        print("   • Enhanced email validation and cleaning")
        print("   • Domain-based filtering applied")
        
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def demo_email_analysis():
    """Demonstrate email analysis capabilities on sample data"""
    
    print("\n🧪 DEMO: Email Analysis Capabilities")
    print("=" * 50)
    
    # Create sample data
    sample_data = {
        'NAME': ['John Smith', 'Jane Doe', 'Bob Johnson', 'Alice Wilson', 'Mike Brown'],
        'EMAIL': [
            'john.smith@company1.com',
            'jane.doe@gmail.com', 
            'invalid-email',
            'alice.wilson@company2.com',
            'mike.brown@company1.com'
        ],
        'DESCRIPTION': [
            'Contact John Smith at john.smith@company1.com for details',
            'Reach out via jane.doe@gmail.com or jane.alt@company.org',
            'No additional email info',
            'Alice can be reached at alice.wilson@company2.com',
            'Mike Brown - mike.brown@company1.com or m.brown@backup.com'
        ]
    }
    
    df = pd.DataFrame(sample_data)
    print(f"📊 Sample dataset: {len(df)} contacts")
    print(df.to_string(index=False))
    
    # Initialize email finder
    email_finder = EmailFinder()
    
    # Analyze existing email column
    print(f"\n📧 EMAIL COLUMN ANALYSIS:")
    analysis = email_finder.analyze_email_column(df, 'EMAIL')
    print(f"Valid emails: {analysis['valid_count']}/{analysis['total_rows']}")
    print(f"Quality score: {analysis['quality_score']}/100")
    print(f"Top domains: {analysis['top_domains']}")
    
    # Find emails in description text
    print(f"\n🔍 FINDING EMAILS IN TEXT:")
    df_enhanced = email_finder.find_emails_in_dataframe(df, ['DESCRIPTION'])
    for idx, row in df_enhanced.iterrows():
        if row['found_email_count'] > 0:
            print(f"  {row['NAME']}: Found {row['found_email_count']} emails - {row['found_emails']}")
    
    # Demonstrate domain filtering
    print(f"\n🏢 DOMAIN FILTERING DEMO:")
    business_only = email_finder.filter_by_email_domain(df, ['gmail.com'], mode='exclude')
    print(f"After excluding gmail.com: {len(business_only)}/{len(df)} contacts remain")
    
    # Generate report
    print(f"\n📋 FULL EMAIL REPORT:")
    report = email_finder.generate_email_report(df, 'EMAIL')
    print(report)

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--demo':
        demo_email_analysis()
    else:
        main()
