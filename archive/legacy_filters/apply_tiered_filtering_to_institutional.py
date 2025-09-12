#!/usr/bin/env python3
"""
Apply Tiered Filtering to Combined Institutional List

This script takes the combined Institutional-Tiered-List-v1.xlsx and applies 
the same tiered filtering logic used for family office contacts, adapted for 
institutional data structure.
"""

import pandas as pd
import re
import sys
from pathlib import Path
from typing import Tuple, Dict, Any
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InstitutionalTieredFilter:
    """Apply tiered filtering to institutional contact data."""
    
    def __init__(self, input_file: str = "output/Institutional-Tiered-List-v1.xlsx", 
                 output_folder: str = "output"):
        self.input_file = Path(input_file)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(exist_ok=True)
    
    def createTier1Filter(self) -> Dict[str, Any]:
        """Create Tier 1 filter configuration for senior institutional contacts."""
        return {
            'name': 'Tier 1 - Senior Institutional Contacts',
            'description': 'Senior investment professionals: CIO, deputy CIO, heads of investments/private markets, managing directors, etc.',
            'job_title_pattern': r".*\b(cio|c\.i\.o\.|c\.i\.o|chief\s+investment\s+officer|deputy\s+chief\s+investment\s+officer|deputy\s+cio|head\s+of\s+investments?|head\s+of\s+research|head\s+of\s+private\s+markets?|head\s+of\s+private\s+equity|investment\s+committee|investment\s+partner|managing\s+director|executive\s+director|senior\s+portfolio\s+manager|investment\s+director|portfolio\s+manager|investment\s+manager|fund\s+manager|private\s+markets?|private\s+equity|private\s+credit|private\s+debt|hedge\s+fund|hedge|alternatives?|fixed\s+income|absolute\s+return)\b",
            'exclusion_pattern': r".*\b(operations?|hr|human\s+resources?|investor\s+relations?|client\s+relations?|marketing|sales|compliance|technology|administrator|assistant|secretary|receptionist|intern|trainee|junior)\b",
            'required_role_terms': [],  # Institutional data may not have role filtering
            'priority_keywords': ['cio', 'chief investment officer', 'deputy cio', 'head of investments', 'head of private markets', 'private markets', 'private equity', 'hedge fund', 'managing director', 'executive director', 'investment director', 'portfolio manager']
        }
    
    def createTier2Filter(self) -> Dict[str, Any]:
        """Create Tier 2 filter configuration for mid-level institutional contacts."""
        return {
            'name': 'Tier 2 - Mid-Level Institutional Contacts', 
            'description': 'Mid-level investment professionals: directors, VPs, analysts, associates, specialists, etc.',
            'job_title_pattern': r".*\b(director|vice\s+president|vp|senior\s+vice\s+president|associate\s+director|investment\s+analyst|research\s+analyst|portfolio\s+analyst|senior\s+analyst|investment\s+advisor|wealth\s+advisor|trust\s+officer|principal|associate|coordinator|specialist|advisor|representative|assistant\s+portfolio\s+manager|research|portfolio|investment|analyst)\b",
            'exclusion_pattern': r".*\b(operations?|hr|human\s+resources?|investor\s+relations?|client\s+relations?|marketing|sales|compliance|technology|administrator|assistant|secretary|receptionist|intern|trainee|junior|cio|c\.i\.o\.|c\.i\.o|chief\s+investment\s+officer|deputy\s+chief\s+investment\s+officer|head\s+of\s+investments?|head\s+of\s+research|head\s+of\s+private\s+markets?|investment\s+committee|investment\s+partner|managing\s+director|executive\s+director|senior\s+portfolio\s+manager|investment\s+director)\b",
            'required_role_terms': [],  # Institutional data may not have role filtering
            'priority_keywords': ['director', 'vice president', 'investment analyst', 'research analyst', 'associate director', 'principal', 'associate', 'portfolio', 'investment']
        }
    
    def calculatePriority(self, row: pd.Series, tier_config: Dict[str, Any]) -> int:
        """Calculate priority score for contact ranking."""
        job_title = str(row.get('Job_Title', '')).lower()
        priority_score = 0
        
        # Tier 1: Highest priority roles (score 150+) - C-level and senior investment roles
        if 'cio' in job_title or 'chief investment officer' in job_title:
            priority_score += 150
        if 'deputy chief investment officer' in job_title or 'deputy cio' in job_title:
            priority_score += 140
        if 'head of investments' in job_title or 'head of research' in job_title:
            priority_score += 130
        if 'head of private markets' in job_title or 'head of private equity' in job_title:
            priority_score += 125
        if 'investment committee' in job_title and ('chair' in job_title or 'member' in job_title):
            priority_score += 120
        if 'investment partner' in job_title:
            priority_score += 115
        
        # Tier 2: Senior management with investment focus (score 100-110)
        if 'managing director' in job_title and ('private' in job_title or 'investment' in job_title or 'portfolio' in job_title):
            priority_score += 110
        if 'executive director' in job_title and ('private' in job_title or 'investment' in job_title):
            priority_score += 105
        if 'senior portfolio manager' in job_title or 'investment director' in job_title:
            priority_score += 100
        
        # Tier 3: High priority investment focus areas (score 70-90)
        if 'private markets' in job_title:
            priority_score += 90
        if 'private equity' in job_title or 'private credit' in job_title or 'private debt' in job_title:
            priority_score += 85
        if 'hedge fund' in job_title or 'hedge' in job_title:
            priority_score += 80
        if 'alternatives' in job_title or 'absolute return' in job_title:
            priority_score += 75
        if 'fixed income' in job_title:
            priority_score += 70
        
        # Tier 4: Medium priority roles (score 40-65)
        if 'managing director' in job_title and priority_score == 0:  # MD without investment keywords
            priority_score += 65
        if 'portfolio manager' in job_title:
            priority_score += 60
        if 'investment manager' in job_title or 'fund manager' in job_title:
            priority_score += 55
        if 'investment analyst' in job_title:
            priority_score += 50
        if 'associate director' in job_title and 'investment' in job_title:
            priority_score += 45
        if 'credit' in job_title or 'income' in job_title:
            priority_score += 40
        
        # Tier 5: Junior but relevant roles (score 20-35)
        if 'associate' in job_title and ('private' in job_title or 'investment' in job_title):
            priority_score += 35
        if 'analyst' in job_title and ('private' in job_title or 'investment' in job_title):
            priority_score += 30
        if 'director' in job_title and 'investment' in job_title:
            priority_score += 25
        
        # Base score for other keywords (only if no score yet)
        if priority_score == 0:
            for keyword in tier_config['priority_keywords']:
                if keyword.lower() in job_title:
                    priority_score += 10
                    break  # Only add base score once
        
        return priority_score
    
    def applyTierFilter(self, df: pd.DataFrame, tier_config: Dict[str, Any], 
                       max_contacts_per_firm: int = 6) -> pd.DataFrame:
        """Apply tier-specific filtering to dataframe with firm-based contact limits."""
        filtered_df = df.copy()
        
        # Apply job title regex filter using Job_Title column
        if 'Job_Title' in filtered_df.columns:
            job_title_regex = re.compile(tier_config['job_title_pattern'], re.IGNORECASE)
            exclusion_regex = re.compile(tier_config['exclusion_pattern'], re.IGNORECASE)
            
            def matchesTierCriteria(row):
                job_title = str(row.get('Job_Title', '')).lower()
                
                # Check job title matches (must contain at least one positive term)
                if not job_title_regex.search(job_title):
                    return False
                    
                # Check exclusions (must NOT contain any exclusion terms)  
                if exclusion_regex.search(job_title):
                    return False
                    
                return True
            
            tier_filter = filtered_df.apply(matchesTierCriteria, axis=1)
            filtered_df = filtered_df[tier_filter]
        
        # Apply firm-based contact limits using Institution_Name
        if 'Institution_Name' in filtered_df.columns and len(filtered_df) > 0:
            # Add priority score and sort
            filtered_df = filtered_df.copy()
            filtered_df['Priority_Score'] = filtered_df.apply(
                lambda row: self.calculatePriority(row, tier_config), axis=1
            )
            
            # Sort by priority score (descending)
            filtered_df = filtered_df.sort_values('Priority_Score', ascending=False)
            
            # Apply firm-based limits
            firm_limited_df = []
            for firm_name in filtered_df['Institution_Name'].unique():
                if pd.isna(firm_name) or firm_name == '':
                    continue
                    
                firm_contacts = filtered_df[filtered_df['Institution_Name'] == firm_name]
                # Take top N contacts per firm based on priority
                top_contacts = firm_contacts.head(max_contacts_per_firm)
                firm_limited_df.append(top_contacts)
            
            if firm_limited_df:
                filtered_df = pd.concat(firm_limited_df, ignore_index=True)
            else:
                filtered_df = pd.DataFrame()
        
        return filtered_df
    
    def applyBucketOverflowFilter(self, df: pd.DataFrame, tier1_config: Dict[str, Any], 
                                 tier2_config: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Apply bucket overflow filtering approach."""
        
        # Step 1: Apply Tier 1 filter (max 10 per firm)
        tier1_df = self.applyTierFilter(df, tier1_config, max_contacts_per_firm=10)
        
        # Step 2: Remove Tier 1 contacts from original dataset
        if 'Record_ID' in df.columns and 'Record_ID' in tier1_df.columns:
            tier1_ids = set(tier1_df['Record_ID'].values)
            remaining_df = df[~df['Record_ID'].isin(tier1_ids)]
        else:
            # Fallback: use index-based removal
            remaining_df = df.drop(tier1_df.index, errors='ignore')
        
        # Step 3: Apply Tier 2 filter to remaining contacts (max 6 per firm)
        tier2_df = self.applyTierFilter(remaining_df, tier2_config, max_contacts_per_firm=6)
        
        return tier1_df, tier2_df
    
    def loadInstitutionalData(self) -> pd.DataFrame:
        """Load the combined institutional data."""
        logger.info(f"Loading institutional data from {self.input_file}")
        
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")
        
        df = pd.read_excel(self.input_file, sheet_name='Combined_Contacts')
        logger.info(f"Loaded {len(df)} institutional contacts")
        
        return df
    
    def preFilterData(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply pre-filtering steps adapted for institutional data."""
        logger.info("Applying pre-filtering steps...")
        
        original_count = len(df)
        filtered_df = df.copy()
        
        # Step 1: Remove contacts without job titles (essential for tiered filtering)
        if 'Job_Title' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['Job_Title'].notna()) & 
                (filtered_df['Job_Title'] != '')
            ]
            logger.info(f"Contacts with job titles: {len(filtered_df)} (removed {original_count - len(filtered_df)})")
        
        # Step 2: Remove contacts without institution names
        if 'Institution_Name' in filtered_df.columns:
            before_institution_filter = len(filtered_df)
            filtered_df = filtered_df[
                (filtered_df['Institution_Name'].notna()) & 
                (filtered_df['Institution_Name'] != '')
            ]
            logger.info(f"Contacts with institution names: {len(filtered_df)} (removed {before_institution_filter - len(filtered_df)})")
        
        # Step 3: Remove obvious non-investment roles
        if 'Job_Title' in filtered_df.columns:
            before_role_filter = len(filtered_df)
            non_investment_pattern = r".*\b(secretary|receptionist|accounting|finance\s+(?!investment)|legal|counsel|administrative|admin|office\s+manager|facilities|maintenance|security|guard|janitor|cleaner)\b"
            non_investment_regex = re.compile(non_investment_pattern, re.IGNORECASE)
            
            role_filter = ~filtered_df['Job_Title'].apply(
                lambda x: bool(non_investment_regex.search(str(x))) if pd.notna(x) else False
            )
            filtered_df = filtered_df[role_filter]
            logger.info(f"After removing non-investment roles: {len(filtered_df)} (removed {before_role_filter - len(filtered_df)})")
        
        logger.info(f"Pre-filtering complete: {len(filtered_df)} contacts remaining from {original_count} original")
        return filtered_df
    
    def removeDuplicatesBetweenSources(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate contacts that appear across multiple sources."""
        logger.info("Removing duplicates between sources...")
        
        original_count = len(df)
        
        # Create a normalized email field for comparison
        df_copy = df.copy()
        df_copy['Email_Normalized'] = df_copy['Email'].str.lower().str.strip()
        
        # Remove duplicates based on email and name combination
        # Priority: Keep the record with the most complete information
        df_copy['Completeness_Score'] = (
            (df_copy['Email'] != '').astype(int) * 3 +
            (df_copy['Phone'] != '').astype(int) * 2 +
            (df_copy['LinkedIn'] != '').astype(int) * 1 +
            (df_copy['Job_Title'] != '').astype(int) * 2
        )
        
        # Sort by completeness score (descending) and then by source priority
        source_priority = {
            'HF Seeding Firms USA': 1,
            'HFoF investors': 2, 
            'ConsultantsICs-2025-08-25T18_42_08': 3,
            'MusicRoyaltiesLPs-2025-08-25T17_33_11': 4
        }
        
        df_copy['Source_Priority'] = df_copy['Source_File'].map(source_priority).fillna(5)
        df_copy = df_copy.sort_values(['Completeness_Score', 'Source_Priority'], ascending=[False, True])
        
        # Remove duplicates based on email and full name
        duplicates_removed = df_copy.drop_duplicates(
            subset=['Email_Normalized', 'Full_Name'], 
            keep='first'
        )
        
        # Also remove duplicates based on email only (if no name match)
        email_only_duplicates = duplicates_removed.drop_duplicates(
            subset=['Email_Normalized'], 
            keep='first'
        )
        
        # Clean up temporary columns
        email_only_duplicates = email_only_duplicates.drop(['Email_Normalized', 'Completeness_Score', 'Source_Priority'], axis=1)
        
        duplicates_removed_count = original_count - len(email_only_duplicates)
        logger.info(f"Removed {duplicates_removed_count} duplicate contacts between sources")
        logger.info(f"Contacts after duplicate removal: {len(email_only_duplicates)}")
        
        return email_only_duplicates
    
    def runTieredFiltering(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Run the complete tiered filtering process."""
        logger.info("Starting institutional tiered filtering process...")
        
        # Load data
        df = self.loadInstitutionalData()
        
        # Pre-filter data
        df_filtered = self.preFilterData(df)
        
        if len(df_filtered) == 0:
            logger.error("No contacts remaining after pre-filtering!")
            return pd.DataFrame(), pd.DataFrame()
        
        # Remove duplicates between sources
        df_deduplicated = self.removeDuplicatesBetweenSources(df_filtered)
        
        if len(df_deduplicated) == 0:
            logger.error("No contacts remaining after duplicate removal!")
            return pd.DataFrame(), pd.DataFrame()
        
        # Create tier configurations
        tier1_config = self.createTier1Filter()
        tier2_config = self.createTier2Filter()
        
        # Apply bucket overflow filtering
        logger.info(f"Applying {tier1_config['name']} filter (max 10 per institution)...")
        logger.info(f"Applying {tier2_config['name']} filter (max 6 per institution)...")
        
        tier1_df, tier2_df = self.applyBucketOverflowFilter(df_deduplicated, tier1_config, tier2_config)
        
        logger.info(f"Tier 1 senior contacts: {len(tier1_df)}")
        logger.info(f"Tier 2 junior contacts: {len(tier2_df)}")
        
        # Ensure no duplicates between tiers
        if 'Record_ID' in tier1_df.columns and 'Record_ID' in tier2_df.columns:
            tier1_ids = set(tier1_df['Record_ID'].values)
            tier2_ids = set(tier2_df['Record_ID'].values)
            duplicates = tier1_ids.intersection(tier2_ids)
            if duplicates:
                logger.warning(f"Found {len(duplicates)} duplicates between tiers, removing from Tier 2")
                tier2_df = tier2_df[~tier2_df['Record_ID'].isin(duplicates)]
        
        return tier1_df, tier2_df
    
    def saveResults(self, tier1_df: pd.DataFrame, tier2_df: pd.DataFrame) -> str:
        """Save the tiered filtering results."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.output_folder / f"Tiered_Institutional_Contacts_{timestamp}.xlsx"
        
        logger.info(f"Saving results to {output_file}")
        
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            # Tier 1 contacts
            tier1_df.to_excel(writer, sheet_name='Tier1_Senior_Contacts', index=False)
            
            # Tier 2 contacts
            tier2_df.to_excel(writer, sheet_name='Tier2_Junior_Contacts', index=False)
            
            # Combined results
            combined_df = pd.concat([tier1_df, tier2_df], ignore_index=True)
            combined_df.to_excel(writer, sheet_name='All_Filtered_Contacts', index=False)
            
            # Summary statistics
            summary_data = {
                'Metric': [
                    'Original Combined Contacts',
                    'After Pre-filtering',
                    'After Duplicate Removal',
                    'Tier 1 Senior Contacts', 
                    'Tier 2 Junior Contacts',
                    'Total Filtered Contacts',
                    'Filtering Efficiency (%)',
                    'Unique Institutions (Tier 1)',
                    'Unique Institutions (Tier 2)',
                    'Avg Contacts per Institution (Tier 1)',
                    'Avg Contacts per Institution (Tier 2)'
                ],
                'Value': [
                    len(pd.read_excel(self.input_file, sheet_name='Combined_Contacts')),
                    "See processing logs",  # Pre-filtering count
                    "See processing logs",  # Duplicate removal count
                    len(tier1_df),
                    len(tier2_df), 
                    len(combined_df),
                    f"{len(combined_df) / len(pd.read_excel(self.input_file, sheet_name='Combined_Contacts')) * 100:.1f}%",
                    tier1_df['Institution_Name'].nunique() if not tier1_df.empty else 0,
                    tier2_df['Institution_Name'].nunique() if not tier2_df.empty else 0,
                    f"{len(tier1_df) / tier1_df['Institution_Name'].nunique():.1f}" if not tier1_df.empty else "0.0",
                    f"{len(tier2_df) / tier2_df['Institution_Name'].nunique():.1f}" if not tier2_df.empty else "0.0"
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Filtering_Summary', index=False)
        
        return str(output_file)
    
    def generateReport(self, tier1_df: pd.DataFrame, tier2_df: pd.DataFrame) -> None:
        """Generate a summary report."""
        original_df = pd.read_excel(self.input_file, sheet_name='Combined_Contacts')
        
        print(f"\n{'='*60}")
        print(f"🎯 INSTITUTIONAL TIERED FILTERING RESULTS")
        print(f"{'='*60}")
        print(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n📊 FILTERING SUMMARY:")
        print(f"  📥 Original Combined Contacts: {len(original_df):,}")
        print(f"  🥇 Tier 1 Senior Contacts: {len(tier1_df):,}")
        print(f"  🥈 Tier 2 Junior Contacts: {len(tier2_df):,}")
        print(f"  📊 Total Filtered Contacts: {len(tier1_df) + len(tier2_df):,}")
        print(f"  📈 Filtering Efficiency: {(len(tier1_df) + len(tier2_df)) / len(original_df) * 100:.1f}%")
        
        print(f"\n🏢 INSTITUTION BREAKDOWN:")
        if not tier1_df.empty:
            print(f"  🥇 Tier 1 Institutions: {tier1_df['Institution_Name'].nunique():,}")
            print(f"     Avg contacts per institution: {len(tier1_df) / tier1_df['Institution_Name'].nunique():.1f}")
        
        if not tier2_df.empty:
            print(f"  🥈 Tier 2 Institutions: {tier2_df['Institution_Name'].nunique():,}")
            print(f"     Avg contacts per institution: {len(tier2_df) / tier2_df['Institution_Name'].nunique():.1f}")
        
        # Top institutions by contact count
        if not tier1_df.empty:
            print(f"\n🏆 TOP TIER 1 INSTITUTIONS:")
            top_tier1_institutions = tier1_df['Institution_Name'].value_counts().head(10)
            for institution, count in top_tier1_institutions.items():
                print(f"  🏢 {institution}: {count} contacts")

def main():
    """Main function to run institutional tiered filtering."""
    filter_processor = InstitutionalTieredFilter()
    
    try:
        # Run tiered filtering
        tier1_df, tier2_df = filter_processor.runTieredFiltering()
        
        if tier1_df.empty and tier2_df.empty:
            logger.error("❌ No contacts passed filtering criteria!")
            return
        
        # Save results
        output_file = filter_processor.saveResults(tier1_df, tier2_df)
        
        # Generate report
        filter_processor.generateReport(tier1_df, tier2_df)
        
        print(f"\n🎉 SUCCESS! Tiered institutional filtering complete!")
        print(f"📁 Results saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"❌ Error during processing: {e}")
        raise

if __name__ == "__main__":
    main()
