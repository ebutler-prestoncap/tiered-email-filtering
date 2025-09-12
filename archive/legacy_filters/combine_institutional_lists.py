#!/usr/bin/env python3
"""
Combine all institutional lists from the input folder into a unified 
'Institutional-Tiered-List-v1.xlsx' file.

This script processes:
- HF Seeding Firms USA.xlsx (Contacts_Export sheet)
- HFoF investors.xlsx (Contacts_Export sheet) 
- ConsultantsICs-2025-08-25T18_42_08.xlsx (Institution Contacts sheet)
- MusicRoyaltiesLPs-2025-08-25T17_33_11.xlsx (Contacts sheet)
"""

import pandas as pd
from pathlib import Path
import os
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InstitutionalListCombiner:
    """Class to combine institutional contact lists into a standardized format."""
    
    def __init__(self, input_folder: str = "input", output_folder: str = "output"):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(exist_ok=True)
        
        # Standard column mapping
        self.standard_columns = [
            'Source_File',
            'Source_Sheet', 
            'Firm_ID',
            'Contact_ID',
            'Institution_Name',
            'Firm_Name',
            'First_Name',
            'Last_Name',
            'Full_Name',
            'Job_Title',
            'Email',
            'Phone',
            'Address',
            'City',
            'State',
            'Country',
            'Region',
            'Website',
            'Firm_Type',
            'Institution_Type',
            'AUM_USD_Million',
            'LinkedIn',
            'Additional_Info'
        ]
    
    def standardize_dataframe(self, df: pd.DataFrame, source_file: str, source_sheet: str) -> pd.DataFrame:
        """Standardize a dataframe to the common column format."""
        
        # Initialize with standard columns
        standardized_df = pd.DataFrame(columns=self.standard_columns)
        
        # Add source tracking
        df_copy = df.copy()
        df_copy['Source_File'] = source_file
        df_copy['Source_Sheet'] = source_sheet
        
        # Column mapping logic based on source
        if 'Contacts_Export' in source_sheet or 'CONTACT_ID' in df.columns:
            # Preqin format (HF Seeding Firms, HFoF investors)
            column_mapping = {
                'Source_File': 'Source_File',
                'Source_Sheet': 'Source_Sheet',
                'FIRM_ID': 'Firm_ID',
                'CONTACT_ID': 'Contact_ID',
                'INVESTOR': 'Institution_Name',
                'FIRM NAME': 'Firm_Name',
                'NAME': 'Full_Name',
                'JOB TITLE': 'Job_Title',
                'EMAIL': 'Email',
                'TEL': 'Phone',
                'ADDRESS': 'Address',
                'CITY': 'City',
                'STATE': 'State',
                'COUNTRY/TERRITORY': 'Country',
                'FIRM TYPE': 'Firm_Type',
                'LINKEDIN': 'LinkedIn'
            }
        else:
            # PitchBook format (Consultants/ICs, Music Royalties)
            column_mapping = {
                'Source_File': 'Source_File',
                'Source_Sheet': 'Source_Sheet',
                'Institution Name': 'Institution_Name',
                'Institution name': 'Institution_Name',
                'First Name': 'First_Name',
                'Last Name': 'Last_Name',
                'Job title': 'Job_Title',
                'Email': 'Email',
                'Telephone': 'Phone',
                'Head office address': 'Address',
                'City': 'City',
                'US state': 'State',
                'Country': 'Country',
                'Region': 'Region',
                'Website': 'Website',
                'Institution type': 'Institution_Type',
                'Institution Type': 'Institution_Type'
            }
        
        # Apply column mapping
        for old_col, new_col in column_mapping.items():
            if old_col in df_copy.columns and new_col in self.standard_columns:
                standardized_df[new_col] = df_copy[old_col]
        
        # Create Full_Name if not present but First/Last names are
        if standardized_df['Full_Name'].isna().all() and not standardized_df['First_Name'].isna().all():
            standardized_df['Full_Name'] = (
                standardized_df['First_Name'].fillna('') + ' ' + 
                standardized_df['Last_Name'].fillna('')
            ).str.strip()
        
        # Fill empty strings instead of NaN for better readability
        standardized_df = standardized_df.fillna('')
        
        return standardized_df
    
    def process_hf_seeding_firms(self) -> pd.DataFrame:
        """Process HF Seeding Firms USA.xlsx file."""
        file_path = self.input_folder / "HF Seeding Firms USA.xlsx"
        logger.info(f"Processing {file_path.name}")
        
        if not file_path.exists():
            logger.warning(f"{file_path.name} not found, skipping...")
            return pd.DataFrame()
        
        try:
            # Read from Contacts_Export sheet
            df = pd.read_excel(file_path, sheet_name='Contacts_Export')
            logger.info(f"Read {len(df)} contacts from HF Seeding Firms")
            return self.standardize_dataframe(df, file_path.stem, 'Contacts_Export')
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            return pd.DataFrame()
    
    def process_hfof_investors(self) -> pd.DataFrame:
        """Process HFoF investors.xlsx file."""
        file_path = self.input_folder / "HFoF investors.xlsx"
        logger.info(f"Processing {file_path.name}")
        
        if not file_path.exists():
            logger.warning(f"{file_path.name} not found, skipping...")
            return pd.DataFrame()
        
        try:
            # Read from Contacts_Export sheet
            df = pd.read_excel(file_path, sheet_name='Contacts_Export')
            logger.info(f"Read {len(df)} contacts from HFoF investors")
            return self.standardize_dataframe(df, file_path.stem, 'Contacts_Export')
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            return pd.DataFrame()
    
    def process_consultants_ics(self) -> pd.DataFrame:
        """Process ConsultantsICs file."""
        file_path = self.input_folder / "ConsultantsICs-2025-08-25T18_42_08.xlsx"
        logger.info(f"Processing {file_path.name}")
        
        if not file_path.exists():
            logger.warning(f"{file_path.name} not found, skipping...")
            return pd.DataFrame()
        
        try:
            # Read from Institution Contacts sheet
            df = pd.read_excel(file_path, sheet_name='Institution Contacts')
            logger.info(f"Read {len(df)} contacts from Consultants/ICs")
            return self.standardize_dataframe(df, file_path.stem, 'Institution Contacts')
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            return pd.DataFrame()
    
    def process_music_royalties(self) -> pd.DataFrame:
        """Process MusicRoyaltiesLPs file."""
        file_path = self.input_folder / "MusicRoyaltiesLPs-2025-08-25T17_33_11.xlsx"
        logger.info(f"Processing {file_path.name}")
        
        if not file_path.exists():
            logger.warning(f"{file_path.name} not found, skipping...")
            return pd.DataFrame()
        
        try:
            # Read from Contacts sheet
            df = pd.read_excel(file_path, sheet_name='Contacts')
            logger.info(f"Read {len(df)} contacts from Music Royalties LPs")
            return self.standardize_dataframe(df, file_path.stem, 'Contacts')
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            return pd.DataFrame()
    
    def combine_all_lists(self) -> pd.DataFrame:
        """Combine all institutional lists into a single dataframe."""
        logger.info("Starting combination of all institutional lists...")
        
        # Process each file
        dfs = []
        
        # Process HF Seeding Firms
        hf_seeding = self.process_hf_seeding_firms()
        if not hf_seeding.empty:
            dfs.append(hf_seeding)
        
        # Process HFoF investors  
        hfof = self.process_hfof_investors()
        if not hfof.empty:
            dfs.append(hfof)
        
        # Process Consultants/ICs
        consultants = self.process_consultants_ics()
        if not consultants.empty:
            dfs.append(consultants)
        
        # Process Music Royalties LPs
        music = self.process_music_royalties()
        if not music.empty:
            dfs.append(music)
        
        if not dfs:
            logger.error("No valid dataframes to combine!")
            return pd.DataFrame()
        
        # Combine all dataframes
        logger.info(f"Combining {len(dfs)} dataframes...")
        combined_df = pd.concat(dfs, ignore_index=True, sort=False)
        
        # Add metadata
        combined_df['Combined_Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        combined_df['Record_ID'] = range(1, len(combined_df) + 1)
        
        logger.info(f"Successfully combined {len(combined_df)} total records")
        
        return combined_df
    
    def save_combined_list(self, df: pd.DataFrame) -> str:
        """Save the combined list to Excel file."""
        output_file = self.output_folder / "Institutional-Tiered-List-v1.xlsx"
        
        logger.info(f"Saving combined list to {output_file}")
        
        # Create Excel writer with multiple sheets
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            # Main combined data
            df.to_excel(writer, sheet_name='Combined_Contacts', index=False)
            
            # Summary statistics
            summary_data = {
                'Metric': [
                    'Total Records',
                    'Unique Sources',
                    'Records with Email',
                    'Records with Phone', 
                    'Records with LinkedIn',
                    'Unique Institutions',
                    'Unique Countries'
                ],
                'Value': [
                    len(df),
                    df['Source_File'].nunique(),
                    len(df[df['Email'] != '']),
                    len(df[df['Phone'] != '']),
                    len(df[df['LinkedIn'] != '']),
                    df['Institution_Name'].nunique(),
                    df['Country'].nunique()
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Source breakdown
            source_breakdown = df.groupby(['Source_File', 'Source_Sheet']).size().reset_index(name='Record_Count')
            source_breakdown.to_excel(writer, sheet_name='Source_Breakdown', index=False)
        
        logger.info(f"✅ Successfully saved to {output_file}")
        return str(output_file)
    
    def generate_report(self, df: pd.DataFrame) -> None:
        """Generate a summary report of the combined data."""
        print(f"\n{'='*60}")
        print(f"📊 INSTITUTIONAL TIERED LIST v1 - SUMMARY REPORT")
        print(f"{'='*60}")
        print(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Total Records: {len(df):,}")
        
        # Source breakdown
        print(f"\n📂 SOURCE BREAKDOWN:")
        source_counts = df.groupby(['Source_File', 'Source_Sheet']).size()
        for (source_file, source_sheet), count in source_counts.items():
            print(f"  📄 {source_file} ({source_sheet}): {count:,} records")
        
        # Data quality metrics
        print(f"\n📈 DATA QUALITY METRICS:")
        print(f"  📧 Records with Email: {len(df[df['Email'] != '']):,} ({len(df[df['Email'] != ''])/len(df)*100:.1f}%)")
        print(f"  📞 Records with Phone: {len(df[df['Phone'] != '']):,} ({len(df[df['Phone'] != ''])/len(df)*100:.1f}%)")
        print(f"  💼 Records with LinkedIn: {len(df[df['LinkedIn'] != '']):,} ({len(df[df['LinkedIn'] != ''])/len(df)*100:.1f}%)")
        print(f"  🏢 Unique Institutions: {df['Institution_Name'].nunique():,}")
        print(f"  🌍 Unique Countries: {df['Country'].nunique():,}")
        
        # Top countries
        print(f"\n🌍 TOP COUNTRIES BY RECORDS:")
        top_countries = df[df['Country'] != '']['Country'].value_counts().head(10)
        for country, count in top_countries.items():
            print(f"  🏴 {country}: {count:,} records")

def main():
    """Main function to combine institutional lists."""
    combiner = InstitutionalListCombiner()
    
    # Combine all lists
    combined_df = combiner.combine_all_lists()
    
    if combined_df.empty:
        logger.error("❌ No data to process!")
        return
    
    # Save combined list
    output_file = combiner.save_combined_list(combined_df)
    
    # Generate report
    combiner.generate_report(combined_df)
    
    print(f"\n🎉 SUCCESS! Combined institutional list saved to:")
    print(f"📁 {output_file}")

if __name__ == "__main__":
    main()
