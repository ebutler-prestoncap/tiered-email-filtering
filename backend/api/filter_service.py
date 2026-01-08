"""
Service layer wrapping TieredFilter for web app use.
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import pandas as pd

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

class FilterService:
    """Service for processing contacts with TieredFilter"""
    
    def __init__(self, input_folder: str, output_folder: str):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.filter = TieredFilter(
            input_folder=str(self.input_folder),
            output_folder=str(self.output_folder)
        )
    
    def process_contacts(
        self,
        uploaded_files: list,
        settings: Dict[str, Any],
        job_id: str,
        original_filenames: list = None
    ) -> Dict[str, Any]:
        """
        Process contacts with given settings.
        
        Args:
            uploaded_files: List of file paths to process
            settings: Configuration settings dict
            job_id: Job ID for output filename
            original_filenames: List of original filenames (for display in analytics)
            
        Returns:
            Dict with output_path and analytics
        """
        # Configure filter instance
        self.filter.enable_firm_exclusion = settings.get("firmExclusion", False)
        self.filter.enable_contact_inclusion = settings.get("contactInclusion", False)
        self.filter.enable_find_emails = settings.get("findEmails", True)
        self.filter.tier1_limit = settings.get("tier1Limit", 10)
        self.filter.tier2_limit = settings.get("tier2Limit", 6)
        
        # Set input folder to uploaded files location
        # Copy files to input folder temporarily
        temp_input_folder = self.input_folder / job_id
        temp_input_folder.mkdir(parents=True, exist_ok=True)
        
        import shutil
        for file_path in uploaded_files:
            shutil.copy2(file_path, temp_input_folder / Path(file_path).name)
        
        # Temporarily set input folder
        original_input_folder = self.filter.input_folder
        self.filter.input_folder = temp_input_folder
        
        try:
            # Load exclusion/inclusion lists if enabled
            # First check for inline lists from settings, then fall back to CSV files
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
                filename_mapping=filename_mapping
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
        filename_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Process contacts and extract analytics"""
        # Clean output folder
        self.filter.clean_and_archive_output()
        
        # Load and combine input files
        combined_df, file_info = self.filter.load_and_combine_input_files()
        
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
        standardized_df = self.filter.standardize_columns(combined_df)
        
        # Remove duplicates
        deduplicated_df = self.filter.remove_duplicates(standardized_df)
        dedup_count = len(deduplicated_df)
        
        # Apply firm exclusion if enabled
        if self.filter.enable_firm_exclusion:
            self.filter.pre_exclusion_count = len(deduplicated_df)
            deduplicated_df = self.filter.apply_firm_exclusion(deduplicated_df)
        
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
        
        tier1_df = self.filter.apply_tier_filter(deduplicated_df, tier1_config, self.filter.tier1_limit)
        tier2_df = self.filter.apply_tier_filter(deduplicated_df, tier2_config, self.filter.tier2_limit)
        
        # Apply contact inclusion
        if self.filter.enable_contact_inclusion:
            tier1_df, tier2_df = self.filter.apply_contact_inclusion(tier1_df, tier2_df, deduplicated_df)
        
        # Email discovery and filling
        firm_patterns = {}
        if self.filter.enable_find_emails:
            firm_patterns = self.filter.extract_email_patterns_by_firm(standardized_df)
            if len(tier1_df) > 0:
                tier1_df = self.filter.fill_missing_emails_with_patterns(tier1_df, firm_patterns)
            if len(tier2_df) > 0:
                tier2_df = self.filter.fill_missing_emails_with_patterns(tier2_df, firm_patterns)
        
        # Create delta analysis
        delta_df = self.filter.create_delta_analysis(
            combined_df, standardized_df, deduplicated_df,
            tier1_df, tier2_df, tier1_config, tier2_config
        )
        
        # Rescue excluded firms
        rescued_df = None
        rescue_stats = None
        if include_all_firms:
            rescued_df, rescue_stats = self.filter.rescue_excluded_firms(
                deduplicated_df, tier1_df, tier2_df
            )
            if len(rescued_df) > 0:
                rescued_df['tier_type'] = 'Tier 3 - Rescued Contacts'
                if self.filter.enable_find_emails and firm_patterns:
                    rescued_df = self.filter.fill_missing_emails_with_patterns(rescued_df, firm_patterns)
        
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
        
        # Extract analytics before creating Excel
        from api.analytics_extractor import extract_analytics
        analytics = extract_analytics(
            tier1_df, tier2_df, rescued_df, file_info, dedup_count,
            deduplicated_df, delta_df, excluded_firms_analysis,
            rescue_stats, self.filter
        )
        
        # Create Excel file with contact lists only
        output_path = self.filter.create_output_file(
            tier1_df, tier2_df, file_info, dedup_count, output_filename,
            deduplicated_df, delta_df, excluded_firms_analysis,
            rescued_df, rescue_stats, contact_lists_only=True
        )
        
        return {
            "output_path": output_path,
            "output_filename": output_filename,
            "analytics": analytics
        }

