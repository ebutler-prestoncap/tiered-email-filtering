"""
Service layer wrapping TieredFilter for web app use.
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Add parent directory to path to import tiered_filter
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tiered_filter import TieredFilter

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
        job_id: str
    ) -> Dict[str, Any]:
        """
        Process contacts with given settings.
        
        Args:
            uploaded_files: List of file paths to process
            settings: Configuration settings dict
            job_id: Job ID for output filename
            
        Returns:
            Dict with output_path and analytics
        """
        # Configure filter instance
        self.filter.enable_firm_exclusion = settings.get("firmExclusion", False)
        self.filter.enable_contact_inclusion = settings.get("contactInclusion", False)
        self.filter.enable_find_emails = settings.get("findEmails", False)
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
            if self.filter.enable_firm_exclusion:
                self.filter.load_firm_exclusion_list()
            
            if self.filter.enable_contact_inclusion:
                self.filter.load_contact_inclusion_list()
            
            # Process contacts
            include_all_firms = settings.get("includeAllFirms", False)
            user_prefix = settings.get("userPrefix", "Combined-Contacts")
            
            # Generate output filename
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{user_prefix}_{timestamp}.xlsx"
            
            # Call the main processing method
            # We need to replicate the process_contacts logic but extract analytics
            result = self._process_with_analytics(
                include_all_firms=include_all_firms,
                user_prefix=user_prefix,
                output_filename=output_filename
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
    
    def _process_with_analytics(
        self,
        include_all_firms: bool,
        user_prefix: str,
        output_filename: str
    ) -> Dict[str, Any]:
        """Process contacts and extract analytics"""
        # Clean output folder
        self.filter.clean_and_archive_output()
        
        # Load and combine input files
        combined_df, file_info = self.filter.load_and_combine_input_files()
        
        # Standardize columns
        standardized_df = self.filter.standardize_columns(combined_df)
        
        # Remove duplicates
        deduplicated_df = self.filter.remove_duplicates(standardized_df)
        dedup_count = len(deduplicated_df)
        
        # Apply firm exclusion if enabled
        if self.filter.enable_firm_exclusion:
            self.filter.pre_exclusion_count = len(deduplicated_df)
            deduplicated_df = self.filter.apply_firm_exclusion(deduplicated_df)
        
        # Apply tier filtering
        tier1_config = self.filter.create_tier1_config()
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
        # Import here to avoid circular dependencies
        import importlib.util
        analytics_path = Path(__file__).parent / "analytics_extractor.py"
        spec = importlib.util.spec_from_file_location("analytics_extractor", analytics_path)
        analytics_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(analytics_module)
        analytics = analytics_module.extract_analytics(
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
            "analytics": analytics
        }

