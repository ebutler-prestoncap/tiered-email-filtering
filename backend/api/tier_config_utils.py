"""
Utilities for converting user-friendly keyword lists to regex patterns for tier filtering.
"""
import re
from typing import List, Dict, Any


def keywords_to_regex_pattern(keywords: List[str]) -> str:
    """
    Convert a list of keywords to a regex pattern.
    
    Args:
        keywords: List of keyword strings (e.g., ["cio", "chief investment officer"])
        
    Returns:
        Regex pattern string that matches any of the keywords
    """
    if not keywords:
        return r'(?!.*)'  # Match nothing
    
    # Escape special regex characters and create word boundary patterns
    escaped_keywords = []
    for keyword in keywords:
        keyword = keyword.strip()
        if not keyword:
            continue
        
        # Escape special regex characters except spaces
        escaped = re.escape(keyword)
        # Replace escaped spaces with \s+ to allow flexible spacing
        escaped = escaped.replace(r'\ ', r'\s+')
        # Add word boundaries
        escaped = r'\b' + escaped + r'\b'
        escaped_keywords.append(escaped)
    
    if not escaped_keywords:
        return r'(?!.*)'
    
    # Combine with OR
    pattern = r'.*\b(' + r'|'.join(escaped_keywords) + r')\b'
    return pattern


def create_tier_config_from_keywords(
    name: str,
    description: str,
    include_keywords: List[str],
    exclude_keywords: List[str],
    require_investment_team: bool = False,
    priority_keywords: List[str] = None
) -> Dict[str, Any]:
    """
    Create a tier configuration dictionary from keyword lists.
    
    Args:
        name: Tier name
        description: Tier description
        include_keywords: List of keywords that must be in job title
        exclude_keywords: List of keywords that must NOT be in job title
        require_investment_team: Whether investment team role is required
        priority_keywords: List of keywords for priority scoring
        
    Returns:
        Tier configuration dictionary
    """
    return {
        'name': name,
        'description': description,
        'job_title_pattern': keywords_to_regex_pattern(include_keywords),
        'exclusion_pattern': keywords_to_regex_pattern(exclude_keywords),
        'require_investment_team': require_investment_team,
        'priority_keywords': priority_keywords or include_keywords[:10]  # Use first 10 as defaults
    }


def get_default_tier1_keywords() -> Dict[str, List[str]]:
    """Get default Tier 1 keywords"""
    return {
        'include': [
            'cio', 'c.i.o.', 'chief investment officer',
            'deputy chief investment officer', 'deputy cio',
            'head of investments', 'head of investment',
            'head of alternatives', 'head of alternative',
            'head of alternative investments', 'head of alternative investment',
            'head of private markets', 'head of private market',
            'head of private equity', 'head of private debt', 'head of private credit',
            'head of multi-asset', 'head of multi asset',
            'head of hedge funds', 'head of hedge fund',
            'head of hedge fund research', 'head of research',
            'head of manager research', 'head of manager selection',
            'investment director', 'director of investments', 'director of investment',
            'portfolio manager', 'fund manager', 'investment manager',
            'investment analyst', 'research analyst',
            'senior investment officer', 'investment officer', 'investment strategist',
            'asset allocation', 'multi-manager', 'multi manager',
            'manager research', 'due diligence',
            'managing director', 'managing partner',
            'executive director', 'senior portfolio manager',
            'president', 'vice president', 'senior vice president', 'executive vice president'
        ],
        'exclude': [
            'operations', 'operation', 'hr', 'human resources', 'human resource',
            'investor relations', 'investor relation', 'client relations', 'client relation',
            'marketing', 'sales', 'compliance', 'technology',
            'administrator', 'assistant', 'secretary', 'receptionist', 'intern', 'trainee'
        ]
    }


def get_default_tier2_keywords() -> Dict[str, List[str]]:
    """Get default Tier 2 keywords"""
    return {
        'include': [
            'director', 'associate director',
            'vice president', 'investment analyst', 'research analyst',
            'portfolio analyst', 'senior analyst', 'investment advisor',
            'principal', 'associate', 'coordinator', 'specialist', 'advisor', 'analyst'
        ],
        'exclude': [
            'operations', 'operation', 'hr', 'human resources', 'human resource',
            'investor relations', 'investor relation', 'client relations', 'client relation',
            'marketing', 'sales', 'compliance', 'technology',
            'administrator', 'assistant', 'secretary', 'receptionist', 'intern', 'trainee',
            'cio', 'chief investment officer', 'managing director', 'executive director',
            'president', 'senior vice president', 'executive vice president'
        ]
    }


def get_default_tier3_keywords() -> Dict[str, List[str]]:
    """Get default Tier 3 keywords (for rescue)"""
    return {
        'include': [
            'ceo', 'chief executive', 'managing director', 'managing partner',
            'cfo', 'chief financial', 'cio', 'chief investment',
            'coo', 'chief operating', 'president', 'chairman', 'chair',
            'director', 'partner', 'vice president',
            'manager', 'head of',
            'analyst', 'associate'
        ],
        'exclude': []
    }

