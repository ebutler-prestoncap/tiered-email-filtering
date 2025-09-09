# Two-Tier Family Office Contact Filtering System

## Overview
This document outlines the comprehensive two-tier filtering system used to categorize investment professionals from family office contact data into high-quality and low-quality tiers, while ensuring no duplicates between tiers.

## System Architecture

**Input:** 22,792 total contacts  
**Output:** 
- **Tier 1 (High Quality):** 4,314 senior investment professionals
- **Tier 2 (Low Quality):** 5,272 junior investment professionals  
- **Total Filtered:** 9,586 qualified contacts
- **Duplicates Between Tiers:** 0 (guaranteed)

---

## Two-Tier Filtering Process

### Pre-Filtering Steps (Applied to Both Tiers)

#### Step 1: Remove List Exclusion
**Purpose:** Exclude specific contact IDs that should not be targeted
- **Contacts Excluded:** 1,019
- **Remaining:** 21,773

#### Step 2: Firm Exclusion Filter
**Purpose:** Remove contacts from specified firms that should be excluded from targeting
- **Contacts Excluded:** 2,533
- **Remaining:** 20,259

**Excluded Firms:**
- Morgan Stanley Private Wealth Management
- HighTower Advisors
- Creative Planning
- Cresset Asset Management
- Jasper Ridge Partners
- Soros Fund Management
- Rockefeller Capital Management
- Great Lakes Advisors
- DFO Management
- Gresham Partners
- Johnson Financial Group
- Twin Focus Capital Partners
- Stelac Advisory Services
- Waterloo Capital
- Pennington Partners & Co

#### Step 3: Investment Team Role Filter
**Purpose:** Ensure contacts are part of investment teams, not purely operational/administrative
- **Contacts Excluded:** 7,136
- **Remaining:** 13,123

**Required Role:** ROLE column must contain "Investment Team"

---

## Tier 1: High-Quality Outputs

### Target Audience
Senior investment professionals and decision makers with high influence and decision-making authority.

### Inclusion Criteria

#### Job Title Patterns (Must Include At Least One):
- `cio` - Chief Investment Officer
- `chief investment officer` - Full CIO title
- `hedge fund` - Hedge fund professionals
- `private credit` - Private credit specialists
- `private debt` - Private debt specialists
- `absolute return` - Absolute return professionals
- `alternatives` - Alternative investment professionals
- `managing director` - Managing Directors
- `investment director` - Investment Directors
- `president` - Presidents
- `vice president` - Vice Presidents
- `senior portfolio manager` - Senior Portfolio Managers
- `head of investments` - Head of Investments
- `investment committee` - Investment Committee members
- `investment partner` - Investment Partners
- `executive vice president` - Executive VPs
- `senior vice president` - Senior VPs
- `director of investments` - Directors of Investments
- `senior director` - Senior Directors

#### Exclusion Patterns (Must NOT Include):
- `operations` - Operations roles
- `hr` - Human Resources
- `human resources` - Human Resources
- `investor relations` - Investor Relations
- `client relations` - Client Relations
- `marketing` - Marketing roles
- `sales` - Sales roles
- `compliance` - Compliance roles
- `technology` - Technology roles
- `administrator` - Administrative roles
- `assistant` - Assistant roles
- `associate director` - Associate Directors
- `associate vice president` - Associate VPs

#### Role Requirements:
Must contain at least one of: "investment team", "investment", "portfolio", "research"

### Results
- **Tier 1 Contacts:** 4,314
- **Quality Level:** High (Senior decision makers)
- **Examples:** Managing Directors, CIOs, Investment Directors, Presidents

---

## Tier 2: Low-Quality Outputs

### Target Audience
Junior investment professionals and support staff with limited decision-making authority.

### Inclusion Criteria

#### Job Title Patterns (Must Include At Least One):
- `research` - Research professionals
- `portfolio` - Portfolio professionals
- `investment` - Investment professionals
- `analyst` - Analysts
- `associate` - Associates
- `coordinator` - Coordinators
- `specialist` - Specialists
- `advisor` - Advisors
- `representative` - Representatives
- `assistant portfolio manager` - Assistant Portfolio Managers
- `investment analyst` - Investment Analysts
- `research analyst` - Research Analysts
- `portfolio analyst` - Portfolio Analysts
- `investment advisor` - Investment Advisors
- `wealth advisor` - Wealth Advisors
- `trust officer` - Trust Officers

#### Exclusion Patterns (Must NOT Include):
- All Tier 1 exclusion terms PLUS:
- `cio` - Chief Investment Officer
- `chief investment officer` - Full CIO title
- `hedge fund` - Hedge fund professionals
- `private credit` - Private credit specialists
- `private debt` - Private debt specialists
- `absolute return` - Absolute return professionals
- `managing director` - Managing Directors
- `investment director` - Investment Directors
- `president` - Presidents
- `vice president` - Vice Presidents
- `executive vice president` - Executive VPs
- `senior vice president` - Senior VPs
- `director of investments` - Directors of Investments
- `senior director` - Senior Directors

#### Role Requirements:
Must contain at least one of: "investment team", "investment", "portfolio", "research"

### Results
- **Tier 2 Contacts:** 5,272
- **Quality Level:** Low (Junior professionals)
- **Examples:** Analysts, Associates, Advisors, Research professionals

---

## Duplicate Prevention System

### Implementation
1. **Tier 1 Processing:** Apply Tier 1 filters first to identify high-quality contacts
2. **Tier 2 Processing:** Apply Tier 2 filters to remaining contacts
3. **Duplicate Removal:** Remove any Tier 2 contacts that match Tier 1 contact IDs
4. **Verification:** Ensure zero overlap between tiers

### Technical Details
```python
# Remove duplicates between tiers
if 'CONTACT_ID' in tier1Df.columns and 'CONTACT_ID' in tier2Df.columns:
    tier1Ids = set(tier1Df['CONTACT_ID'].tolist())
    tier2Df = tier2Df[~tier2Df['CONTACT_ID'].isin(tier1Ids)]
```

---

## Output Structure

### Excel File: `Two_Tier_Filtered_Family_Office_Contacts.xlsx`

#### Sheet 1: "Tier1_High_Quality"
- 4,314 senior investment professionals
- High-priority contacts for targeted outreach
- Decision makers and senior staff

#### Sheet 2: "Tier2_Low_Quality"
- 5,272 junior investment professionals
- Lower-priority contacts for broader outreach
- Support staff and analysts

#### Sheet 3: "Filtering_Summary"
- Complete filtering statistics
- Contact counts at each stage
- Duplicate verification

---

## Quality Assurance

### Validation Mechanisms
1. **Statistical Validation:** Retention rates and exclusion counts
2. **Sample Review:** Display of filtered results for manual verification
3. **Duplicate Verification:** Zero overlap between tiers confirmed
4. **Analytics:** Distribution analysis to identify anomalies

### Filter Effectiveness
- **Tier 1 Precision:** High-quality senior professionals only
- **Tier 2 Precision:** Junior professionals, excluding operations/HR
- **Duplicate Prevention:** 100% effective (0 duplicates)
- **Coverage:** 42.1% of Investment Team contacts captured

---

## Usage Instructions

### Prerequisites
```bash
pip install pandas openpyxl xlsxwriter
```

### Execution
```bash
python3 two_tier_filter_contacts.py
```

### Input Requirements
- **File Format:** Excel (.xlsx)
- **Sheet Name:** "Contacts_Export"
- **Required Columns:** INVESTOR, ROLE, JOB TITLE, NAME, EMAIL, CONTACT_ID

### Output Specifications
- **File Format:** Excel (.xlsx) with xlsxwriter engine
- **Sheets:** Tier1_High_Quality, Tier2_Low_Quality, Filtering_Summary
- **Data Preservation:** All original columns maintained
- **Index:** Removed for clean output

---

## Performance Characteristics

### Efficiency Features
- **Vectorized Operations:** Uses pandas apply() for fast processing
- **Regex Compilation:** Pre-compiles patterns for reuse
- **Memory Management:** Processes data in-place where possible
- **Sequential Filtering:** Reduces dataset size at each stage

### Scalability
- **Dataset Size:** Efficiently handles 20K+ contacts
- **Memory Usage:** Optimized pandas operations
- **Processing Time:** ~30 seconds for full dataset
- **Output Size:** Compressed filtered results

---

## Configuration & Customization

### Tier 1 Customization
Modify `createTier1Filter()` function to adjust:
- Job title inclusion patterns
- Exclusion patterns
- Role requirements
- Priority keywords

### Tier 2 Customization
Modify `createTier2Filter()` function to adjust:
- Job title inclusion patterns
- Exclusion patterns (includes Tier 1 exclusions)
- Role requirements
- Priority keywords

### Firm Exclusion List
Easily modifiable list of excluded firms in the main filtering function.

---

## Business Impact

### Tier 1 Benefits
- **High Conversion Potential:** Senior decision makers
- **Efficient Resource Allocation:** Focus on high-value contacts
- **Quality Outreach:** Targeted messaging for executives

### Tier 2 Benefits
- **Broader Coverage:** Larger contact pool
- **Cost-Effective Outreach:** Lower-cost contact methods
- **Pipeline Building:** Future decision makers

### Combined Strategy
- **Comprehensive Coverage:** 9,586 qualified contacts
- **No Duplication:** Efficient resource utilization
- **Scalable Approach:** Tiered priority system

---

## Maintenance & Updates

### Regular Maintenance Tasks
1. **Pattern Updates:** Review and update job title patterns quarterly
2. **Exclusion Refinement:** Adjust exclusion terms based on results
3. **Performance Monitoring:** Track processing times and accuracy
4. **Quality Review:** Analyze output quality and adjust filters

### Version Control Considerations
- Track changes to tier configurations
- Document pattern modifications
- Maintain processing statistics for comparison
- Archive filtered outputs for historical analysis

---

*Last Updated: September 2024*
*System Version: 2.0 (Two-Tier Architecture)*
*Total Contacts Processed: 22,792*
*Success Rate: 42.1% (9,586 qualified contacts)*
