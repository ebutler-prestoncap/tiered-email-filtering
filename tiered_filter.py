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
import argparse
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
        # Toggle email pattern finding and filling via CLI
        self.enable_find_emails = False
        
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
            # Filter out invalid single-character values like "Y", "N", etc. that are likely boolean flags
            mask = (current_names != '') & (current_names != 'nan') & current_names.notna()
            # Exclude single-character values that are likely not names (Y, N, etc.)
            mask = mask & (current_names.astype(str).str.len() > 1)
            full_names[mask] = current_names[mask]
            priority1_count = mask.sum()
            logger.info(f"Used {priority1_count} existing NAME values")
        
        # Priority 1.5: Check for Full Name or Full_Name columns in original df if NAME is still empty
        if 'Full Name' in df.columns or 'Full_Name' in df.columns:
            full_name_col = 'Full Name' if 'Full Name' in df.columns else 'Full_Name'
            full_name_values = df[full_name_col].fillna('').astype(str)
            # Filter out invalid single-character values
            valid_full_names = (full_name_values != '') & (full_name_values != 'nan') & (full_name_values.str.len() > 1)
            empty_mask = (full_names == '') | (full_names == 'nan') | full_names.isna()
            fill_mask = empty_mask & valid_full_names
            if fill_mask.any():
                full_names[fill_mask] = full_name_values[fill_mask]
                priority1_5_count = fill_mask.sum()
                logger.info(f"Used {priority1_5_count} names from '{full_name_col}' column")
        
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
                delta_df.at[idx, 'FILTER_REASON'] = 'Duplicate in input data (same name + firm)'
        
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
                
                # Check tier patterns using actual regex (consistent with filtering logic)
                tier1_cfg = tier1_config if tier1_config else self.create_tier1_config()
                tier2_cfg = tier2_config if tier2_config else self.create_tier2_config()
                
                # Compile regex patterns
                tier1_regex = re.compile(tier1_cfg['job_title_pattern'], re.IGNORECASE)
                tier1_exclusion = re.compile(tier1_cfg['exclusion_pattern'], re.IGNORECASE)
                tier2_regex = re.compile(tier2_cfg['job_title_pattern'], re.IGNORECASE)
                tier2_exclusion = re.compile(tier2_cfg['exclusion_pattern'], re.IGNORECASE)
                
                # Check tier 1 match
                tier1_matches = tier1_regex.search(job_title) and not tier1_exclusion.search(job_title)
                # Check tier 2 match  
                tier2_matches = tier2_regex.search(job_title) and not tier2_exclusion.search(job_title)
                
                if tier1_matches:
                    delta_df.at[idx, 'TIER_MATCH'] = 'Tier 1'
                    delta_df.at[idx, 'PRIORITY_SCORE'] = self.calculate_priority(mock_row, tier1_cfg)
                elif tier2_matches and 'investment team' in role:
                    delta_df.at[idx, 'TIER_MATCH'] = 'Tier 2'
                    delta_df.at[idx, 'PRIORITY_SCORE'] = self.calculate_priority(mock_row, tier2_cfg)
                elif tier2_matches:
                    delta_df.at[idx, 'TIER_MATCH'] = 'Tier 2 (No Inv Team)'
                    delta_df.at[idx, 'PRIORITY_SCORE'] = self.calculate_priority(mock_row, tier2_cfg)
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
            'NAME': ['NAME', 'name', 'Key Contact', 'contact name', 'contact_name', 'Full Name', 'Full_Name', 'full name', 'full_name'],
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
        
        # Special handling for NAME column: filter out single-character values like "Y", "N" that are likely boolean flags
        if 'NAME' in result_df.columns:
            result_df['NAME'] = result_df['NAME'].apply(
                lambda x: '' if len(str(x).strip()) <= 1 and str(x).strip().upper() in ['Y', 'N', 'T', 'F'] else str(x).strip()
            )
        
        # Add default role if missing
        mask = result_df['ROLE'] == ''
        result_df.loc[mask, 'ROLE'] = 'Investment Team'
        
        logger.info(f"Standardized {len(result_df)} contacts")
        return result_df
    
    # Email pattern extraction removed per request to simplify and avoid firm miscount.
    def extract_email_patterns_by_firm(self, df: pd.DataFrame) -> Dict[str, Dict[str, List[str]]]:
        """Extract firm email schemas and domains from the original standardized dataset.

        Returns mapping: firm -> { 'domains': [domain,...], 'patterns': [patternCode,...] }
        Supported pattern codes: 'first.last', 'fLast', 'firstL', 'first_last', 'firstlast'
        """
        logger.info("Extracting email schemas by firm from standardized input")
        if len(df) == 0:
            return {}

        firm_to_domain_counts: Dict[str, Counter] = defaultdict(Counter)
        firm_to_pattern_counts: Dict[str, Counter] = defaultdict(Counter)

        def make_local(first: str, last: str, pattern: str) -> str:
            f = first.lower()
            l = last.lower()
            if not f or not l:
                return ''
            if pattern == 'first.last':
                return f"{f}.{l}"
            if pattern == 'first_last':
                return f"{f}_{l}"
            if pattern == 'firstlast':
                return f"{f}{l}"
            if pattern == 'fLast':
                return f"{f[0]}{l}"
            if pattern == 'firstL':
                return f"{f}{l[0]}"
            if pattern == 'last.first':
                return f"{l}.{f}"
            if pattern == 'last_first':
                return f"{l}_{f}"
            if pattern == 'lastfirst':
                return f"{l}{f}"
            if pattern == 'lFirst':
                return f"{l[0]}{f}"
            if pattern == 'f.last':
                return f"{f[0]}.{l}"
            if pattern == 'f_last':
                return f"{f[0]}_{l}"
            if pattern == 'first_l':
                return f"{f}_{l[0]}"
            return ''

        def get_first_last(name_val: Any, row: pd.Series) -> Tuple[str, str]:
            first = str(row.get('First Name', '')).strip()
            last = str(row.get('Last Name', '')).strip()
            if first and last:
                return first.lower(), last.lower()
            # Fallback to splitting NAME
            name = str(name_val).strip()
            if not name:
                return '', ''
            parts = re.sub(r"[.,]", "", name).split()
            if len(parts) >= 2:
                return parts[0].lower(), parts[-1].lower()
            return '', ''

        for _, row in df.iterrows():
            firm = str(row.get('INVESTOR', '')).strip()
            email = str(row.get('EMAIL', '')).strip()
            if not firm or not email or '@' not in email:
                continue
            local, domain = email.lower().split('@', 1)
            first, last = get_first_last(row.get('NAME', ''), row)
            if not first or not last:
                continue

            # Count domains
            firm_to_domain_counts[firm][domain] += 1

            # Detect pattern across expanded set
            pattern_order = ['first.last','first_last','firstlast','fLast','firstL','last.first','last_first','lastfirst','lFirst','f.last','f_last','first_l']
            for code in pattern_order:
                candidate = make_local(first, last, code)
                if candidate and local == candidate:
                    firm_to_pattern_counts[firm][code] += 1
                    break

        # Build final mapping selecting most common domains/patterns
        firm_patterns: Dict[str, Dict[str, List[str]]] = {}
        for firm, domain_counts in firm_to_domain_counts.items():
            top_domains = [d for d, _ in domain_counts.most_common(3)]
            pattern_counts = firm_to_pattern_counts.get(firm, Counter())
            top_patterns = [p for p, _ in pattern_counts.most_common(3)] or ['first.last']
            firm_patterns[firm] = {'domains': top_domains, 'patterns': top_patterns}

        logger.info(f"Extracted email schemas for {len(firm_patterns)} firms")
        return firm_patterns

    def fill_missing_emails_with_patterns(self, df: pd.DataFrame, firm_patterns: Dict[str, Dict[str, List[str]]]) -> pd.DataFrame:
        """Fill missing emails using detected firm domains and local-part patterns."""
        if len(df) == 0:
            return df
        df_filled = df.copy()

        # Ensure annotation columns exist
        if 'EMAIL_STATUS' not in df_filled.columns:
            df_filled['EMAIL_STATUS'] = ''
        if 'EMAIL_SCHEMA' not in df_filled.columns:
            df_filled['EMAIL_SCHEMA'] = ''

        def gen_email(first: str, last: str, domain: str, pattern: str) -> str:
            fl = first.lower().replace('.', '').replace(',', '').strip()
            ll = last.lower().replace('.', '').replace(',', '').strip()
            if not fl or not ll or not domain:
                return ''
            if pattern == 'first.last':
                local = f"{fl}.{ll}"
            elif pattern == 'first_last':
                local = f"{fl}_{ll}"
            elif pattern == 'firstlast':
                local = f"{fl}{ll}"
            elif pattern == 'fLast':
                local = f"{fl[0]}{ll}"
            elif pattern == 'firstL':
                local = f"{fl}{ll[0]}"
            elif pattern == 'last.first':
                local = f"{ll}.{fl}"
            elif pattern == 'last_first':
                local = f"{ll}_{fl}"
            elif pattern == 'lastfirst':
                local = f"{ll}{fl}"
            elif pattern == 'lFirst':
                local = f"{ll[0]}{fl}"
            elif pattern == 'f.last':
                local = f"{fl[0]}.{ll}"
            elif pattern == 'f_last':
                local = f"{fl[0]}_{ll}"
            elif pattern == 'first_l':
                local = f"{fl}_{ll[0]}"
            else:
                local = f"{fl}.{ll}"
            return f"{local}@{domain}"

        for idx, row in df_filled.iterrows():
            current = str(row.get('EMAIL', '')).strip()
            if current:
                # Mark existing
                if not str(row.get('EMAIL_STATUS', '')).strip():
                    df_filled.at[idx, 'EMAIL_STATUS'] = 'existing'
                continue
            firm = str(row.get('INVESTOR', '')).strip()
            name = str(row.get('NAME', '')).strip()
            if not firm or not name or firm not in firm_patterns:
                continue

            parts = re.sub(r"[.,]", "", name.lower()).split()
            if len(parts) < 2:
                continue
            first, last = parts[0], parts[-1]
            domains = firm_patterns[firm].get('domains', [])
            patterns = firm_patterns[firm].get('patterns', [])
            if not domains:
                continue
            domain = domains[0]
            # Try each known pattern; fall back to first.last
            tried_patterns = patterns or ['first.last']
            filled = ''
            for pat in tried_patterns:
                candidate = gen_email(first, last, domain, pat)
                if candidate:
                    filled = candidate
                    used_pattern = pat
                    break
            if filled:
                df_filled.at[idx, 'EMAIL'] = filled
                df_filled.at[idx, 'EMAIL_STATUS'] = 'estimated'
                df_filled.at[idx, 'EMAIL_SCHEMA'] = used_pattern
        return df_filled

    def annotate_email_status(self, df: pd.DataFrame) -> pd.DataFrame:
        """Annotate EMAIL_STATUS as 'existing' or 'missing' where not already set."""
        if len(df) == 0:
            return df
        annotated = df.copy()
        if 'EMAIL_STATUS' not in annotated.columns:
            annotated['EMAIL_STATUS'] = ''
        if 'EMAIL_SCHEMA' not in annotated.columns:
            annotated['EMAIL_SCHEMA'] = ''
        for idx, row in annotated.iterrows():
            status = str(row.get('EMAIL_STATUS', '')).strip()
            email_val = str(row.get('EMAIL', '')).strip()
            if not status:
                if email_val:
                    annotated.at[idx, 'EMAIL_STATUS'] = 'existing'
                else:
                    annotated.at[idx, 'EMAIL_STATUS'] = 'missing'
        return annotated
    
    def create_tier1_config(self) -> Dict[str, Any]:
        """Create Tier 1 filter configuration (key contacts, no investment team requirement)"""
        return {
            'name': 'Tier 1 - Key Contacts',
            'description': 'Senior decision makers and key investment professionals',
            'job_title_pattern': r'.*\b(cio|c\.i\.o\.|chief\s+investment\s+officers?t?|deputy\s+chief\s+investment\s+officer|deputy\s+cio|head\s+of\s+investments?|head\s+of\s+investment|head\s+of\s+alternatives?|head\s+of\s+alternative\s+investments?|head\s+of\s+private\s+markets?|head\s+of\s+private\s+equity|head\s+of\s+private\s+debt|head\s+of\s+private\s+credit|head\s+of\s+multi[- ]asset|head\s+of\s+hedge\s+funds?|head\s+of\s+hedge\s+fund\s+research|head\s+of\s+research|head\s+of\s+manager\s+research|head\s+of\s+manager\s+selection|investment\s+directors?|director\s+of\s+investments?|portfolio\s+managers?|fund\s+managers?|investment\s+managers?|investment\s+analyst|research\s+analyst|senior\s+investment\s+officer|investment\s+officer|investment\s+strategist|asset\s+allocation|multi[- ]manager|manager\s+research|due\s+diligence|managing\s+directors?|managing\s+partners?|executive\s+directors?|senior\s+portfolio\s+managers?|presidents?|vice\s+presidents?|senior\s+vice\s+presidents?|executive\s+vice\s+presidents?)\b',
            'exclusion_pattern': r'.*\b(operations?|hr|human\s+resources?|investor\s+relations?|client\s+relations?|marketing|sales|compliance|technology|administrator|assistant|secretary|receptionist|intern|trainee)\b',
            'require_investment_team': False,
            'priority_keywords': ['cio', 'chief investment officer', 'deputy chief investment officer', 'managing director', 'managing partner', 'portfolio manager', 'fund manager', 'president', 'head of investments', 'head of investment', 'head of alternatives', 'head of alternative investments', 'head of private markets', 'head of private equity', 'head of private debt', 'head of private credit', 'head of multi-asset', 'head of hedge funds', 'head of hedge fund research', 'head of research', 'head of manager research', 'head of manager selection', 'investment director', 'director of investments', 'investment analyst', 'research analyst', 'senior investment officer', 'investment officer', 'investment strategist', 'asset allocation', 'multi-manager', 'manager research', 'due diligence']
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
                elif keyword.lower() in ['managing director', 'managing partner', 'president']:
                    priority_score += 80
                elif keyword.lower() in ['portfolio manager', 'fund manager', 'head of investments', 'head of research', 'head of private markets']:
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
        logger.info(f"  Max contacts per firm: {max_contacts}")
        logger.info(f"  Require investment team: {tier_config.get('require_investment_team', False)}")
        
        if len(df) == 0:
            return df
        
        # Compile regex patterns
        job_title_regex = re.compile(tier_config['job_title_pattern'], re.IGNORECASE)
        exclusion_regex = re.compile(tier_config['exclusion_pattern'], re.IGNORECASE)
        
        # Filter contacts based on criteria
        filtered_contacts = []
        debug_count = 0
        stats = {
            'title_match': 0,
            'excluded': 0,
            'role_filtered': 0,
            'passed': 0
        }
        
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
            stats['title_match'] += 1
            
            # Check exclusions
            if exclusion_regex.search(job_title):
                stats['excluded'] += 1
                continue
            
            # Check investment team requirement
            if tier_config['require_investment_team']:
                has_investment = 'investment team' in role or 'investment' in role
                if not has_investment:
                    stats['role_filtered'] += 1
                    continue
            
            stats['passed'] += 1
            
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
        
        logger.info(f"  Filtering stats: {stats['title_match']} title matches, {stats['excluded']} excluded by keywords, "
                   f"{stats['role_filtered']} filtered by role requirement, {stats['passed']} passed all filters")
        
        if not filtered_contacts:
            logger.info(f"No contacts matched {tier_config['name']} criteria")
            return pd.DataFrame()
        
        # Convert back to DataFrame
        filtered_df = pd.DataFrame(filtered_contacts)
        logger.info(f"  Contacts matching criteria (before firm limits): {len(filtered_df)}")
        
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
        unique_firms = len(set(row.get('INVESTOR', '') for row in final_contacts))
        
        logger.info(f"{tier_config['name']} result: {len(result_df)} contacts across {unique_firms} firms")
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
                          delta_df: pd.DataFrame = None, excluded_firms_analysis: Dict = None,
                          rescued_df: pd.DataFrame = None, rescue_stats: Dict = None,
                          contact_lists_only: bool = False) -> str:
        """Create output Excel file with contact lists and optionally analytics sheets
        
        Args:
            contact_lists_only: If True, only write contact list sheets (Tier1, Tier2, Tier3).
                              If False, include all analytics sheets (default behavior for CLI).
        """
        
        output_path = self.output_folder / output_filename
        
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            # Define desired column order for standardized output
            standard_columns = ['NAME', 'INVESTOR', 'EMAIL', 'EMAIL_STATUS', 'EMAIL_SCHEMA', 'JOB_TITLE']
            
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
            
            # Rescued contacts (if any)
            if rescued_df is not None and len(rescued_df) > 0:
                # Reorder rescued contacts with standard columns first
                if 'First Name' in rescued_df.columns and 'Last Name' in rescued_df.columns:
                    rescued_reordered = rescued_df[['First Name', 'Last Name'] + [col for col in rescued_df.columns if col not in ['First Name', 'Last Name']]]
                else:
                    rescued_reordered = rescued_df
                rescued_reordered.to_excel(writer, sheet_name='Tier3_Rescued_Contacts', index=False)
            
            # Always create Processing Summary sheet
            # Processing summary
            total_raw = sum(info.get('contacts', 0) for info in file_info)
            
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
            if hasattr(self, 'enable_firm_exclusion') and self.enable_firm_exclusion and hasattr(self, 'excluded_firms'):
                firms_excluded_count = len(self.excluded_firms)
                # Calculate contacts excluded: difference between before and after exclusion
                if hasattr(self, 'pre_exclusion_count'):
                    contacts_excluded_count = self.pre_exclusion_count - len(deduplicated_df) if deduplicated_df is not None else 0
        
            # Calculate contact inclusion statistics
            contacts_included_count = 0
            contacts_forced_included = 0
            if hasattr(self, 'enable_contact_inclusion') and self.enable_contact_inclusion and hasattr(self, 'included_contacts'):
                contacts_included_count = len(self.included_contacts)
                # This would need to be tracked during inclusion process
                # For now, we'll calculate based on whether contacts were found
                contacts_forced_included = getattr(self, 'contacts_forced_included', 0)
        
            # Get tier configurations for settings display
            tier1_config = getattr(self, '_last_tier1_config', None) or self.create_tier1_config()
            tier2_config = getattr(self, '_last_tier2_config', None) or self.create_tier2_config()
            
            # Determine if include_all_firms was used (check if rescued_df exists and has data)
            include_all_firms_used = (rescue_stats is not None and rescue_stats.get('rescued_contacts', 0) > 0) or (rescued_df is not None and len(rescued_df) > 0)
            
            # Get tier 3 limit if available
            tier3_limit = getattr(self, 'tier3_limit', 3) if include_all_firms_used else None
            
            # Build step and count lists
            step_list = [
                '📁 Input Files',
                '📊 Total Raw Contacts',
                '✅ Unique Contacts After Deduplication',
                '🏢 Unique Firms/Institutions After Deduplication',
                '📊 Avg Contacts per Firm (Before Filtering)',
                '📊 Median Contacts per Firm (Before Filtering)',
                '—',
                '⚙️ FILTERING SETTINGS',
                '⚙️ Tier 1 Max Contacts per Firm',
                '⚙️ Tier 2 Max Contacts per Firm',
            ]
            count_list = [
                len(file_info),
                f"{total_raw:,}",
                f"{dedup_count:,}",
                f"{unique_firms_after_dedup:,}",
                f"{avg_contacts_per_firm_before:.1f}",
                f"{median_contacts_per_firm_before:.1f}",
                '—',
                '',  # Section header
                f"{self.tier1_limit}",
                f"{self.tier2_limit}",
            ]
            
            # Add Tier 3 limit if applicable
            if include_all_firms_used:
                step_list.append('⚙️ Tier 3 Max Contacts per Firm')
                count_list.append(f"{tier3_limit}")
            
            # Continue with remaining settings
            step_list.extend([
                '⚙️ Email Discovery Enabled',
                '⚙️ Firm Exclusion Enabled',
                '⚙️ Contact Inclusion Enabled',
                '⚙️ Include All Firms (Rescue) Enabled',
                '⚙️ Tier 1 Requires Investment Team',
                '⚙️ Tier 2 Requires Investment Team',
                '—',
                '🚫 Firm Exclusion Applied',
                '🚫 Firms Excluded',
                '🚫 Contacts Excluded by Firm Filter',
                '—',
                '✅ Contact Inclusion Applied',
                '✅ Contacts in Inclusion List',
                '✅ Contacts Forced Through Filters',
                '—',
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
                '—',
                '📧 Tier 1 Emails Available',
                '📧 Tier 2 Emails Available',
                '—',
                '🚁 Firm Rescue Applied',
                '🚁 Firms Rescued',
                '🚁 Contacts Rescued',
                '🚁 Firm Rescue Rate',
                '—',
                '📅 Processing Date'
            ])
            count_list.extend([
                "Yes" if (hasattr(self, 'enable_find_emails') and self.enable_find_emails) else "No",
                "Yes" if (hasattr(self, 'enable_firm_exclusion') and self.enable_firm_exclusion) else "No",
                "Yes" if (hasattr(self, 'enable_contact_inclusion') and self.enable_contact_inclusion) else "No",
                "Yes" if include_all_firms_used else "No",
                "Yes" if tier1_config.get('require_investment_team', False) else "No",
                "Yes" if tier2_config.get('require_investment_team', False) else "No",
                '—',
                "Yes" if (hasattr(self, 'enable_firm_exclusion') and self.enable_firm_exclusion) else "No",
                f"{firms_excluded_count:,}" if (hasattr(self, 'enable_firm_exclusion') and self.enable_firm_exclusion) else "0",
                f"{contacts_excluded_count:,}" if (hasattr(self, 'enable_firm_exclusion') and self.enable_firm_exclusion) else "0",
                '—',
                "Yes" if (hasattr(self, 'enable_contact_inclusion') and self.enable_contact_inclusion) else "No",
                f"{contacts_included_count:,}" if (hasattr(self, 'enable_contact_inclusion') and self.enable_contact_inclusion) else "0",
                f"{contacts_forced_included:,}" if (hasattr(self, 'enable_contact_inclusion') and self.enable_contact_inclusion) else "0",
                '—',
                f"{len(tier1_df):,}",
                f"{tier1_firms:,}",
                f"{avg_contacts_per_firm_tier1:.1f}",
                f"{median_contacts_per_firm_tier1:.1f}",
                f"{len(tier2_df):,}",
                f"{tier2_firms:,}",
                f"{avg_contacts_per_firm_tier2:.1f}",
                f"{median_contacts_per_firm_tier2:.1f}",
                f"{len(tier1_df) + len(tier2_df):,}",
                f"{total_firms_filtered:,}",
                f"{((len(tier1_df) + len(tier2_df)) / total_raw * 100):.1f}%" if total_raw > 0 else "0.0%",
                '—',
                f"{tier1_df['EMAIL'].notna().sum():,}" if len(tier1_df) > 0 and 'EMAIL' in tier1_df.columns else "0",
                f"{tier2_df['EMAIL'].notna().sum():,}" if len(tier2_df) > 0 and 'EMAIL' in tier2_df.columns else "0",
                '—',
                "Yes" if (rescue_stats and rescue_stats.get('rescued_contacts', 0) > 0) else "No",
                f"{rescue_stats.get('rescued_firms', 0):,}" if rescue_stats else "0",
                f"{rescue_stats.get('rescued_contacts', 0):,}" if rescue_stats else "0",
                f"{rescue_stats.get('rescue_rate', 0):.1f}%" if rescue_stats else "0.0%",
                '—',
                datetime.now().strftime("%Y-%m-%d")
            ])
            
            summary_data = {
                'Step': step_list,
                'Count': count_list
            }
        
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Processing_Summary', index=False)
        
            # Only write other analytics sheets if contact_lists_only is False
            if not contact_lists_only:
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
                    
                    # Filter breakdown removed - no longer output to Excel
                
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
                        standard_columns = ['NAME', 'INVESTOR', 'EMAIL', 'EMAIL_STATUS', 'EMAIL_SCHEMA', 'JOB_TITLE']
                        available_std_cols = [col for col in standard_columns if col in excluded_contacts_df.columns]
                        other_cols = [col for col in excluded_contacts_df.columns if col not in available_std_cols]
                        excluded_contacts_reordered = excluded_contacts_df[available_std_cols + other_cols]
                        
                        excluded_contacts_reordered.to_excel(writer, sheet_name='Excluded_Firm_Contacts', index=False)
        
        logger.info(f"Output saved to: {output_path}")
        return str(output_path)
    
    def create_excluded_firms_analysis(self, deduplicated_df: pd.DataFrame, tier1_df: pd.DataFrame, tier2_df: pd.DataFrame, rescued_df: pd.DataFrame = None) -> Dict:
        """Create analysis of completely excluded firms vs included firms"""
        logger.info("Creating excluded firms analysis")
        
        # Get all firms from deduplicated data
        all_firms_after_dedup = set()
        if 'INVESTOR' in deduplicated_df.columns and len(deduplicated_df) > 0:
            all_firms_after_dedup = set(deduplicated_df['INVESTOR'].dropna().unique())
        
        # Get firms that made it into either tier (including rescued firms)
        included_firms = set()
        if len(tier1_df) > 0 and 'INVESTOR' in tier1_df.columns:
            included_firms.update(tier1_df['INVESTOR'].dropna().unique())
        if len(tier2_df) > 0 and 'INVESTOR' in tier2_df.columns:
            included_firms.update(tier2_df['INVESTOR'].dropna().unique())
        if rescued_df is not None and len(rescued_df) > 0 and 'INVESTOR' in rescued_df.columns:
            included_firms.update(rescued_df['INVESTOR'].dropna().unique())
        
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
    
    def rescue_excluded_firms(self, deduplicated_df: pd.DataFrame, tier1_df: pd.DataFrame, tier2_df: pd.DataFrame, max_contacts_per_firm: int = 3) -> Tuple[pd.DataFrame, Dict]:
        """
        Rescue top 1-3 contacts from firms that have zero contacts in Tiers 1/2
        
        Args:
            deduplicated_df: All deduplicated contacts
            tier1_df: Current Tier 1 contacts
            tier2_df: Current Tier 2 contacts  
            max_contacts_per_firm: Maximum contacts to rescue per firm (default: 3)
            
        Returns:
            Tuple of (rescued_contacts_df, rescue_stats)
        """
        logger.info("Starting firm rescue process for excluded firms")
        
        # Get firms that have contacts in Tiers 1/2
        included_firms = set()
        if len(tier1_df) > 0 and 'INVESTOR' in tier1_df.columns:
            included_firms.update(tier1_df['INVESTOR'].dropna().unique())
        if len(tier2_df) > 0 and 'INVESTOR' in tier2_df.columns:
            included_firms.update(tier2_df['INVESTOR'].dropna().unique())
        
        # Find firms with zero contacts in tiers
        all_firms = set(deduplicated_df['INVESTOR'].dropna().unique())
        excluded_firms = all_firms - included_firms
        
        logger.info(f"Found {len(excluded_firms)} firms with zero contacts in Tiers 1/2")
        
        if len(excluded_firms) == 0:
            return pd.DataFrame(), {'rescued_firms': 0, 'rescued_contacts': 0}
        
        rescued_contacts = []
        rescued_firms_count = 0
        
        # Define priority scoring for rescue (similar to tier filtering but more inclusive)
        def calculate_rescue_priority(row):
            job_title = str(row.get('JOB_TITLE', '')).lower()
            priority = 0
            
            # High priority titles (C-suite, senior roles)
            if any(term in job_title for term in ['ceo', 'chief executive', 'managing director', 'managing partner']):
                priority += 100
            elif any(term in job_title for term in ['cfo', 'chief financial', 'cio', 'chief investment']):
                priority += 90
            elif any(term in job_title for term in ['coo', 'chief operating', 'president', 'chairman', 'chair']):
                priority += 80
            elif any(term in job_title for term in ['director', 'partner', 'vice president']):
                priority += 60
            elif any(term in job_title for term in ['manager', 'head of']):
                priority += 40
            elif any(term in job_title for term in ['analyst', 'associate']):
                priority += 20
            
            # Bonus for investment-related terms
            if 'investment' in job_title:
                priority += 15
            if 'portfolio' in job_title:
                priority += 10
            if 'fund' in job_title:
                priority += 10
                
            return priority
        
        # Process each excluded firm
        for firm in excluded_firms:
            firm_contacts = deduplicated_df[deduplicated_df['INVESTOR'] == firm].copy()
            
            if len(firm_contacts) == 0:
                continue
                
            # Calculate priority scores
            firm_contacts['rescue_priority'] = firm_contacts.apply(calculate_rescue_priority, axis=1)
            
            # Sort by priority (descending) and take top contacts
            firm_contacts = firm_contacts.sort_values('rescue_priority', ascending=False)
            top_contacts = firm_contacts.head(max_contacts_per_firm)
            
            # Only rescue contacts with some priority (avoid completely irrelevant contacts)
            top_contacts = top_contacts[top_contacts['rescue_priority'] > 0]
            
            if len(top_contacts) > 0:
                rescued_contacts.extend(top_contacts.to_dict('records'))
                rescued_firms_count += 1
                
                logger.info(f"Rescued {len(top_contacts)} contacts from {firm}")
        
        rescued_df = pd.DataFrame(rescued_contacts) if rescued_contacts else pd.DataFrame()
        
        rescue_stats = {
            'total_excluded_firms': len(excluded_firms),
            'rescued_firms': rescued_firms_count,
            'rescued_contacts': len(rescued_df),
            'rescue_rate': (rescued_firms_count / len(excluded_firms) * 100) if len(excluded_firms) > 0 else 0
        }
        
        logger.info(f"Firm rescue complete: {rescue_stats['rescued_contacts']} contacts from {rescue_stats['rescued_firms']} firms")
        
        return rescued_df, rescue_stats
    
    def process_contacts(self, user_prefix: str = None, enable_firm_exclusion: bool = False, enable_contact_inclusion: bool = False, include_all_firms: bool = False, enable_find_emails: bool = False) -> str:
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
        
        # 4.5. If enabled, extract email schemas from standardized data and fill missing emails in tiers
        self.enable_find_emails = enable_find_emails
        firm_patterns = {}
        if self.enable_find_emails:
            logger.info("Email schema discovery enabled: extracting and filling emails")
            firm_patterns = self.extract_email_patterns_by_firm(standardized_df)
            if len(tier1_df) > 0:
                tier1_df = self.fill_missing_emails_with_patterns(tier1_df, firm_patterns)
            if len(tier2_df) > 0:
                tier2_df = self.fill_missing_emails_with_patterns(tier2_df, firm_patterns)

        # 5. Create delta analysis
        delta_df = self.create_delta_analysis(combined_df, standardized_df, deduplicated_df, tier1_df, tier2_df, tier1_config, tier2_config)
        
        # 5.5. Rescue excluded firms (if enabled)
        rescued_df = pd.DataFrame()
        rescue_stats = {'rescued_firms': 0, 'rescued_contacts': 0, 'total_excluded_firms': 0, 'rescue_rate': 0}
        
        if include_all_firms:
            logger.info("Applying firm rescue process")
            rescued_df, rescue_stats = self.rescue_excluded_firms(deduplicated_df, tier1_df, tier2_df)
            
            if len(rescued_df) > 0:
                # Add rescued contacts as a new tier (Tier 3 - Rescued Contacts)
                rescued_df['tier_type'] = 'Tier 3 - Rescued Contacts'
                logger.info(f"Added {len(rescued_df)} rescued contacts from {rescue_stats['rescued_firms']} firms")
                # If email discovery is enabled, also fill/annotate rescued contacts
                if self.enable_find_emails and firm_patterns:
                    rescued_df = self.fill_missing_emails_with_patterns(rescued_df, firm_patterns)
        
        # 5.6. Annotate email status for all tiers (ensure existing/missing set)
        if len(tier1_df) > 0:
            tier1_df = self.annotate_email_status(tier1_df)
        if len(tier2_df) > 0:
            tier2_df = self.annotate_email_status(tier2_df)
        if include_all_firms and len(rescued_df) > 0:
            rescued_df = self.annotate_email_status(rescued_df)

        # 6. Create excluded firms analysis (after rescue)
        excluded_firms_analysis = self.create_excluded_firms_analysis(deduplicated_df, tier1_df, tier2_df, rescued_df if include_all_firms else pd.DataFrame())
        
        # 7. Generate output file with delta analysis and excluded firms
        output_filename = self.generate_output_filename(file_info, user_prefix)
        output_path = self.create_output_file(tier1_df, tier2_df, file_info, dedup_count, output_filename, deduplicated_df, delta_df, excluded_firms_analysis, rescued_df, rescue_stats)
        
        # Summary
        total_contacts = len(tier1_df) + len(tier2_df)
        if include_all_firms and len(rescued_df) > 0:
            total_contacts += len(rescued_df)
            logger.info(f"Processing complete! Final result: {total_contacts} qualified contacts ({len(tier1_df)} Tier 1 + {len(tier2_df)} Tier 2 + {len(rescued_df)} Rescued)")
        else:
            logger.info(f"Processing complete! Final result: {total_contacts} qualified contacts ({len(tier1_df)} Tier 1 + {len(tier2_df)} Tier 2)")
        
        return output_path


def main():
    """Main execution function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Tiered Contact Filter')
    parser.add_argument('--include-all-firms', action='store_true', 
                       help='Include top 1-3 contacts from firms with zero contacts in Tiers 1/2')
    parser.add_argument('--find-emails', action='store_true',
                       help='Discover firm email schemas from input and fill missing emails in tiers')
    args = parser.parse_args()
    
    print("🚀 TIERED CONTACT FILTER")
    print("=" * 60)
    
    if args.include_all_firms:
        print("🏢 --include-all-firms flag enabled: Will rescue top contacts from excluded firms")
        print()
    
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
        output_file = filter_tool.process_contacts(user_prefix, enable_firm_exclusion, enable_contact_inclusion, args.include_all_firms, args.find_emails)
        
        print()
        print("=" * 60)
        print("✅ SUCCESS! Tiered filtering completed.")
        print(f"📊 Output file: {output_file}")
        print()
        print("📋 Output includes:")
        print("   • Tier1_Key_Contacts: Senior decision makers")
        print("   • Tier2_Junior_Contacts: Junior professionals (investment team)")
        if args.include_all_firms:
            print("   • Tier3_Rescued_Contacts: Top contacts from excluded firms")
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
