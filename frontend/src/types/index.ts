/**
 * TypeScript interfaces for the application
 */

export interface TierFilterConfig {
  includeKeywords: string[];  // Job titles/keywords to include
  excludeKeywords: string[];  // Job titles/keywords to exclude
  requireInvestmentTeam: boolean;  // Whether investment team role is required
}

export interface FieldFilter {
  field: string;  // Column name (e.g., 'COUNTRY', 'CITY', 'ASSET_CLASS', 'FIRM_TYPE')
  values: string[];  // List of values to include (empty means no filter)
}

export interface ProcessingSettings {
  includeAllFirms: boolean;
  findEmails: boolean;
  firmExclusion: boolean;
  contactInclusion: boolean;
  tier1Limit: number;
  tier2Limit: number;
  tier3Limit: number;
  userPrefix: string;
  tier1Filters?: TierFilterConfig;  // Custom Tier 1 filter configuration
  tier2Filters?: TierFilterConfig;  // Custom Tier 2 filter configuration
  tier3Filters?: TierFilterConfig;  // Custom Tier 3 filter configuration
  firmExclusionList?: string;  // Inline list of firms to exclude (newline-separated)
  firmInclusionList?: string;  // Inline list of firms to include (newline-separated)
  contactExclusionList?: string;  // Inline list of contacts to exclude (format: Name|Firm, newline-separated)
  contactInclusionList?: string;  // Inline list of contacts to include (format: Name|Firm, newline-separated)
  fieldFilters?: FieldFilter[];  // Field-based filters (country, city, asset class, firm type, etc.)
  separateByFirmType?: boolean;  // Split output into separate files by firm type groups
  applyAccountRemovalList?: boolean;  // Whether to apply the active account removal list
  applyContactRemovalList?: boolean;  // Whether to apply the active contact removal list
  enableAumMerge?: boolean;  // Whether to merge AUM data from accounts sheets
  extractPremierContacts?: boolean;  // Whether to extract top firms by AUM into Premier list
  premierLimit?: number;  // Number of top firms per bucket for Premier list (default 25)
}

export interface SettingsPreset {
  id: string;
  name: string;
  is_default: boolean;
  settings: ProcessingSettings;
  created_at: string;
}

export interface Job {
  id: string;
  created_at: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  settings: ProcessingSettings;
  input_files: string[];
  output_filename?: string;
  analytics?: Analytics;
  progress_text?: string;
  progress_percent?: number;
}

export interface ProcessingSummary {
  input_files_count: number;
  total_raw_contacts: number;
  unique_contacts_after_dedup: number;
  unique_firms_after_dedup: number;
  avg_contacts_per_firm_before: number;
  median_contacts_per_firm_before: number;
  firm_exclusion_applied: boolean;
  firms_excluded: number;
  contacts_excluded_by_firm_filter: number;
  contact_inclusion_applied: boolean;
  contacts_in_inclusion_list: number;
  contacts_forced_through_filters: number;
  tier1_contacts: number;
  tier1_firms: number;
  avg_contacts_per_firm_tier1: number;
  median_contacts_per_firm_tier1: number;
  tier2_contacts: number;
  tier2_firms: number;
  avg_contacts_per_firm_tier2: number;
  median_contacts_per_firm_tier2: number;
  tier3_contacts: number;
  tier3_firms: number;
  total_filtered_contacts: number;
  total_firms_filtered: number;
  retention_rate: number;
  tier1_emails_available: number;
  tier2_emails_available: number;
  firm_rescue_applied: boolean;
  firms_rescued: number;
  contacts_rescued: number;
  firm_rescue_rate: number;
  processing_date: string;
}

export interface InputFileDetail {
  file: string;
  contacts: number;
  firms: string[];
}

export interface FirmTypeBreakdownEntry {
  firmTypeGroup: string;
  displayName: string;
  tier1Contacts: number;
  tier2Contacts: number;
  tier3Contacts: number;
  totalContacts: number;
}

export interface FileInZipEntry {
  filename: string;
  firmTypeGroup: string;
  tier1Contacts: number;
  tier2Contacts: number;
  tier3Contacts: number;
  totalContacts: number;
}

export interface Analytics {
  processing_summary: ProcessingSummary;
  input_file_details: InputFileDetail[];
  delta_analysis: any[] | null;
  delta_summary: Record<string, number> | null;
  filter_breakdown: Record<string, number> | null;
  excluded_firms_summary: {
    total_firms_after_dedup: number;
    included_firms_count: number;
    completely_excluded_firms_count: number;
    excluded_firm_contacts_count: number;
    exclusion_rate_firms: number;
    exclusion_rate_contacts: number;
  } | null;
  excluded_firms_list: string[];
  included_firms_list: string[];
  excluded_firm_contacts_count: number;
  // Firm type separation fields
  is_separated_by_firm_type?: boolean;
  firm_type_breakdown?: FirmTypeBreakdownEntry[];
  files_in_zip?: FileInZipEntry[];
  // AUM merge fields
  aum_merge?: {
    enabled: boolean;
    contacts_with_aum?: number;
    contacts_without_aum?: number;
    aum_min?: number | null;
    aum_max?: number | null;
    aum_avg?: number | null;
    merge_method?: string | null;
  };
  // Premier contacts extraction fields
  premier_extraction?: {
    enabled: boolean;
    premier_limit?: number;
    premier_firms_count?: number;
    premier_contacts_count?: number;
    by_firm_type?: boolean;
    breakdown_by_type?: Record<string, { firms: number; contacts: number }>;
  };
  // Removal list statistics
  removal_list_stats?: {
    account_removal: {
      applied: boolean;
      list_name?: string;
      list_size?: number;
      contacts_removed: number;
      accounts_matched: number;
    };
    contact_removal: {
      applied: boolean;
      list_name?: string;
      list_size?: number;
      contacts_removed: number;
      email_matches: number;
      name_account_matches: number;
    };
    total_removed: number;
  };
}

export interface ApiResponse<T> {
  success: boolean;
  error?: string;
  data?: T;
}

export interface RemovalList {
  id: string;
  listType: 'account' | 'contact';
  originalName: string;
  storedPath?: string;
  fileSize: number;
  entryCount: number;
  isActive: boolean;
  uploadedAt: string;
  lastUsedAt: string | null;
  fileExists?: boolean;
}

export interface ActiveRemovalLists {
  accountRemovalList: RemovalList | null;
  contactRemovalList: RemovalList | null;
}

