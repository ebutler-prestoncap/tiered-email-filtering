"""
Extract analytics data from TieredFilter processing results.
Converts DataFrames to JSON-serializable format.
"""
import pandas as pd
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def extract_analytics(
    tier1_df: pd.DataFrame,
    tier2_df: pd.DataFrame,
    rescued_df: Optional[pd.DataFrame],
    file_info: list,
    dedup_count: int,
    deduplicated_df: pd.DataFrame,
    delta_df: Optional[pd.DataFrame],
    excluded_firms_analysis: Optional[Dict],
    rescue_stats: Optional[Dict],
    filter_instance: Any
) -> Dict[str, Any]:
    """
    Extract all analytics data from processing results.
    
    Returns a dictionary with all analytics data in JSON-serializable format.
    """
    analytics = {}
    
    # Processing Summary
    analytics["processing_summary"] = extract_processing_summary(
        tier1_df, tier2_df, rescued_df, file_info, dedup_count,
        deduplicated_df, rescue_stats, filter_instance
    )
    
    # Input File Details
    analytics["input_file_details"] = extract_input_file_details(file_info)
    
    # Delta Analysis
    if delta_df is not None:
        analytics["delta_analysis"] = dataframe_to_dict(delta_df)
        analytics["delta_summary"] = extract_delta_summary(delta_df)
        # Filter breakdown removed - no longer extracted
        analytics["filter_breakdown"] = None
    else:
        analytics["delta_analysis"] = None
        analytics["delta_summary"] = None
        analytics["filter_breakdown"] = None
    
    # Excluded Firms Analysis
    if excluded_firms_analysis:
        analytics["excluded_firms_summary"] = extract_excluded_firms_summary(
            excluded_firms_analysis, dedup_count
        )
        analytics["excluded_firms_list"] = excluded_firms_analysis.get("completely_excluded_firms", [])
        analytics["included_firms_list"] = excluded_firms_analysis.get("included_firms", [])
        analytics["excluded_firm_contacts_count"] = len(excluded_firms_analysis.get("excluded_firm_contacts", pd.DataFrame()))
    else:
        analytics["excluded_firms_summary"] = None
        analytics["excluded_firms_list"] = []
        analytics["included_firms_list"] = []
        analytics["excluded_firm_contacts_count"] = 0
    
    return analytics

def extract_processing_summary(
    tier1_df: pd.DataFrame,
    tier2_df: pd.DataFrame,
    rescued_df: Optional[pd.DataFrame],
    file_info: list,
    dedup_count: int,
    deduplicated_df: pd.DataFrame,
    rescue_stats: Optional[Dict],
    filter_instance: Any
) -> Dict[str, Any]:
    """Extract processing summary statistics"""
    total_raw = sum(info.get("contacts", 0) for info in file_info)
    
    # Calculate firm counts
    unique_firms_after_dedup = 0
    avg_contacts_per_firm_before = 0
    median_contacts_per_firm_before = 0
    
    if deduplicated_df is not None and "INVESTOR" in deduplicated_df.columns and len(deduplicated_df) > 0:
        unique_firms_after_dedup = deduplicated_df["INVESTOR"].nunique()
        firm_contact_counts_before = deduplicated_df["INVESTOR"].value_counts()
        avg_contacts_per_firm_before = float(firm_contact_counts_before.mean())
        median_contacts_per_firm_before = float(firm_contact_counts_before.median())
    
    # Tier statistics
    tier1_firms = tier1_df["INVESTOR"].nunique() if "INVESTOR" in tier1_df.columns and len(tier1_df) > 0 else 0
    tier2_firms = tier2_df["INVESTOR"].nunique() if "INVESTOR" in tier2_df.columns and len(tier2_df) > 0 else 0
    
    avg_contacts_per_firm_tier1 = 0
    median_contacts_per_firm_tier1 = 0
    if len(tier1_df) > 0 and "INVESTOR" in tier1_df.columns:
        tier1_firm_counts = tier1_df["INVESTOR"].value_counts()
        avg_contacts_per_firm_tier1 = float(tier1_firm_counts.mean())
        median_contacts_per_firm_tier1 = float(tier1_firm_counts.median())
    
    avg_contacts_per_firm_tier2 = 0
    median_contacts_per_firm_tier2 = 0
    if len(tier2_df) > 0 and "INVESTOR" in tier2_df.columns:
        tier2_firm_counts = tier2_df["INVESTOR"].value_counts()
        avg_contacts_per_firm_tier2 = float(tier2_firm_counts.mean())
        median_contacts_per_firm_tier2 = float(tier2_firm_counts.median())
    
    # Total firms across both tiers
    if len(tier1_df) > 0 and len(tier2_df) > 0 and "INVESTOR" in tier1_df.columns and "INVESTOR" in tier2_df.columns:
        all_tier_firms = set(tier1_df["INVESTOR"].dropna().unique()) | set(tier2_df["INVESTOR"].dropna().unique())
        total_firms_filtered = len(all_tier_firms)
    else:
        total_firms_filtered = tier1_firms + tier2_firms
    
    # Firm exclusion stats
    firms_excluded_count = 0
    contacts_excluded_count = 0
    if hasattr(filter_instance, "enable_firm_exclusion") and filter_instance.enable_firm_exclusion:
        if hasattr(filter_instance, "excluded_firms"):
            firms_excluded_count = len(filter_instance.excluded_firms)
        if hasattr(filter_instance, "pre_exclusion_count"):
            contacts_excluded_count = filter_instance.pre_exclusion_count - len(deduplicated_df) if deduplicated_df is not None else 0
    
    # Contact inclusion stats
    contacts_included_count = 0
    contacts_forced_included = 0
    if hasattr(filter_instance, "enable_contact_inclusion") and filter_instance.enable_contact_inclusion:
        if hasattr(filter_instance, "included_contacts"):
            contacts_included_count = len(filter_instance.included_contacts)
        contacts_forced_included = getattr(filter_instance, "contacts_forced_included", 0)
    
    # Email stats
    tier1_emails = tier1_df["EMAIL"].notna().sum() if len(tier1_df) > 0 and "EMAIL" in tier1_df.columns else 0
    tier2_emails = tier2_df["EMAIL"].notna().sum() if len(tier2_df) > 0 and "EMAIL" in tier2_df.columns else 0
    
    # Tier 3 stats
    tier3_count = len(rescued_df) if rescued_df is not None else 0
    tier3_firms = rescued_df["INVESTOR"].nunique() if rescued_df is not None and len(rescued_df) > 0 and "INVESTOR" in rescued_df.columns else 0
    
    # Retention rate
    total_filtered = len(tier1_df) + len(tier2_df) + tier3_count
    retention_rate = (total_filtered / total_raw * 100) if total_raw > 0 else 0.0
    
    return {
        "input_files_count": len(file_info),
        "total_raw_contacts": total_raw,
        "unique_contacts_after_dedup": dedup_count,
        "unique_firms_after_dedup": unique_firms_after_dedup,
        "avg_contacts_per_firm_before": avg_contacts_per_firm_before,
        "median_contacts_per_firm_before": median_contacts_per_firm_before,
        "firm_exclusion_applied": getattr(filter_instance, "enable_firm_exclusion", False),
        "firms_excluded": firms_excluded_count,
        "contacts_excluded_by_firm_filter": contacts_excluded_count,
        "contact_inclusion_applied": getattr(filter_instance, "enable_contact_inclusion", False),
        "contacts_in_inclusion_list": contacts_included_count,
        "contacts_forced_through_filters": contacts_forced_included,
        "tier1_contacts": len(tier1_df),
        "tier1_firms": tier1_firms,
        "avg_contacts_per_firm_tier1": avg_contacts_per_firm_tier1,
        "median_contacts_per_firm_tier1": median_contacts_per_firm_tier1,
        "tier2_contacts": len(tier2_df),
        "tier2_firms": tier2_firms,
        "avg_contacts_per_firm_tier2": avg_contacts_per_firm_tier2,
        "median_contacts_per_firm_tier2": median_contacts_per_firm_tier2,
        "tier3_contacts": tier3_count,
        "tier3_firms": tier3_firms,
        "total_filtered_contacts": total_filtered,
        "total_firms_filtered": total_firms_filtered,
        "retention_rate": retention_rate,
        "tier1_emails_available": int(tier1_emails),
        "tier2_emails_available": int(tier2_emails),
        "firm_rescue_applied": rescue_stats is not None and rescue_stats.get("rescued_contacts", 0) > 0,
        "firms_rescued": rescue_stats.get("rescued_firms", 0) if rescue_stats else 0,
        "contacts_rescued": rescue_stats.get("rescued_contacts", 0) if rescue_stats else 0,
        "firm_rescue_rate": rescue_stats.get("rescue_rate", 0.0) if rescue_stats else 0.0,
        "processing_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def extract_input_file_details(file_info: list) -> list:
    """Extract input file details"""
    return [
        {
            "file": info.get("file", ""),
            "contacts": info.get("contacts", 0),
            "firms": info.get("firms", []) if isinstance(info.get("firms"), list) else []
        }
        for info in file_info
    ]

def extract_delta_summary(delta_df: pd.DataFrame) -> Dict[str, int]:
    """Extract delta summary (status counts)"""
    if "PROCESSING_STATUS" not in delta_df.columns:
        return {}
    
    status_counts = delta_df["PROCESSING_STATUS"].value_counts().to_dict()
    return {str(k): int(v) for k, v in status_counts.items()}

def extract_filter_breakdown(delta_df: pd.DataFrame) -> Dict[str, int]:
    """Extract filter breakdown (reasons for exclusions)"""
    if "FILTER_REASON" not in delta_df.columns:
        return {}
    
    removed_df = delta_df[delta_df["PROCESSING_STATUS"] == "Removed"]
    if len(removed_df) == 0:
        return {}
    
    filter_counts = removed_df["FILTER_REASON"].value_counts().to_dict()
    return {str(k): int(v) for k, v in filter_counts.items()}

def extract_excluded_firms_summary(excluded_firms_analysis: Dict, dedup_count: int) -> Dict[str, Any]:
    """Extract excluded firms summary"""
    total_firms = excluded_firms_analysis.get("total_firms_after_dedup", 0)
    included_firms_count = excluded_firms_analysis.get("included_firms_count", 0)
    completely_excluded_firms_count = excluded_firms_analysis.get("completely_excluded_firms_count", 0)
    excluded_firm_contacts_count = excluded_firms_analysis.get("excluded_firm_contacts_count", 0)
    
    exclusion_rate_firms = (completely_excluded_firms_count / total_firms * 100) if total_firms > 0 else 0.0
    exclusion_rate_contacts = (excluded_firm_contacts_count / dedup_count * 100) if dedup_count > 0 else 0.0
    
    return {
        "total_firms_after_dedup": total_firms,
        "included_firms_count": included_firms_count,
        "completely_excluded_firms_count": completely_excluded_firms_count,
        "excluded_firm_contacts_count": excluded_firm_contacts_count,
        "exclusion_rate_firms": exclusion_rate_firms,
        "exclusion_rate_contacts": exclusion_rate_contacts
    }

def dataframe_to_dict(df: pd.DataFrame) -> list:
    """Convert DataFrame to list of dictionaries"""
    if df is None or len(df) == 0:
        return []
    
    # Replace NaN with None for JSON serialization
    df = df.where(pd.notnull(df), None)
    
    # Convert to dict, handling datetime and other types
    records = df.to_dict("records")
    
    # Convert any remaining non-serializable types
    for record in records:
        for key, value in record.items():
            if pd.isna(value) if isinstance(value, (float, type(None))) else False:
                record[key] = None
            elif isinstance(value, (pd.Timestamp, pd.Timedelta)):
                record[key] = str(value)
            elif isinstance(value, (int, float)) and pd.isna(value):
                record[key] = None
    
    return records

