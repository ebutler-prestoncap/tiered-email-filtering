/**
 * TypeScript interfaces for the application
 */

export interface TierFilterConfig {
  includeKeywords: string[];  // Job titles/keywords to include
  excludeKeywords: string[];  // Job titles/keywords to exclude
  requireInvestmentTeam: boolean;  // Whether investment team role is required
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
  status: 'pending' | 'processing' | 'completed' | 'failed';
  settings: ProcessingSettings;
  input_files: string[];
  output_filename?: string;
  analytics?: Analytics;
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
}

export interface ApiResponse<T> {
  success: boolean;
  error?: string;
  data?: T;
}

