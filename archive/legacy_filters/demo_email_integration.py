#!/usr/bin/env python3
"""
Demo script showing integration of email finding logic with tiered filtering
This demonstrates the full capability without requiring the actual large input file
"""

import pandas as pd
import numpy as np
from email_finder import EmailFinder
import tempfile
import os

def create_sample_dataset():
    """Create a realistic sample dataset for demonstration"""
    
    # Sample firm names
    firms = [
        "Blackstone Group", "Apollo Global Management", "KKR & Co",
        "Goldman Sachs Asset Management", "Morgan Stanley Investment Management",
        "JP Morgan Asset Management", "Carlyle Group", "TPG Capital",
        "Bain Capital", "Silver Lake Partners"
    ]
    
    # Sample job titles for Tier 1 (key contacts)
    tier1_titles = [
        "Chief Investment Officer", "Managing Director", "Investment Director",
        "Head of Investments", "Head of Research", "Senior Portfolio Manager",
        "Investment Committee Member", "Investment Partner", "President",
        "Vice President of Investments"
    ]
    
    # Sample job titles for Tier 2 (junior contacts)
    tier2_titles = [
        "Investment Analyst", "Research Analyst", "Portfolio Analyst",
        "Associate", "Investment Associate", "Research Associate",
        "Junior Portfolio Manager", "Investment Coordinator"
    ]
    
    # Create sample data
    np.random.seed(42)  # For reproducible results
    contacts = []
    
    for i in range(100):
        firm = np.random.choice(firms)
        
        # Mix of tier 1 and tier 2 contacts
        if i < 40:  # 40% tier 1 contacts
            job_title = np.random.choice(tier1_titles)
        else:  # 60% tier 2 contacts
            job_title = np.random.choice(tier2_titles)
        
        # Generate realistic names
        first_names = ["John", "Jane", "Michael", "Sarah", "David", "Lisa", "Robert", "Emily", "James", "Mary"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
        
        first_name = np.random.choice(first_names)
        last_name = np.random.choice(last_names)
        full_name = f"{first_name} {last_name}"
        
        # Generate email addresses with various patterns
        domain_base = firm.lower().replace(" ", "").replace("&", "").replace(".", "")[:15]
        
        # Different email formats
        email_formats = [
            f"{first_name.lower()}.{last_name.lower()}@{domain_base}.com",
            f"{first_name[0].lower()}{last_name.lower()}@{domain_base}.com",
            f"{first_name.lower()}{last_name[0].lower()}@{domain_base}.com",
            f"{last_name.lower()}@{domain_base}.com"
        ]
        
        email = np.random.choice(email_formats)
        
        # Sometimes add personal emails or issues
        if np.random.random() < 0.1:  # 10% personal emails
            email = f"{first_name.lower()}.{last_name.lower()}@gmail.com"
        elif np.random.random() < 0.05:  # 5% invalid emails
            email = "invalid-email-format"
        
        # Create description with potential additional emails
        description = f"{full_name} is a {job_title} at {firm}."
        if np.random.random() < 0.3:  # 30% have additional contact info
            alt_email = f"{first_name.lower()}{np.random.randint(1,99)}@{domain_base}.com"
            description += f" Alternative contact: {alt_email}"
        
        contact = {
            'CONTACT_ID': i + 1,
            'NAME': full_name,
            'INVESTOR': firm,
            'JOB TITLE': job_title,
            'ROLE': 'Investment Team',
            'EMAIL': email,
            'DESCRIPTION': description,
            'LOCATION': np.random.choice(['New York', 'London', 'San Francisco', 'Boston', 'Chicago'])
        }
        
        contacts.append(contact)
    
    return pd.DataFrame(contacts)

def demo_email_analysis_with_tiered_filtering():
    """Demonstrate email analysis integrated with tiered filtering approach"""
    
    print("🚀 DEMO: Email Intelligence with Tiered Filtering")
    print("=" * 70)
    
    # Create sample dataset
    print("📊 Creating sample dataset...")
    df = create_sample_dataset()
    print(f"Generated {len(df)} sample contacts from {df['INVESTOR'].nunique()} firms")
    
    # Initialize email finder
    email_finder = EmailFinder()
    
    # Step 1: Analyze original email quality
    print(f"\n📧 STEP 1: Email Quality Analysis")
    print("-" * 40)
    original_analysis = email_finder.analyze_email_column(df, 'EMAIL')
    print(f"Original email quality score: {original_analysis['quality_score']}/100")
    print(f"Valid emails: {original_analysis['valid_count']}/{original_analysis['total_rows']}")
    print(f"Business emails: {original_analysis['business_count']}")
    print(f"Personal emails: {original_analysis['personal_count']}")
    
    # Step 2: Find additional emails in text fields
    print(f"\n🔍 STEP 2: Finding Additional Emails in Text")
    print("-" * 40)
    df_enhanced = email_finder.find_emails_in_dataframe(df, ['DESCRIPTION'])
    additional_emails_found = df_enhanced['found_email_count'].sum()
    contacts_with_additional = len(df_enhanced[df_enhanced['found_email_count'] > 0])
    print(f"Found {additional_emails_found} additional emails in {contacts_with_additional} contacts")
    
    # Show examples
    examples = df_enhanced[df_enhanced['found_email_count'] > 0].head(3)
    for _, row in examples.iterrows():
        print(f"  {row['NAME']}: {row['found_emails']}")
    
    # Step 3: Apply tier-based filtering simulation
    print(f"\n🎯 STEP 3: Simulating Tier-Based Filtering")
    print("-" * 40)
    
    # Simulate Tier 1 filter (senior roles)
    tier1_keywords = ['chief', 'cio', 'managing director', 'head of', 'president', 'vice president']
    tier1_mask = df['JOB TITLE'].str.lower().str.contains('|'.join(tier1_keywords))
    tier1_df = df[tier1_mask].copy()
    
    # Simulate Tier 2 filter (junior roles)
    tier2_keywords = ['analyst', 'associate', 'coordinator', 'junior']
    tier2_mask = df['JOB TITLE'].str.lower().str.contains('|'.join(tier2_keywords))
    tier2_df = df[tier2_mask].copy()
    
    print(f"Tier 1 (Senior): {len(tier1_df)} contacts")
    print(f"Tier 2 (Junior): {len(tier2_df)} contacts")
    
    # Step 4: Apply email-based filtering
    print(f"\n🏢 STEP 4: Email Domain Filtering")
    print("-" * 40)
    
    # Filter out personal emails for business focus
    tier1_business = email_finder.filter_by_email_domain(
        tier1_df, ['gmail.com', 'yahoo.com', 'hotmail.com'], mode='exclude'
    )
    tier2_business = email_finder.filter_by_email_domain(
        tier2_df, ['gmail.com', 'yahoo.com', 'hotmail.com'], mode='exclude'
    )
    
    print(f"After excluding personal domains:")
    print(f"  Tier 1: {len(tier1_df)} → {len(tier1_business)} contacts")
    print(f"  Tier 2: {len(tier2_df)} → {len(tier2_business)} contacts")
    
    # Step 5: Clean and analyze final results
    print(f"\n🧹 STEP 5: Email Cleaning and Final Analysis")
    print("-" * 40)
    
    # Clean email columns
    tier1_clean = email_finder.clean_email_column(tier1_business)
    tier2_clean = email_finder.clean_email_column(tier2_business)
    
    # Final analysis
    tier1_final_analysis = email_finder.analyze_email_column(tier1_clean, 'EMAIL')
    tier2_final_analysis = email_finder.analyze_email_column(tier2_clean, 'EMAIL')
    
    print(f"Final Results:")
    print(f"  Tier 1 Quality Score: {tier1_final_analysis['quality_score']}/100")
    print(f"  Tier 2 Quality Score: {tier2_final_analysis['quality_score']}/100")
    print(f"  Total Valid Business Emails: {tier1_final_analysis['valid_count'] + tier2_final_analysis['valid_count']}")
    
    # Step 6: Generate comprehensive reports
    print(f"\n📋 STEP 6: Comprehensive Email Reports")
    print("-" * 40)
    
    print("\n📊 TIER 1 EMAIL REPORT:")
    tier1_report = email_finder.generate_email_report(tier1_clean)
    print(tier1_report)
    
    print("\n📊 TIER 2 EMAIL REPORT:")
    tier2_report = email_finder.generate_email_report(tier2_clean)
    print(tier2_report)
    
    # Step 7: Save demo results
    print(f"\n💾 STEP 7: Saving Demo Results")
    print("-" * 40)
    
    # Create temporary file to demonstrate Excel output
    with tempfile.NamedTemporaryFile(mode='w', suffix='_demo_results.xlsx', delete=False) as tmp_file:
        output_path = tmp_file.name
    
    try:
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            # Save original data
            df.to_excel(writer, sheet_name="Original_Contacts", index=False)
            
            # Save tiered results
            tier1_clean.to_excel(writer, sheet_name="Tier1_Senior_Contacts", index=False)
            tier2_clean.to_excel(writer, sheet_name="Tier2_Junior_Contacts", index=False)
            
            # Save email analysis summary
            summary_data = {
                'Metric': [
                    'Original Contacts',
                    'Original Valid Emails',
                    'Additional Emails Found',
                    'Tier 1 Final Contacts',
                    'Tier 1 Valid Emails',
                    'Tier 1 Quality Score',
                    'Tier 2 Final Contacts',
                    'Tier 2 Valid Emails', 
                    'Tier 2 Quality Score',
                    'Total Business Emails'
                ],
                'Value': [
                    len(df),
                    original_analysis['valid_count'],
                    additional_emails_found,
                    len(tier1_clean),
                    tier1_final_analysis['valid_count'],
                    f"{tier1_final_analysis['quality_score']}/100",
                    len(tier2_clean),
                    tier2_final_analysis['valid_count'],
                    f"{tier2_final_analysis['quality_score']}/100",
                    tier1_final_analysis['valid_count'] + tier2_final_analysis['valid_count']
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name="Email_Analysis_Summary", index=False)
        
        print(f"✅ Demo results saved to: {output_path}")
        print(f"📊 Excel file contains:")
        print(f"   • Original_Contacts sheet")
        print(f"   • Tier1_Senior_Contacts sheet") 
        print(f"   • Tier2_Junior_Contacts sheet")
        print(f"   • Email_Analysis_Summary sheet")
        
    except Exception as e:
        print(f"❌ Error saving demo results: {e}")
    finally:
        # Clean up temp file
        if os.path.exists(output_path):
            try:
                os.unlink(output_path)
                print(f"🗑️ Cleaned up temporary file")
            except:
                print(f"⚠️ Temporary file remains at: {output_path}")
    
    print(f"\n🎉 Demo completed successfully!")
    print(f"This demonstrates how email intelligence enhances the tiered filtering system:")
    print(f"   ✅ Email validation and quality scoring")
    print(f"   ✅ Additional email extraction from text")
    print(f"   ✅ Business email focus through domain filtering")
    print(f"   ✅ Comprehensive email analytics and reporting")
    print(f"   ✅ Integration with existing tiered contact filtering")

if __name__ == "__main__":
    demo_email_analysis_with_tiered_filtering()
