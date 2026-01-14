"""
Service layer wrapping TieredFilter for web app use.
"""
import sys
import threading
import csv
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set
from difflib import SequenceMatcher
import logging
import pandas as pd
import zipfile
import io

# Add parent directory to path to import tiered_filter
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tiered_filter import TieredFilter
from api.excel_validator import (
    validate_excel_file,
    find_column_match,
    ACCOUNTS_COLUMNS,
    CONTACTS_COLUMNS,
)


def normalize_name(name: str) -> str:
    """Normalize a name for fuzzy matching - lowercase, remove punctuation, extra spaces"""
    if not name:
        return ''
    # Lowercase and strip
    name = name.lower().strip()
    # Remove common suffixes/prefixes that vary
    name = re.sub(r'\b(inc|llc|lp|ltd|corp|corporation|company|co|llp|plc|group|partners|management|capital|advisors|advisory|fund|funds)\b\.?', '', name)
    # Remove punctuation except spaces
    name = re.sub(r'[^\w\s]', '', name)
    # Collapse multiple spaces
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def fuzzy_match_score(str1: str, str2: str) -> float:
    """Calculate fuzzy match score between two strings (0.0 to 1.0)"""
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1, str2).ratio()


def is_fuzzy_account_match(account_name: str, removal_accounts: Set[str], threshold: float = 0.85) -> Tuple[bool, str]:
    """
    Check if an account name fuzzy matches any account in the removal set.
    Returns (is_match, matched_account_name).
    Uses both exact normalized matching and fuzzy matching.
    """
    if not account_name:
        return False, ''

    normalized = normalize_name(account_name)
    if not normalized:
        return False, ''

    # First try exact match on normalized name
    if normalized in removal_accounts:
        return True, normalized

    # Also check if the original lowercase matches
    original_lower = account_name.strip().lower()
    if original_lower in removal_accounts:
        return True, original_lower

    # Fuzzy match against all accounts in removal set
    for removal_account in removal_accounts:
        # Try fuzzy match on normalized versions
        removal_normalized = normalize_name(removal_account)
        if removal_normalized and fuzzy_match_score(normalized, removal_normalized) >= threshold:
            return True, removal_account

        # Also try substring containment for longer names
        if len(normalized) >= 5 and len(removal_normalized) >= 5:
            if normalized in removal_normalized or removal_normalized in normalized:
                return True, removal_account

    return False, ''


def is_fuzzy_contact_match(
    name: str, email: str, account: str,
    contact_removal_set: Set[Tuple[str, str]],
    threshold: float = 0.85
) -> Tuple[bool, str]:
    """
    Check if a contact fuzzy matches any contact in the removal set.
    Matches by email (exact) or by name+account (fuzzy).
    Returns (is_match, match_reason).
    """
    # Check email matches first (exact match on email)
    if email:
        email_lower = email.strip().lower()
        for removal_name, removal_email_or_account in contact_removal_set:
            if not removal_name and removal_email_or_account == email_lower:
                return True, f'Email match: {email_lower}'

    # Check name + account fuzzy match
    if name and account:
        name_normalized = normalize_name(name)
        account_normalized = normalize_name(account)

        for removal_name, removal_account in contact_removal_set:
            if removal_name:  # This is a name+account entry, not email
                removal_name_normalized = normalize_name(removal_name)
                removal_account_normalized = normalize_name(removal_account)

                # Check if both name and account match (fuzzy)
                name_score = fuzzy_match_score(name_normalized, removal_name_normalized)
                account_score = fuzzy_match_score(account_normalized, removal_account_normalized)

                # Both must meet threshold, or one must be exact and other close
                if name_score >= threshold and account_score >= threshold:
                    return True, f'Name+Account match: {removal_name} @ {removal_account}'

                # If name is very close and account contains/is contained
                if name_score >= 0.9:
                    if account_normalized in removal_account_normalized or removal_account_normalized in account_normalized:
                        return True, f'Name match with account substring: {removal_name} @ {removal_account}'

    return False, ''
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
        # Removal lists loaded from CSV files
        self.account_removal_set: Set[str] = set()
        self.contact_removal_set: Set[Tuple[str, str]] = set()  # (name, email) tuples
        # Track removed contacts for analytics
        self.removal_list_removed: List[Dict] = []  # Track contacts removed by removal lists

    def load_account_removal_list(self, csv_path: str) -> int:
        """Load account removal list from CSV file.
        Returns the number of accounts loaded."""
        self.account_removal_set = set()
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Look for Account Name column (case insensitive)
                    account_name = None
                    for key in row.keys():
                        if key.lower().strip() in ['account name', 'account', 'investor', 'firm']:
                            account_name = row[key]
                            break
                    if account_name and account_name.strip():
                        self.account_removal_set.add(account_name.strip().lower())
            logger.info(f"Loaded {len(self.account_removal_set)} accounts from removal list")
            return len(self.account_removal_set)
        except Exception as e:
            logger.error(f"Failed to load account removal list: {e}")
            return 0

    def load_contact_removal_list(self, csv_path: str) -> int:
        """Load contact removal list from CSV file.
        Returns the number of contacts loaded."""
        self.contact_removal_set = set()
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Look for relevant columns
                    contact_name = None
                    email = None
                    account_name = None
                    for key in row.keys():
                        key_lower = key.lower().strip()
                        if key_lower in ['contact name', 'name', 'full name']:
                            contact_name = row[key]
                        elif key_lower in ['email', 'email address', 'e-mail']:
                            email = row[key]
                        elif key_lower in ['account name', 'account', 'investor', 'firm']:
                            account_name = row[key]

                    # Add to removal set - prefer email, fall back to name+account
                    if email and email.strip():
                        self.contact_removal_set.add(('', email.strip().lower()))
                    elif contact_name and contact_name.strip() and account_name and account_name.strip():
                        self.contact_removal_set.add((
                            contact_name.strip().lower(),
                            account_name.strip().lower()
                        ))
            logger.info(f"Loaded {len(self.contact_removal_set)} contacts from removal list")
            return len(self.contact_removal_set)
        except Exception as e:
            logger.error(f"Failed to load contact removal list: {e}")
            return 0

    def apply_account_removal(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
        """Remove rows where the INVESTOR/account column matches the removal list (with fuzzy matching).
        Returns (filtered_df, list of removed contact records)."""
        if not self.account_removal_set:
            return df, []

        initial_count = len(df)
        removed_records = []

        # Find the investor/account column
        investor_col = None
        for col in df.columns:
            if col.upper() in ['INVESTOR', 'ACCOUNT', 'FIRM', 'ACCOUNT NAME']:
                investor_col = col
                break

        if investor_col is None:
            logger.warning("No INVESTOR/ACCOUNT column found, skipping account removal")
            return df, []

        # Find name column for tracking
        name_col = None
        for col in df.columns:
            if col.upper() in ['NAME', 'FULL NAME', 'CONTACT NAME']:
                name_col = col
                break

        # Check each row with fuzzy matching
        keep_indices = []
        for idx, row in df.iterrows():
            investor_val = row.get(investor_col)
            if pd.isna(investor_val) or not investor_val:
                keep_indices.append(idx)
                continue

            is_match, matched_account = is_fuzzy_account_match(
                str(investor_val),
                self.account_removal_set,
                threshold=0.85
            )

            if is_match:
                # Track the removed contact
                removed_records.append({
                    'name': str(row.get(name_col, '')) if name_col else '',
                    'investor': str(investor_val),
                    'reason': f'Account Removal List: matched "{matched_account}"',
                    'row_data': row.to_dict()
                })
            else:
                keep_indices.append(idx)

        filtered_df = df.loc[keep_indices].copy()
        removed_count = initial_count - len(filtered_df)
        logger.info(f"Account removal (fuzzy): removed {removed_count} contacts from {len(self.account_removal_set)} excluded accounts")

        return filtered_df, removed_records

    def apply_contact_removal(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
        """Remove rows where the contact matches the removal list (by email or name+account with fuzzy matching).
        Returns (filtered_df, list of removed contact records)."""
        if not self.contact_removal_set:
            return df, []

        initial_count = len(df)
        removed_records = []

        # Find relevant columns
        email_col = None
        name_col = None
        investor_col = None

        for col in df.columns:
            col_upper = col.upper()
            if col_upper in ['EMAIL', 'E-MAIL', 'EMAIL ADDRESS']:
                email_col = col
            elif col_upper in ['NAME', 'FULL NAME', 'CONTACT NAME']:
                name_col = col
            elif col_upper in ['INVESTOR', 'ACCOUNT', 'FIRM', 'ACCOUNT NAME']:
                investor_col = col

        if email_col is None and (name_col is None or investor_col is None):
            logger.warning("Missing required columns for contact removal, skipping")
            return df, []

        # Check each row with fuzzy matching
        keep_indices = []
        for idx, row in df.iterrows():
            email_val = str(row.get(email_col, '')) if email_col and row.get(email_col) else ''
            name_val = str(row.get(name_col, '')) if name_col and row.get(name_col) else ''
            investor_val = str(row.get(investor_col, '')) if investor_col and row.get(investor_col) else ''

            is_match, match_reason = is_fuzzy_contact_match(
                name_val,
                email_val,
                investor_val,
                self.contact_removal_set,
                threshold=0.85
            )

            if is_match:
                # Track the removed contact
                removed_records.append({
                    'name': name_val,
                    'email': email_val,
                    'investor': investor_val,
                    'reason': f'Contact Removal List: {match_reason}',
                    'row_data': row.to_dict()
                })
            else:
                keep_indices.append(idx)

        filtered_df = df.loc[keep_indices].copy()
        removed_count = initial_count - len(filtered_df)
        logger.info(f"Contact removal (fuzzy): removed {removed_count} contacts")

        return filtered_df, removed_records

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

    def load_accounts_from_excel(self, file_path: str) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
        """
        Load accounts data from an Excel file that may contain multiple sheets.
        Returns (accounts_df, info_dict) where info_dict contains column mappings.
        """
        info = {
            'accounts_sheet': None,
            'firm_id_column': None,
            'firm_name_column': None,
            'aum_column': None,
            'row_count': 0,
            'loaded': False,
        }

        try:
            validation = validate_excel_file(file_path)

            if not validation.get('accounts_sheet'):
                logger.debug(f"No accounts sheet found in {file_path}")
                return None, info

            accounts_sheet = validation['accounts_sheet']
            xlsx = pd.ExcelFile(file_path)
            accounts_df = pd.read_excel(xlsx, sheet_name=accounts_sheet)

            if len(accounts_df) == 0:
                logger.warning(f"Accounts sheet '{accounts_sheet}' is empty")
                return None, info

            # Find key columns
            columns = list(accounts_df.columns)

            firm_id_col = find_column_match(columns, 'FIRM ID', ACCOUNTS_COLUMNS['aliases'])
            firm_name_col = find_column_match(columns, 'FIRM NAME', ACCOUNTS_COLUMNS['aliases'])
            aum_col = find_column_match(columns, 'AUM (USD MN)', ACCOUNTS_COLUMNS['aliases'])

            if not firm_id_col and not firm_name_col:
                logger.warning("Accounts sheet missing both FIRM ID and FIRM NAME columns")
                return None, info

            info['accounts_sheet'] = accounts_sheet
            info['firm_id_column'] = firm_id_col
            info['firm_name_column'] = firm_name_col
            info['aum_column'] = aum_col
            info['row_count'] = len(accounts_df)
            info['loaded'] = True

            logger.info(f"Loaded accounts from '{accounts_sheet}': {len(accounts_df)} rows, AUM column: {aum_col}")
            return accounts_df, info

        except Exception as e:
            logger.error(f"Error loading accounts from {file_path}: {e}")
            return None, info

    def merge_aum_into_contacts(
        self,
        contacts_df: pd.DataFrame,
        accounts_df: pd.DataFrame,
        accounts_info: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Merge AUM data from accounts into contacts based on FIRM_ID or firm name.
        Returns (merged_df, merge_stats).
        """
        merge_stats = {
            'contacts_total': len(contacts_df),
            'contacts_with_aum': 0,
            'contacts_without_aum': 0,
            'aum_min': None,
            'aum_max': None,
            'aum_avg': None,
            'merge_method': None,
        }

        if accounts_df is None or len(accounts_df) == 0:
            merge_stats['contacts_without_aum'] = len(contacts_df)
            return contacts_df, merge_stats

        aum_col = accounts_info.get('aum_column')
        if not aum_col:
            logger.warning("No AUM column in accounts data, skipping AUM merge")
            merge_stats['contacts_without_aum'] = len(contacts_df)
            return contacts_df, merge_stats

        # Try to merge by FIRM_ID first
        firm_id_col = accounts_info.get('firm_id_column')
        firm_name_col = accounts_info.get('firm_name_column')

        # Find contacts FIRM_ID column
        contacts_firm_id_col = None
        for col in contacts_df.columns:
            if col.upper().replace('_', ' ').strip() in ['FIRM ID', 'FIRMID', 'FIRM_ID']:
                contacts_firm_id_col = col
                break

        merged_df = contacts_df.copy()

        # Initialize AUM column
        merged_df['AUM_USD_MN'] = None

        if firm_id_col and contacts_firm_id_col:
            # Merge by FIRM_ID
            logger.info(f"Merging AUM by FIRM_ID: accounts.{firm_id_col} -> contacts.{contacts_firm_id_col}")
            merge_stats['merge_method'] = 'FIRM_ID'

            # Create lookup dict from accounts
            aum_lookup = {}
            for _, row in accounts_df.iterrows():
                fid = row.get(firm_id_col)
                aum = row.get(aum_col)
                if pd.notna(fid) and pd.notna(aum):
                    try:
                        aum_lookup[str(fid).strip()] = float(aum)
                    except (ValueError, TypeError):
                        pass

            # Apply lookup
            def get_aum(firm_id):
                if pd.isna(firm_id):
                    return None
                return aum_lookup.get(str(firm_id).strip())

            merged_df['AUM_USD_MN'] = merged_df[contacts_firm_id_col].apply(get_aum)

        elif firm_name_col:
            # Fallback: merge by firm name (fuzzy)
            logger.info(f"Merging AUM by firm name (fuzzy matching)")
            merge_stats['merge_method'] = 'FIRM_NAME_FUZZY'

            # Find contacts INVESTOR column
            investor_col = None
            for col in merged_df.columns:
                if col.upper() in ['INVESTOR', 'FIRM', 'ACCOUNT', 'FIRM NAME', 'ACCOUNT NAME']:
                    investor_col = col
                    break

            if investor_col:
                # Create normalized lookup
                aum_lookup = {}
                for _, row in accounts_df.iterrows():
                    fname = row.get(firm_name_col)
                    aum = row.get(aum_col)
                    if pd.notna(fname) and pd.notna(aum):
                        normalized = normalize_name(str(fname))
                        if normalized:
                            try:
                                aum_lookup[normalized] = float(aum)
                            except (ValueError, TypeError):
                                pass

                def get_aum_by_name(investor):
                    if pd.isna(investor):
                        return None
                    normalized = normalize_name(str(investor))
                    return aum_lookup.get(normalized)

                merged_df['AUM_USD_MN'] = merged_df[investor_col].apply(get_aum_by_name)

        # Calculate stats
        aum_values = merged_df['AUM_USD_MN'].dropna()
        merge_stats['contacts_with_aum'] = len(aum_values)
        merge_stats['contacts_without_aum'] = len(merged_df) - len(aum_values)

        if len(aum_values) > 0:
            merge_stats['aum_min'] = float(aum_values.min())
            merge_stats['aum_max'] = float(aum_values.max())
            merge_stats['aum_avg'] = float(aum_values.mean())

        logger.info(
            f"AUM merge complete: {merge_stats['contacts_with_aum']}/{merge_stats['contacts_total']} "
            f"contacts have AUM data (method: {merge_stats['merge_method']})"
        )

        return merged_df, merge_stats

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

            # Load removal lists from database if enabled
            # Import here to avoid circular imports
            from database import Database
            from config import DATABASE_PATH
            db = Database(str(DATABASE_PATH))

            apply_account_removal = settings.get("applyAccountRemovalList", True)
            apply_contact_removal = settings.get("applyContactRemovalList", True)

            if apply_account_removal:
                account_removal_list = db.get_active_removal_list('account')
                if account_removal_list and account_removal_list.get('stored_path'):
                    stored_path = Path(account_removal_list['stored_path'])
                    if stored_path.exists():
                        self.load_account_removal_list(str(stored_path))
                        db.update_removal_list_last_used(account_removal_list['id'])
                        logger.info(f"Job {job_id}: Loaded account removal list: {account_removal_list['original_name']}")

            if apply_contact_removal:
                contact_removal_list = db.get_active_removal_list('contact')
                if contact_removal_list and contact_removal_list.get('stored_path'):
                    stored_path = Path(contact_removal_list['stored_path'])
                    if stored_path.exists():
                        self.load_contact_removal_list(str(stored_path))
                        db.update_removal_list_last_used(contact_removal_list['id'])
                        logger.info(f"Job {job_id}: Loaded contact removal list: {contact_removal_list['original_name']}")

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

        # Load and merge AUM data from accounts sheets if available
        aum_merge_stats = None
        enable_aum_merge = settings.get("enableAumMerge", True)  # Default to True

        if enable_aum_merge:
            logger.info(f"Job {job_id}: Checking for accounts sheets to merge AUM data")
            all_accounts_df = []
            accounts_info = None

            # Check each input file for accounts sheet
            for file_path in self.filter.input_folder.glob("*.xlsx"):
                accounts_df, info = self.load_accounts_from_excel(str(file_path))
                if accounts_df is not None and info.get('loaded'):
                    all_accounts_df.append(accounts_df)
                    if accounts_info is None:
                        accounts_info = info
                    logger.info(f"Job {job_id}: Found accounts data in {file_path.name}")

            # Combine all accounts data
            if all_accounts_df:
                combined_accounts = pd.concat(all_accounts_df, ignore_index=True)
                # Remove duplicate accounts by FIRM_ID if available
                if accounts_info and accounts_info.get('firm_id_column'):
                    firm_id_col = accounts_info['firm_id_column']
                    combined_accounts = combined_accounts.drop_duplicates(subset=[firm_id_col], keep='first')

                logger.info(f"Job {job_id}: Merging AUM from {len(combined_accounts)} accounts into contacts")
                standardized_df, aum_merge_stats = self.merge_aum_into_contacts(
                    standardized_df, combined_accounts, accounts_info
                )
                logger.info(f"Job {job_id}: AUM merge complete - {aum_merge_stats.get('contacts_with_aum', 0)} contacts have AUM")

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

        # Apply account removal list (from uploaded CSV) with fuzzy matching
        account_removed_records = []
        if self.account_removal_set:
            logger.info(f"Job {job_id}: Applying account removal list to {len(deduplicated_df)} contacts")
            deduplicated_df, account_removed_records = self.apply_account_removal(deduplicated_df)
            logger.info(f"Job {job_id}: After account removal: {len(deduplicated_df)} contacts remain ({len(account_removed_records)} removed)")

        # Apply contact removal list (from uploaded CSV) with fuzzy matching
        contact_removed_records = []
        if self.contact_removal_set:
            logger.info(f"Job {job_id}: Applying contact removal list to {len(deduplicated_df)} contacts")
            deduplicated_df, contact_removed_records = self.apply_contact_removal(deduplicated_df)
            logger.info(f"Job {job_id}: After contact removal: {len(deduplicated_df)} contacts remain ({len(contact_removed_records)} removed)")

        # Store removal list records for delta analysis
        self.removal_list_removed = account_removed_records + contact_removed_records

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

        # Add removal list removals to delta analysis
        if self.removal_list_removed:
            logger.info(f"Job {job_id}: Adding {len(self.removal_list_removed)} removal list entries to delta analysis")
            removal_rows = []
            for record in self.removal_list_removed:
                row_data = record.get('row_data', {})
                # Create delta row entry
                delta_row = {
                    'STD_NAME': record.get('name', ''),
                    'STD_INVESTOR': record.get('investor', ''),
                    'STD_JOB_TITLE': row_data.get('JOB_TITLE', row_data.get('STD_JOB_TITLE', '')),
                    'STD_EMAIL': record.get('email', row_data.get('EMAIL', '')),
                    'PROCESSING_STATUS': 'Removed',
                    'FILTER_REASON': record.get('reason', 'Removal List'),
                    'FINAL_TIER': '',
                    'TIER_MATCH': 'Removal List',
                    'PRIORITY_SCORE': 0,
                }
                # Add any other columns from original row
                for col in delta_df.columns:
                    if col not in delta_row:
                        delta_row[col] = row_data.get(col, '')
                removal_rows.append(delta_row)

            if removal_rows:
                removal_df = pd.DataFrame(removal_rows)
                # Ensure columns match
                for col in delta_df.columns:
                    if col not in removal_df.columns:
                        removal_df[col] = ''
                removal_df = removal_df[delta_df.columns]
                delta_df = pd.concat([delta_df, removal_df], ignore_index=True)
                logger.info(f"Job {job_id}: Delta analysis now has {len(delta_df)} entries")

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

        # Add AUM merge stats to analytics
        if aum_merge_stats:
            analytics["aum_merge"] = {
                "enabled": True,
                "contacts_with_aum": aum_merge_stats.get('contacts_with_aum', 0),
                "contacts_without_aum": aum_merge_stats.get('contacts_without_aum', 0),
                "aum_min": aum_merge_stats.get('aum_min'),
                "aum_max": aum_merge_stats.get('aum_max'),
                "aum_avg": aum_merge_stats.get('aum_avg'),
                "merge_method": aum_merge_stats.get('merge_method'),
            }
        else:
            analytics["aum_merge"] = {"enabled": False}

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

            # Build firm type breakdown for analytics
            firm_type_breakdown = []
            files_in_zip = []

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
                        # Define standard column order (including AUM if available)
                        standard_columns = ['NAME', 'INVESTOR', 'EMAIL', 'EMAIL_STATUS', 'EMAIL_SCHEMA', 'JOB_TITLE', 'AUM_USD_MN']

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

                    # Track file info for analytics
                    tier3_count = len(group_rescued) if group_rescued is not None else 0
                    files_in_zip.append({
                        "filename": group_filename,
                        "firmTypeGroup": group_name,
                        "tier1Contacts": len(group_tier1),
                        "tier2Contacts": len(group_tier2),
                        "tier3Contacts": tier3_count,
                        "totalContacts": total_contacts
                    })

                    # Build breakdown entry
                    firm_type_breakdown.append({
                        "firmTypeGroup": group_name,
                        "displayName": group_name.replace('_', ' / ').replace('FamilyOffice', 'Family Office'),
                        "tier1Contacts": len(group_tier1),
                        "tier2Contacts": len(group_tier2),
                        "tier3Contacts": tier3_count,
                        "totalContacts": total_contacts
                    })

            # Add firm type breakdown to analytics
            analytics["firm_type_breakdown"] = firm_type_breakdown
            analytics["files_in_zip"] = files_in_zip
            analytics["is_separated_by_firm_type"] = True

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

