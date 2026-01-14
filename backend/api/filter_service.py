"""
Service layer wrapping TieredFilter for web app use.
"""
import sys
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging
import pandas as pd
import zipfile
import io

# Add parent directory to path to import tiered_filter
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tiered_filter import TieredFilter
from api.tier_config_utils import (
    create_tier_config_from_keywords,
    get_default_tier1_keywords,
    get_default_tier2_keywords,
    get_default_tier3_keywords
)

logger = logging.getLogger(__name__)

# Firm type groupings for separation feature
FIRM_TYPE_GROUPS = {
    'Insurance': [
        'insurance company',
        'insurance',
    ],
    'Wealth_FamilyOffice': [
        'wealth manager',
        'multi family office',
        'single family office',
        'family office',
        'mfo',
        'sfo',
    ],
    'Endowments_Foundations': [
        'endowment',
        'foundation',
    ],
    'Pension_Funds': [
        'public pension fund',
        'private pension fund',
        'pension fund',
        'pension',
        'public pension',
        'private pension',
    ],
    'Funds_of_Funds': [
        'fund of funds',
        'fund of hedge funds',
        'funds of funds',
        'fof',
        'fohf',
    ],
}

class FilterService:
    """Service for processing contacts with TieredFilter"""

    def __init__(self, input_folder: str, output_folder: str):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.filter = TieredFilter(
            input_folder=str(self.input_folder),
            output_folder=str(self.output_folder)
        )

    def _classify_firm_type(self, firm_type_value: str) -> str:
        """Classify a firm type value into one of the 6 groups"""
        if pd.isna(firm_type_value) or not firm_type_value:
            return 'Other'

        firm_type_lower = str(firm_type_value).lower().strip()

        # Check each group's keywords
        for group_name, keywords in FIRM_TYPE_GROUPS.items():
            for keyword in keywords:
                if keyword in firm_type_lower:
                    return group_name

        return 'Other'

    def _separate_by_firm_type(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Separate a dataframe into 6 groups based on FIRM TYPE field"""
        # Initialize empty dataframes for each group
        groups = {
            'Insurance': pd.DataFrame(),
            'Wealth_FamilyOffice': pd.DataFrame(),
            'Endowments_Foundations': pd.DataFrame(),
            'Pension_Funds': pd.DataFrame(),
            'Funds_of_Funds': pd.DataFrame(),
            'Other': pd.DataFrame(),
        }

        if df is None or len(df) == 0:
            return groups

        # Find the FIRM TYPE column (may have variations)
        firm_type_col = None
        for col in df.columns:
            if col.upper().replace('_', ' ').strip() in ['FIRM TYPE', 'FIRMTYPE', 'FIRM_TYPE']:
                firm_type_col = col
                break

        if firm_type_col is None:
            logger.warning("No FIRM TYPE column found, all contacts will go to 'Other' group")
            groups['Other'] = df.copy()
            return groups

        # Classify each row
        df_copy = df.copy()
        df_copy['_firm_type_group'] = df_copy[firm_type_col].apply(self._classify_firm_type)

        # Split into groups
        for group_name in groups.keys():
            mask = df_copy['_firm_type_group'] == group_name
            group_df = df_copy[mask].drop(columns=['_firm_type_group'])
            groups[group_name] = group_df
            logger.info(f"Firm type group '{group_name}': {len(group_df)} contacts")

        return groups
    
    def process_contacts(
        self,
        uploaded_files: list,
        settings: Dict[str, Any],
        job_id: str,
        original_filenames: list = None,
        cancel_event: Optional[threading.Event] = None
    ) -> Dict[str, Any]:
        """
        Process contacts with given settings.
        
        Args:
            uploaded_files: List of file paths to process
            settings: Configuration settings dict
            job_id: Job ID for output filename
            original_filenames: List of original filenames (for display in analytics)
            cancel_event: Optional threading.Event to signal cancellation
            
        Returns:
            Dict with output_path and analytics
            
        Raises:
            RuntimeError: If cancellation is requested
        """
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        # Configure filter instance
        logger.info(f"Job {job_id}: Configuring filter settings")
        self.filter.enable_firm_exclusion = settings.get("firmExclusion", False)
        self.filter.enable_contact_inclusion = settings.get("contactInclusion", False)
        self.filter.enable_find_emails = settings.get("findEmails", True)
        self.filter.tier1_limit = settings.get("tier1Limit", 10)
        self.filter.tier2_limit = settings.get("tier2Limit", 6)
        logger.info(f"Job {job_id}: Firm exclusion={self.filter.enable_firm_exclusion}, Contact inclusion={self.filter.enable_contact_inclusion}, Find emails={self.filter.enable_find_emails}")
        
        # Set input folder to uploaded files location
        # Copy files to input folder temporarily
        logger.info(f"Job {job_id}: Copying {len(uploaded_files)} file(s) to temp folder")
        temp_input_folder = self.input_folder / job_id
        temp_input_folder.mkdir(parents=True, exist_ok=True)
        
        import shutil
        for file_path in uploaded_files:
            shutil.copy2(file_path, temp_input_folder / Path(file_path).name)
            logger.debug(f"Job {job_id}: Copied {Path(file_path).name} to temp folder")
        
        # Temporarily set input folder
        original_input_folder = self.filter.input_folder
        self.filter.input_folder = temp_input_folder
        
        try:
            # Check for cancellation
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Job cancelled")
            
            # Load exclusion/inclusion lists if enabled
            # First check for inline lists from settings, then fall back to CSV files
            logger.info(f"Job {job_id}: Loading exclusion/inclusion lists")
            if self.filter.enable_firm_exclusion:
                # Check for inline exclusion list
                firm_exclusion_list = settings.get("firmExclusionList", "")
                if firm_exclusion_list and firm_exclusion_list.strip():
                    self._load_firm_exclusion_from_string(firm_exclusion_list)
                else:
                    self.filter.load_firm_exclusion_list()
            
            if self.filter.enable_contact_inclusion:
                # Check for inline inclusion list
                contact_inclusion_list = settings.get("contactInclusionList", "")
                if contact_inclusion_list and contact_inclusion_list.strip():
                    self._load_contact_inclusion_from_string(contact_inclusion_list)
                else:
                    self.filter.load_contact_inclusion_list()
            
            # Handle firm inclusion (new feature)
            firm_inclusion_list = settings.get("firmInclusionList", "")
            if firm_inclusion_list and firm_inclusion_list.strip():
                self._load_firm_inclusion_from_string(firm_inclusion_list)
            
            # Handle contact exclusion (new feature)
            contact_exclusion_list = settings.get("contactExclusionList", "")
            if contact_exclusion_list and contact_exclusion_list.strip():
                self._load_contact_exclusion_from_string(contact_exclusion_list)
            
            # Check for cancellation after loading lists
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Job cancelled")
            
            # Process contacts
            include_all_firms = settings.get("includeAllFirms", False)
            user_prefix = settings.get("userPrefix", "Combined-Contacts")
            
            # Generate output filename
            from datetime import datetime
            import re
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize user prefix for filename (remove invalid characters)
            sanitized_prefix = re.sub(r'[<>:"/\\|?*]', '_', user_prefix).strip()
            if not sanitized_prefix:
                sanitized_prefix = "Combined-Contacts"
            output_filename = f"{sanitized_prefix}_{timestamp}.xlsx"
            
            # Create mapping from UUID filenames to original filenames
            filename_mapping = {}
            if original_filenames and len(original_filenames) == len(uploaded_files):
                for uuid_path, original_name in zip(uploaded_files, original_filenames):
                    uuid_filename = Path(uuid_path).name
                    filename_mapping[uuid_filename] = original_name
                    logger.info(f"Created filename mapping: {uuid_filename} -> {original_name}")
            else:
                logger.warning(f"Filename mapping skipped: original_filenames={len(original_filenames) if original_filenames else 0}, uploaded_files={len(uploaded_files)}")
            
            # Call the main processing method
            # We need to replicate the process_contacts logic but extract analytics
            result = self._process_with_analytics(
                settings=settings,
                include_all_firms=include_all_firms,
                user_prefix=user_prefix,
                output_filename=output_filename,
                filename_mapping=filename_mapping,
                cancel_event=cancel_event,
                job_id=job_id
            )
            
            return result
            
        finally:
            # Restore original input folder
            self.filter.input_folder = original_input_folder
            # Cleanup temp folder
            try:
                shutil.rmtree(temp_input_folder)
            except Exception as e:
                logger.warning(f"Could not cleanup temp folder: {e}")
    
    def _load_firm_exclusion_from_string(self, firm_list: str) -> None:
        """Load firm exclusion list from newline-separated string"""
        excluded_firms = set()
        excluded_firms_normalized = set()
        
        for line in firm_list.split('\n'):
            firm_name = line.strip()
            if firm_name:
                normalized_name = firm_name.lower().strip()
                excluded_firms_normalized.add(normalized_name)
                excluded_firms.add(firm_name.strip())
        
        self.filter.excluded_firms = excluded_firms
        self.filter.excluded_firms_normalized = excluded_firms_normalized
        logger.info(f"Loaded {len(excluded_firms)} firms from inline exclusion list")
    
    def _load_firm_inclusion_from_string(self, firm_list: str) -> None:
        """Load firm inclusion list from newline-separated string"""
        if not hasattr(self.filter, 'included_firms'):
            self.filter.included_firms = set()
            self.filter.included_firms_normalized = set()
        
        for line in firm_list.split('\n'):
            firm_name = line.strip()
            if firm_name:
                normalized_name = firm_name.lower().strip()
                self.filter.included_firms_normalized.add(normalized_name)
                self.filter.included_firms.add(firm_name.strip())
        
        logger.info(f"Loaded {len(self.filter.included_firms)} firms from inline inclusion list")
    
    def _load_contact_inclusion_from_string(self, contact_list: str) -> None:
        """Load contact inclusion list from string (format: Name|Firm, newline-separated)"""
        included_contacts = set()
        included_contacts_normalized = set()
        
        for line in contact_list.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Parse format: Name|Firm or Name, Firm
            if '|' in line:
                parts = line.split('|', 1)
            elif ',' in line:
                parts = line.split(',', 1)
            else:
                continue  # Skip invalid format
            
            if len(parts) == 2:
                full_name = parts[0].strip()
                firm_name = parts[1].strip()
                if full_name and firm_name:
                    normalized_name = full_name.lower().strip()
                    normalized_firm = firm_name.lower().strip()
                    included_contacts_normalized.add((normalized_name, normalized_firm))
                    included_contacts.add((full_name, firm_name))
        
        self.filter.included_contacts = included_contacts
        self.filter.included_contacts_normalized = included_contacts_normalized
        logger.info(f"Loaded {len(included_contacts)} contacts from inline inclusion list")
    
    def _load_contact_exclusion_from_string(self, contact_list: str) -> None:
        """Load contact exclusion list from string (format: Name|Firm, newline-separated)"""
        if not hasattr(self.filter, 'excluded_contacts'):
            self.filter.excluded_contacts = set()
            self.filter.excluded_contacts_normalized = set()
        
        for line in contact_list.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Parse format: Name|Firm or Name, Firm
            if '|' in line:
                parts = line.split('|', 1)
            elif ',' in line:
                parts = line.split(',', 1)
            else:
                continue  # Skip invalid format
            
            if len(parts) == 2:
                full_name = parts[0].strip()
                firm_name = parts[1].strip()
                if full_name and firm_name:
                    normalized_name = full_name.lower().strip()
                    normalized_firm = firm_name.lower().strip()
                    self.filter.excluded_contacts_normalized.add((normalized_name, normalized_firm))
                    self.filter.excluded_contacts.add((full_name, firm_name))
        
        logger.info(f"Loaded {len(self.filter.excluded_contacts)} contacts from inline exclusion list")
    
    def _process_with_analytics(
        self,
        settings: Dict[str, Any],
        include_all_firms: bool,
        user_prefix: str,
        output_filename: str,
        filename_mapping: Optional[Dict[str, str]] = None,
        cancel_event: Optional[threading.Event] = None,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process contacts and extract analytics"""
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        # Clean output folder
        logger.info(f"Job {job_id}: Cleaning and archiving output folder")
        self.filter.clean_and_archive_output()
        
        # Load and combine input files
        logger.info(f"Job {job_id}: Loading and combining input files")
        combined_df, file_info = self.filter.load_and_combine_input_files()
        logger.info(f"Job {job_id}: Loaded {len(combined_df)} total rows from {len(file_info)} file(s)")
        
        # Check for cancellation after loading files
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        # Map UUID filenames to original filenames for display
        if filename_mapping:
            for info in file_info:
                uuid_filename = info.get('file', '')
                # Try exact match first
                if uuid_filename in filename_mapping:
                    info['file'] = filename_mapping[uuid_filename]
                    logger.info(f"Mapped file name: {uuid_filename} -> {filename_mapping[uuid_filename]}")
                else:
                    # Try matching just the filename part (in case of path differences)
                    uuid_name_only = Path(uuid_filename).name if uuid_filename else ''
                    if uuid_name_only in filename_mapping:
                        info['file'] = filename_mapping[uuid_name_only]
                        logger.info(f"Mapped file name: {uuid_name_only} -> {filename_mapping[uuid_name_only]}")
                    else:
                        logger.warning(f"Could not map filename: {uuid_filename} (not found in mapping)")
        
        # Standardize columns
        logger.info(f"Job {job_id}: Standardizing columns")
        standardized_df = self.filter.standardize_columns(combined_df)
        logger.info(f"Job {job_id}: Standardized {len(standardized_df)} rows")
        
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        # Remove duplicates
        logger.info(f"Job {job_id}: Removing duplicates")
        deduplicated_df = self.filter.remove_duplicates(standardized_df)
        dedup_count = len(deduplicated_df)
        logger.info(f"Job {job_id}: After deduplication: {dedup_count} rows (removed {len(standardized_df) - dedup_count} duplicates)")
        
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        # Apply firm exclusion if enabled
        if self.filter.enable_firm_exclusion:
            logger.info(f"Job {job_id}: Applying firm exclusion to {len(deduplicated_df)} contacts")
            self.filter.pre_exclusion_count = len(deduplicated_df)
            deduplicated_df = self.filter.apply_firm_exclusion(deduplicated_df)
            logger.info(f"Job {job_id}: After firm exclusion: {len(deduplicated_df)} contacts remain")
        
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        # Apply firm inclusion (only include firms in the list)
        if hasattr(self.filter, 'included_firms_normalized') and self.filter.included_firms_normalized:
            logger.info(f"Applying firm inclusion to {len(deduplicated_df)} contacts")
            if 'INVESTOR' in deduplicated_df.columns:
                def is_firm_included(firm_name):
                    if pd.isna(firm_name) or firm_name == '':
                        return False
                    normalized_firm = str(firm_name).lower().strip()
                    return normalized_firm in self.filter.included_firms_normalized
                
                mask = deduplicated_df['INVESTOR'].apply(is_firm_included)
                deduplicated_df = deduplicated_df[mask].copy()
                logger.info(f"After firm inclusion: {len(deduplicated_df)} contacts remain")
        
        # Apply contact exclusion (remove specific contacts)
        if hasattr(self.filter, 'excluded_contacts_normalized') and self.filter.excluded_contacts_normalized:
            logger.info(f"Applying contact exclusion to {len(deduplicated_df)} contacts")
            if 'NAME' in deduplicated_df.columns and 'INVESTOR' in deduplicated_df.columns:
                def is_contact_excluded(row):
                    name = str(row.get('NAME', '')).lower().strip()
                    firm = str(row.get('INVESTOR', '')).lower().strip()
                    return (name, firm) in self.filter.excluded_contacts_normalized
                
                mask = ~deduplicated_df.apply(is_contact_excluded, axis=1)
                excluded_count = len(deduplicated_df) - len(deduplicated_df[mask])
                deduplicated_df = deduplicated_df[mask].copy()
                logger.info(f"Excluded {excluded_count} contacts from exclusion list")
        
        # Apply field filters (country, city, asset class, firm type, etc.)
        field_filters = settings.get("fieldFilters", [])
        if field_filters:
            logger.info(f"Applying {len(field_filters)} field filters to {len(deduplicated_df)} contacts")
            initial_count = len(deduplicated_df)
            
            for field_filter in field_filters:
                field_name = field_filter.get("field", "")
                filter_values = field_filter.get("values", [])
                
                if not field_name or field_name not in deduplicated_df.columns:
                    logger.warning(f"Field '{field_name}' not found in data, skipping filter")
                    continue
                
                if not filter_values:
                    # Empty values list means no filter (include all)
                    continue
                
                # Normalize filter values for case-insensitive matching
                normalized_filter_values = {str(v).lower().strip() for v in filter_values if v}
                
                def matches_field_filter(row):
                    field_value = str(row.get(field_name, '')).lower().strip()
                    return field_value in normalized_filter_values
                
                mask = deduplicated_df.apply(matches_field_filter, axis=1)
                filtered_count = mask.sum()
                deduplicated_df = deduplicated_df[mask].copy()
                logger.info(f"Field filter '{field_name}': {filtered_count} contacts match {len(filter_values)} values")
            
            final_count = len(deduplicated_df)
            excluded_by_fields = initial_count - final_count
            if excluded_by_fields > 0:
                logger.info(f"Field filters excluded {excluded_by_fields} contacts ({initial_count} -> {final_count})")
        
        # Apply tier filtering - use custom configs if provided, otherwise defaults
        tier1_filters = settings.get("tier1Filters")
        tier2_filters = settings.get("tier2Filters")
        
        if tier1_filters:
            tier1_config = create_tier_config_from_keywords(
                name='Tier 1 - Key Contacts',
                description='Senior decision makers and key investment professionals',
                include_keywords=tier1_filters.get("includeKeywords", []),
                exclude_keywords=tier1_filters.get("excludeKeywords", []),
                require_investment_team=tier1_filters.get("requireInvestmentTeam", False)
            )
        else:
            tier1_config = self.filter.create_tier1_config()
        
        if tier2_filters:
            tier2_config = create_tier_config_from_keywords(
                name='Tier 2 - Junior Contacts',
                description='Junior investment professionals (must be on investment team)',
                include_keywords=tier2_filters.get("includeKeywords", []),
                exclude_keywords=tier2_filters.get("excludeKeywords", []),
                require_investment_team=tier2_filters.get("requireInvestmentTeam", True)
            )
        else:
            tier2_config = self.filter.create_tier2_config()
        
        # Check for cancellation before tier filtering
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        # Apply tier filtering
        logger.info(f"Job {job_id}: Applying tier 1 filter (limit: {self.filter.tier1_limit}, requireInvestmentTeam: {tier1_config.get('require_investment_team', False)})")
        tier1_df = self.filter.apply_tier_filter(deduplicated_df, tier1_config, self.filter.tier1_limit)
        logger.info(f"Job {job_id}: Tier 1 result: {len(tier1_df)} contacts")
        
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        logger.info(f"Job {job_id}: Applying tier 2 filter (limit: {self.filter.tier2_limit}, requireInvestmentTeam: {tier2_config.get('require_investment_team', False)})")
        tier2_df = self.filter.apply_tier_filter(deduplicated_df, tier2_config, self.filter.tier2_limit)
        logger.info(f"Job {job_id}: Tier 2 result: {len(tier2_df)} contacts")
        
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        # Apply contact inclusion
        if self.filter.enable_contact_inclusion:
            logger.info(f"Job {job_id}: Applying contact inclusion")
            tier1_df, tier2_df = self.filter.apply_contact_inclusion(tier1_df, tier2_df, deduplicated_df)
            logger.info(f"Job {job_id}: After contact inclusion - Tier 1: {len(tier1_df)}, Tier 2: {len(tier2_df)}")
        
        # Check for cancellation before email discovery
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        # Email discovery and filling
        firm_patterns = {}
        if self.filter.enable_find_emails:
            logger.info(f"Job {job_id}: Extracting email patterns by firm")
            firm_patterns = self.filter.extract_email_patterns_by_firm(standardized_df)
            logger.info(f"Job {job_id}: Extracted email patterns for {len(firm_patterns)} firms")
            
            if len(tier1_df) > 0:
                logger.info(f"Job {job_id}: Filling missing emails for tier 1 contacts")
                tier1_df = self.filter.fill_missing_emails_with_patterns(tier1_df, firm_patterns)
            if len(tier2_df) > 0:
                logger.info(f"Job {job_id}: Filling missing emails for tier 2 contacts")
                tier2_df = self.filter.fill_missing_emails_with_patterns(tier2_df, firm_patterns)
        
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        # Create delta analysis
        logger.info(f"Job {job_id}: Creating delta analysis")
        delta_df = self.filter.create_delta_analysis(
            combined_df, standardized_df, deduplicated_df,
            tier1_df, tier2_df, tier1_config, tier2_config
        )
        
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        # Rescue excluded firms
        rescued_df = None
        rescue_stats = None
        if include_all_firms:
            logger.info(f"Job {job_id}: Rescuing excluded firms")
            rescued_df, rescue_stats = self.filter.rescue_excluded_firms(
                deduplicated_df, tier1_df, tier2_df
            )
            if len(rescued_df) > 0:
                logger.info(f"Job {job_id}: Rescued {len(rescued_df)} contacts")
                rescued_df['tier_type'] = 'Tier 3 - Rescued Contacts'
                if self.filter.enable_find_emails and firm_patterns:
                    logger.info(f"Job {job_id}: Filling missing emails for rescued contacts")
                    rescued_df = self.filter.fill_missing_emails_with_patterns(rescued_df, firm_patterns)
        
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        # Annotate email status
        if len(tier1_df) > 0:
            tier1_df = self.filter.annotate_email_status(tier1_df)
        if len(tier2_df) > 0:
            tier2_df = self.filter.annotate_email_status(tier2_df)
        if rescued_df is not None and len(rescued_df) > 0:
            rescued_df = self.filter.annotate_email_status(rescued_df)
        
        # Create excluded firms analysis
        excluded_firms_analysis = self.filter.create_excluded_firms_analysis(
            deduplicated_df, tier1_df, tier2_df, rescued_df if include_all_firms else None
        )
        
        # Check for cancellation before analytics extraction
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        # Extract analytics before creating Excel
        logger.info(f"Job {job_id}: Extracting analytics")
        from api.analytics_extractor import extract_analytics
        analytics = extract_analytics(
            tier1_df, tier2_df, rescued_df, file_info, dedup_count,
            deduplicated_df, delta_df, excluded_firms_analysis,
            rescue_stats, self.filter
        )
        
        # Check for cancellation before creating output file
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")

        # Check if we need to separate by firm type
        separate_by_firm_type = settings.get("separateByFirmType", False)

        if separate_by_firm_type:
            # Create 6 separate files by firm type, then zip them
            logger.info(f"Job {job_id}: Separating contacts by firm type into 6 files")

            # Separate each tier by firm type
            tier1_groups = self._separate_by_firm_type(tier1_df)
            tier2_groups = self._separate_by_firm_type(tier2_df)
            rescued_groups = self._separate_by_firm_type(rescued_df) if rescued_df is not None else None

            # Create a zip file containing all 6 Excel files
            zip_filename = output_filename.replace('.xlsx', '.zip')
            zip_path = self.filter.output_folder / zip_filename

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for group_name in ['Insurance', 'Wealth_FamilyOffice', 'Endowments_Foundations',
                                   'Pension_Funds', 'Funds_of_Funds', 'Other']:
                    # Get data for this group
                    group_tier1 = tier1_groups.get(group_name, pd.DataFrame())
                    group_tier2 = tier2_groups.get(group_name, pd.DataFrame())
                    group_rescued = rescued_groups.get(group_name, pd.DataFrame()) if rescued_groups else None

                    # Skip empty groups
                    total_contacts = len(group_tier1) + len(group_tier2)
                    if group_rescued is not None:
                        total_contacts += len(group_rescued)

                    if total_contacts == 0:
                        logger.info(f"Job {job_id}: Skipping empty group '{group_name}'")
                        continue

                    # Create Excel file in memory
                    group_filename = output_filename.replace('.xlsx', f'_{group_name}.xlsx')
                    excel_buffer = io.BytesIO()

                    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                        # Define standard column order
                        standard_columns = ['NAME', 'INVESTOR', 'EMAIL', 'EMAIL_STATUS', 'EMAIL_SCHEMA', 'JOB_TITLE']

                        # Add First Name and Last Name if they exist
                        if len(group_tier1) > 0 and 'First Name' in group_tier1.columns:
                            standard_columns.insert(0, 'First Name')
                        if len(group_tier1) > 0 and 'Last Name' in group_tier1.columns:
                            standard_columns.insert(1 if 'First Name' in standard_columns else 0, 'Last Name')

                        # Write Tier 1 sheet
                        if len(group_tier1) > 0:
                            available_std_cols = [col for col in standard_columns if col in group_tier1.columns]
                            other_cols = [col for col in group_tier1.columns if col not in available_std_cols]
                            tier1_reordered = group_tier1[available_std_cols + other_cols]
                        else:
                            tier1_reordered = group_tier1
                        tier1_reordered.to_excel(writer, sheet_name='Tier1_Key_Contacts', index=False)

                        # Write Tier 2 sheet
                        if len(group_tier2) > 0:
                            available_std_cols = [col for col in standard_columns if col in group_tier2.columns]
                            other_cols = [col for col in group_tier2.columns if col not in available_std_cols]
                            tier2_reordered = group_tier2[available_std_cols + other_cols]
                        else:
                            tier2_reordered = group_tier2
                        tier2_reordered.to_excel(writer, sheet_name='Tier2_Junior_Contacts', index=False)

                        # Write Tier 3 sheet (rescued contacts)
                        if group_rescued is not None and len(group_rescued) > 0:
                            if len(group_rescued) > 0:
                                available_std_cols = [col for col in standard_columns if col in group_rescued.columns]
                                other_cols = [col for col in group_rescued.columns if col not in available_std_cols]
                                rescued_reordered = group_rescued[available_std_cols + other_cols]
                            else:
                                rescued_reordered = group_rescued
                            rescued_reordered.to_excel(writer, sheet_name='Tier3_Rescued_Contacts', index=False)

                    # Add to zip
                    excel_buffer.seek(0)
                    zipf.writestr(group_filename, excel_buffer.read())
                    logger.info(f"Job {job_id}: Added {group_filename} to zip (T1: {len(group_tier1)}, T2: {len(group_tier2)}, T3: {len(group_rescued) if group_rescued is not None else 0})")

            logger.info(f"Job {job_id}: Created zip file with separated firm type files: {zip_path}")
            output_path = str(zip_path)
            output_filename = zip_filename
        else:
            # Create single Excel file (original behavior)
            logger.info(f"Job {job_id}: Creating output Excel file: {output_filename}")
            output_path = self.filter.create_output_file(
                tier1_df, tier2_df, file_info, dedup_count, output_filename,
                deduplicated_df, delta_df, excluded_firms_analysis,
                rescued_df, rescue_stats, contact_lists_only=True
            )
            logger.info(f"Job {job_id}: Output file created at {output_path}")

        return {
            "output_path": output_path,
            "output_filename": output_filename,
            "analytics": analytics
        }

