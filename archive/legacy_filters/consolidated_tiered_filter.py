#!/usr/bin/env python3
"""
Consolidated Tiered Contact Filter
Unified filtering tool that combines all contact sources into a single tiered output
with email pattern extraction and missing email filling capabilities.
"""

import pandas as pd
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

class ConsolidatedTieredFilter:
    """Unified tiered filtering with email pattern extraction"""
    
    def __init__(self, input_folder: str = "input", output_folder: str = "output"):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(exist_ok=True)
        
        # Email pattern regex
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', re.IGNORECASE)
        
        # Store extracted email patterns by firm
        self.firm_email_patterns = {}
        
        # Firm exclusion settings
        self.enable_firm_exclusion = False
        self.excluded_firms = set()
        
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
        
    def load_and_combine_input_files(self) -> pd.DataFrame:
        """Load all Excel files from input folder and combine them (excluding CSV files)"""
        logger.info(f"Loading files from {self.input_folder}")
        
        excel_files = list(self.input_folder.glob("*.xlsx"))
        # Exclude any CSV files from processing (like firm exclusion.csv)
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
                    'Contacts_Export',  # Standard contact export
                    'Contacts',         # Contact data
                    'Institution Contacts',  # Institution contact data
                    'Sheet1',           # Default sheet
                    available_sheets[0] if available_sheets else None  # First available sheet
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
        
        # Check for duplicate columns before combining
        for i, df in enumerate(combined_data):
            # Remove duplicate columns by keeping only the first occurrence
            df_cleaned = df.loc[:, ~df.columns.duplicated()]
            combined_data[i] = df_cleaned
            if len(df.columns) != len(df_cleaned.columns):
                logger.warning(f"Removed {len(df.columns) - len(df_cleaned.columns)} duplicate columns from {df['source_file'].iloc[0] if 'source_file' in df.columns else 'unknown file'}")
        
        # Combine all dataframes
        combined_df = pd.concat(combined_data, ignore_index=True)
        logger.info(f"Combined dataset: {len(combined_df)} total contacts from {len(file_info)} files")
        
        return combined_df, file_info
    
    def standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names across different data sources"""
        # Enhanced column mapping for multiple formats
        column_mapping = {
            # Institution/Firm names
            'investor': 'INVESTOR',
            'firm': 'INVESTOR', 
            'company': 'INVESTOR',
            'organization': 'INVESTOR',
            'institution_name': 'INVESTOR',
            'institution name': 'INVESTOR',
            'firm_name': 'INVESTOR',
            
            # Contact names
            'name': 'NAME',
            'contact_name': 'NAME',
            'full_name': 'NAME',
            'full name': 'NAME',
            'key contact': 'NAME',
            
            # Job titles
            'job_title': 'JOB TITLE',
            'job title': 'JOB TITLE',
            'title': 'JOB TITLE',
            'position': 'JOB TITLE',
            
            # Roles
            'role': 'ROLE',
            
            # Emails
            'email': 'EMAIL',
            'email_address': 'EMAIL',
            
            # Contact IDs
            'contact_id': 'CONTACT_ID',
            'id': 'CONTACT_ID'
        }
        
        # Rename columns (case insensitive)
        df_renamed = df.copy()
        for old_col in df.columns:
            if old_col.lower() in column_mapping:
                new_col = column_mapping[old_col.lower()]
                df_renamed = df_renamed.rename(columns={old_col: new_col})
                logger.info(f"Renamed column '{old_col}' to '{new_col}'")
        
        # Handle special cases for combined name fields
        if 'NAME' not in df_renamed.columns:
            logger.info(f"No NAME column found. Available columns: {list(df_renamed.columns)}")
            # Try to combine First Name + Last Name
            if 'First Name' in df_renamed.columns and 'Last Name' in df_renamed.columns:
                df_renamed['NAME'] = (df_renamed['First Name'].fillna('').astype(str) + ' ' + 
                                    df_renamed['Last Name'].fillna('').astype(str)).apply(lambda x: x.strip())
                logger.info("Combined 'First Name' and 'Last Name' into 'NAME' column")
            elif 'first name' in df_renamed.columns and 'last name' in df_renamed.columns:
                df_renamed['NAME'] = (df_renamed['first name'].fillna('').astype(str) + ' ' + 
                                    df_renamed['last name'].fillna('').astype(str)).apply(lambda x: x.strip())
                logger.info("Combined 'first name' and 'last name' into 'NAME' column")
        
        # Handle institution-only data (convert institution names to contact names)
        # Simple check - if we don't have NAME column or it's mostly empty, create placeholder names
        if 'NAME' not in df_renamed.columns:
            logger.info(f"No NAME column found after name combination. Available columns: {list(df_renamed.columns)}")
            if 'INVESTOR' in df_renamed.columns:
                df_renamed['NAME'] = 'Contact at ' + df_renamed['INVESTOR'].fillna('Unknown Institution').astype(str)
                df_renamed['JOB TITLE'] = 'Institutional Contact'
                logger.info("Created placeholder names for institution-only data (no NAME column)")
            else:
                logger.warning("No INVESTOR column found either. This will cause issues.")
        
        # Ensure required columns exist with proper data types
        required_columns = ['INVESTOR', 'NAME', 'JOB TITLE', 'EMAIL']
        for col in required_columns:
            if col not in df_renamed.columns:
                df_renamed[col] = ''
                logger.warning(f"Added missing column: {col}")
            else:
                # Clean existing columns
                df_renamed[col] = df_renamed[col].fillna('').astype(str)
                df_renamed[col] = df_renamed[col].apply(lambda x: '' if str(x).lower().strip() in ['nan', 'none', 'null'] else str(x).strip())
        
        # Add ROLE column if missing (optional)
        if 'ROLE' not in df_renamed.columns:
            df_renamed['ROLE'] = 'Investment Team'  # Default assumption for institutional data
        else:
            df_renamed['ROLE'] = df_renamed['ROLE'].fillna('Investment Team').astype(str)
        
        # Create CONTACT_ID if missing
        if 'CONTACT_ID' not in df_renamed.columns:
            df_renamed['CONTACT_ID'] = range(1, len(df_renamed) + 1)
        
        # Remove any duplicate columns that might have been created
        df_renamed = df_renamed.loc[:, ~df_renamed.columns.duplicated()]
        
        # Skip add_final_columns completely to avoid DataFrame structure issues
        # self.add_final_columns(df_renamed)
        
        return df_renamed
    
    def clean_data_after_standardization(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean data after column standardization"""
        logger.info("Cleaning data after standardization")
        
        # Clean NaN values in key columns
        if 'NAME' in df.columns:
            df['NAME'] = df['NAME'].fillna('')
        if 'INVESTOR' in df.columns:
            df['INVESTOR'] = df['INVESTOR'].fillna('')
        
        # Remove rows where both NAME and INVESTOR are empty (optional cleanup)
        if 'NAME' in df.columns and 'INVESTOR' in df.columns:
            initial_count = len(df)
            df = df[~((df['NAME'].str.strip() == '') & (df['INVESTOR'].str.strip() == ''))]
            removed_count = initial_count - len(df)
            
            if removed_count > 0:
                logger.info(f"Removed {removed_count} rows with empty NAME and INVESTOR")
        
        return df
    
    def add_final_columns(self, df: pd.DataFrame) -> None:
        """Add cleaned consolidated final columns with proper data handling"""
        
        if len(df) == 0:
            return
        
        def clean_value(value):
            """Clean values to remove nan, None, etc."""
            # Handle Series by taking the first value
            if isinstance(value, pd.Series):
                if value.empty:
                    return ''
                value = value.iloc[0]
            
            if pd.isna(value) or value is None:
                return ''
            value_str = str(value).strip()
            if value_str.lower() in ['nan', 'none', 'null', '']:
                return ''
            return value_str
        
        # Full Name Final - clean and use NAME column
        if 'NAME' in df.columns:
            df['Full_Name_Final'] = df['NAME'].apply(clean_value)
        else:
            df['Full_Name_Final'] = ''
        
        # Email Final - clean and use EMAIL column
        if 'EMAIL' in df.columns:
            df['Email_Final'] = df['EMAIL'].apply(clean_value)
        else:
            df['Email_Final'] = ''
        
        # Institution Final - clean and use INVESTOR column
        if 'INVESTOR' in df.columns:
            df['Institution_Final'] = df['INVESTOR'].apply(clean_value)
        else:
            df['Institution_Final'] = ''
        
        # Job Title Final - clean and use JOB TITLE column
        if 'JOB TITLE' in df.columns:
            df['Job_Title_Final'] = df['JOB TITLE'].apply(clean_value)
        else:
            df['Job_Title_Final'] = ''
        
        # Extract First and Last names from Full Name
        def extract_first_name(full_name):
            clean_name = clean_value(full_name)
            if not clean_name:
                return ''
            name_parts = clean_name.split()
            return name_parts[0] if name_parts else ''
        
        def extract_last_name(full_name):
            clean_name = clean_value(full_name)
            if not clean_name:
                return ''
            name_parts = clean_name.split()
            return name_parts[-1] if len(name_parts) > 1 else ''
        
        # Apply name extraction
        df['First_Name_Final'] = df['Full_Name_Final'].apply(extract_first_name)
        df['Last_Name_Final'] = df['Full_Name_Final'].apply(extract_last_name)
    
    def remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicates based on name and firm combination from raw data"""
        logger.info(f"Removing duplicates from {len(df)} contacts")
        
        if len(df) == 0:
            return df
        
        # Reset index to avoid duplicate labels issue
        df_reset = df.reset_index(drop=True)
        
        # Create normalized columns for comparison
        def normalize_text(text):
            try:
                if text is None or str(text).lower() in ['nan', 'none', '']:
                    return ''
                return str(text).lower().strip()
            except:
                return ''
        
        # Create normalized versions for duplicate detection
        # Handle different column name formats from different files
        normalized_names = []
        normalized_firms = []
        
        for idx, row in df_reset.iterrows():
            # Try different name column possibilities
            name_val = ''
            if 'NAME' in row and pd.notna(row.get('NAME')):
                name_val = str(row.get('NAME', ''))
            elif 'First Name' in row and 'Last Name' in row:
                first = str(row.get('First Name', ''))
                last = str(row.get('Last Name', ''))
                name_val = f"{first} {last}".strip()
            elif 'Key Contact' in row and pd.notna(row.get('Key Contact')):
                name_val = str(row.get('Key Contact', ''))
            
            # Try different firm column possibilities
            firm_val = ''
            if 'INVESTOR' in row and pd.notna(row.get('INVESTOR')):
                firm_val = str(row.get('INVESTOR', ''))
            elif 'Institution Name' in row and pd.notna(row.get('Institution Name')):
                firm_val = str(row.get('Institution Name', ''))
            
            name_norm = normalize_text(name_val)
            firm_norm = normalize_text(firm_val)
            normalized_names.append(name_norm)
            normalized_firms.append(firm_norm)
        
        # Track which rows to keep (first occurrence of each name+firm combination)
        seen_combinations = set()
        rows_to_keep = []
        
        for idx in range(len(df_reset)):
            combination = (normalized_names[idx], normalized_firms[idx])
            if combination not in seen_combinations:
                seen_combinations.add(combination)
                rows_to_keep.append(idx)
        
        logger.info(f"Found {len(seen_combinations)} unique combinations out of {len(df_reset)} total rows")
        
        # Create deduplicated dataframe
        df_deduped = df_reset.iloc[rows_to_keep].copy()
        
        duplicates_removed = len(df) - len(df_deduped)
        logger.info(f"Removed {duplicates_removed} duplicates, {len(df_deduped)} unique contacts remain")
        
        return df_deduped
    
    def extract_email_patterns_by_firm(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Extract email patterns from the full dataset, organized by firm"""
        logger.info("Extracting email patterns by firm from full dataset")
        
        firm_patterns = defaultdict(list)
        
        for _, row in df.iterrows():
            firm = str(row.get('INVESTOR', '')).strip()
            email = str(row.get('EMAIL', '')).strip()
            name = str(row.get('NAME', '')).strip()
            
            if not firm or not email or '@' not in email:
                continue
            
            # Extract domain
            try:
                domain = email.split('@')[1].lower()
                
                # Analyze email structure relative to name
                if name:
                    # Try to identify pattern
                    email_local = email.split('@')[0].lower()
                    name_parts = name.lower().replace('.', '').replace('-', '').split()
                    
                    if len(name_parts) >= 2:
                        first_name = name_parts[0]
                        last_name = name_parts[-1]
                        
                        # Common patterns
                        patterns = []
                        if email_local == f"{first_name}.{last_name}":
                            patterns.append(f"firstname.lastname@{domain}")
                        elif email_local == f"{first_name[0]}{last_name}":
                            patterns.append(f"firstinitiallastname@{domain}")
                        elif email_local == f"{first_name}{last_name[0]}":
                            patterns.append(f"firstnamelastinitial@{domain}")
                        elif email_local == f"{first_name}_{last_name}":
                            patterns.append(f"firstname_lastname@{domain}")
                        elif email_local == f"{first_name}{last_name}":
                            patterns.append(f"firstnamelastname@{domain}")
                        
                        # Store patterns for this firm
                        for pattern in patterns:
                            if pattern not in firm_patterns[firm]:
                                firm_patterns[firm].append(pattern)
                
            except Exception as e:
                continue
        
        # Convert to regular dict and log results
        final_patterns = dict(firm_patterns)
        logger.info(f"Extracted email patterns for {len(final_patterns)} firms")
        for firm, patterns in list(final_patterns.items())[:5]:  # Show first 5 as example
            logger.info(f"  {firm}: {patterns}")
        
        return final_patterns
    
    def create_tier1_filter(self) -> Dict[str, Any]:
        """Create Tier 1 filter configuration for key contacts (no investment team requirement)"""
        return {
            'name': 'Tier 1 - Key Contacts',
            'description': 'Senior decision makers and key investment professionals',
            'job_title_pattern': r".*\b(cio|c\.i\.o\.|c\.i\.o|chief\s+investment\s+officer|deputy\s+chief\s+investment\s+officer|deputy\s+cio|head\s+of\s+investments?|head\s+of\s+research|head\s+of\s+private\s+markets?|head\s+of\s+private\s+equity|investment\s+committee|investment\s+partner|managing\s+director|executive\s+director|senior\s+portfolio\s+manager|investment\s+director|portfolio\s+manager|investment\s+manager|fund\s+manager|private\s+markets?|private\s+equity|private\s+credit|private\s+debt|hedge\s+fund|hedge|alternatives?|fixed\s+income|absolute\s+return|president|vice\s+president|senior\s+vice\s+president|executive\s+vice\s+president)\b",
            'exclusion_pattern': r".*\b(operations?|hr|human\s+resources?|investor\s+relations?|client\s+relations?|marketing|sales|compliance|technology|administrator|assistant|secretary|receptionist|intern|trainee)\b",
            'require_investment_team': False,  # Key contacts don't need investment team requirement
            'priority_keywords': ['cio', 'chief investment officer', 'deputy cio', 'head of investments', 'head of private markets', 'private markets', 'private equity', 'hedge fund', 'managing director', 'executive director', 'investment director', 'portfolio manager', 'president']
        }
    
    def create_tier2_filter(self) -> Dict[str, Any]:
        """Create Tier 2 filter configuration for junior contacts (requires investment team)"""
        return {
            'name': 'Tier 2 - Junior Contacts',
            'description': 'Junior investment professionals (must be on investment team)',
            'job_title_pattern': r".*\b(director|associate\s+director|vice\s+president|vp|investment\s+analyst|research\s+analyst|portfolio\s+analyst|senior\s+analyst|investment\s+advisor|wealth\s+advisor|trust\s+officer|principal|associate|coordinator|specialist|advisor|representative|assistant\s+portfolio\s+manager|research|portfolio|investment|analyst)\b",
            'exclusion_pattern': r".*\b(operations?|hr|human\s+resources?|investor\s+relations?|client\s+relations?|marketing|sales|compliance|technology|administrator|assistant|secretary|receptionist|intern|trainee|junior|cio|c\.i\.o\.|c\.i\.o|chief\s+investment\s+officer|deputy\s+chief\s+investment\s+officer|head\s+of\s+investments?|head\s+of\s+research|head\s+of\s+private\s+markets?|investment\s+committee|investment\s+partner|managing\s+director|executive\s+director|senior\s+portfolio\s+manager|investment\s+director|president|senior\s+vice\s+president|executive\s+vice\s+president)\b",
            'require_investment_team': False,  # Temporarily disable investment team requirement for testing
            'priority_keywords': ['director', 'vice president', 'investment analyst', 'research analyst', 'associate director', 'principal', 'associate', 'portfolio', 'investment', 'research']
        }
    
    def calculate_priority(self, row: pd.Series, tier_config: Dict[str, Any]) -> int:
        """Calculate priority score for contact ranking"""
        job_title = str(row.get('JOB TITLE', '')).lower()
        priority_score = 0
        
        # Tier 1: Highest priority roles (score 150+)
        if 'cio' in job_title or 'chief investment officer' in job_title:
            priority_score += 150
        elif 'deputy chief investment officer' in job_title or 'deputy cio' in job_title:
            priority_score += 140
        elif 'head of investments' in job_title or 'head of research' in job_title:
            priority_score += 130
        elif 'head of private markets' in job_title or 'head of private equity' in job_title:
            priority_score += 125
        elif 'president' in job_title:
            priority_score += 120
        elif 'investment committee' in job_title:
            priority_score += 115
        elif 'investment partner' in job_title:
            priority_score += 110
        
        # Senior management (score 80-105)
        elif 'managing director' in job_title:
            priority_score += 105
        elif 'executive director' in job_title:
            priority_score += 100
        elif 'senior portfolio manager' in job_title or 'investment director' in job_title:
            priority_score += 95
        elif 'executive vice president' in job_title or 'senior vice president' in job_title:
            priority_score += 90
        elif 'vice president' in job_title:
            priority_score += 85
        elif 'portfolio manager' in job_title or 'investment manager' in job_title:
            priority_score += 80
        
        # Asset class expertise (score 60-75)
        if 'private markets' in job_title or 'private equity' in job_title:
            priority_score += 75
        elif 'private credit' in job_title or 'private debt' in job_title:
            priority_score += 70
        elif 'hedge fund' in job_title or 'hedge' in job_title:
            priority_score += 65
        elif 'alternatives' in job_title or 'absolute return' in job_title:
            priority_score += 60
        
        # Mid-level roles (score 30-55)
        if 'director' in job_title and 'managing' not in job_title and 'executive' not in job_title:
            priority_score += 55
        elif 'principal' in job_title:
            priority_score += 50
        elif 'investment analyst' in job_title or 'research analyst' in job_title:
            priority_score += 45
        elif 'associate director' in job_title:
            priority_score += 40
        elif 'senior analyst' in job_title:
            priority_score += 35
        elif 'associate' in job_title:
            priority_score += 30
        
        # General investment terms (score 10-25)
        if 'investment' in job_title:
            priority_score += 25
        elif 'portfolio' in job_title:
            priority_score += 20
        elif 'research' in job_title:
            priority_score += 15
        elif 'analyst' in job_title:
            priority_score += 10
        
        return priority_score
    
    def apply_tier_filter(self, df: pd.DataFrame, tier_config: Dict[str, Any], max_contacts_per_firm: int) -> pd.DataFrame:
        """Apply tier-specific filtering with firm-based limits"""
        logger.info(f"Starting {tier_config['name']} filtering on {len(df)} contacts")
        filtered_df = df.copy()
        
        # Apply job title regex filter
        job_title_regex = re.compile(tier_config['job_title_pattern'], re.IGNORECASE)
        exclusion_regex = re.compile(tier_config['exclusion_pattern'], re.IGNORECASE)
        
        def matches_tier_criteria(row):
            # Handle Series values properly
            job_title_val = row.get('JOB TITLE', '')
            role_val = row.get('ROLE', '')
            
            # Extract scalar value if it's a Series
            if isinstance(job_title_val, pd.Series):
                job_title_val = job_title_val.iloc[0] if not job_title_val.empty else ''
            if isinstance(role_val, pd.Series):
                role_val = role_val.iloc[0] if not role_val.empty else ''
            
            job_title = str(job_title_val).lower()
            role = str(role_val).lower()
            
            # Debug logging for first few rows
            if len(filtered_df) < 5:  # Only log for first few rows to avoid spam
                logger.info(f"Checking row: job_title='{job_title}', role='{role}'")
            
            # Check job title matches (must contain at least one positive term)
            title_match = job_title_regex.search(job_title)
            if not title_match:
                if len(filtered_df) < 5:
                    logger.info(f"  -> FAILED: Job title pattern match")
                return False
            
            # Check exclusions (must NOT contain any exclusion terms)
            exclusion_match = exclusion_regex.search(job_title)
            if exclusion_match:
                if len(filtered_df) < 5:
                    logger.info(f"  -> FAILED: Exclusion pattern match")
                return False
            
            # Check investment team requirement (only for Tier 2)
            if tier_config['require_investment_team']:
                if 'investment team' not in role and 'investment' not in role:
                    if len(filtered_df) < 5:
                        logger.info(f"  -> FAILED: Investment team requirement")
                    return False
            
            if len(filtered_df) < 5:
                logger.info(f"  -> PASSED: All criteria met")
            return True
        
        tier_filter = filtered_df.apply(matches_tier_criteria, axis=1)
        filtered_df = filtered_df[tier_filter]
        
        # Apply firm-based contact limits with priority ranking
        if 'INVESTOR' in filtered_df.columns and len(filtered_df) > 0:
            # Reset index to ensure clean grouping
            filtered_df = filtered_df.reset_index(drop=True)
            
            # Calculate priority scores
            priority_scores = []
            for idx, row in filtered_df.iterrows():
                score = self.calculate_priority(row, tier_config)
                priority_scores.append(score)
            
            filtered_df['priority_score'] = priority_scores
            
            # Apply firm limits manually to avoid groupby issues
            result_contacts = []
            
            # Convert to list of dictionaries for easier processing
            contacts_list = filtered_df.to_dict('records')
            
            # Group by firm manually
            firms_dict = {}
            for contact in contacts_list:
                firm_name = contact.get('INVESTOR', 'Unknown')
                if firm_name is None or str(firm_name).lower() in ['nan', 'none']:
                    firm_name = 'Unknown'
                
                if firm_name not in firms_dict:
                    firms_dict[firm_name] = []
                firms_dict[firm_name].append(contact)
            
            # Process each firm
            result_contacts = []
            for firm_name, firm_contacts in firms_dict.items():
                # Sort by priority score (descending)
                firm_contacts_sorted = sorted(firm_contacts, key=lambda x: x.get('priority_score', 0), reverse=True)
                
                # Take top N contacts for this firm
                firm_limited = firm_contacts_sorted[:max_contacts_per_firm]
                result_contacts.extend(firm_limited)
            
            # Convert back to DataFrame and ensure no duplicate columns
            if result_contacts:
                filtered_df = pd.DataFrame(result_contacts)
                # Remove duplicate columns if they exist
                filtered_df = filtered_df.loc[:, ~filtered_df.columns.duplicated()]
            else:
                filtered_df = pd.DataFrame()
            
            # Remove the temporary priority score column
            if 'priority_score' in filtered_df.columns:
                filtered_df = filtered_df.drop('priority_score', axis=1)
        
        return filtered_df
    
    def fill_missing_emails(self, df: pd.DataFrame, firm_email_patterns: Dict[str, List[str]]) -> pd.DataFrame:
        """Fill missing emails using extracted patterns"""
        logger.info(f"Filling missing emails for {len(df)} contacts")
        
        df_filled = df.copy()
        filled_count = 0
        
        for idx, row in df_filled.iterrows():
            current_email = str(row.get('EMAIL', '')).strip()
            
            # Skip if email already exists and is valid
            if current_email and '@' in current_email:
                continue
            
            firm = str(row.get('INVESTOR', '')).strip()
            name = str(row.get('NAME', '')).strip()
            
            if not firm or not name:
                continue
            
            # Get patterns for this firm
            patterns = firm_email_patterns.get(firm, [])
            if not patterns:
                continue
            
            # Try to generate email using most common pattern
            name_parts = name.lower().replace('.', '').replace('-', '').split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = name_parts[-1]
                
                # Use the first (most common) pattern for this firm
                pattern = patterns[0]
                
                try:
                    if "firstname.lastname@" in pattern:
                        domain = pattern.split('@')[1]
                        generated_email = f"{first_name}.{last_name}@{domain}"
                    elif "firstinitiallastname@" in pattern:
                        domain = pattern.split('@')[1]
                        generated_email = f"{first_name[0]}{last_name}@{domain}"
                    elif "firstnamelastinitial@" in pattern:
                        domain = pattern.split('@')[1]
                        generated_email = f"{first_name}{last_name[0]}@{domain}"
                    elif "firstname_lastname@" in pattern:
                        domain = pattern.split('@')[1]
                        generated_email = f"{first_name}_{last_name}@{domain}"
                    elif "firstnamelastname@" in pattern:
                        domain = pattern.split('@')[1]
                        generated_email = f"{first_name}{last_name}@{domain}"
                    else:
                        continue
                    
                    df_filled.at[idx, 'EMAIL'] = generated_email
                    filled_count += 1
                    
                except Exception as e:
                    continue
        
        logger.info(f"Filled {filled_count} missing emails using firm patterns")
        return df_filled
    
    def generate_output_filename(self, file_info: List[Dict], user_prefix: str = None) -> str:
        """Generate standardized output filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if len(file_info) == 1:
            # Single file - use file name as base
            base_name = Path(file_info[0]['file']).stem
            return f"{base_name}_Tiered_List_{timestamp}.xlsx"
        else:
            # Multiple files - use user prefix or default
            prefix = user_prefix or "Combined-Contacts"
            return f"{prefix}_Tiered_List_{timestamp}.xlsx"
    
    def create_excluded_firms_analysis(self, combined_df: pd.DataFrame, tier1_contacts: pd.DataFrame, tier2_contacts: pd.DataFrame) -> Dict:
        """Create analysis of completely excluded firms vs included firms"""
        logger.info("Creating excluded firms analysis")
        
        # Get all firms from combined/deduplicated data
        all_firms_after_dedup = set()
        if 'INVESTOR' in combined_df.columns and len(combined_df) > 0:
            all_firms_after_dedup = set(combined_df['INVESTOR'].dropna().unique())
        
        # Get firms that made it into either tier
        included_firms = set()
        if len(tier1_contacts) > 0 and 'INVESTOR' in tier1_contacts.columns:
            included_firms.update(tier1_contacts['INVESTOR'].dropna().unique())
        if len(tier2_contacts) > 0 and 'INVESTOR' in tier2_contacts.columns:
            included_firms.update(tier2_contacts['INVESTOR'].dropna().unique())
        
        # Find completely excluded firms (had contacts after dedup but none in final tiers)
        completely_excluded_firms = all_firms_after_dedup - included_firms
        
        # Get all contacts from completely excluded firms
        excluded_firm_contacts = pd.DataFrame()
        if len(completely_excluded_firms) > 0 and len(combined_df) > 0:
            excluded_mask = combined_df['INVESTOR'].isin(completely_excluded_firms)
            excluded_firm_contacts = combined_df[excluded_mask].copy()
            
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
    
    def process_contacts(self, user_prefix: str = None, enable_firm_exclusion: bool = False) -> str:
        """Main processing function"""
        logger.info("Starting consolidated tiered filtering process")
        
        # Set firm exclusion setting
        self.enable_firm_exclusion = enable_firm_exclusion
        
        # Load firm exclusion list if enabled
        if self.enable_firm_exclusion:
            self.load_firm_exclusion_list()
        
        # Load and combine input files
        combined_df, file_info = self.load_and_combine_input_files()
        logger.info(f"After load_and_combine: {len(combined_df)} contacts")
        
        # Remove duplicates immediately after combination (before other processing)
        combined_df = self.remove_duplicates(combined_df)
        logger.info(f"After remove_duplicates: {len(combined_df)} contacts")
        
        # Standardize column names
        combined_df = self.standardize_column_names(combined_df)
        logger.info(f"After standardize_column_names: {len(combined_df)} contacts")
        
        # Clean data after standardization (no longer needed before deduplication)
        combined_df = self.clean_data_after_standardization(combined_df)
        logger.info(f"After clean_data: {len(combined_df)} contacts")
        
        # Apply firm exclusion if enabled
        if self.enable_firm_exclusion:
            combined_df = self.apply_firm_exclusion(combined_df)
            logger.info(f"After firm_exclusion: {len(combined_df)} contacts")
        
        # Extract email patterns from full dataset
        firm_email_patterns = self.extract_email_patterns_by_firm(combined_df)
        
        # Create tier configurations
        tier1_config = self.create_tier1_filter()
        tier2_config = self.create_tier2_filter()
        
        # Apply Tier 1 filtering (max 10 per firm)
        logger.info("Applying Tier 1 filtering...")
        tier1_contacts = self.apply_tier_filter(combined_df, tier1_config, max_contacts_per_firm=10)
        logger.info(f"Tier 1 result: {len(tier1_contacts)} contacts")
        
        # Apply Tier 2 filtering (max 6 per firm, excluding Tier 1 contacts)
        logger.info("Applying Tier 2 filtering...")
        # Remove Tier 1 contacts from consideration for Tier 2 using multiple methods
        if len(tier1_contacts) > 0:
            # Method 1: Remove by CONTACT_ID if available
            if 'CONTACT_ID' in tier1_contacts.columns and 'CONTACT_ID' in combined_df.columns:
                tier1_ids = set(tier1_contacts['CONTACT_ID'].tolist())
                tier2_candidates = combined_df[~combined_df['CONTACT_ID'].isin(tier1_ids)]
            else:
                # Method 2: Remove by name + firm combination
                tier1_combinations = set()
                for _, row in tier1_contacts.iterrows():
                    name = str(row.get('NAME', '')).lower().strip()
                    firm = str(row.get('INVESTOR', '')).lower().strip()
                    tier1_combinations.add((name, firm))
                
                # Filter out Tier 1 combinations from candidates
                tier2_candidates = []
                for _, row in combined_df.iterrows():
                    name = str(row.get('NAME', '')).lower().strip()
                    firm = str(row.get('INVESTOR', '')).lower().strip()
                    if (name, firm) not in tier1_combinations:
                        tier2_candidates.append(row)
                
                tier2_candidates = pd.DataFrame(tier2_candidates) if tier2_candidates else pd.DataFrame()
        else:
            tier2_candidates = combined_df
        
        tier2_contacts = self.apply_tier_filter(tier2_candidates, tier2_config, max_contacts_per_firm=6)
        logger.info(f"Tier 2 result: {len(tier2_contacts)} contacts")
        
        # Final duplicate check between tiers
        if len(tier1_contacts) > 0 and len(tier2_contacts) > 0:
            # Remove any remaining duplicates between tiers
            tier1_combinations = set()
            for _, row in tier1_contacts.iterrows():
                name = str(row.get('NAME', '')).lower().strip()
                firm = str(row.get('INVESTOR', '')).lower().strip()
                tier1_combinations.add((name, firm))
            
            tier2_final = []
            duplicates_found = 0
            for _, row in tier2_contacts.iterrows():
                name = str(row.get('NAME', '')).lower().strip()
                firm = str(row.get('INVESTOR', '')).lower().strip()
                if (name, firm) not in tier1_combinations:
                    tier2_final.append(row)
                else:
                    duplicates_found += 1
            
            tier2_contacts = pd.DataFrame(tier2_final) if tier2_final else pd.DataFrame()
            if duplicates_found > 0:
                logger.info(f"Removed {duplicates_found} remaining duplicates between tiers")
                logger.info(f"Final Tier 2 result: {len(tier2_contacts)} contacts")
        
        # Fill missing emails for both tiers
        tier1_contacts = self.fill_missing_emails(tier1_contacts, firm_email_patterns)
        tier2_contacts = self.fill_missing_emails(tier2_contacts, firm_email_patterns)
        
        # Generate output filename
        output_filename = self.generate_output_filename(file_info, user_prefix)
        output_path = self.output_folder / output_filename
        
        # Calculate comprehensive metrics
        total_input = sum(f['contacts'] for f in file_info)
        duplicates_removed = total_input - len(combined_df)
        total_before_filtering = len(combined_df)
        total_after_filtering = len(tier1_contacts) + len(tier2_contacts)
        contacts_filtered_out = total_before_filtering - total_after_filtering
        
        # Count emails filled (handle non-string values)
        def count_filled_emails(df):
            if len(df) == 0:
                return 0
            count = 0
            for _, row in df.iterrows():
                email = row.get('EMAIL', '')
                if email and str(email).strip() and str(email).strip().lower() not in ['nan', 'none', '']:
                    count += 1
            return count
        
        tier1_emails_filled = count_filled_emails(tier1_contacts)
        tier2_emails_filled = count_filled_emails(tier2_contacts)
        
        # Create excluded firms analysis
        excluded_firms_analysis = self.create_excluded_firms_analysis(combined_df, tier1_contacts, tier2_contacts)
        
        # Create Excel output with organized columns
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            # Organize columns for better readability and clean data
            def organize_columns(df):
                if len(df) == 0:
                    return df
                
                # Clean all data in the dataframe before output
                for col in df.columns:
                    if df[col].dtype == 'object':  # String columns
                        df[col] = df[col].apply(lambda x: '' if pd.isna(x) or str(x).lower().strip() in ['nan', 'none', 'null'] else str(x).strip())
                    else:
                        df[col] = df[col].fillna('')
                
                # Define preferred column order with clean final columns first
                priority_columns = [
                    'First_Name_Final', 'Last_Name_Final', 'Full_Name_Final', 'Email_Final',
                    'Institution_Final', 'Job_Title_Final', 'CONTACT_ID', 'source_file'
                ]
                
                # Get columns that exist in the dataframe
                available_priority = [col for col in priority_columns if col in df.columns]
                remaining_columns = [col for col in df.columns if col not in priority_columns]
                
                # Reorder columns with consolidated ones first
                ordered_columns = available_priority + remaining_columns
                return df[ordered_columns]
            
            # Tier 1 sheet with organized columns
            tier1_organized = organize_columns(tier1_contacts)
            tier1_organized.to_excel(writer, sheet_name='Tier1_Key_Contacts', index=False)
            
            # Tier 2 sheet with organized columns
            tier2_organized = organize_columns(tier2_contacts)
            tier2_organized.to_excel(writer, sheet_name='Tier2_Junior_Contacts', index=False)
            
            # Calculate firm/institution counts
            # Unique firms after deduplication
            unique_firms_after_dedup = combined_df['INVESTOR'].nunique() if 'INVESTOR' in combined_df.columns and len(combined_df) > 0 else 0
            
            # Calculate tier-specific firm counts
            tier1_firms = tier1_contacts['INVESTOR'].nunique() if 'INVESTOR' in tier1_contacts.columns and len(tier1_contacts) > 0 else 0
            tier2_firms = tier2_contacts['INVESTOR'].nunique() if 'INVESTOR' in tier2_contacts.columns and len(tier2_contacts) > 0 else 0
            
            # Calculate unique firms across both tiers (avoiding double counting)
            if len(tier1_contacts) > 0 and len(tier2_contacts) > 0 and 'INVESTOR' in tier1_contacts.columns and 'INVESTOR' in tier2_contacts.columns:
                all_tier_firms = set(tier1_contacts['INVESTOR'].dropna().unique()) | set(tier2_contacts['INVESTOR'].dropna().unique())
                total_firms_filtered = len(all_tier_firms)
            else:
                total_firms_filtered = tier1_firms + tier2_firms
            
            # Comprehensive summary sheet
            summary_data = {
                'Step': [
                    '📁 Input Files',
                    '📊 Total Raw Contacts',
                    '🔄 After Deduplication',
                    '🏢 Unique Firms/Institutions After Deduplication',
                    '❌ Duplicates Removed',
                    '✅ Unique Contacts for Filtering',
                    '',
                    '🎯 Tier 1 (Key Contacts)',
                    '🏢 Tier 1 Firms/Institutions',
                    '🎯 Tier 2 (Junior Contacts)',
                    '🏢 Tier 2 Firms/Institutions', 
                    '📈 Total Filtered Contacts',
                    '🏢 Total Firms/Institutions (Both Tiers)',
                    '📉 Contacts Filtered Out',
                    '📊 Retention Rate',
                    '',
                    '📧 Email Patterns Extracted',
                    '📧 Tier 1 Emails Available',
                    '📧 Tier 2 Emails Available',
                    '📧 Total Emails Available',
                    '',
                    '📅 Processing Date'
                ],
                'Count': [
                    len(file_info),
                    f"{total_input:,}",
                    f"{len(combined_df):,}",
                    f"{unique_firms_after_dedup:,}",
                    f"{duplicates_removed:,}",
                    f"{total_before_filtering:,}",
                    '',
                    f"{len(tier1_contacts):,}",
                    f"{tier1_firms:,}",
                    f"{len(tier2_contacts):,}",
                    f"{tier2_firms:,}",
                    f"{total_after_filtering:,}",
                    f"{total_firms_filtered:,}",
                    f"{contacts_filtered_out:,}",
                    f"{(total_after_filtering/total_before_filtering)*100:.1f}%",
                    '',
                    f"{len(firm_email_patterns):,} firms",
                    f"{tier1_emails_filled:,}",
                    f"{tier2_emails_filled:,}",
                    f"{tier1_emails_filled + tier2_emails_filled:,}",
                    '',
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Processing_Summary', index=False)
            
            # Detailed file breakdown
            file_breakdown_data = []
            for f in file_info:
                file_breakdown_data.append({
                    'File_Name': f['file'],
                    'Contacts': f['contacts'],
                    'Percentage': f"{(f['contacts']/total_input)*100:.1f}%"
                })
            
            file_details_df = pd.DataFrame(file_breakdown_data)
            file_details_df.to_excel(writer, sheet_name='Input_File_Details', index=False)
            
            # Email patterns summary
            if firm_email_patterns:
                pattern_data = []
                for firm, patterns in list(firm_email_patterns.items())[:20]:  # Top 20 firms
                    pattern_data.append({
                        'Firm': firm,
                        'Email_Patterns': ', '.join(patterns),
                        'Pattern_Count': len(patterns)
                    })
                
                if pattern_data:
                    patterns_df = pd.DataFrame(pattern_data)
                    patterns_df.to_excel(writer, sheet_name='Email_Patterns_Sample', index=False)
            
            # Excluded firms analysis
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
                        f"{(excluded_firms_analysis['excluded_firm_contacts_count'] / total_before_filtering * 100):.1f}%" if total_before_filtering > 0 else "0.0%"
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
                    excluded_contacts_organized = organize_columns(excluded_contacts_df.copy())
                    excluded_contacts_organized.to_excel(writer, sheet_name='Excluded_Firm_Contacts', index=False)
        
        # Print comprehensive summary to console
        print(f"\n{'='*70}")
        print("📊 COMPREHENSIVE PROCESSING SUMMARY")
        print(f"{'='*70}")
        
        print(f"\n📁 INPUT FILES ({len(file_info)} files):")
        for f in file_info:
            percentage = (f['contacts']/total_input)*100
            print(f"   • {f['file']}: {f['contacts']:,} contacts ({percentage:.1f}%)")
        
        print(f"\n🔄 PROCESSING PIPELINE:")
        print(f"   📊 Total Raw Contacts: {total_input:,}")
        print(f"   ❌ Duplicates Removed: {duplicates_removed:,}")
        print(f"   ✅ Unique Contacts: {len(combined_df):,}")
        print(f"   📉 Filtered Out: {contacts_filtered_out:,}")
        print(f"   📈 Final Qualified: {total_after_filtering:,}")
        print(f"   📊 Retention Rate: {(total_after_filtering/total_before_filtering)*100:.1f}%")
        
        print(f"\n🎯 TIERED RESULTS:")
        print(f"   🥇 Tier 1 (Key): {len(tier1_contacts):,} contacts")
        print(f"   🥈 Tier 2 (Junior): {len(tier2_contacts):,} contacts")
        print(f"   📧 Total Emails: {tier1_emails_filled + tier2_emails_filled:,} available")
        
        print(f"\n📧 EMAIL INTELLIGENCE:")
        print(f"   🏢 Firms with Patterns: {len(firm_email_patterns):,}")
        print(f"   📧 Tier 1 Emails: {tier1_emails_filled:,}")
        print(f"   📧 Tier 2 Emails: {tier2_emails_filled:,}")
        
        logger.info(f"Processing complete! Output saved to: {output_path}")
        logger.info(f"Final result: {total_after_filtering:,} qualified contacts ({len(tier1_contacts):,} Tier 1 + {len(tier2_contacts):,} Tier 2)")
        
        return str(output_path)

def main():
    """Main execution function"""
    print("🚀 CONSOLIDATED TIERED CONTACT FILTER")
    print("=" * 60)
    
    # Get user input for prefix if multiple files
    input_folder = Path("input")
    excel_files = list(input_folder.glob("*.xlsx"))
    
    user_prefix = None
    if len(excel_files) > 1:
        print(f"Found {len(excel_files)} input files:")
        for i, file in enumerate(excel_files, 1):
            print(f"  {i}. {file.name}")
        
        print("\nSince multiple files were found, please provide a prefix for the output filename.")
        print("Examples: 'Institutional-Contacts', 'Family-Office-Contacts', 'Combined-Contacts'")
        user_prefix = input("Enter output prefix (or press Enter for 'Combined-Contacts'): ").strip()
        
        if not user_prefix:
            user_prefix = "Combined-Contacts"
    
    # Check for firm exclusion option
    exclusion_file = input_folder / "firm exclusion.csv"
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
    
    # Initialize and run filter
    filter_tool = ConsolidatedTieredFilter()
    
    try:
        output_file = filter_tool.process_contacts(user_prefix, enable_firm_exclusion)
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS! Consolidated filtering completed.")
        print(f"📊 Output file: {output_file}")
        print("\n📋 Output includes:")
        print("   • Tier1_Key_Contacts: Senior decision makers (no investment team requirement)")
        print("   • Tier2_Junior_Contacts: Junior professionals (investment team required)")
        print("   • Processing_Summary: Statistics and metrics")
        print("   • Input_Files: Source file details")
        print("   • Excluded_Firms_Summary: Analysis of completely excluded firms")
        print("   • Excluded_Firms_List: List of firms with zero contacts included")
        print("   • Included_Firms_List: List of firms with contacts included")
        print("   • Excluded_Firm_Contacts: All contacts from excluded firms")
        print("   • Email pattern extraction and missing email filling applied")
        
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
