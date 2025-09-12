#!/usr/bin/env python3
"""
Run Enhanced Tiered Filtering on Institutional Contact Lists
Processes institutional contact data with email intelligence and generates properly versioned outputs
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
from email_finder import EmailFinder, enhance_tiered_filtering_with_emails

def run_institutional_filtering():
    """Run enhanced tiered filtering on institutional contact lists with proper versioning"""
    
    print("🏛️ INSTITUTIONAL CONTACT FILTERING WITH EMAIL INTELLIGENCE")
    print("=" * 80)
    
    # Get current timestamp for versioning
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    version = "v2.1"  # Version 2.1 with email intelligence
    
    # Define input files and their corresponding output configurations
    datasets = [
        {
            'name': 'Institutional_Combined_Contact_List',
            'input_file': 'input/Institutional Combined_Contact_List.xlsx',
            'output_file': f'output/Enhanced_Institutional_Contacts_{version}_{timestamp}.xlsx',
            'description': 'Combined institutional contacts with tiered filtering and email intelligence'
        },
        {
            'name': 'Family_Office_Contacts', 
            'input_file': 'input/AI list- Family offices (002).xlsx',
            'output_file': f'output/Enhanced_Family_Office_Contacts_{version}_{timestamp}.xlsx',
            'description': 'Family office contacts with tiered filtering and email intelligence'
        }
    ]
    
    # Email domain filters for institutional focus
    institutional_domain_filters = {
        'exclude': [
            # Personal email domains
            'gmail.com', 'yahoo.com', 'hotmail.com', 'aol.com',
            'outlook.com', 'icloud.com', 'comcast.net', 'verizon.net',
            'live.com', 'msn.com', 'att.net', 'charter.net',
            # Temporary/suspicious domains
            '10minutemail.com', 'guerrillamail.com', 'mailinator.com',
            'tempmail.org', 'throwaway.email', 'temp-mail.org',
            'yopmail.com', 'mailnesia.com', 'maildrop.cc'
        ]
        # Note: No 'include' filter to allow all business domains
    }
    
    print(f"📅 Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔖 Version: {version}")
    print(f"📧 Email Domain Exclusions: {len(institutional_domain_filters['exclude'])} personal/suspicious domains")
    print()
    
    successful_runs = []
    failed_runs = []
    
    # Process each dataset
    for i, dataset in enumerate(datasets, 1):
        print(f"📊 PROCESSING DATASET {i}/{len(datasets)}: {dataset['name']}")
        print("=" * 60)
        print(f"📁 Input: {dataset['input_file']}")
        print(f"📁 Output: {dataset['output_file']}")
        print(f"📝 Description: {dataset['description']}")
        
        # Check if input file exists
        if not Path(dataset['input_file']).exists():
            print(f"❌ Error: Input file '{dataset['input_file']}' not found!")
            failed_runs.append(dataset['name'])
            print()
            continue
        
        try:
            # Get input file info
            input_df = pd.read_excel(dataset['input_file'], sheet_name=0)  # Read first sheet
            print(f"📈 Input Data: {len(input_df):,} contacts, {len(input_df.columns)} columns")
            
            # Run enhanced filtering with email intelligence
            print(f"\n🚀 Running enhanced tiered filtering...")
            enhance_tiered_filtering_with_emails(
                input_file=dataset['input_file'],
                output_file=dataset['output_file'],
                email_analysis=True,
                domain_filters=institutional_domain_filters
            )
            
            successful_runs.append(dataset['name'])
            print(f"\n✅ Successfully processed {dataset['name']}")
            
        except Exception as e:
            print(f"\n❌ Error processing {dataset['name']}: {e}")
            import traceback
            traceback.print_exc()
            failed_runs.append(dataset['name'])
        
        print("\n" + "="*60 + "\n")
    
    # Generate summary report
    print("📋 PROCESSING SUMMARY")
    print("=" * 40)
    print(f"✅ Successful: {len(successful_runs)}/{len(datasets)} datasets")
    print(f"❌ Failed: {len(failed_runs)}/{len(datasets)} datasets")
    
    if successful_runs:
        print(f"\n🎉 Successfully processed datasets:")
        for dataset_name in successful_runs:
            dataset = next(d for d in datasets if d['name'] == dataset_name)
            output_file = dataset['output_file'].replace('.xlsx', '_with_email_analysis.xlsx')
            print(f"   • {dataset_name}")
            print(f"     📁 Output: {output_file}")
    
    if failed_runs:
        print(f"\n⚠️ Failed to process datasets:")
        for dataset_name in failed_runs:
            print(f"   • {dataset_name}")
    
    # Generate master summary if we have successful runs
    if successful_runs:
        print(f"\n📊 Generating master summary...")
        generate_master_summary(datasets, successful_runs, version, timestamp)
    
    print(f"\n🏁 Institutional contact filtering completed!")
    print(f"📅 Processing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return len(successful_runs) > 0

def generate_master_summary(datasets, successful_runs, version, timestamp):
    """Generate a master summary Excel file with combined statistics"""
    
    try:
        master_summary_file = f"output/Master_Institutional_Filtering_Summary_{version}_{timestamp}.xlsx"
        
        summary_data = []
        
        # Collect data from each successful run
        for dataset_name in successful_runs:
            dataset = next(d for d in datasets if d['name'] == dataset_name)
            output_file = dataset['output_file'].replace('.xlsx', '_with_email_analysis.xlsx')
            
            if Path(output_file).exists():
                try:
                    # Read the email analysis summary
                    summary_df = pd.read_excel(output_file, sheet_name='Email_Analysis_Summary')
                    tier1_df = pd.read_excel(output_file, sheet_name='Tier1_Key_Contacts')
                    tier2_df = pd.read_excel(output_file, sheet_name='Tier2_Junior_Contacts')
                    
                    summary_data.append({
                        'Dataset': dataset_name,
                        'Tier_1_Contacts': len(tier1_df),
                        'Tier_2_Contacts': len(tier2_df),
                        'Total_Filtered_Contacts': len(tier1_df) + len(tier2_df),
                        'Output_File': output_file,
                        'Processing_Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
                except Exception as e:
                    print(f"⚠️ Warning: Could not read summary from {output_file}: {e}")
        
        if summary_data:
            # Create master summary Excel file
            with pd.ExcelWriter(master_summary_file, engine='xlsxwriter') as writer:
                # Master summary sheet
                master_df = pd.DataFrame(summary_data)
                master_df.to_excel(writer, sheet_name='Master_Summary', index=False)
                
                # Combined totals
                totals_data = {
                    'Metric': [
                        'Total Datasets Processed',
                        'Total Tier 1 (Key) Contacts',
                        'Total Tier 2 (Junior) Contacts',
                        'Grand Total Filtered Contacts',
                        'Processing Version',
                        'Processing Date'
                    ],
                    'Value': [
                        len(summary_data),
                        master_df['Tier_1_Contacts'].sum(),
                        master_df['Tier_2_Contacts'].sum(),
                        master_df['Total_Filtered_Contacts'].sum(),
                        version,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ]
                }
                
                totals_df = pd.DataFrame(totals_data)
                totals_df.to_excel(writer, sheet_name='Combined_Totals', index=False)
                
                # Processing details
                details_data = {
                    'Feature': [
                        'Two-Tier Contact Filtering',
                        'Email Validation & Quality Analysis',
                        'Email Domain Filtering',
                        'Business Email Focus',
                        'Duplicate Email Detection',
                        'Email Normalization & Cleaning',
                        'Comprehensive Email Reporting',
                        'Excel Output with Multiple Sheets',
                        'Automated Quality Scoring',
                        'Domain-Based Contact Prioritization'
                    ],
                    'Status': ['✅ Enabled'] * 10,
                    'Description': [
                        'Separates senior (Tier 1) from junior (Tier 2) professionals',
                        'Validates email formats and calculates quality scores',
                        'Excludes personal and suspicious email domains',
                        'Prioritizes business emails over personal accounts',
                        'Identifies and reports duplicate email addresses',
                        'Standardizes email formats and removes formatting issues',
                        'Generates detailed email analysis reports',
                        'Creates organized Excel output with multiple data sheets',
                        'Automated quality metrics for data assessment',
                        'Prioritizes contacts based on email domain type'
                    ]
                }
                
                details_df = pd.DataFrame(details_data)
                details_df.to_excel(writer, sheet_name='Processing_Features', index=False)
            
            print(f"📊 Master summary saved to: {master_summary_file}")
            
    except Exception as e:
        print(f"⚠️ Warning: Could not generate master summary: {e}")

if __name__ == "__main__":
    success = run_institutional_filtering()
    sys.exit(0 if success else 1)
