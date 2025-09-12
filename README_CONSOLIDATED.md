# Consolidated Tiered Contact Filter

## Overview

A unified filtering tool that consolidates all contact sources into a single tiered output with intelligent email pattern extraction and missing email filling capabilities.

## Key Features

✅ **Unified Processing**: Handles multiple input files and combines them intelligently  
✅ **Smart Duplicate Removal**: Removes duplicates based on name + firm combination  
✅ **Two-Tier Filtering**: Separates key contacts (Tier 1) from junior contacts (Tier 2)  
✅ **Flexible Investment Team Requirements**: Tier 1 contacts don't require investment team roles, Tier 2 contacts do  
✅ **Email Pattern Extraction**: Analyzes full dataset to extract firm-specific email patterns  
✅ **Missing Email Filling**: Uses extracted patterns to fill missing emails for final contacts  
✅ **Firm-Based Limits**: Max 10 Tier 1 contacts and max 6 Tier 2 contacts per firm  

## Usage

### Basic Usage
```bash
python3 consolidated_tiered_filter.py
```

### File Organization
- **Input**: Place Excel files in `/input` folder
- **Output**: Results saved to `/output` folder with timestamped names

### Output Naming
- **Single File**: `[OriginalName]_Tiered_List_[timestamp].xlsx`
- **Multiple Files**: `[UserPrefix]_Tiered_List_[timestamp].xlsx`

## Filtering Logic

### Tier 1: Key Contacts (Senior Decision Makers)
- **No Investment Team Requirement** - Prioritizes key contacts regardless of role classification
- **Max 10 contacts per firm**
- **Inclusion Criteria**:
  - C-Level: CIO, Chief Investment Officer, Deputy CIO
  - Leadership: Head of Investments, Head of Research, Head of Private Markets
  - Senior Management: Managing Director, Executive Director, President
  - Investment Focus: Portfolio Manager, Investment Director, Investment Manager

### Tier 2: Junior Contacts (Supporting Professionals)  
- **Investment Team Required** - Must be classified as investment team to avoid broad filtering
- **Max 6 contacts per firm**
- **Inclusion Criteria**:
  - Analysis: Investment Analyst, Research Analyst, Portfolio Analyst
  - Management: Director, Associate Director, Vice President
  - Advisory: Investment Advisor, Wealth Advisor, Trust Officer
  - Support: Associate, Principal, Coordinator, Specialist

## Email Pattern Extraction

The system analyzes the **full combined dataset** to extract email patterns by firm:

1. **Pattern Detection**: Identifies common formats like:
   - `firstname.lastname@company.com`
   - `firstinitiallastname@company.com` 
   - `firstname_lastname@company.com`
   - `firstnamelastname@company.com`

2. **Firm-Specific Patterns**: Each firm gets its own email pattern based on existing emails

3. **Missing Email Filling**: Uses the most common pattern per firm to generate missing emails

## Data Processing Pipeline

```
Input Files → Combine → Standardize Columns → Remove Duplicates → Extract Email Patterns
     ↓
Apply Tier 1 Filter → Apply Tier 2 Filter → Fill Missing Emails → Generate Output
```

## Output Structure

### Excel Sheets:
1. **Tier1_Key_Contacts**: Senior professionals with priority access
2. **Tier2_Junior_Contacts**: Junior professionals with investment team focus  
3. **Processing_Summary**: Statistics and processing metrics
4. **Input_Files**: Details of source files processed

## Removed Features (Simplified Logic)

❌ **Contact ID Exclusions**: No pre-processing exclusion lists  
❌ **Firm Exclusions**: No firm-based exclusion filtering  
❌ **Email Domain Filtering**: No business vs personal email filtering  
❌ **Email Validation**: No format validation or quality scoring  
❌ **Separate Tools**: Single tool handles all contact types  

## Examples

### Multiple Files Input
```
input/
├── Family_Office_Contacts.xlsx
├── Institutional_Contacts.xlsx
└── Additional_Contacts.xlsx

Output: "Combined-Contacts_Tiered_List_20250911_133045.xlsx"
```

### Single File Input
```
input/
└── Institutional_Contact_List.xlsx

Output: "Institutional_Contact_List_Tiered_List_20250911_133045.xlsx"
```

## Testing

Run the test suite to validate functionality:
```bash
python3 test_consolidated_filter.py
```

## Requirements

- pandas
- openpyxl 
- xlsxwriter

Install with:
```bash
pip install pandas openpyxl xlsxwriter
```
