#!/usr/bin/env python3
"""
Unified Tiered Contact Filter
A single, consolidated filtering tool that processes contact data with two-tier filtering:
- Tier 1: Key contacts (no investment team requirement)
- Tier 2: Junior contacts (must be on investment team)

Key Features:
- Combines multiple input files and removes duplicates
- Email pattern extraction from full dataset
- Missing email filling using firm patterns
- Firm-based contact limits with priority ranking
"""

import pandas as pd
import numpy as np
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
from collections import Counter, defaultdict
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TieredFilter:
    """Unified tiered filtering with email pattern extraction"""
    
    def __init__(self, input_folder: str = "input", output_folder: str = "output"):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.archive_folder = Path(output_folder) / "archive"
        
        # Create directories
        self.output_folder.mkdir(exist_ok=True)
        self.archive_folder.mkdir(exist_ok=True)
        
        # Email pattern regex
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', re.IGNORECASE)
        
        # Firm-based contact limits
        self.tier1_limit = 10  # Max Tier 1 contacts per firm
        self.tier2_limit = 6   # Max Tier 2 contacts per firm
        
        # Toggle email filling (disabled for testing to avoid confusion)
        self.enable_email_fill = False
        
        # Firm exclusion settings
        self.enable_firm_exclusion = False
        self.excluded_firms = set()
        
        # Contact inclusion settings
        self.enable_contact_inclusion = False
        self.included_contacts = set()  # Set of (name, firm) tuples
        self.contacts_forced_included = 0  # Count of contacts forced through filters
        
    def load_firm_exclusion_list(self) -> None:
        """Load firm exclusion list from CSV file"""
        exclusion_file = self.input_folder / "firm exclusion.csv"
        
        if not exclusion_file.exists():
            logger.warning(f"Firm exclusion file not found: {exclusion_file}")
            return
        
        try:
            # Read CSV file - it's a simple single column list
            with open(exclusion_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Clean and normalize firm names
            excluded_firms = set()
            for line in lines:
                firm_name = line.strip()
                if firm_name:  # Skip empty lines
                    # Normalize for matching (lowercase, remove extra whitespace)
                    normalized_name = firm_name.lower().strip()
                    excluded_firms.add(normalized_name)
                    # Also store original case for logging
                    self.excluded_firms.add(firm_name.strip())
            
            # Store normalized versions for matching
            self.excluded_firms_normalized = excluded_firms
            
            logger.info(f"Loaded {len(self.excluded_firms)} firms from exclusion list")
            logger.info(f"Sample excluded firms: {list(self.excluded_firms)[:5]}...")
            
        except Exception as e:
            logger.error(f"Error loading firm exclusion list: {e}")
            self.excluded_firms = set()
            self.excluded_firms_normalized = set()
    
    def apply_firm_exclusion(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply firm exclusion filtering"""
        if not self.enable_firm_exclusion or not hasattr(self, 'excluded_firms_normalized'):
            return df
        
        if len(df) == 0:
            return df
        
        logger.info(f"Applying firm exclusion to {len(df)} contacts")
        
        # Create mask for non-excluded firms
        if 'INVESTOR' not in df.columns:
            logger.warning("No INVESTOR column found for firm exclusion")
            return df
        
        def is_firm_excluded(firm_name):
            if pd.isna(firm_name) or firm_name == '':
                return False
            
            normalized_firm = str(firm_name).lower().strip()
            return normalized_firm in self.excluded_firms_normalized
        
        # Apply exclusion filter
        mask = ~df['INVESTOR'].apply(is_firm_excluded)
        filtered_df = df[mask].copy()
        
        excluded_count = len(df) - len(filtered_df)
        logger.info(f"Excluded {excluded_count} contacts from {len(self.excluded_firms)} excluded firms")
        
        if excluded_count > 0:
            # Log some examples of excluded firms found in data
            excluded_firms_found = set()
            for _, row in df[~mask].iterrows():
                firm = str(row.get('INVESTOR', '')).strip()
                if firm:
                    excluded_firms_found.add(firm)
            
            logger.info(f"Excluded firms found in data: {list(excluded_firms_found)[:5]}...")
        
        return filtered_df
    
    def load_contact_inclusion_list(self) -> None:
        """Load contact inclusion list from CSV file"""
        inclusion_file = self.input_folder / "include_contacts.csv"
        
        if not inclusion_file.exists():
            logger.warning(f"Contact inclusion file not found: {inclusion_file}")
            return
        
        try:
            # Read CSV file with Institution_Name and Full_Name columns
            import pandas as pd
            df = pd.read_csv(inclusion_file)
            
            # Ensure required columns exist
            if 'Institution_Name' not in df.columns or 'Full_Name' not in df.columns:
                logger.error("Contact inclusion CSV must have 'Institution_Name' and 'Full_Name' columns")
                return
            
            # Clean and normalize contact combinations
            included_contacts = set()
            for _, row in df.iterrows():
                firm_name = str(row.get('Institution_Name', '')).strip()
                full_name = str(row.get('Full_Name', '')).strip()
                
                if firm_name and full_name:  # Skip empty rows
                    # Normalize for matching (lowercase, remove extra whitespace)
                    normalized_firm = firm_name.lower().strip()
                    normalized_name = full_name.lower().strip()
                    included_contacts.add((normalized_name, normalized_firm))
                    # Also store original case for logging
                    self.included_contacts.add((full_name.strip(), firm_name.strip()))
            
            # Store normalized versions for matching
            self.included_contacts_normalized = included_contacts
            
            logger.info(f"Loaded {len(self.included_contacts)} contacts from inclusion list")
            logger.info(f"Sample included contacts: {list(self.included_contacts)[:5]}...")
            
        except Exception as e:
            logger.error(f"Error loading contact inclusion list: {e}")
            self.included_contacts = set()
            self.included_contacts_normalized = set()
    
    def apply_contact_inclusion(self, tier1_df: pd.DataFrame, tier2_df: pd.DataFrame, 
                               source_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Apply contact inclusion to ensure specific contacts are included"""
        if not self.enable_contact_inclusion or not hasattr(self, 'included_contacts_normalized'):
            return tier1_df, tier2_df
        
        logger.info(f"Applying contact inclusion for {len(self.included_contacts)} specified contacts")
        
        # Find contacts that should be included but aren't in current tiers
        missing_contacts = []
        
        # Create lookup sets for current tier contacts
        tier1_lookup = set()
        tier2_lookup = set()
        
        for _, row in tier1_df.iterrows():
            name = str(row.get('NAME', '')).lower().strip()
            firm = str(row.get('INVESTOR', '')).lower().strip()
            tier1_lookup.add((name, firm))
        
        for _, row in tier2_df.iterrows():
            name = str(row.get('NAME', '')).lower().strip()
            firm = str(row.get('INVESTOR', '')).lower().strip()
            tier2_lookup.add((name, firm))
        
        # Check which included contacts are missing from both tiers
        for (name, firm) in self.included_contacts_normalized:
            if (name, firm) not in tier1_lookup and (name, firm) not in tier2_lookup:
                # Find this contact in the source data
                source_match = None
                for _, source_row in source_df.iterrows():
                    source_name = str(source_row.get('NAME', '')).lower().strip()
                    source_firm = str(source_row.get('INVESTOR', '')).lower().strip()
                    
                    if source_name == name and source_firm == firm:
                        source_match = source_row
                        break
                
                if source_match is not None:
                    missing_contacts.append(source_match)
                    logger.info(f"Found missing included contact: {source_match.get('NAME')} at {source_match.get('INVESTOR')}")
                else:
                    logger.warning(f"Included contact not found in source data: {name} at {firm}")
        
        # Add missing contacts to appropriate tier based on job title patterns
        added_to_tier1 = 0
        added_to_tier2 = 0
        
        if missing_contacts:
            tier1_config = self.create_tier1_config()
            tier2_config = self.create_tier2_config()
            
            # Convert missing contacts to DataFrame for easier processing
            missing_df = pd.DataFrame(missing_contacts)
            
            for _, contact in missing_df.iterrows():
                job_title = str(contact.get('JOB_TITLE', '')).lower()
                
                # Check if contact matches Tier 1 patterns (prioritize Tier 1)
                tier1_regex = re.compile(tier1_config['job_title_pattern'], re.IGNORECASE)
                tier1_exclusion = re.compile(tier1_config['exclusion_pattern'], re.IGNORECASE)
                
                if (tier1_regex.search(job_title) and not tier1_exclusion.search(job_title)):
                    # Add to Tier 1
                    tier1_df = pd.concat([tier1_df, contact.to_frame().T], ignore_index=True)
                    added_to_tier1 += 1
                else:
                    # Add to Tier 2 (forced inclusion regardless of investment team requirement)
                    tier2_df = pd.concat([tier2_df, contact.to_frame().T], ignore_index=True)
                    added_to_tier2 += 1
        
        logger.info(f"Contact inclusion: Added {added_to_tier1} to Tier 1, {added_to_tier2} to Tier 2")
        
        # Store count for summary statistics
        self.contacts_forced_included = added_to_tier1 + added_to_tier2
        
        return tier1_df, tier2_df
        
    def clean_and_archive_output(self) -> None:
        """Clean output folder and archive previous runs with organized structure"""
        logger.info("Cleaning output folder and archiving previous runs")
        
        # Get all Excel files in output folder (excluding archive subfolder)
        excel_files = [f for f in self.output_folder.glob("*.xlsx") if f.is_file()]
        
        if not excel_files:
            logger.info("No previous output files to archive")
            return
        
        # Create timestamp-based archive folder for this cleanup
        cleanup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cleanup_folder = self.archive_folder / f"run_{cleanup_timestamp}"
        cleanup_folder.mkdir(exist_ok=True)
        
        # Move files to archive with organized naming
        moved_count = 0
        for file_path in excel_files:
            try:
                # Move file to archive folder
                archived_path = cleanup_folder / file_path.name
                file_path.rename(archived_path)
                moved_count += 1
                logger.info(f"Archived: {file_path.name} -> {archived_path.relative_to(self.output_folder)}")
            except Exception as e:
                logger.warning(f"Failed to archive {file_path.name}: {e}")
        
        if moved_count > 0:
            logger.info(f"Successfully archived {moved_count} files to {cleanup_folder.relative_to(self.output_folder)}")
    
    def _process_names_comprehensive(self, df: pd.DataFrame, result_data: dict) -> None:
        """Comprehensive name processing: combine all name sources, then split back to First/Last"""
        logger.info("Processing names comprehensively")
        
        # Step 1: Create the most complete NAME field possible
        # Combine from multiple sources in priority order
        full_names = pd.Series([''] * len(df), index=df.index)
        
        # Priority 1: Use existing NAME if available and not empty
        if 'NAME' in result_data:
            current_names = pd.Series(result_data['NAME'])
            mask = (current_names != '') & (current_names != 'nan') & current_names.notna()
            full_names[mask] = current_names[mask]
            priority1_count = mask.sum()
            logger.info(f"Used {priority1_count} existing NAME values")
        
        # Priority 2: Combine First Name + Last Name for remaining empty names
        if 'First Name' in df.columns and 'Last Name' in df.columns:
            first_names = df['First Name'].fillna('').astype(str)
            last_names = df['Last Name'].fillna('').astype(str)
            combined_names = (first_names + ' ' + last_names).str.strip()
            
            # Fill empty spots with combined names (only where we have useful data)
            empty_mask = (full_names == '') | (full_names == 'nan') | full_names.isna()
            valid_combined_mask = (combined_names != '') & (combined_names != 'nan') & (combined_names != ' ')
            fill_mask = empty_mask & valid_combined_mask
            
            if fill_mask.any():
                full_names[fill_mask] = combined_names[fill_mask]
                priority2_count = fill_mask.sum()
                logger.info(f"Combined {priority2_count} names from 'First Name' + 'Last Name'")
        
        # Step 2: Now split full names back to First Name/Last Name for missing components
        # Ensure we have First Name and Last Name columns in result_data
        if 'First Name' not in result_data:
            if 'First Name' in df.columns:
                result_data['First Name'] = df['First Name'].fillna('').astype(str).values
            else:
                result_data['First Name'] = np.array([''] * len(df), dtype=str)
        if 'Last Name' not in result_data:
            if 'Last Name' in df.columns:
                result_data['Last Name'] = df['Last Name'].fillna('').astype(str).values
            else:
                result_data['Last Name'] = np.array([''] * len(df), dtype=str)
        
        # Split full names for records missing First Name or Last Name
        first_names_series = pd.Series(result_data['First Name'])
        last_names_series = pd.Series(result_data['Last Name'])
        
        # Identify records that need name splitting (ensure string comparison)
        first_names_str = first_names_series.astype(str)
        last_names_str = last_names_series.astype(str)
        full_names_str = full_names.astype(str)
        
        missing_first = (first_names_str == '') | (first_names_str == 'nan') | (first_names_str == 'None')
        missing_last = (last_names_str == '') | (last_names_str == 'nan') | (last_names_str == 'None')
        needs_splitting = (missing_first | missing_last) & (full_names_str != '') & (full_names_str != 'nan') & (full_names_str != 'None')
        
        if needs_splitting.any():
            logger.info(f"Splitting {needs_splitting.sum()} full names to fill missing First/Last Name fields")
            
            for idx in needs_splitting[needs_splitting].index:
                full_name = str(full_names_str[idx]).strip()
                if full_name and full_name not in ['nan', 'None', '']:
                    name_parts = full_name.split()
                    
                    if len(name_parts) >= 2:
                        # If missing first name, use first part
                        if missing_first[idx]:
                            first_names_series[idx] = str(name_parts[0])
                        # If missing last name, use last part
                        if missing_last[idx]:
                            last_names_series[idx] = str(name_parts[-1])
                    elif len(name_parts) == 1:
                        # Single name - put in First Name if that's what's missing
                        if missing_first[idx] and not missing_last[idx]:
                            first_names_series[idx] = str(name_parts[0])
                        elif missing_last[idx] and not missing_first[idx]:
                            last_names_series[idx] = str(name_parts[0])
                        else:
                            # Both missing, put single name in First Name
                            first_names_series[idx] = str(name_parts[0])
        
        # Update result_data with processed names
        result_data['NAME'] = full_names.values
        result_data['First Name'] = first_names_series.values
        result_data['Last Name'] = last_names_series.values
        
        # Final statistics
        final_full_names = full_names[full_names != '']
        final_first_names = first_names_series[first_names_series != '']
        final_last_names = last_names_series[last_names_series != '']
        
        logger.info(f"Name processing complete: {len(final_full_names)} full names, {len(final_first_names)} first names, {len(final_last_names)} last names")
    
    def create_delta_analysis(self, original_df: pd.DataFrame, standardized_df: pd.DataFrame, 
                            deduplicated_df: pd.DataFrame, tier1_df: pd.DataFrame, 
                            tier2_df: pd.DataFrame, tier1_config: Dict = None, tier2_config: Dict = None) -> pd.DataFrame:
        """Create delta analysis between input and final output"""
        logger.info("Creating delta analysis between combined input and final tiered output")
        
        # Create tracking DataFrame with all original contacts
        delta_df = original_df.copy()
        
        # Add standardized fields for comparison
        std_cols = ['NAME', 'INVESTOR', 'JOB_TITLE', 'EMAIL', 'ROLE']
        for col in std_cols:
            if col in standardized_df.columns:
                delta_df[f'STD_{col}'] = standardized_df[col].values
        
        # Add processing status tracking
        delta_df['PROCESSING_STATUS'] = 'Input'
        delta_df['FILTER_REASON'] = ''
        delta_df['FINAL_TIER'] = ''
        delta_df['PRIORITY_SCORE'] = 0
        delta_df['TIER_MATCH'] = ''
        
        # Track deduplication
        # Create lookup for deduplicated contacts
        dedup_lookup = set()
        for _, row in deduplicated_df.iterrows():
            key = f"{str(row.get('NAME', '')).lower().strip()}|{str(row.get('INVESTOR', '')).lower().strip()}"
            dedup_lookup.add(key)
        
        # Mark duplicates
        for idx, row in delta_df.iterrows():
            std_name = str(row.get('STD_NAME', '')).lower().strip()
            std_investor = str(row.get('STD_INVESTOR', '')).lower().strip()
            key = f"{std_name}|{std_investor}"
            
            if key not in dedup_lookup:
                delta_df.at[idx, 'PROCESSING_STATUS'] = 'Removed'
                delta_df.at[idx, 'FILTER_REASON'] = 'Duplicate (name + firm)'
        
        # Track tier filtering
        # Create lookups for tier contacts
        tier1_lookup = set()
        tier2_lookup = set()
        
        for _, row in tier1_df.iterrows():
            key = f"{str(row.get('NAME', '')).lower().strip()}|{str(row.get('INVESTOR', '')).lower().strip()}"
            tier1_lookup.add(key)
            
        for _, row in tier2_df.iterrows():
            key = f"{str(row.get('NAME', '')).lower().strip()}|{str(row.get('INVESTOR', '')).lower().strip()}"
            tier2_lookup.add(key)
        
        # Calculate priority scores and tier matches for all contacts
        for idx, row in delta_df.iterrows():
            if delta_df.at[idx, 'PROCESSING_STATUS'] == 'Input':  # Not marked as duplicate
                std_name = str(row.get('STD_NAME', '')).lower().strip()
                std_investor = str(row.get('STD_INVESTOR', '')).lower().strip()
                key = f"{std_name}|{std_investor}"
                
                # Calculate priority score using the same logic as tier filtering
                job_title = str(row.get('STD_JOB_TITLE', '')).lower()
                role = str(row.get('STD_ROLE', '')).lower()
                
                # Create a row-like object for calculate_priority
                mock_row = pd.Series({
                    'JOB_TITLE': row.get('STD_JOB_TITLE', ''),
                    'ROLE': row.get('STD_ROLE', ''),
                    'NAME': row.get('STD_NAME', ''),
                    'INVESTOR': row.get('STD_INVESTOR', '')
                })
                
                # Check tier 1 patterns
                tier1_score = self.calculate_priority(mock_row, tier1_config if tier1_config else self.create_tier1_config())
                # Check tier 2 patterns  
                tier2_score = self.calculate_priority(mock_row, tier2_config if tier2_config else self.create_tier2_config())
                
                if tier1_score > 0:
                    delta_df.at[idx, 'TIER_MATCH'] = 'Tier 1'
                    delta_df.at[idx, 'PRIORITY_SCORE'] = tier1_score
                elif tier2_score > 0 and 'investment team' in role:
                    delta_df.at[idx, 'TIER_MATCH'] = 'Tier 2'
                    delta_df.at[idx, 'PRIORITY_SCORE'] = tier2_score
                elif tier2_score > 0:
                    delta_df.at[idx, 'TIER_MATCH'] = 'Tier 2 (No Inv Team)'
                    delta_df.at[idx, 'PRIORITY_SCORE'] = tier2_score
                else:
                    delta_df.at[idx, 'TIER_MATCH'] = 'No Match'
                
                # Check if included in final output
                if key in tier1_lookup:
                    delta_df.at[idx, 'PROCESSING_STATUS'] = 'Included'
                    delta_df.at[idx, 'FINAL_TIER'] = 'Tier 1 - Key Contacts'
                elif key in tier2_lookup:
                    delta_df.at[idx, 'PROCESSING_STATUS'] = 'Included'
                    delta_df.at[idx, 'FINAL_TIER'] = 'Tier 2 - Junior Contacts'
                else:
                    delta_df.at[idx, 'PROCESSING_STATUS'] = 'Removed'
                    # Use tier match information for better filter reasons
                    tier_match = delta_df.at[idx, 'TIER_MATCH']
                    priority_score = delta_df.at[idx, 'PRIORITY_SCORE']
                    
                    if tier_match == 'No Match':
                        if not job_title or job_title.strip() == '' or job_title == 'nan':
                            delta_df.at[idx, 'FILTER_REASON'] = 'Missing job title'
                        else:
                            delta_df.at[idx, 'FILTER_REASON'] = f'Job title does not match tier patterns: "{job_title[:50]}"'
                    elif tier_match == 'Tier 2 (No Inv Team)':
                        delta_df.at[idx, 'FILTER_REASON'] = 'Tier 2 pattern but not investment team'
                    elif tier_match == 'Tier 1':
                        delta_df.at[idx, 'FILTER_REASON'] = f'Tier 1 pattern but exceeded firm limit (10 max per firm) - Priority: {priority_score}'
                    elif tier_match == 'Tier 2':
                        delta_df.at[idx, 'FILTER_REASON'] = f'Tier 2 pattern but exceeded firm limit (6 max per firm) - Priority: {priority_score}'
                    else:
                        delta_df.at[idx, 'FILTER_REASON'] = f'Other filtering criteria - Tier: {tier_match}'
        
        # Reorder columns for better readability
        cols = ['STD_NAME', 'STD_INVESTOR', 'STD_JOB_TITLE', 'TIER_MATCH', 'PRIORITY_SCORE', 
                'PROCESSING_STATUS', 'FINAL_TIER', 'FILTER_REASON', 'STD_EMAIL']
        other_cols = [col for col in delta_df.columns if col not in cols]
        delta_df = delta_df[cols + other_cols]
        
        return delta_df
        
    def load_and_combine_input_files(self) -> Tuple[pd.DataFrame, List[Dict]]:
        """Load all Excel files from input folder and combine them"""
        logger.info(f"Loading files from {self.input_folder}")
        
        excel_files = list(self.input_folder.glob("*.xlsx"))
        # Exclude any CSV files from processing (like firm exclusion.csv, include_contacts.csv)
        csv_files = list(self.input_folder.glob("*.csv"))
        if csv_files:
            logger.info(f"Found {len(csv_files)} CSV files in input folder - these will be ignored for contact processing: {[f.name for f in csv_files]}")
        
        if not excel_files:
            raise FileNotFoundError(f"No Excel files found in {self.input_folder}")
        
        logger.info(f"Found {len(excel_files)} Excel files: {[f.name for f in excel_files]}")
        
        combined_data = []
        file_info = []
        
        for file_path in excel_files:
            try:
                # Get available sheets first
                excel_file = pd.ExcelFile(file_path)
                available_sheets = excel_file.sheet_names
                
                # Try common sheet names in priority order
                df = None
                sheet_priority = [
                    'Contacts_Export',      # Standard contact export
                    'Contacts',             # Contact data
                    'Institution Contacts', # Institution contact data
                    'Sheet1',               # Default sheet
                    available_sheets[0] if available_sheets else None
                ]
                
                for sheet_name in sheet_priority:
                    if sheet_name and sheet_name in available_sheets:
                        try:
                            df = pd.read_excel(file_path, sheet_name=sheet_name)
                            logger.info(f"Loaded {file_path.name} from sheet '{sheet_name}': {len(df)} rows")
                            break
                        except Exception as e:
                            logger.warning(f"Failed to load sheet '{sheet_name}' from {file_path.name}: {e}")
                            continue
                
                if df is None:
                    logger.warning(f"Could not load any sheet from {file_path.name}")
                    continue
                
                # Add source file column
                df['source_file'] = file_path.name
                combined_data.append(df)
                file_info.append({'file': file_path.name, 'contacts': len(df)})
                
            except Exception as e:
                logger.error(f"Error loading {file_path.name}: {e}")
                continue
        
        if not combined_data:
            raise Exception("No files could be loaded successfully")
        
        # Clean duplicate columns from each file
        for i, df in enumerate(combined_data):
            df_cleaned = df.loc[:, ~df.columns.duplicated()]
            combined_data[i] = df_cleaned
        
        # Combine all dataframes
        combined_df = pd.concat(combined_data, ignore_index=True)
        logger.info(f"Combined dataset: {len(combined_df)} total contacts from {len(file_info)} files")
        
        return combined_df, file_info
    
    def remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicates based on standardized NAME + INVESTOR (case-insensitive)."""
        logger.info(f"Removing duplicates from {len(df)} contacts")
        if len(df) == 0:
            return df
        work = df.reset_index(drop=True).copy()
        # Ensure required columns exist
        if 'NAME' not in work.columns:
            work['NAME'] = ''
        if 'INVESTOR' not in work.columns:
            work['INVESTOR'] = ''
        # Normalize
        work['_norm_name'] = (
            work['NAME'].astype(str).str.lower().str.strip().replace({'nan': '', 'none': ''})
        )
        work['_norm_firm'] = (
            work['INVESTOR'].astype(str).str.lower().str.replace(r"\s+", " ", regex=True).str.strip().replace({'nan': '', 'none': ''})
        )
        before = len(work)
        work = work.drop_duplicates(subset=['_norm_name', '_norm_firm'], keep='first')
        after = len(work)
        work = work.drop(columns=['_norm_name', '_norm_firm'])
        logger.info(f"Removed {before - after} duplicates, {after} unique contacts remain")
        return work
    
    def standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names to consistent format - rebuilt to fix Series issue"""
        logger.info("Standardizing column names")
        
        # Create result DataFrame with clean structure
        result_data = {}
        
        # Standard column mappings (source -> target)
        mappings = {
            'NAME': ['NAME', 'name', 'Key Contact', 'contact name', 'contact_name'],
            'INVESTOR': ['INVESTOR', 'investor', 'Institution Name', 'institution_name', 'firm', 'company'],
            'JOB_TITLE': ['JOB TITLE', 'Job title', 'job_title', 'position'],  # Removed 'TITLE' since it contains salutations
            'EMAIL': ['EMAIL', 'email', 'Email', 'email address'],
            'ROLE': ['ROLE', 'role'],
            'CONTACT_ID': ['CONTACT_ID', 'contact_id', 'id']
        }
        
        # Copy all original non-mapped columns
        mapped_sources = set()
        for target, sources in mappings.items():
            mapped_sources.update(sources)
        
        for col in df.columns:
            if col not in mapped_sources:
                result_data[col] = df[col].values
        
        # Process standard mappings
        for target_col, source_cols in mappings.items():
            # Find ALL available sources and merge them
            available_sources = [col for col in source_cols if col in df.columns]
            
            if available_sources:
                # Start with the first available source
                primary_source = available_sources[0]
                result_data[target_col] = df[primary_source].fillna('').astype(str).values
                logger.info(f"Mapped '{primary_source}' to '{target_col}'")
                
                # Fill missing values from additional sources
                for source in available_sources[1:]:
                    source_values = df[source].fillna('').astype(str)
                    # Create mask for empty/missing values in target
                    current_values = pd.Series(result_data[target_col])
                    mask = (current_values == '') | (current_values == 'nan') | current_values.isna()
                    
                    if mask.any():
                        # Fill missing values
                        filled_values = current_values.copy()
                        filled_values.loc[mask] = source_values.loc[mask]
                        result_data[target_col] = filled_values.values
                        filled_count = mask.sum()
                        logger.info(f"Filled {filled_count} missing values in '{target_col}' from '{source}'")
            else:
                result_data[target_col] = [''] * len(df)
                logger.info(f"Created empty column: {target_col}")
        
        # Enhanced name processing: Create comprehensive full names, then split back to First/Last
        self._process_names_comprehensive(df, result_data)
        
        # Create final DataFrame
        result_df = pd.DataFrame(result_data)
        
        # Clean required columns
        required_columns = ['NAME', 'INVESTOR', 'JOB_TITLE', 'EMAIL', 'ROLE']
        for col in required_columns:
            if col in result_df.columns:
                result_df[col] = result_df[col].fillna('').astype(str)
                result_df[col] = result_df[col].apply(
                    lambda x: '' if str(x).lower().strip() in ['nan', 'none', 'null'] else str(x).strip()
                )
        
        # Add default role if missing
        mask = result_df['ROLE'] == ''
        result_df.loc[mask, 'ROLE'] = 'Investment Team'
        
        logger.info(f"Standardized {len(result_df)} contacts")
        return result_df
    
    # Email pattern extraction removed per request to simplify and avoid firm miscount.
    
    def create_tier1_config(self) -> Dict[str, Any]:
        """Create Tier 1 filter configuration (key contacts, no investment team requirement)"""
        return {
            'name': 'Tier 1 - Key Contacts',
            'description': 'Senior decision makers and key investment professionals',
            'job_title_pattern': r'.*\b(cio|c\.i\.o\.|chief\s+investment\s+officer|deputy\s+cio|head\s+of\s+investments?|head\s+of\s+research|head\s+of\s+private\s+markets?|managing\s+director|executive\s+director|senior\s+portfolio\s+manager|investment\s+director|portfolio\s+manager|investment\s+manager|fund\s+manager|president|vice\s+president|senior\s+vice\s+president|executive\s+vice\s+president)\b',
            'exclusion_pattern': r'.*\b(operations?|hr|human\s+resources?|investor\s+relations?|client\s+relations?|marketing|sales|compliance|technology|administrator|assistant|secretary|receptionist|intern|trainee)\b',
            'require_investment_team': False,
            'priority_keywords': ['cio', 'chief investment officer', 'managing director', 'portfolio manager', 'president']
        }
    
    def create_tier2_config(self) -> Dict[str, Any]:
        """Create Tier 2 filter configuration (junior contacts, must be on investment team)"""
        return {
            'name': 'Tier 2 - Junior Contacts',
            'description': 'Junior investment professionals (must be on investment team)',
            'job_title_pattern': r'.*\b(director|associate\s+director|vice\s+president|investment\s+analyst|research\s+analyst|portfolio\s+analyst|senior\s+analyst|investment\s+advisor|principal|associate|coordinator|specialist|advisor|analyst)\b',
            'exclusion_pattern': r'.*\b(operations?|hr|human\s+resources?|investor\s+relations?|client\s+relations?|marketing|sales|compliance|technology|administrator|assistant|secretary|receptionist|intern|trainee|cio|chief\s+investment\s+officer|managing\s+director|executive\s+director|president|senior\s+vice\s+president|executive\s+vice\s+president)\b',
            'require_investment_team': True,
            'priority_keywords': ['director', 'vice president', 'investment analyst', 'research analyst', 'principal', 'associate']
        }
    
    def calculate_priority(self, row: pd.Series, tier_config: Dict[str, Any]) -> int:
        """Calculate priority score for contact ranking"""
        job_title = str(row.get('JOB_TITLE', '')).lower()
        priority_score = 0
        
        # Score based on priority keywords
        for keyword in tier_config['priority_keywords']:
            if keyword.lower() in job_title:
                if keyword.lower() in ['cio', 'chief investment officer']:
                    priority_score += 100
                elif keyword.lower() in ['managing director', 'president']:
                    priority_score += 80
                elif keyword.lower() in ['portfolio manager']:
                    priority_score += 60
                else:
                    priority_score += 40
                break
        
        # Additional scoring for investment-related terms
        if 'investment' in job_title:
            priority_score += 20
        if 'portfolio' in job_title:
            priority_score += 15
        if 'research' in job_title:
            priority_score += 10
        
        return priority_score
    
    def apply_tier_filter(self, df: pd.DataFrame, tier_config: Dict[str, Any], max_contacts: int) -> pd.DataFrame:
        """Apply tier-specific filtering with firm-based limits"""
        logger.info(f"Applying {tier_config['name']} filtering to {len(df)} contacts")
        
        if len(df) == 0:
            return df
        
        # Compile regex patterns
        job_title_regex = re.compile(tier_config['job_title_pattern'], re.IGNORECASE)
        exclusion_regex = re.compile(tier_config['exclusion_pattern'], re.IGNORECASE)
        
        # Filter contacts based on criteria
        filtered_contacts = []
        debug_count = 0
        
        for idx, row in df.iterrows():
            # Handle potential Series values properly
            job_title_val = row.get('JOB_TITLE', '')
            role_val = row.get('ROLE', '')
            
            # Extract scalar values if they're Series
            if isinstance(job_title_val, pd.Series):
                job_title_val = job_title_val.iloc[0] if not job_title_val.empty else ''
            if isinstance(role_val, pd.Series):
                role_val = role_val.iloc[0] if not role_val.empty else ''
            
            job_title = str(job_title_val).lower()
            role = str(role_val).lower()
            
            # Debug first few contacts
            if debug_count < 5:
                logger.info(f"Debug contact {debug_count}: job_title='{job_title}', role='{role}'")
                match = job_title_regex.search(job_title)
                logger.info(f"  Pattern match: {'YES' if match else 'NO'}")
                debug_count += 1
            
            # Check job title matches
            if not job_title_regex.search(job_title):
                continue
            
            # Check exclusions
            if exclusion_regex.search(job_title):
                continue
            
            # Check investment team requirement (only for Tier 2)
            if tier_config['require_investment_team']:
                if 'investment team' not in role and 'investment' not in role:
                    continue
            
            # Calculate priority score
            priority = self.calculate_priority(row, tier_config)
            
            # Create clean row dictionary with scalar values
            row_dict = {}
            for col in df.columns:
                val = row.get(col, '')
                if isinstance(val, pd.Series):
                    val = val.iloc[0] if not val.empty else ''
                row_dict[col] = val
            
            row_dict['priority_score'] = priority
            filtered_contacts.append(row_dict)
        
        if not filtered_contacts:
            logger.info(f"No contacts matched {tier_config['name']} criteria")
            return pd.DataFrame()
        
        # Convert back to DataFrame
        filtered_df = pd.DataFrame(filtered_contacts)
        
        # Apply firm-based limits with priority ranking
        final_contacts = []
        firm_counts = defaultdict(int)
        
        # Sort by priority score (descending)
        filtered_df = filtered_df.sort_values('priority_score', ascending=False)
        
        for _, row in filtered_df.iterrows():
            firm = row.get('INVESTOR', '')
            if firm_counts[firm] < max_contacts:
                final_contacts.append(row.to_dict())
                firm_counts[firm] += 1
        
        result_df = pd.DataFrame(final_contacts) if final_contacts else pd.DataFrame()
        
        logger.info(f"{tier_config['name']} result: {len(result_df)} contacts")
        return result_df
    
    def fill_missing_emails(self, df: pd.DataFrame, email_patterns: Dict[str, List[str]]) -> pd.DataFrame:
        """Fill missing emails using firm-based patterns"""
        if len(df) == 0:
            return df
        
        logger.info(f"Filling missing emails for {len(df)} contacts")
        
        filled_count = 0
        df_copy = df.copy()
        
        for idx, row in df_copy.iterrows():
            if pd.notna(row.get('EMAIL')) and str(row.get('EMAIL', '')).strip():
                continue  # Email already exists
            
            firm = str(row.get('INVESTOR', '')).strip()
            name = str(row.get('NAME', '')).strip()
            
            if not firm or not name or firm not in email_patterns:
                continue
            
            # Try to generate email using firm patterns
            domains = email_patterns[firm]
            if domains:
                # Use the first (most common) domain
                domain = domains[0]
                
                # Create email from name
                name_parts = name.lower().replace('.', '').replace(',', '').split()
                if len(name_parts) >= 2:
                    # Try firstname.lastname@domain format
                    email_candidate = f"{name_parts[0]}.{name_parts[-1]}@{domain}"
                    df_copy.at[idx, 'EMAIL'] = email_candidate
                    filled_count += 1
        
        logger.info(f"Filled {filled_count} missing emails using firm patterns")
        return df_copy
    
    def generate_output_filename(self, file_info: List[Dict], user_prefix: str = None) -> str:
        """Generate appropriate output filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if len(file_info) == 1:
            # Single file - use file name + standard suffix
            base_name = Path(file_info[0]['file']).stem
            return f"{base_name}_Tiered_List_{timestamp}.xlsx"
        else:
            # Multiple files - use user prefix or default
            prefix = user_prefix if user_prefix else "Combined-Contacts"
            return f"{prefix}_Tiered_List_{timestamp}.xlsx"
    
    def create_output_file(self, tier1_df: pd.DataFrame, tier2_df: pd.DataFrame, 
                          file_info: List[Dict], dedup_count: int, 
                          output_filename: str, deduplicated_df: pd.DataFrame = None, 
                          delta_df: pd.DataFrame = None, excluded_firms_analysis: Dict = None) -> str:
        """Create comprehensive output Excel file"""
        
        output_path = self.output_folder / output_filename
        
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            # Define desired column order for standardized output
            standard_columns = ['NAME', 'INVESTOR', 'EMAIL', 'JOB_TITLE']
            
            # Add First Name and Last Name if they exist in the data
            if 'First Name' in tier1_df.columns:
                standard_columns.insert(0, 'First Name')
            if 'Last Name' in tier1_df.columns:
                standard_columns.insert(1, 'Last Name')
                
            # Reorder Tier 1 contacts with standard columns first
            if len(tier1_df) > 0:
                available_std_cols = [col for col in standard_columns if col in tier1_df.columns]
                other_cols = [col for col in tier1_df.columns if col not in available_std_cols]
                tier1_reordered = tier1_df[available_std_cols + other_cols]
            else:
                tier1_reordered = tier1_df
            tier1_reordered.to_excel(writer, sheet_name='Tier1_Key_Contacts', index=False)
            
            # Reorder Tier 2 contacts with standard columns first
            if len(tier2_df) > 0:
                available_std_cols = [col for col in standard_columns if col in tier2_df.columns]
                other_cols = [col for col in tier2_df.columns if col not in available_std_cols]
                tier2_reordered = tier2_df[available_std_cols + other_cols]
            else:
                tier2_reordered = tier2_df
            tier2_reordered.to_excel(writer, sheet_name='Tier2_Junior_Contacts', index=False)
            
            # Processing summary
            total_raw = sum(info['contacts'] for info in file_info)
            
            # Calculate firm/institution counts and statistics
            raw_firms = set()
            for info in file_info:
                # Estimate firms from file info if available
                if 'firms' in info:
                    raw_firms.update(info['firms'])
            
            # Calculate unique firms after deduplication
            unique_firms_after_dedup = 0
            avg_contacts_per_firm_before = 0
            median_contacts_per_firm_before = 0
            
            if deduplicated_df is not None and 'INVESTOR' in deduplicated_df.columns and len(deduplicated_df) > 0:
                unique_firms_after_dedup = deduplicated_df['INVESTOR'].nunique()
                
                # Calculate average and median contacts per firm before filtering
                firm_contact_counts_before = deduplicated_df['INVESTOR'].value_counts()
                avg_contacts_per_firm_before = firm_contact_counts_before.mean()
                median_contacts_per_firm_before = firm_contact_counts_before.median()
            
            # Calculate tier-specific firm counts and statistics
            tier1_firms = tier1_df['INVESTOR'].nunique() if 'INVESTOR' in tier1_df.columns and len(tier1_df) > 0 else 0
            tier2_firms = tier2_df['INVESTOR'].nunique() if 'INVESTOR' in tier2_df.columns and len(tier2_df) > 0 else 0
            
            # Calculate tier-specific averages and medians
            avg_contacts_per_firm_tier1 = 0
            median_contacts_per_firm_tier1 = 0
            avg_contacts_per_firm_tier2 = 0
            median_contacts_per_firm_tier2 = 0
            
            if len(tier1_df) > 0 and 'INVESTOR' in tier1_df.columns:
                tier1_firm_counts = tier1_df['INVESTOR'].value_counts()
                avg_contacts_per_firm_tier1 = tier1_firm_counts.mean()
                median_contacts_per_firm_tier1 = tier1_firm_counts.median()
            
            if len(tier2_df) > 0 and 'INVESTOR' in tier2_df.columns:
                tier2_firm_counts = tier2_df['INVESTOR'].value_counts()
                avg_contacts_per_firm_tier2 = tier2_firm_counts.mean()
                median_contacts_per_firm_tier2 = tier2_firm_counts.median()
            
            # Calculate unique firms across both tiers (avoiding double counting)
            if len(tier1_df) > 0 and len(tier2_df) > 0 and 'INVESTOR' in tier1_df.columns and 'INVESTOR' in tier2_df.columns:
                all_tier_firms = set(tier1_df['INVESTOR'].dropna().unique()) | set(tier2_df['INVESTOR'].dropna().unique())
                total_firms_filtered = len(all_tier_firms)
            else:
                total_firms_filtered = tier1_firms + tier2_firms
            
            # Calculate firm exclusion statistics
            firms_excluded_count = 0
            contacts_excluded_count = 0
            if self.enable_firm_exclusion and hasattr(self, 'excluded_firms'):
                firms_excluded_count = len(self.excluded_firms)
                # Calculate contacts excluded: difference between before and after exclusion
                if hasattr(self, 'pre_exclusion_count'):
                    contacts_excluded_count = self.pre_exclusion_count - len(deduplicated_df) if deduplicated_df is not None else 0
            
            # Calculate contact inclusion statistics
            contacts_included_count = 0
            contacts_forced_included = 0
            if self.enable_contact_inclusion and hasattr(self, 'included_contacts'):
                contacts_included_count = len(self.included_contacts)
                # This would need to be tracked during inclusion process
                # For now, we'll calculate based on whether contacts were found
                contacts_forced_included = getattr(self, 'contacts_forced_included', 0)
            
            summary_data = {
                'Step': [
                    '📁 Input Files',
                    '📊 Total Raw Contacts',
                    '✅ Unique Contacts After Deduplication',
                    '🏢 Unique Firms/Institutions After Deduplication',
                    '📊 Avg Contacts per Firm (Before Filtering)',
                    '📊 Median Contacts per Firm (Before Filtering)',
                    '',
                    '🚫 Firm Exclusion Applied',
                    '🚫 Firms Excluded',
                    '🚫 Contacts Excluded by Firm Filter',
                    '',
                    '✅ Contact Inclusion Applied',
                    '✅ Contacts in Inclusion List',
                    '✅ Contacts Forced Through Filters',
                    '',
                    '🎯 Tier 1 (Key Contacts)',
                    '🏢 Tier 1 Firms/Institutions',
                    '📊 Avg Contacts per Firm (Tier 1)',
                    '📊 Median Contacts per Firm (Tier 1)',
                    '🎯 Tier 2 (Junior Contacts)',
                    '🏢 Tier 2 Firms/Institutions', 
                    '📊 Avg Contacts per Firm (Tier 2)',
                    '📊 Median Contacts per Firm (Tier 2)',
                    '📈 Total Filtered Contacts',
                    '🏢 Total Firms/Institutions (Both Tiers)',
                    '📊 Retention Rate',
                    '',
                    '📧 Tier 1 Emails Available',
                    '📧 Tier 2 Emails Available',
                    '',
                    '📅 Processing Date'
                ],
                'Count': [
                    len(file_info),
                    f"{total_raw:,}",
                    f"{dedup_count:,}",
                    f"{unique_firms_after_dedup:,}",
                    f"{avg_contacts_per_firm_before:.1f}",
                    f"{median_contacts_per_firm_before:.1f}",
                    '',
                    "Yes" if self.enable_firm_exclusion else "No",
                    f"{firms_excluded_count:,}" if self.enable_firm_exclusion else "0",
                    f"{contacts_excluded_count:,}" if self.enable_firm_exclusion else "0",
                    '',
                    "Yes" if self.enable_contact_inclusion else "No",
                    f"{contacts_included_count:,}" if self.enable_contact_inclusion else "0",
                    f"{contacts_forced_included:,}" if self.enable_contact_inclusion else "0",
                    '',
                    len(tier1_df),
                    f"{tier1_firms:,}",
                    f"{avg_contacts_per_firm_tier1:.1f}",
                    f"{median_contacts_per_firm_tier1:.1f}",
                    len(tier2_df),
                    f"{tier2_firms:,}",
                    f"{avg_contacts_per_firm_tier2:.1f}",
                    f"{median_contacts_per_firm_tier2:.1f}",
                    len(tier1_df) + len(tier2_df),
                    f"{total_firms_filtered:,}",
                    f"{((len(tier1_df) + len(tier2_df)) / total_raw * 100):.1f}%" if total_raw > 0 else "0.0%",
                    '',
                    tier1_df['EMAIL'].notna().sum() if len(tier1_df) > 0 else 0,
                    tier2_df['EMAIL'].notna().sum() if len(tier2_df) > 0 else 0,
                    '',
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Processing_Summary', index=False)
            
            # Input file details
            file_details_df = pd.DataFrame(file_info)
            file_details_df.to_excel(writer, sheet_name='Input_File_Details', index=False)
            
            # Delta analysis (if provided)
            if delta_df is not None:
                delta_df.to_excel(writer, sheet_name='Delta_Analysis', index=False)
                
                # Create delta summary
                delta_summary = delta_df['PROCESSING_STATUS'].value_counts().reset_index()
                delta_summary.columns = ['Status', 'Count']
                delta_summary.to_excel(writer, sheet_name='Delta_Summary', index=False)
                
                # Create filter reason breakdown for removed contacts
                removed_df = delta_df[delta_df['PROCESSING_STATUS'] == 'Removed']
                if len(removed_df) > 0:
                    filter_breakdown = removed_df['FILTER_REASON'].value_counts().reset_index()
                    filter_breakdown.columns = ['Filter Reason', 'Count']
                    filter_breakdown.to_excel(writer, sheet_name='Filter_Breakdown', index=False)
            
            # Excluded firms analysis (if provided)
            if excluded_firms_analysis is not None:
                # Excluded firms summary
                excluded_summary_data = {
                    'Metric': [
                        'Total Firms After Deduplication',
                        'Firms Included in Final Output',
                        'Firms Completely Excluded',
                        'Contacts from Excluded Firms',
                        '',
                        'Exclusion Rate (Firms)',
                        'Exclusion Rate (Contacts)'
                    ],
                    'Count': [
                        f"{excluded_firms_analysis['total_firms_after_dedup']:,}",
                        f"{excluded_firms_analysis['included_firms_count']:,}",
                        f"{excluded_firms_analysis['completely_excluded_firms_count']:,}",
                        f"{excluded_firms_analysis['excluded_firm_contacts_count']:,}",
                        '',
                        f"{(excluded_firms_analysis['completely_excluded_firms_count'] / excluded_firms_analysis['total_firms_after_dedup'] * 100):.1f}%" if excluded_firms_analysis['total_firms_after_dedup'] > 0 else "0.0%",
                        f"{(excluded_firms_analysis['excluded_firm_contacts_count'] / dedup_count * 100):.1f}%" if dedup_count > 0 else "0.0%"
                    ]
                }
                excluded_summary_df = pd.DataFrame(excluded_summary_data)
                excluded_summary_df.to_excel(writer, sheet_name='Excluded_Firms_Summary', index=False)
                
                # List of completely excluded firms
                if excluded_firms_analysis['completely_excluded_firms']:
                    excluded_firms_list_df = pd.DataFrame({
                        'Completely_Excluded_Firms': excluded_firms_analysis['completely_excluded_firms']
                    })
                    excluded_firms_list_df.to_excel(writer, sheet_name='Excluded_Firms_List', index=False)
                
                # List of included firms for reference
                if excluded_firms_analysis['included_firms']:
                    included_firms_list_df = pd.DataFrame({
                        'Included_Firms': excluded_firms_analysis['included_firms']
                    })
                    included_firms_list_df.to_excel(writer, sheet_name='Included_Firms_List', index=False)
                
                # All contacts from completely excluded firms
                if len(excluded_firms_analysis['excluded_firm_contacts']) > 0:
                    excluded_contacts_df = excluded_firms_analysis['excluded_firm_contacts']
                    
                    # Organize columns for better readability
                    standard_columns = ['NAME', 'INVESTOR', 'EMAIL', 'JOB_TITLE']
                    available_std_cols = [col for col in standard_columns if col in excluded_contacts_df.columns]
                    other_cols = [col for col in excluded_contacts_df.columns if col not in available_std_cols]
                    excluded_contacts_reordered = excluded_contacts_df[available_std_cols + other_cols]
                    
                    excluded_contacts_reordered.to_excel(writer, sheet_name='Excluded_Firm_Contacts', index=False)
        
        logger.info(f"Output saved to: {output_path}")
        return str(output_path)
    
    def create_excluded_firms_analysis(self, deduplicated_df: pd.DataFrame, tier1_df: pd.DataFrame, tier2_df: pd.DataFrame) -> Dict:
        """Create analysis of completely excluded firms vs included firms"""
        logger.info("Creating excluded firms analysis")
        
        # Get all firms from deduplicated data
        all_firms_after_dedup = set()
        if 'INVESTOR' in deduplicated_df.columns and len(deduplicated_df) > 0:
            all_firms_after_dedup = set(deduplicated_df['INVESTOR'].dropna().unique())
        
        # Get firms that made it into either tier
        included_firms = set()
        if len(tier1_df) > 0 and 'INVESTOR' in tier1_df.columns:
            included_firms.update(tier1_df['INVESTOR'].dropna().unique())
        if len(tier2_df) > 0 and 'INVESTOR' in tier2_df.columns:
            included_firms.update(tier2_df['INVESTOR'].dropna().unique())
        
        # Find completely excluded firms (had contacts after dedup but none in final tiers)
        completely_excluded_firms = all_firms_after_dedup - included_firms
        
        # Get all contacts from completely excluded firms
        excluded_firm_contacts = pd.DataFrame()
        if len(completely_excluded_firms) > 0 and len(deduplicated_df) > 0:
            excluded_mask = deduplicated_df['INVESTOR'].isin(completely_excluded_firms)
            excluded_firm_contacts = deduplicated_df[excluded_mask].copy()
            
            # Sort by firm name then by contact name
            excluded_firm_contacts = excluded_firm_contacts.sort_values(['INVESTOR', 'NAME'])
        
        # Create summary statistics
        analysis = {
            'total_firms_after_dedup': len(all_firms_after_dedup),
            'included_firms_count': len(included_firms),
            'completely_excluded_firms_count': len(completely_excluded_firms),
            'excluded_firm_contacts_count': len(excluded_firm_contacts),
            'included_firms': sorted(list(included_firms)),
            'completely_excluded_firms': sorted(list(completely_excluded_firms)),
            'excluded_firm_contacts': excluded_firm_contacts
        }
        
        logger.info(f"Excluded firms analysis: {len(completely_excluded_firms)} firms completely excluded with {len(excluded_firm_contacts)} contacts")
        
        return analysis
    
    def process_contacts(self, user_prefix: str = None, enable_firm_exclusion: bool = False, enable_contact_inclusion: bool = False) -> str:
        """Main processing function"""
        logger.info("Starting tiered filtering process")
        
        # Set firm exclusion setting
        self.enable_firm_exclusion = enable_firm_exclusion
        
        # Set contact inclusion setting  
        self.enable_contact_inclusion = enable_contact_inclusion
        
        # Load firm exclusion list if enabled
        if self.enable_firm_exclusion:
            self.load_firm_exclusion_list()
        
        # Load contact inclusion list if enabled
        if self.enable_contact_inclusion:
            self.load_contact_inclusion_list()
        
        # 0. Clean output folder and archive previous runs
        self.clean_and_archive_output()
        
        # 1. Load and combine input files
        combined_df, file_info = self.load_and_combine_input_files()
        
        # 2. Standardize column names (normalize schemas first)
        standardized_df = self.standardize_columns(combined_df)
        
        # 3. Remove duplicates using standardized columns (NAME + INVESTOR)
        deduplicated_df = self.remove_duplicates(standardized_df)
        dedup_count = len(deduplicated_df)
        
        # 3.5. Apply firm exclusion if enabled
        if self.enable_firm_exclusion:
            # Store pre-exclusion count for statistics
            self.pre_exclusion_count = len(deduplicated_df)
            deduplicated_df = self.apply_firm_exclusion(deduplicated_df)
            logger.info(f"After firm exclusion: {len(deduplicated_df)} contacts")
        else:
            self.pre_exclusion_count = len(deduplicated_df)
        
        # 4. Apply tier filtering
        tier1_config = self.create_tier1_config()
        tier2_config = self.create_tier2_config()
        
        tier1_df = self.apply_tier_filter(deduplicated_df, tier1_config, self.tier1_limit)
        tier2_df = self.apply_tier_filter(deduplicated_df, tier2_config, self.tier2_limit)
        
        # Apply contact inclusion to ensure specified contacts are included
        if self.enable_contact_inclusion:
            tier1_df, tier2_df = self.apply_contact_inclusion(tier1_df, tier2_df, deduplicated_df)
        
        # 5. Create delta analysis
        delta_df = self.create_delta_analysis(combined_df, standardized_df, deduplicated_df, tier1_df, tier2_df, tier1_config, tier2_config)
        
        # 6. Create excluded firms analysis
        excluded_firms_analysis = self.create_excluded_firms_analysis(deduplicated_df, tier1_df, tier2_df)
        
        # 7. Generate output file with delta analysis and excluded firms
        output_filename = self.generate_output_filename(file_info, user_prefix)
        output_path = self.create_output_file(tier1_df, tier2_df, file_info, dedup_count, output_filename, deduplicated_df, delta_df, excluded_firms_analysis)
        
        # Summary
        total_contacts = len(tier1_df) + len(tier2_df)
        logger.info(f"Processing complete! Final result: {total_contacts} qualified contacts ({len(tier1_df)} Tier 1 + {len(tier2_df)} Tier 2)")
        
        return output_path


def main():
    """Main execution function"""
    print("🚀 TIERED CONTACT FILTER")
    print("=" * 60)
    
    # Initialize filter
    filter_tool = TieredFilter()
    
    # Check for input files
    input_files = list(filter_tool.input_folder.glob("*.xlsx"))
    if not input_files:
        print(f"❌ No Excel files found in {filter_tool.input_folder}")
        return
    
    print(f"Found {len(input_files)} input file(s):")
    for i, file_path in enumerate(input_files, 1):
        print(f"  {i}. {file_path.name}")
    print()
    
    # Get user prefix if multiple files
    user_prefix = None
    if len(input_files) > 1:
        print("Since multiple files were found, please provide a prefix for the output filename.")
        print("Examples: 'Institutional-Contacts', 'Family-Office-Contacts', 'Combined-Contacts'")
        user_prefix = input("Enter output prefix (or press Enter for 'Combined-Contacts'): ").strip()
        if not user_prefix:
            user_prefix = "Combined-Contacts"
    
    # Check for firm exclusion option
    exclusion_file = filter_tool.input_folder / "firm exclusion.csv"
    enable_firm_exclusion = False
    
    if exclusion_file.exists():
        print(f"\n📋 Found firm exclusion list: {exclusion_file.name}")
        print("This file contains firms that can be excluded from processing.")
        
        while True:
            response = input("Do you want to apply firm exclusion? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                enable_firm_exclusion = True
                print("✅ Firm exclusion will be applied")
                break
            elif response in ['no', 'n']:
                enable_firm_exclusion = False
                print("❌ Firm exclusion will NOT be applied")
                break
            else:
                print("Please enter 'yes' or 'no'")
    else:
        print(f"\n📋 No firm exclusion file found at: {exclusion_file}")
        print("All firms will be processed normally.")
    
    # Check for contact inclusion option
    inclusion_file = filter_tool.input_folder / "include_contacts.csv"
    enable_contact_inclusion = False
    
    if inclusion_file.exists():
        print(f"\n📋 Found contact inclusion list: {inclusion_file.name}")
        print("This file contains specific contacts that will be forced through the filters.")
        
        while True:
            response = input("Do you want to apply contact inclusion? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                enable_contact_inclusion = True
                print("✅ Contact inclusion will be applied")
                break
            elif response in ['no', 'n']:
                enable_contact_inclusion = False
                print("❌ Contact inclusion will NOT be applied")
                break
            else:
                print("Please enter 'yes' or 'no'")
    else:
        print(f"\n📋 No contact inclusion file found at: {inclusion_file}")
        print("Standard filtering will be applied to all contacts.")
    
    try:
        # Process contacts
        output_file = filter_tool.process_contacts(user_prefix, enable_firm_exclusion, enable_contact_inclusion)
        
        print()
        print("=" * 60)
        print("✅ SUCCESS! Tiered filtering completed.")
        print(f"📊 Output file: {output_file}")
        print()
        print("📋 Output includes:")
        print("   • Tier1_Key_Contacts: Senior decision makers")
        print("   • Tier2_Junior_Contacts: Junior professionals (investment team)")
        print("   • Processing_Summary: Statistics and metrics")
        print("   • Input_File_Details: Source file information")
        print("   • Excluded_Firms_Summary: Analysis of completely excluded firms")
        print("   • Excluded_Firms_List: List of firms with zero contacts included")
        print("   • Included_Firms_List: List of firms with contacts included")
        print("   • Excluded_Firm_Contacts: All contacts from excluded firms")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
