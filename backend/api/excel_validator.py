"""
Excel file validation service for multi-sheet file uploads.
Validates sheets, detects accounts/contacts sheets, and reports schema issues.
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Expected columns for accounts sheet (Preqin-style export)
ACCOUNTS_COLUMNS = {
    'required': ['FIRM ID', 'FIRM NAME'],
    'optional': [
        'CITY', 'COUNTRY', 'FIRM TYPE', 'FUNDS COUNT',
        'AUM (USD MN)', 'PE ALLOCATION (USD MN)', 'PE TARGET ALLOCATION (USD MN)',
        'PD ALLOCATION (USD MN)', 'PD TARGET ALLOCATION (USD MN)',
        'HF ALLOCATION (USD MN)', 'HF TARGET ALLOCATION (USD MN)',
        # Alternative column names
        'AUM', 'TOTAL AUM', 'ASSETS UNDER MANAGEMENT',
    ],
    # Aliases for fuzzy column matching
    'aliases': {
        'FIRM ID': ['FIRM_ID', 'FIRMID', 'ACCOUNT ID', 'ACCOUNT_ID', 'ID'],
        'FIRM NAME': ['FIRM_NAME', 'FIRMNAME', 'ACCOUNT NAME', 'ACCOUNT_NAME', 'INVESTOR', 'NAME'],
        'AUM (USD MN)': ['AUM', 'AUM_USD_MN', 'TOTAL AUM', 'ASSETS UNDER MANAGEMENT', 'TOTAL_AUM'],
    }
}

# Expected columns for contacts sheet
CONTACTS_COLUMNS = {
    'required': ['NAME'],  # At minimum we need contact names
    'optional': [
        'FIRM_ID', 'CONTACT_ID', 'INVESTOR', 'FIRM TYPE', 'TITLE',
        'ALTERNATIVE NAME', 'ROLE', 'JOB TITLE', 'ASSET CLASS',
        'EMAIL', 'TEL', 'CITY', 'STATE', 'COUNTRY/TERRITORY', 'ZIP CODE',
        'LINKEDIN', 'LAST UPDATED',
        # Alternative names
        'FIRM NAME', 'COMPANY', 'ACCOUNT', 'ACCOUNT NAME',
        'JOB_TITLE', 'POSITION', 'E-MAIL', 'EMAIL ADDRESS',
        'PHONE', 'TELEPHONE', 'COUNTRY',
    ],
    'aliases': {
        'NAME': ['FULL NAME', 'CONTACT NAME', 'CONTACT_NAME', 'FULLNAME'],
        'EMAIL': ['E-MAIL', 'EMAIL ADDRESS', 'EMAIL_ADDRESS', 'EMAILADDRESS'],
        'INVESTOR': ['FIRM NAME', 'FIRM_NAME', 'ACCOUNT', 'ACCOUNT NAME', 'COMPANY', 'EMPLOYER'],
        'JOB TITLE': ['JOB_TITLE', 'JOBTITLE', 'POSITION', 'TITLE', 'ROLE'],
        'FIRM_ID': ['FIRM ID', 'FIRMID', 'ACCOUNT_ID', 'ACCOUNT ID'],
    }
}

# Known sheet name patterns
ACCOUNTS_SHEET_PATTERNS = [
    'preqin_export', 'preqin', 'accounts', 'account', 'firms', 'firm',
    'investors', 'investor', 'companies', 'company', 'organizations',
]

CONTACTS_SHEET_PATTERNS = [
    'contacts_export', 'contacts', 'contact', 'people', 'persons',
    'employees', 'staff', 'team', 'members',
]

IGNORED_SHEET_PATTERNS = [
    'filters', 'filter', 'settings', 'config', 'metadata', 'info',
    'summary', 'notes', 'instructions', 'readme',
]


def normalize_column_name(col: str) -> str:
    """Normalize column name for comparison"""
    return str(col).upper().strip().replace('_', ' ').replace('-', ' ')


def find_column_match(columns: List[str], target: str, aliases: Dict[str, List[str]]) -> Optional[str]:
    """
    Find a column that matches the target or any of its aliases.
    Returns the actual column name if found, None otherwise.
    """
    target_normalized = normalize_column_name(target)
    target_aliases = [target_normalized]

    # Add aliases if available
    if target in aliases:
        target_aliases.extend([normalize_column_name(a) for a in aliases[target]])

    for col in columns:
        col_normalized = normalize_column_name(col)
        if col_normalized in target_aliases:
            return col

    return None


def detect_sheet_type(df: pd.DataFrame, sheet_name: str) -> Tuple[str, float]:
    """
    Detect whether a sheet is an accounts sheet, contacts sheet, or unknown.
    Returns (sheet_type, confidence_score)
    """
    if df is None or len(df) == 0:
        return 'empty', 0.0

    columns = list(df.columns)
    sheet_name_lower = sheet_name.lower().strip()

    # Check sheet name patterns first
    accounts_name_match = any(pattern in sheet_name_lower for pattern in ACCOUNTS_SHEET_PATTERNS)
    contacts_name_match = any(pattern in sheet_name_lower for pattern in CONTACTS_SHEET_PATTERNS)
    ignored_name_match = any(pattern in sheet_name_lower for pattern in IGNORED_SHEET_PATTERNS)

    if ignored_name_match:
        return 'metadata', 0.9

    # Score based on column matches
    accounts_score = 0.0
    contacts_score = 0.0

    # Check accounts columns
    for req_col in ACCOUNTS_COLUMNS['required']:
        if find_column_match(columns, req_col, ACCOUNTS_COLUMNS['aliases']):
            accounts_score += 0.3

    for opt_col in ACCOUNTS_COLUMNS['optional']:
        if find_column_match(columns, opt_col, ACCOUNTS_COLUMNS.get('aliases', {})):
            accounts_score += 0.1

    # Check for AUM column specifically (strong indicator of accounts sheet)
    aum_col = find_column_match(columns, 'AUM (USD MN)', ACCOUNTS_COLUMNS['aliases'])
    if aum_col:
        accounts_score += 0.3

    # Check contacts columns
    for req_col in CONTACTS_COLUMNS['required']:
        if find_column_match(columns, req_col, CONTACTS_COLUMNS['aliases']):
            contacts_score += 0.2

    for opt_col in CONTACTS_COLUMNS['optional']:
        if find_column_match(columns, opt_col, CONTACTS_COLUMNS.get('aliases', {})):
            contacts_score += 0.05

    # Check for email column (strong indicator of contacts sheet)
    email_col = find_column_match(columns, 'EMAIL', CONTACTS_COLUMNS['aliases'])
    if email_col:
        contacts_score += 0.3

    # Check for job title (strong indicator of contacts sheet)
    job_col = find_column_match(columns, 'JOB TITLE', CONTACTS_COLUMNS['aliases'])
    if job_col:
        contacts_score += 0.2

    # Apply name match bonus
    if accounts_name_match:
        accounts_score += 0.2
    if contacts_name_match:
        contacts_score += 0.2

    # Normalize scores
    accounts_score = min(accounts_score, 1.0)
    contacts_score = min(contacts_score, 1.0)

    # Determine type
    if accounts_score > contacts_score and accounts_score >= 0.4:
        return 'accounts', accounts_score
    elif contacts_score > accounts_score and contacts_score >= 0.3:
        return 'contacts', contacts_score
    elif contacts_score >= 0.3:
        return 'contacts', contacts_score
    else:
        return 'unknown', max(accounts_score, contacts_score)


def validate_accounts_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate accounts sheet schema and return issues/warnings.
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'columns_found': [],
        'columns_missing': [],
        'row_count': len(df),
        'aum_column': None,
        'firm_id_column': None,
        'firm_name_column': None,
    }

    columns = list(df.columns)

    # Check required columns
    for req_col in ACCOUNTS_COLUMNS['required']:
        matched = find_column_match(columns, req_col, ACCOUNTS_COLUMNS['aliases'])
        if matched:
            result['columns_found'].append({'expected': req_col, 'found': matched})
            if req_col == 'FIRM ID':
                result['firm_id_column'] = matched
            elif req_col == 'FIRM NAME':
                result['firm_name_column'] = matched
        else:
            result['columns_missing'].append(req_col)
            result['errors'].append(f"Missing required column: {req_col}")
            result['valid'] = False

    # Check for AUM column
    aum_col = find_column_match(columns, 'AUM (USD MN)', ACCOUNTS_COLUMNS['aliases'])
    if aum_col:
        result['columns_found'].append({'expected': 'AUM (USD MN)', 'found': aum_col})
        result['aum_column'] = aum_col

        # Check AUM data quality
        aum_values = df[aum_col].dropna()
        if len(aum_values) == 0:
            result['warnings'].append("AUM column exists but all values are empty")
        else:
            try:
                numeric_count = pd.to_numeric(aum_values, errors='coerce').notna().sum()
                if numeric_count < len(aum_values) * 0.5:
                    result['warnings'].append(f"Only {numeric_count}/{len(aum_values)} AUM values are numeric")
            except Exception:
                result['warnings'].append("Could not validate AUM values")
    else:
        result['warnings'].append("No AUM column found - AUM-based filtering will not be available")

    # Check for empty firm IDs
    if result['firm_id_column']:
        empty_ids = df[result['firm_id_column']].isna().sum()
        if empty_ids > 0:
            result['warnings'].append(f"{empty_ids} rows have empty firm IDs")

    return result


def validate_contacts_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate contacts sheet schema and return issues/warnings.
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'columns_found': [],
        'columns_missing': [],
        'row_count': len(df),
        'name_column': None,
        'email_column': None,
        'firm_id_column': None,
        'investor_column': None,
        'job_title_column': None,
    }

    columns = list(df.columns)

    # Check required columns
    for req_col in CONTACTS_COLUMNS['required']:
        matched = find_column_match(columns, req_col, CONTACTS_COLUMNS['aliases'])
        if matched:
            result['columns_found'].append({'expected': req_col, 'found': matched})
            if req_col == 'NAME':
                result['name_column'] = matched
        else:
            result['columns_missing'].append(req_col)
            result['errors'].append(f"Missing required column: {req_col}")
            result['valid'] = False

    # Check optional but important columns
    email_col = find_column_match(columns, 'EMAIL', CONTACTS_COLUMNS['aliases'])
    if email_col:
        result['columns_found'].append({'expected': 'EMAIL', 'found': email_col})
        result['email_column'] = email_col
    else:
        result['warnings'].append("No EMAIL column found")

    investor_col = find_column_match(columns, 'INVESTOR', CONTACTS_COLUMNS['aliases'])
    if investor_col:
        result['columns_found'].append({'expected': 'INVESTOR', 'found': investor_col})
        result['investor_column'] = investor_col
    else:
        result['warnings'].append("No INVESTOR/FIRM column found - cannot link to accounts")

    firm_id_col = find_column_match(columns, 'FIRM_ID', CONTACTS_COLUMNS['aliases'])
    if firm_id_col:
        result['columns_found'].append({'expected': 'FIRM_ID', 'found': firm_id_col})
        result['firm_id_column'] = firm_id_col

    job_col = find_column_match(columns, 'JOB TITLE', CONTACTS_COLUMNS['aliases'])
    if job_col:
        result['columns_found'].append({'expected': 'JOB TITLE', 'found': job_col})
        result['job_title_column'] = job_col
    else:
        result['warnings'].append("No JOB TITLE column found - tier filtering may be limited")

    # Check data quality
    if result['name_column']:
        empty_names = df[result['name_column']].isna().sum()
        if empty_names > 0:
            result['warnings'].append(f"{empty_names} contacts have empty names")

    if result['email_column']:
        empty_emails = df[result['email_column']].isna().sum()
        total = len(df)
        if empty_emails > total * 0.5:
            result['warnings'].append(f"{empty_emails}/{total} contacts have no email address")

    return result


def validate_excel_file(file_path: str) -> Dict[str, Any]:
    """
    Validate an Excel file and return detailed validation results.

    Returns:
        {
            'valid': bool,
            'can_process': bool,  # True if at least contacts sheet is valid
            'file_name': str,
            'sheets': [
                {
                    'name': str,
                    'type': 'accounts' | 'contacts' | 'metadata' | 'unknown',
                    'confidence': float,
                    'valid': bool,
                    'row_count': int,
                    'columns_found': [...],
                    'columns_missing': [...],
                    'errors': [...],
                    'warnings': [...],
                    'schema_details': {...}
                }
            ],
            'accounts_sheet': str | None,  # Name of detected accounts sheet
            'contacts_sheet': str | None,  # Name of detected contacts sheet
            'can_merge_aum': bool,  # True if accounts + contacts can be merged by FIRM_ID
            'summary': str,  # Human-readable summary
            'errors': [...],  # File-level errors
            'warnings': [...],  # File-level warnings
        }
    """
    result = {
        'valid': True,
        'can_process': False,
        'file_name': Path(file_path).name,
        'sheets': [],
        'accounts_sheet': None,
        'contacts_sheet': None,
        'can_merge_aum': False,
        'summary': '',
        'errors': [],
        'warnings': [],
    }

    try:
        # Load Excel file
        xlsx = pd.ExcelFile(file_path)
        sheet_names = xlsx.sheet_names

        if not sheet_names:
            result['valid'] = False
            result['errors'].append("Excel file has no sheets")
            return result

        accounts_firm_id_col = None
        contacts_firm_id_col = None

        # Analyze each sheet
        for sheet_name in sheet_names:
            try:
                df = pd.read_excel(xlsx, sheet_name=sheet_name)

                sheet_type, confidence = detect_sheet_type(df, sheet_name)

                sheet_info = {
                    'name': sheet_name,
                    'type': sheet_type,
                    'confidence': round(confidence, 2),
                    'valid': True,
                    'row_count': len(df),
                    'column_count': len(df.columns),
                    'columns': list(df.columns)[:20],  # First 20 columns
                    'columns_found': [],
                    'columns_missing': [],
                    'errors': [],
                    'warnings': [],
                    'schema_details': {},
                }

                if sheet_type == 'accounts':
                    schema_result = validate_accounts_schema(df)
                    sheet_info.update({
                        'valid': schema_result['valid'],
                        'columns_found': schema_result['columns_found'],
                        'columns_missing': schema_result['columns_missing'],
                        'errors': schema_result['errors'],
                        'warnings': schema_result['warnings'],
                        'schema_details': {
                            'aum_column': schema_result['aum_column'],
                            'firm_id_column': schema_result['firm_id_column'],
                            'firm_name_column': schema_result['firm_name_column'],
                        }
                    })

                    if schema_result['valid'] and result['accounts_sheet'] is None:
                        result['accounts_sheet'] = sheet_name
                        accounts_firm_id_col = schema_result['firm_id_column']

                elif sheet_type == 'contacts':
                    schema_result = validate_contacts_schema(df)
                    sheet_info.update({
                        'valid': schema_result['valid'],
                        'columns_found': schema_result['columns_found'],
                        'columns_missing': schema_result['columns_missing'],
                        'errors': schema_result['errors'],
                        'warnings': schema_result['warnings'],
                        'schema_details': {
                            'name_column': schema_result['name_column'],
                            'email_column': schema_result['email_column'],
                            'firm_id_column': schema_result['firm_id_column'],
                            'investor_column': schema_result['investor_column'],
                            'job_title_column': schema_result['job_title_column'],
                        }
                    })

                    if schema_result['valid'] and result['contacts_sheet'] is None:
                        result['contacts_sheet'] = sheet_name
                        contacts_firm_id_col = schema_result['firm_id_column']

                elif sheet_type == 'empty':
                    sheet_info['warnings'].append("Sheet is empty")

                result['sheets'].append(sheet_info)

            except Exception as e:
                logger.warning(f"Error reading sheet '{sheet_name}': {e}")
                result['sheets'].append({
                    'name': sheet_name,
                    'type': 'error',
                    'confidence': 0,
                    'valid': False,
                    'row_count': 0,
                    'errors': [f"Could not read sheet: {str(e)}"],
                    'warnings': [],
                })

        # Determine if file can be processed
        if result['contacts_sheet']:
            result['can_process'] = True
        elif result['accounts_sheet']:
            result['can_process'] = False
            result['errors'].append("File contains only accounts data - contacts sheet is required")
        else:
            result['can_process'] = False
            result['errors'].append("No recognizable contacts or accounts sheets found")

        # Check if AUM merge is possible
        if result['accounts_sheet'] and result['contacts_sheet']:
            if accounts_firm_id_col and contacts_firm_id_col:
                result['can_merge_aum'] = True
            else:
                result['warnings'].append(
                    "Both accounts and contacts sheets found, but cannot merge: "
                    "missing FIRM_ID column in one or both sheets"
                )

        # Generate summary
        if result['can_process']:
            parts = []
            if result['contacts_sheet']:
                contacts_info = next((s for s in result['sheets'] if s['name'] == result['contacts_sheet']), None)
                if contacts_info:
                    parts.append(f"Contacts: {contacts_info['row_count']} rows")
            if result['accounts_sheet']:
                accounts_info = next((s for s in result['sheets'] if s['name'] == result['accounts_sheet']), None)
                if accounts_info:
                    parts.append(f"Accounts: {accounts_info['row_count']} rows")
            if result['can_merge_aum']:
                parts.append("AUM data can be merged")
            result['summary'] = " | ".join(parts)
        else:
            result['summary'] = "File cannot be processed: " + "; ".join(result['errors'])

        result['valid'] = result['can_process'] and len(result['errors']) == 0

    except Exception as e:
        logger.error(f"Error validating Excel file: {e}")
        result['valid'] = False
        result['can_process'] = False
        result['errors'].append(f"Failed to read Excel file: {str(e)}")

    return result
