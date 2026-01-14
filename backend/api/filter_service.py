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
from api.tier_config_utils import (
    create_tier_config_from_keywords,
    get_default_tier1_keywords,
    get_default_tier2_keywords,
    get_default_tier3_keywords
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
        self.account_removal_set: Set[str] = set()  # Original lowercase names
        self.account_removal_normalized: Set[str] = set()  # Pre-normalized names for exact matching
        self.contact_removal_set: Set[Tuple[str, str]] = set()  # (name, email_or_account) tuples
        self.contact_removal_emails: Set[str] = set()  # Pre-extracted emails for O(1) lookup
        self.contact_removal_normalized: Set[Tuple[str, str]] = set()  # Pre-normalized (name, account) tuples
        # Track removed contacts for analytics
        self.removal_list_removed: List[Dict] = []  # Track contacts removed by removal lists
        # Track removal list metadata for summary
        self.account_removal_list_name: Optional[str] = None
        self.account_removal_list_size: int = 0
        self.contact_removal_list_name: Optional[str] = None
        self.contact_removal_list_size: int = 0

    def load_account_removal_list(self, csv_path: str, list_name: Optional[str] = None) -> int:
        """Load account removal list from CSV file.
        Returns the number of accounts loaded."""
        self.account_removal_set = set()
        self.account_removal_normalized = set()
        self.account_removal_list_name = list_name or Path(csv_path).name
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
                        lower_name = account_name.strip().lower()
                        self.account_removal_set.add(lower_name)
                        # Also store normalized version for exact matching
                        normalized = normalize_name(lower_name)
                        if normalized:
                            self.account_removal_normalized.add(normalized)
            self.account_removal_list_size = len(self.account_removal_set)
            logger.info(f"Loaded {self.account_removal_list_size} accounts from removal list '{self.account_removal_list_name}'")
            return self.account_removal_list_size
        except Exception as e:
            logger.error(f"Failed to load account removal list: {e}")
            return 0

    def load_contact_removal_list(self, csv_path: str, list_name: Optional[str] = None) -> int:
        """Load contact removal list from CSV file.
        Returns the number of contacts loaded."""
        self.contact_removal_set = set()
        self.contact_removal_emails = set()
        self.contact_removal_normalized = set()
        self.contact_removal_list_name = list_name or Path(csv_path).name
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
                        email_lower = email.strip().lower()
                        self.contact_removal_set.add(('', email_lower))
                        self.contact_removal_emails.add(email_lower)
                    elif contact_name and contact_name.strip() and account_name and account_name.strip():
                        name_lower = contact_name.strip().lower()
                        account_lower = account_name.strip().lower()
                        self.contact_removal_set.add((name_lower, account_lower))
                        # Also store normalized version for exact matching
                        name_normalized = normalize_name(name_lower)
                        account_normalized = normalize_name(account_lower)
                        if name_normalized and account_normalized:
                            self.contact_removal_normalized.add((name_normalized, account_normalized))
            self.contact_removal_list_size = len(self.contact_removal_set)
            logger.info(f"Loaded {self.contact_removal_list_size} contacts from removal list '{self.contact_removal_list_name}' ({len(self.contact_removal_emails)} emails, {len(self.contact_removal_normalized)} name+account)")
            return self.contact_removal_list_size
        except Exception as e:
            logger.error(f"Failed to load contact removal list: {e}")
            return 0

    def apply_account_removal(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict], Dict[str, Any]]:
        """Remove rows where the INVESTOR/account column matches the removal list.
        Uses fast exact matching first, with fuzzy fallback only for non-matches.
        Returns (filtered_df, list of removed contact records, stats dict)."""
        stats = {
            'contacts_removed': 0,
            'accounts_matched': 0,
            'exact_matches': 0,
            'substring_matches': 0,
        }
        if not self.account_removal_set:
            return df, [], stats

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

        # Vectorized: pre-compute lowercase investor values
        df_investor_lower = df[investor_col].fillna('').astype(str).str.lower().str.strip()
        df_investor_normalized = df_investor_lower.apply(normalize_name)

        # Phase 1: Fast exact matching using set lookups (O(1) per row)
        exact_match_mask = df_investor_lower.isin(self.account_removal_set) | df_investor_normalized.isin(self.account_removal_normalized)

        exact_removed_df = df[exact_match_mask]
        for idx in exact_removed_df.index:
            row = df.loc[idx]
            investor_val = row.get(investor_col, '')
            removed_records.append({
                'name': str(row.get(name_col, '')) if name_col else '',
                'investor': str(investor_val),
                'reason': f'Account Removal List: exact match',
                'row_data': row.to_dict()
            })

        # Phase 2: For non-exact matches, check substring containment (still fast)
        # Skip expensive fuzzy matching - substring containment is sufficient
        remaining_mask = ~exact_match_mask
        remaining_indices = df[remaining_mask].index.tolist()

        fuzzy_removed_indices = []
        for idx in remaining_indices:
            investor_val = df_investor_normalized.loc[idx]
            if not investor_val or len(investor_val) < 5:
                continue

            # Check substring containment against normalized removal list
            for removal_account in self.account_removal_normalized:
                if len(removal_account) >= 5:
                    if investor_val in removal_account or removal_account in investor_val:
                        row = df.loc[idx]
                        removed_records.append({
                            'name': str(row.get(name_col, '')) if name_col else '',
                            'investor': str(row.get(investor_col, '')),
                            'reason': f'Account Removal List: substring match with "{removal_account}"',
                            'row_data': row.to_dict()
                        })
                        fuzzy_removed_indices.append(idx)
                        break

        # Combine all removed indices
        all_removed_mask = exact_match_mask.copy()
        for idx in fuzzy_removed_indices:
            all_removed_mask.loc[idx] = True

        filtered_df = df[~all_removed_mask].copy()
        removed_count = initial_count - len(filtered_df)

        # Calculate unique accounts matched
        matched_accounts = set()
        for record in removed_records:
            if record.get('investor'):
                matched_accounts.add(record['investor'].lower().strip())

        stats['contacts_removed'] = removed_count
        stats['accounts_matched'] = len(matched_accounts)
        stats['exact_matches'] = int(exact_match_mask.sum())
        stats['substring_matches'] = len(fuzzy_removed_indices)

        logger.info(f"Account removal: removed {removed_count} contacts from {len(matched_accounts)} matched accounts (exact: {stats['exact_matches']}, substring: {stats['substring_matches']})")

        return filtered_df, removed_records, stats

    def apply_contact_removal(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict], Dict[str, Any]]:
        """Remove rows where the contact matches the removal list (by email or name+account).
        Uses fast exact matching first, with substring fallback only for non-matches.
        Returns (filtered_df, list of removed contact records, stats dict)."""
        stats = {
            'contacts_removed': 0,
            'email_matches': 0,
            'name_account_matches': 0,
        }
        if not self.contact_removal_set:
            return df, [], stats

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
            return df, [], stats

        # Vectorized: pre-compute normalized values
        if email_col:
            df_email_lower = df[email_col].fillna('').astype(str).str.lower().str.strip()
        else:
            df_email_lower = pd.Series([''] * len(df), index=df.index)

        if name_col:
            df_name_normalized = df[name_col].fillna('').astype(str).str.lower().str.strip().apply(normalize_name)
        else:
            df_name_normalized = pd.Series([''] * len(df), index=df.index)

        if investor_col:
            df_investor_normalized = df[investor_col].fillna('').astype(str).str.lower().str.strip().apply(normalize_name)
        else:
            df_investor_normalized = pd.Series([''] * len(df), index=df.index)

        # Phase 1: Fast exact email matching using set lookup (O(1) per row)
        email_match_mask = pd.Series([False] * len(df), index=df.index)
        if self.contact_removal_emails:
            email_match_mask = df_email_lower.isin(self.contact_removal_emails)

        for idx in df[email_match_mask].index:
            row = df.loc[idx]
            removed_records.append({
                'name': str(row.get(name_col, '')) if name_col else '',
                'email': str(row.get(email_col, '')) if email_col else '',
                'investor': str(row.get(investor_col, '')) if investor_col else '',
                'reason': 'Contact Removal List: email match',
                'row_data': row.to_dict()
            })

        # Phase 2: For non-email matches, check name+account exact matches
        remaining_mask = ~email_match_mask
        name_account_match_indices = []

        # Create a set of normalized (name, account) tuples from remaining rows for fast lookup
        for idx in df[remaining_mask].index:
            name_norm = df_name_normalized.loc[idx]
            investor_norm = df_investor_normalized.loc[idx]

            if name_norm and investor_norm:
                if (name_norm, investor_norm) in self.contact_removal_normalized:
                    row = df.loc[idx]
                    removed_records.append({
                        'name': str(row.get(name_col, '')) if name_col else '',
                        'email': str(row.get(email_col, '')) if email_col else '',
                        'investor': str(row.get(investor_col, '')) if investor_col else '',
                        'reason': 'Contact Removal List: name+account exact match',
                        'row_data': row.to_dict()
                    })
                    name_account_match_indices.append(idx)

        # Combine all removed indices
        all_removed_mask = email_match_mask.copy()
        for idx in name_account_match_indices:
            all_removed_mask.loc[idx] = True

        filtered_df = df[~all_removed_mask].copy()
        removed_count = initial_count - len(filtered_df)

        stats['contacts_removed'] = removed_count
        stats['email_matches'] = int(email_match_mask.sum())
        stats['name_account_matches'] = len(name_account_match_indices)

        logger.info(f"Contact removal: removed {removed_count} contacts (email: {stats['email_matches']}, name+account: {stats['name_account_matches']})")

        return filtered_df, removed_records, stats

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
        cancel_event: Optional[threading.Event] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Process contacts with given settings.

        Args:
            uploaded_files: List of file paths to process
            settings: Configuration settings dict
            job_id: Job ID for output filename
            original_filenames: List of original filenames (for display in analytics)
            cancel_event: Optional threading.Event to signal cancellation
            progress_callback: Optional callback(text, percent) to report progress

        Returns:
            Dict with output_path and analytics

        Raises:
            RuntimeError: If cancellation is requested
        """
        def report_progress(text: str, percent: int = 0):
            """Helper to safely call progress callback"""
            if progress_callback:
                try:
                    progress_callback(text, percent)
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")

        report_progress("Initializing processing...", 5)

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
                        list_name = account_removal_list.get('original_name', stored_path.name)
                        self.load_account_removal_list(str(stored_path), list_name=list_name)
                        db.update_removal_list_last_used(account_removal_list['id'])
                        logger.info(f"Job {job_id}: Loaded account removal list: {list_name}")

            if apply_contact_removal:
                contact_removal_list = db.get_active_removal_list('contact')
                if contact_removal_list and contact_removal_list.get('stored_path'):
                    stored_path = Path(contact_removal_list['stored_path'])
                    if stored_path.exists():
                        list_name = contact_removal_list.get('original_name', stored_path.name)
                        self.load_contact_removal_list(str(stored_path), list_name=list_name)
                        db.update_removal_list_last_used(contact_removal_list['id'])
                        logger.info(f"Job {job_id}: Loaded contact removal list: {list_name}")

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
            
            report_progress("Loading and combining input files...", 10)

            # Call the main processing method
            # We need to replicate the process_contacts logic but extract analytics
            result = self._process_with_analytics(
                settings=settings,
                include_all_firms=include_all_firms,
                user_prefix=user_prefix,
                output_filename=output_filename,
                filename_mapping=filename_mapping,
                cancel_event=cancel_event,
                job_id=job_id,
                progress_callback=progress_callback
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

    def _extract_premier_contacts(
        self,
        df: pd.DataFrame,
        premier_limit: int,
        separate_by_firm_type: bool
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Extract Premier contacts - top firms by AUM.

        Args:
            df: DataFrame with contacts (must have AUM_USD_MN column)
            premier_limit: Number of top firms per bucket
            separate_by_firm_type: Whether to extract per firm type or overall

        Returns:
            Tuple of (premier_df, remaining_df, stats)
            - premier_df: Contacts from top AUM firms
            - remaining_df: Contacts NOT in premier firms (for regular tier processing)
            - stats: Dictionary with extraction statistics
        """
        stats = {
            'enabled': True,
            'premier_limit': premier_limit,
            'premier_firms_count': 0,
            'premier_contacts_count': 0,
            'by_firm_type': separate_by_firm_type,
            'breakdown_by_type': {},
        }

        # Check for required columns
        if 'AUM_USD_MN' not in df.columns:
            logger.warning("Premier extraction requires AUM_USD_MN column, skipping")
            stats['enabled'] = False
            return pd.DataFrame(), df, stats

        # Find investor column
        investor_col = None
        for col in df.columns:
            if col.upper() in ['INVESTOR', 'ACCOUNT', 'FIRM', 'ACCOUNT NAME']:
                investor_col = col
                break

        if investor_col is None:
            logger.warning("No INVESTOR column found for Premier extraction")
            stats['enabled'] = False
            return pd.DataFrame(), df, stats

        # Only consider contacts WITH AUM data for Premier
        df_with_aum = df[df['AUM_USD_MN'].notna() & (df['AUM_USD_MN'] > 0)].copy()
        df_without_aum = df[df['AUM_USD_MN'].isna() | (df['AUM_USD_MN'] <= 0)].copy()

        if len(df_with_aum) == 0:
            logger.warning("No contacts have AUM data, skipping Premier extraction")
            stats['enabled'] = False
            return pd.DataFrame(), df, stats

        # Calculate max AUM per firm
        firm_aum = df_with_aum.groupby(investor_col)['AUM_USD_MN'].max().reset_index()
        firm_aum.columns = [investor_col, 'MAX_AUM']

        premier_firms = set()

        if separate_by_firm_type:
            # Extract top N per firm type bucket
            firm_type_col = None
            for col in df_with_aum.columns:
                if col.upper().replace('_', ' ').strip() in ['FIRM TYPE', 'FIRMTYPE', 'FIRM_TYPE']:
                    firm_type_col = col
                    break

            if firm_type_col is None:
                logger.warning("No FIRM TYPE column found, falling back to overall extraction")
                separate_by_firm_type = False
                stats['by_firm_type'] = False
            else:
                # Get firm type for each firm (take most common if multiple)
                firm_types = df_with_aum.groupby(investor_col)[firm_type_col].first().reset_index()
                firm_types.columns = [investor_col, 'FIRM_TYPE_VAL']

                # Merge AUM with firm type
                firm_aum = firm_aum.merge(firm_types, on=investor_col, how='left')

                # Classify into groups
                firm_aum['FIRM_TYPE_GROUP'] = firm_aum['FIRM_TYPE_VAL'].apply(self._classify_firm_type)

                # Get top N per group
                for group_name in ['Insurance', 'Wealth_FamilyOffice', 'Endowments_Foundations',
                                   'Pension_Funds', 'Funds_of_Funds', 'Other']:
                    group_firms = firm_aum[firm_aum['FIRM_TYPE_GROUP'] == group_name].copy()
                    group_firms = group_firms.sort_values('MAX_AUM', ascending=False)
                    top_firms = group_firms.head(premier_limit)[investor_col].tolist()

                    premier_firms.update(top_firms)

                    # Track stats per type
                    stats['breakdown_by_type'][group_name] = {
                        'firms': len(top_firms),
                        'contacts': 0,  # Will be calculated after filtering
                    }
                    logger.info(f"Premier extraction: {group_name} - {len(top_firms)} firms")

        if not separate_by_firm_type:
            # Extract top N overall
            firm_aum = firm_aum.sort_values('MAX_AUM', ascending=False)
            top_firms = firm_aum.head(premier_limit)[investor_col].tolist()
            premier_firms.update(top_firms)
            logger.info(f"Premier extraction: {len(top_firms)} top firms overall")

        # Filter contacts - Premier = contacts from top firms WITH AUM
        premier_mask = df_with_aum[investor_col].isin(premier_firms)
        premier_df = df_with_aum[premier_mask].copy()

        # Remaining = contacts from non-premier firms (with AUM) + contacts without AUM
        remaining_from_aum = df_with_aum[~premier_mask].copy()
        remaining_df = pd.concat([remaining_from_aum, df_without_aum], ignore_index=True)

        stats['premier_firms_count'] = len(premier_firms)
        stats['premier_contacts_count'] = len(premier_df)

        # Update breakdown stats with contact counts
        if separate_by_firm_type and stats['breakdown_by_type']:
            firm_type_col = None
            for col in premier_df.columns:
                if col.upper().replace('_', ' ').strip() in ['FIRM TYPE', 'FIRMTYPE', 'FIRM_TYPE']:
                    firm_type_col = col
                    break

            if firm_type_col:
                for group_name in stats['breakdown_by_type']:
                    group_mask = premier_df[firm_type_col].apply(
                        lambda x: self._classify_firm_type(x) == group_name
                    )
                    stats['breakdown_by_type'][group_name]['contacts'] = group_mask.sum()

        logger.info(
            f"Premier extraction complete: {stats['premier_firms_count']} firms, "
            f"{stats['premier_contacts_count']} contacts extracted"
        )

        return premier_df, remaining_df, stats
    
    def _process_with_analytics(
        self,
        settings: Dict[str, Any],
        include_all_firms: bool,
        user_prefix: str,
        output_filename: str,
        filename_mapping: Optional[Dict[str, str]] = None,
        cancel_event: Optional[threading.Event] = None,
        job_id: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Process contacts and extract analytics"""
        def report_progress(text: str, percent: int = 0):
            """Helper to safely call progress callback"""
            if progress_callback:
                try:
                    progress_callback(text, percent)
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")

        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        # Clean output folder
        logger.info(f"Job {job_id}: Cleaning and archiving output folder")
        self.filter.clean_and_archive_output()

        report_progress("Loading input files...", 12)

        # Load and combine input files
        logger.info(f"Job {job_id}: Loading and combining input files")
        combined_df, file_info = self.filter.load_and_combine_input_files()
        logger.info(f"Job {job_id}: Loaded {len(combined_df)} total rows from {len(file_info)} file(s)")

        report_progress(f"Loaded {len(combined_df):,} rows from {len(file_info)} file(s)", 18)
        
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
        
        report_progress("Standardizing columns...", 22)

        # Standardize columns
        logger.info(f"Job {job_id}: Standardizing columns")
        standardized_df = self.filter.standardize_columns(combined_df)
        logger.info(f"Job {job_id}: Standardized {len(standardized_df)} rows")

        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")

        report_progress("Checking for AUM data...", 28)

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

        report_progress("Removing duplicate contacts...", 35)

        # Remove duplicates
        logger.info(f"Job {job_id}: Removing duplicates")
        deduplicated_df = self.filter.remove_duplicates(standardized_df)
        dedup_count = len(deduplicated_df)
        logger.info(f"Job {job_id}: After deduplication: {dedup_count} rows (removed {len(standardized_df) - dedup_count} duplicates)")

        report_progress(f"Found {dedup_count:,} unique contacts", 40)
        
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        report_progress("Applying firm exclusion filters...", 45)

        # Apply firm exclusion if enabled
        if self.filter.enable_firm_exclusion:
            logger.info(f"Job {job_id}: Applying firm exclusion to {len(deduplicated_df)} contacts")
            self.filter.pre_exclusion_count = len(deduplicated_df)
            deduplicated_df = self.filter.apply_firm_exclusion(deduplicated_df)
            logger.info(f"Job {job_id}: After firm exclusion: {len(deduplicated_df)} contacts remain")

        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")

        report_progress("Applying firm inclusion filters...", 46)

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

        report_progress("Applying contact exclusion list...", 47)

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

        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")

        report_progress("Applying account removal list...", 48)

        # Apply account removal list (from uploaded CSV)
        account_removed_records = []
        account_removal_stats = {'contacts_removed': 0, 'accounts_matched': 0, 'exact_matches': 0, 'substring_matches': 0}
        if self.account_removal_set:
            logger.info(f"Job {job_id}: Applying account removal list to {len(deduplicated_df)} contacts")
            deduplicated_df, account_removed_records, account_removal_stats = self.apply_account_removal(deduplicated_df)
            logger.info(f"Job {job_id}: After account removal: {len(deduplicated_df)} contacts remain ({len(account_removed_records)} removed)")

        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")

        report_progress("Applying contact removal list...", 50)

        # Apply contact removal list (from uploaded CSV)
        contact_removed_records = []
        contact_removal_stats = {'contacts_removed': 0, 'email_matches': 0, 'name_account_matches': 0}
        if self.contact_removal_set:
            logger.info(f"Job {job_id}: Applying contact removal list to {len(deduplicated_df)} contacts")
            deduplicated_df, contact_removed_records, contact_removal_stats = self.apply_contact_removal(deduplicated_df)
            logger.info(f"Job {job_id}: After contact removal: {len(deduplicated_df)} contacts remain ({len(contact_removed_records)} removed)")

        # Store removal list records for delta analysis
        self.removal_list_removed = account_removed_records + contact_removed_records

        report_progress("Applying field filters...", 52)

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

                # Vectorized: normalize filter values and column values for matching
                normalized_filter_values = {str(v).lower().strip() for v in filter_values if v}
                column_lower = deduplicated_df[field_name].fillna('').astype(str).str.lower().str.strip()
                mask = column_lower.isin(normalized_filter_values)

                filtered_count = mask.sum()
                deduplicated_df = deduplicated_df[mask].copy()
                logger.info(f"Field filter '{field_name}': {filtered_count} contacts match {len(filter_values)} values")

            final_count = len(deduplicated_df)
            excluded_by_fields = initial_count - final_count
            if excluded_by_fields > 0:
                logger.info(f"Field filters excluded {excluded_by_fields} contacts ({initial_count} -> {final_count})")

        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")

        # Premier contacts extraction (before tier filtering)
        premier_df = None
        premier_stats = None
        extract_premier = settings.get("extractPremierContacts", False)
        premier_limit = settings.get("premierLimit", 25)
        separate_by_firm_type = settings.get("separateByFirmType", False)

        if extract_premier and enable_aum_merge:
            report_progress("Extracting Premier contacts...", 53)
            logger.info(f"Job {job_id}: Extracting Premier contacts (limit: {premier_limit}, by_firm_type: {separate_by_firm_type})")

            premier_df, deduplicated_df, premier_stats = self._extract_premier_contacts(
                deduplicated_df, premier_limit, separate_by_firm_type
            )

            if premier_stats and premier_stats.get('enabled'):
                logger.info(
                    f"Job {job_id}: Premier extraction - {premier_stats['premier_firms_count']} firms, "
                    f"{premier_stats['premier_contacts_count']} contacts removed from tier processing"
                )
                report_progress(
                    f"Extracted {premier_stats['premier_contacts_count']:,} Premier contacts from "
                    f"{premier_stats['premier_firms_count']} firms",
                    54
                )
            else:
                logger.info(f"Job {job_id}: Premier extraction skipped (no AUM data or disabled)")
                premier_df = None

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

        report_progress("Applying tier filters...", 55)

        # Apply tier filtering
        logger.info(f"Job {job_id}: Applying tier 1 filter (limit: {self.filter.tier1_limit}, requireInvestmentTeam: {tier1_config.get('require_investment_team', False)})")
        tier1_df = self.filter.apply_tier_filter(deduplicated_df, tier1_config, self.filter.tier1_limit)
        logger.info(f"Job {job_id}: Tier 1 result: {len(tier1_df)} contacts")
        
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")
        
        report_progress("Processing Tier 2 contacts...", 62)

        logger.info(f"Job {job_id}: Applying tier 2 filter (limit: {self.filter.tier2_limit}, requireInvestmentTeam: {tier2_config.get('require_investment_team', False)})")
        tier2_df = self.filter.apply_tier_filter(deduplicated_df, tier2_config, self.filter.tier2_limit)
        logger.info(f"Job {job_id}: Tier 2 result: {len(tier2_df)} contacts")

        report_progress(f"Selected {len(tier1_df):,} Tier 1 and {len(tier2_df):,} Tier 2 contacts", 68)
        
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
        
        report_progress("Finding email patterns...", 72)

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
        
        report_progress("Creating delta analysis...", 80)

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
        
        report_progress("Extracting analytics...", 85)

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

        # Add Premier extraction stats to analytics
        if premier_stats and premier_stats.get('enabled'):
            analytics["premier_extraction"] = {
                "enabled": True,
                "premier_limit": premier_stats.get('premier_limit', 25),
                "premier_firms_count": premier_stats.get('premier_firms_count', 0),
                "premier_contacts_count": premier_stats.get('premier_contacts_count', 0),
                "by_firm_type": premier_stats.get('by_firm_type', False),
                "breakdown_by_type": premier_stats.get('breakdown_by_type', {}),
            }
        else:
            analytics["premier_extraction"] = {"enabled": False}

        # Add removal list stats to analytics
        analytics["removal_list_stats"] = {
            "account_removal": {
                "applied": bool(self.account_removal_set),
                "list_name": self.account_removal_list_name,
                "list_size": self.account_removal_list_size,
                "contacts_removed": account_removal_stats.get('contacts_removed', 0),
                "accounts_matched": account_removal_stats.get('accounts_matched', 0),
            },
            "contact_removal": {
                "applied": bool(self.contact_removal_set),
                "list_name": self.contact_removal_list_name,
                "list_size": self.contact_removal_list_size,
                "contacts_removed": contact_removal_stats.get('contacts_removed', 0),
                "email_matches": contact_removal_stats.get('email_matches', 0),
                "name_account_matches": contact_removal_stats.get('name_account_matches', 0),
            },
            "total_removed": account_removal_stats.get('contacts_removed', 0) + contact_removal_stats.get('contacts_removed', 0),
        }

        # Check for cancellation before creating output file
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Job cancelled")

        report_progress("Creating output file...", 90)

        # Check if we need to separate by firm type
        separate_by_firm_type = settings.get("separateByFirmType", False)

        # Helper function to create Premier Excel file in memory
        def create_premier_excel_buffer(premier_contacts_df: pd.DataFrame) -> io.BytesIO:
            """Create an Excel file with Premier contacts in memory"""
            excel_buffer = io.BytesIO()
            standard_columns = ['NAME', 'INVESTOR', 'EMAIL', 'EMAIL_STATUS', 'EMAIL_SCHEMA', 'JOB_TITLE', 'AUM_USD_MN']

            # Add First Name and Last Name if they exist
            if len(premier_contacts_df) > 0 and 'First Name' in premier_contacts_df.columns:
                standard_columns.insert(0, 'First Name')
            if len(premier_contacts_df) > 0 and 'Last Name' in premier_contacts_df.columns:
                standard_columns.insert(1 if 'First Name' in standard_columns else 0, 'Last Name')

            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                if len(premier_contacts_df) > 0:
                    # Sort by AUM descending, then by firm name
                    sorted_df = premier_contacts_df.sort_values(
                        by=['AUM_USD_MN', 'INVESTOR'] if 'INVESTOR' in premier_contacts_df.columns else ['AUM_USD_MN'],
                        ascending=[False, True] if 'INVESTOR' in premier_contacts_df.columns else [False]
                    )
                    available_std_cols = [col for col in standard_columns if col in sorted_df.columns]
                    other_cols = [col for col in sorted_df.columns if col not in available_std_cols]
                    reordered_df = sorted_df[available_std_cols + other_cols]
                else:
                    reordered_df = premier_contacts_df
                reordered_df.to_excel(writer, sheet_name='Premier_Contacts', index=False)

            excel_buffer.seek(0)
            return excel_buffer

        # Determine if we need to create a ZIP (when separating by firm type OR when extracting Premier)
        has_premier = premier_df is not None and len(premier_df) > 0

        if separate_by_firm_type or has_premier:
            # Create ZIP file containing all output files
            logger.info(f"Job {job_id}: Creating ZIP file with output files")

            # Build firm type breakdown for analytics
            firm_type_breakdown = []
            files_in_zip = []

            # Create a zip file
            zip_filename = output_filename.replace('.xlsx', '.zip')
            zip_path = self.filter.output_folder / zip_filename

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:

                if separate_by_firm_type:
                    # Create 6 separate files by firm type
                    logger.info(f"Job {job_id}: Separating contacts by firm type into 6 files")

                    # Separate each tier by firm type
                    tier1_groups = self._separate_by_firm_type(tier1_df)
                    tier2_groups = self._separate_by_firm_type(tier2_df)
                    rescued_groups = self._separate_by_firm_type(rescued_df) if rescued_df is not None else None

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
                                available_std_cols = [col for col in standard_columns if col in group_rescued.columns]
                                other_cols = [col for col in group_rescued.columns if col not in available_std_cols]
                                rescued_reordered = group_rescued[available_std_cols + other_cols]
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

                    analytics["firm_type_breakdown"] = firm_type_breakdown
                    analytics["is_separated_by_firm_type"] = True

                else:
                    # Not separating by firm type - create single tiered file
                    logger.info(f"Job {job_id}: Creating main contacts file")
                    main_filename = output_filename  # Keep original .xlsx name
                    excel_buffer = io.BytesIO()

                    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                        standard_columns = ['NAME', 'INVESTOR', 'EMAIL', 'EMAIL_STATUS', 'EMAIL_SCHEMA', 'JOB_TITLE', 'AUM_USD_MN']

                        # Add First Name and Last Name if they exist
                        if len(tier1_df) > 0 and 'First Name' in tier1_df.columns:
                            standard_columns.insert(0, 'First Name')
                        if len(tier1_df) > 0 and 'Last Name' in tier1_df.columns:
                            standard_columns.insert(1 if 'First Name' in standard_columns else 0, 'Last Name')

                        # Write Tier 1 sheet
                        if len(tier1_df) > 0:
                            available_std_cols = [col for col in standard_columns if col in tier1_df.columns]
                            other_cols = [col for col in tier1_df.columns if col not in available_std_cols]
                            tier1_reordered = tier1_df[available_std_cols + other_cols]
                        else:
                            tier1_reordered = tier1_df
                        tier1_reordered.to_excel(writer, sheet_name='Tier1_Key_Contacts', index=False)

                        # Write Tier 2 sheet
                        if len(tier2_df) > 0:
                            available_std_cols = [col for col in standard_columns if col in tier2_df.columns]
                            other_cols = [col for col in tier2_df.columns if col not in available_std_cols]
                            tier2_reordered = tier2_df[available_std_cols + other_cols]
                        else:
                            tier2_reordered = tier2_df
                        tier2_reordered.to_excel(writer, sheet_name='Tier2_Junior_Contacts', index=False)

                        # Write Tier 3 sheet (rescued contacts)
                        if rescued_df is not None and len(rescued_df) > 0:
                            available_std_cols = [col for col in standard_columns if col in rescued_df.columns]
                            other_cols = [col for col in rescued_df.columns if col not in available_std_cols]
                            rescued_reordered = rescued_df[available_std_cols + other_cols]
                            rescued_reordered.to_excel(writer, sheet_name='Tier3_Rescued_Contacts', index=False)

                    excel_buffer.seek(0)
                    zipf.writestr(main_filename, excel_buffer.read())
                    logger.info(f"Job {job_id}: Added {main_filename} to zip")

                    # Track file info
                    tier3_count = len(rescued_df) if rescued_df is not None else 0
                    files_in_zip.append({
                        "filename": main_filename,
                        "firmTypeGroup": "All",
                        "tier1Contacts": len(tier1_df),
                        "tier2Contacts": len(tier2_df),
                        "tier3Contacts": tier3_count,
                        "totalContacts": len(tier1_df) + len(tier2_df) + tier3_count
                    })

                # Add Premier_Contacts.xlsx if Premier extraction was done
                if has_premier:
                    premier_filename = output_filename.replace('.xlsx', '_Premier_Contacts.xlsx')
                    premier_buffer = create_premier_excel_buffer(premier_df)
                    zipf.writestr(premier_filename, premier_buffer.read())
                    logger.info(f"Job {job_id}: Added {premier_filename} to zip ({len(premier_df)} contacts)")

                    # Track Premier file info
                    files_in_zip.append({
                        "filename": premier_filename,
                        "firmTypeGroup": "Premier",
                        "tier1Contacts": 0,
                        "tier2Contacts": 0,
                        "tier3Contacts": 0,
                        "totalContacts": len(premier_df),
                        "isPremier": True
                    })

            analytics["files_in_zip"] = files_in_zip
            logger.info(f"Job {job_id}: Created zip file: {zip_path}")
            output_path = str(zip_path)
            output_filename = zip_filename
            report_progress("Output files created", 95)
        else:
            # Create single Excel file (original behavior - no separation, no Premier)
            logger.info(f"Job {job_id}: Creating output Excel file: {output_filename}")
            output_path = self.filter.create_output_file(
                tier1_df, tier2_df, file_info, dedup_count, output_filename,
                deduplicated_df, delta_df, excluded_firms_analysis,
                rescued_df, rescue_stats, contact_lists_only=True
            )
            logger.info(f"Job {job_id}: Output file created at {output_path}")
            report_progress("Output file created", 95)

        report_progress("Processing complete", 100)

        return {
            "output_path": output_path,
            "output_filename": output_filename,
            "analytics": analytics
        }

