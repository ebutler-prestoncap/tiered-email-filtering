# Family Office Tiered Contact Filter

A specialized Python tool for implementing bucket overflow filtering on family office contact databases. This tool creates two tiers of filtered contacts based on importance and seniority.

## Overview

This tool implements a "bucket overflow" approach to contact filtering:

- **Tier 1 (Key Contacts)**: Most important contacts (CIO, hedge fund, private credit, fixed income, private debt, alternatives, head of investments, head of research) - max 10 per firm
- **Tier 2 (Junior Contacts)**: Remaining contacts that match junior criteria (research, portfolio, investment, analyst, associate) - max 6 total per firm

## Key Features

- **Bucket Overflow Logic**: Tier 1 acts as a bucket that can overflow into Tier 2
- **Firm-Based Processing**: Each firm is processed separately with individual limits
- **Priority-Based Selection**: Contacts are ranked by importance within each tier
- **No Duplicates**: Ensures no contact appears in both tiers
- **Comprehensive Reporting**: Detailed statistics and sample outputs

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python two_tier_filter_contacts.py
```

The script will process `AI list- Family offices (002).xlsx` and generate `Two_Tier_Filtered_Family_Office_Contacts.xlsx` with separate sheets for each tier.

## Input Requirements

- Excel file with "Contacts_Export" sheet
- Required columns: CONTACT_ID, INVESTOR, NAME, JOB TITLE, ROLE, EMAIL
- Contacts must have "Investment Team" in ROLE column

## Output

- **Tier1_Key_Contacts**: High-priority contacts (max 10 per firm)
- **Tier2_Junior_Contacts**: Junior contacts (max 6 total per firm)
- **Filtering_Summary**: Statistics and metrics

## Filtering Criteria

### Tier 1 (Key Contacts)
- CIO, Chief Investment Officer
- Hedge fund
- Private credit, Private debt, Fixed income
- Alternatives, Head of investments, Head of research
- Investment committee, Investment partner
- **Excludes**: Managing directors, operations, HR, marketing, sales

### Tier 2 (Junior Contacts)
- Research, Portfolio, Investment
- Analyst, Associate, Coordinator, Specialist
- Investment advisor, Wealth advisor, Trust officer
- **Excludes**: All Tier 1 titles, managing directors, operations, HR

## Dependencies

- pandas
- xlsxwriter
- openpyxl

## License

MIT License
