#!/usr/bin/env python3
"""
Email Finding and Analysis Module for Tiered Contact Filtering
Provides email extraction, validation, analysis, and domain filtering capabilities
"""

import pandas as pd
import re
from typing import List, Dict, Set, Tuple, Any, Optional
from collections import Counter
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailFinder:
    """Advanced email finding, validation, and analysis functionality"""
    
    def __init__(self):
        # Comprehensive email regex pattern
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        )
        
        # Strict email validation pattern
        self.strict_email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        # Common business email domains (for prioritization)
        self.business_domains = {
            'gmail.com', 'outlook.com', 'yahoo.com', 'hotmail.com',
            'icloud.com', 'aol.com', 'comcast.net', 'verizon.net'
        }
        
        # Suspicious/temporary email domains to flag
        self.suspicious_domains = {
            '10minutemail.com', 'guerrillamail.com', 'mailinator.com',
            'tempmail.org', 'throwaway.email', 'temp-mail.org'
        }
    
    def find_emails_in_text(self, text: str) -> List[str]:
        """
        Extract all email addresses from a text string
        
        Args:
            text: Text to search for email addresses
            
        Returns:
            List of found email addresses
        """
        if not isinstance(text, str) or not text.strip():
            return []
        
        matches = self.email_pattern.findall(text)
        return [email.lower().strip() for email in matches]
    
    def validate_email(self, email: str) -> Dict[str, Any]:
        """
        Validate an email address and return detailed analysis
        
        Args:
            email: Email address to validate
            
        Returns:
            Dictionary with validation results and metadata
        """
        if not isinstance(email, str):
            return {
                'is_valid': False,
                'email': str(email),
                'normalized': '',
                'domain': '',
                'is_business': False,
                'is_suspicious': False,
                'issues': ['Not a string']
            }
        
        email = email.strip().lower()
        issues = []
        
        # Basic format validation
        is_valid = bool(self.strict_email_pattern.match(email))
        if not is_valid:
            issues.append('Invalid format')
        
        # Extract domain
        domain = ''
        if '@' in email:
            domain = email.split('@')[1]
        
        # Check for suspicious characteristics
        is_suspicious = domain in self.suspicious_domains
        if is_suspicious:
            issues.append('Suspicious domain')
        
        # Check if it's a common business domain
        is_business = domain not in self.business_domains
        
        # Additional validation checks
        if '..' in email:
            issues.append('Double dots')
            is_valid = False
        
        if email.startswith('.') or email.endswith('.'):
            issues.append('Starts or ends with dot')
            is_valid = False
        
        return {
            'is_valid': is_valid,
            'email': email,
            'normalized': email if is_valid else '',
            'domain': domain,
            'is_business': is_business,
            'is_suspicious': is_suspicious,
            'issues': issues
        }
    
    def analyze_email_column(self, df: pd.DataFrame, email_column: str = 'EMAIL') -> Dict[str, Any]:
        """
        Analyze email column in dataframe for quality and patterns
        
        Args:
            df: DataFrame to analyze
            email_column: Name of the email column
            
        Returns:
            Dictionary with analysis results
        """
        if email_column not in df.columns:
            return {
                'column_exists': False,
                'total_rows': len(df),
                'error': f'Column {email_column} not found'
            }
        
        emails = df[email_column].fillna('').astype(str)
        total_rows = len(df)
        
        # Basic statistics
        non_empty = emails[emails.str.strip() != '']
        empty_count = total_rows - len(non_empty)
        
        # Validate all emails
        validations = [self.validate_email(email) for email in emails]
        
        valid_emails = [v for v in validations if v['is_valid']]
        invalid_emails = [v for v in validations if not v['is_valid'] and v['email'].strip()]
        
        # Find duplicates
        email_list = [v['normalized'] for v in valid_emails]
        email_counts = Counter(email_list)
        duplicates = {email: count for email, count in email_counts.items() if count > 1}
        
        # Domain analysis
        domains = [v['domain'] for v in valid_emails if v['domain']]
        domain_counts = Counter(domains)
        
        # Business vs personal email analysis
        business_emails = [v for v in valid_emails if v['is_business']]
        personal_emails = [v for v in valid_emails if not v['is_business']]
        suspicious_emails = [v for v in valid_emails if v['is_suspicious']]
        
        return {
            'column_exists': True,
            'total_rows': total_rows,
            'empty_count': empty_count,
            'filled_count': total_rows - empty_count,
            'valid_count': len(valid_emails),
            'invalid_count': len(invalid_emails),
            'duplicate_count': sum(count - 1 for count in duplicates.values()),
            'unique_valid_count': len(email_counts),
            'business_count': len(business_emails),
            'personal_count': len(personal_emails),
            'suspicious_count': len(suspicious_emails),
            'duplicates': dict(list(duplicates.items())[:10]),  # Top 10 duplicates
            'top_domains': dict(domain_counts.most_common(10)),
            'quality_score': self._calculate_email_quality_score(
                total_rows, len(valid_emails), len(duplicates), len(suspicious_emails)
            ),
            'invalid_samples': [v['email'] for v in invalid_emails[:5]]
        }
    
    def _calculate_email_quality_score(self, total: int, valid: int, duplicate_count: int, suspicious: int) -> float:
        """Calculate email quality score (0-100)"""
        if total == 0:
            return 0.0
        
        validity_score = (valid / total) * 100
        duplicate_penalty = (duplicate_count / total) * 20
        suspicious_penalty = (suspicious / total) * 30
        
        score = max(0, validity_score - duplicate_penalty - suspicious_penalty)
        return round(score, 1)
    
    def find_emails_in_dataframe(self, df: pd.DataFrame, text_columns: List[str] = None) -> pd.DataFrame:
        """
        Find emails in text columns and add them as new columns
        
        Args:
            df: DataFrame to process
            text_columns: List of columns to search for emails (if None, searches all text columns)
            
        Returns:
            DataFrame with additional email columns
        """
        df_result = df.copy()
        
        if text_columns is None:
            # Auto-detect text columns
            text_columns = df.select_dtypes(include=['object']).columns.tolist()
        
        found_emails_data = []
        
        for idx, row in df.iterrows():
            row_emails = set()
            email_sources = {}
            
            for col in text_columns:
                if col in row and pd.notna(row[col]):
                    text = str(row[col])
                    emails = self.find_emails_in_text(text)
                    for email in emails:
                        row_emails.add(email)
                        if email not in email_sources:
                            email_sources[email] = []
                        email_sources[email].append(col)
            
            found_emails_data.append({
                'found_emails': list(row_emails),
                'email_count': len(row_emails),
                'email_sources': email_sources
            })
        
        # Add new columns
        df_result['found_emails'] = [data['found_emails'] for data in found_emails_data]
        df_result['found_email_count'] = [data['email_count'] for data in found_emails_data]
        df_result['email_sources'] = [data['email_sources'] for data in found_emails_data]
        
        return df_result
    
    def filter_by_email_domain(self, df: pd.DataFrame, domains: List[str], 
                              email_column: str = 'EMAIL', mode: str = 'include') -> pd.DataFrame:
        """
        Filter DataFrame by email domains
        
        Args:
            df: DataFrame to filter
            domains: List of domains to filter by
            email_column: Column containing email addresses
            mode: 'include' to keep only these domains, 'exclude' to remove them
            
        Returns:
            Filtered DataFrame
        """
        if email_column not in df.columns:
            logger.warning(f"Email column '{email_column}' not found")
            return df
        
        domains_lower = [d.lower() for d in domains]
        
        def matches_domain(email):
            if not isinstance(email, str) or '@' not in email:
                return False
            domain = email.split('@')[1].lower()
            return domain in domains_lower
        
        mask = df[email_column].apply(matches_domain)
        
        if mode == 'include':
            return df[mask]
        else:  # exclude
            return df[~mask]
    
    def clean_email_column(self, df: pd.DataFrame, email_column: str = 'EMAIL') -> pd.DataFrame:
        """
        Clean and normalize email column
        
        Args:
            df: DataFrame to clean
            email_column: Name of email column
            
        Returns:
            DataFrame with cleaned email column
        """
        df_result = df.copy()
        
        if email_column not in df.columns:
            logger.warning(f"Email column '{email_column}' not found")
            return df_result
        
        def clean_email(email):
            if not isinstance(email, str):
                return ''
            
            # Basic cleaning
            email = email.strip().lower()
            
            # Remove common prefixes/suffixes
            email = re.sub(r'^mailto:', '', email)
            email = re.sub(r'\s+', '', email)  # Remove all whitespace
            
            # Validate and return
            validation = self.validate_email(email)
            return validation['normalized'] if validation['is_valid'] else email
        
        df_result[email_column] = df[email_column].apply(clean_email)
        df_result[f'{email_column}_cleaned'] = df_result[email_column] != df[email_column]
        
        return df_result
    
    def generate_email_report(self, df: pd.DataFrame, email_column: str = 'EMAIL') -> str:
        """
        Generate comprehensive email analysis report
        
        Args:
            df: DataFrame to analyze
            email_column: Name of email column
            
        Returns:
            Formatted text report
        """
        analysis = self.analyze_email_column(df, email_column)
        
        if not analysis['column_exists']:
            return f"❌ Email analysis failed: {analysis['error']}"
        
        report = []
        report.append("📧 EMAIL ANALYSIS REPORT")
        report.append("=" * 50)
        
        # Overview
        report.append(f"\n📊 OVERVIEW:")
        report.append(f"Total contacts: {analysis['total_rows']:,}")
        report.append(f"Filled email fields: {analysis['filled_count']:,}")
        report.append(f"Empty email fields: {analysis['empty_count']:,}")
        report.append(f"Fill rate: {(analysis['filled_count']/analysis['total_rows']*100):.1f}%")
        
        # Quality metrics
        report.append(f"\n✅ QUALITY METRICS:")
        report.append(f"Valid emails: {analysis['valid_count']:,}")
        report.append(f"Invalid emails: {analysis['invalid_count']:,}")
        report.append(f"Duplicate emails: {analysis['duplicate_count']:,}")
        report.append(f"Unique valid emails: {analysis['unique_valid_count']:,}")
        report.append(f"Overall quality score: {analysis['quality_score']}/100")
        
        # Email types
        report.append(f"\n🏢 EMAIL TYPES:")
        report.append(f"Business emails: {analysis['business_count']:,}")
        report.append(f"Personal emails: {analysis['personal_count']:,}")
        report.append(f"Suspicious emails: {analysis['suspicious_count']:,}")
        
        # Top domains
        if analysis['top_domains']:
            report.append(f"\n🌐 TOP EMAIL DOMAINS:")
            for domain, count in list(analysis['top_domains'].items())[:5]:
                report.append(f"  {domain}: {count:,} contacts")
        
        # Duplicates
        if analysis['duplicates']:
            report.append(f"\n⚠️ DUPLICATE EMAILS (Top 5):")
            for email, count in list(analysis['duplicates'].items())[:5]:
                report.append(f"  {email}: {count} occurrences")
        
        # Invalid samples
        if analysis['invalid_samples']:
            report.append(f"\n❌ INVALID EMAIL SAMPLES:")
            for email in analysis['invalid_samples']:
                report.append(f"  {email}")
        
        return "\n".join(report)

def enhance_tiered_filtering_with_emails(input_file: str, output_file: str, 
                                        email_analysis: bool = True,
                                        domain_filters: Dict[str, List[str]] = None) -> None:
    """
    Enhance the existing tiered filtering with comprehensive email analysis
    
    Args:
        input_file: Path to input Excel file
        output_file: Path to output file
        email_analysis: Whether to perform email analysis
        domain_filters: Optional domain filters {'include': [...], 'exclude': [...]}
    """
    # Import the enhanced tiered filtering function
    from enhanced_two_tier_filter_contacts import enhancedTwoTierFilterContacts
    
    print("🚀 Enhanced Tiered Filtering with Email Intelligence")
    print("=" * 60)
    
    # Initialize email finder
    email_finder = EmailFinder()
    
    # Run enhanced tiered filtering
    print("\n📊 Running enhanced two-tier filtering...")
    tier1_df, tier2_df = enhancedTwoTierFilterContacts(input_file, output_file)
    
    if email_analysis:
        print("\n📧 Performing email analysis...")
        
        # Analyze emails in both tiers
        tier1_analysis = email_finder.analyze_email_column(tier1_df, 'EMAIL')
        tier2_analysis = email_finder.analyze_email_column(tier2_df, 'EMAIL')
        
        print(f"\n📊 TIER 1 EMAIL ANALYSIS:")
        print(f"Valid emails: {tier1_analysis['valid_count']:,}/{tier1_analysis['total_rows']:,}")
        print(f"Quality score: {tier1_analysis['quality_score']}/100")
        
        print(f"\n📊 TIER 2 EMAIL ANALYSIS:")
        print(f"Valid emails: {tier2_analysis['valid_count']:,}/{tier2_analysis['total_rows']:,}")
        print(f"Quality score: {tier2_analysis['quality_score']}/100")
        
        # Apply domain filters if specified
        if domain_filters:
            if 'exclude' in domain_filters:
                print(f"\n🚫 Applying domain exclusions: {domain_filters['exclude']}")
                tier1_df = email_finder.filter_by_email_domain(
                    tier1_df, domain_filters['exclude'], mode='exclude'
                )
                tier2_df = email_finder.filter_by_email_domain(
                    tier2_df, domain_filters['exclude'], mode='exclude'
                )
            
            if 'include' in domain_filters:
                print(f"\n✅ Applying domain inclusions: {domain_filters['include']}")
                tier1_df = email_finder.filter_by_email_domain(
                    tier1_df, domain_filters['include'], mode='include'
                )
                tier2_df = email_finder.filter_by_email_domain(
                    tier2_df, domain_filters['include'], mode='include'
                )
        
        # Clean email columns
        print("\n🧹 Cleaning email data...")
        tier1_df = email_finder.clean_email_column(tier1_df)
        tier2_df = email_finder.clean_email_column(tier2_df)
        
        # Generate comprehensive reports
        tier1_report = email_finder.generate_email_report(tier1_df)
        tier2_report = email_finder.generate_email_report(tier2_df)
        
        # Save enhanced results with email analysis
        enhanced_output = output_file.replace('.xlsx', '_with_email_analysis.xlsx')
        with pd.ExcelWriter(enhanced_output, engine='xlsxwriter') as writer:
            tier1_df.to_excel(writer, sheet_name="Tier1_Key_Contacts", index=False)
            tier2_df.to_excel(writer, sheet_name="Tier2_Junior_Contacts", index=False)
            
            # Create email analysis summary
            email_summary = {
                'Metric': [
                    'Tier 1 Total Contacts',
                    'Tier 1 Valid Emails',
                    'Tier 1 Email Quality Score',
                    'Tier 2 Total Contacts', 
                    'Tier 2 Valid Emails',
                    'Tier 2 Email Quality Score',
                    'Combined Valid Emails',
                    'Overall Email Coverage'
                ],
                'Value': [
                    tier1_analysis['total_rows'],
                    tier1_analysis['valid_count'],
                    f"{tier1_analysis['quality_score']}/100",
                    tier2_analysis['total_rows'],
                    tier2_analysis['valid_count'],
                    f"{tier2_analysis['quality_score']}/100",
                    tier1_analysis['valid_count'] + tier2_analysis['valid_count'],
                    f"{((tier1_analysis['valid_count'] + tier2_analysis['valid_count']) / (tier1_analysis['total_rows'] + tier2_analysis['total_rows']) * 100):.1f}%"
                ]
            }
            
            summary_df = pd.DataFrame(email_summary)
            summary_df.to_excel(writer, sheet_name="Email_Analysis_Summary", index=False)
        
        print(f"\n✅ Enhanced filtering complete with email analysis!")
        print(f"Enhanced output saved to: {enhanced_output}")
        print(f"\nFinal Results:")
        print(f"  - Tier 1 (Key Contacts): {len(tier1_df)} contacts with {tier1_analysis['valid_count']} valid emails")
        print(f"  - Tier 2 (Junior Contacts): {len(tier2_df)} contacts with {tier2_analysis['valid_count']} valid emails")
        print(f"  - Total valid emails: {tier1_analysis['valid_count'] + tier2_analysis['valid_count']:,}")

if __name__ == "__main__":
    # Example usage with domain filtering
    domain_filters = {
        'exclude': ['gmail.com', 'yahoo.com', 'hotmail.com'],  # Exclude personal emails
        # 'include': ['company1.com', 'company2.com']  # Only include specific domains
    }
    
    enhance_tiered_filtering_with_emails(
        "input/AI list- Family offices (002).xlsx",
        "output/Enhanced_Tiered_Filtered_Contacts.xlsx",
        email_analysis=True,
        domain_filters=domain_filters
    )
