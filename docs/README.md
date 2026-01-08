# Tiered Email Filtering - Documentation

This folder contains comprehensive documentation for the tiered contact filtering system.

## Documentation Files

### [FILTERING_LOGIC.md](./FILTERING_LOGIC.md)
Complete outline of all filtering criteria, inclusions, exclusions, and processing logic for all tiers.

### [FILE_STORAGE.md](./FILE_STORAGE.md)
Comprehensive documentation of the file storage architecture, including how files are stored on disk vs. in the database, persistence across restarts, and file reuse capabilities.

**Sections:**
- Pre-Filtering Steps (deduplication, firm exclusion, contact inclusion)
- Tier 1 - Key Contacts (senior decision makers)
- Tier 2 - Junior Contacts (supporting professionals)
- Tier 3 - Rescued Contacts (from excluded firms)
- Email Discovery & Filling
- Priority Scoring System
- Firm-Based Limits

## Quick Reference

### Tier 1 - Key Contacts
- **Max per firm:** 10
- **Investment team required:** No
- **Targets:** CIO, Chief Investment Officer, Deputy CIO, Head of Investments/Alternatives/Private Markets/Private Equity/Private Debt/Private Credit/Multi-Asset/Hedge Funds/Research/Manager Research/Manager Selection, Investment Director, Director of Investments, Portfolio Manager, Fund Manager, Investment Manager, Investment Analyst, Research Analyst, Senior Investment Officer, Investment Officer, Investment Strategist, Asset Allocation, Multi-Manager, Manager Research, Due Diligence, Managing Director, Managing Partner, President
- **Excludes:** Operations, HR, marketing, sales, compliance, technology, administrative roles

### Tier 2 - Junior Contacts
- **Max per firm:** 6
- **Investment team required:** Yes
- **Targets:** Director, Associate Director, Vice President, Analyst, Associate, Principal, Advisor
- **Excludes:** All Tier 1 exclusions + Tier 1 inclusion terms (to prevent overlap)

### Tier 3 - Rescued Contacts
- **Max per firm:** 1-3 (default: 3)
- **Activation:** `--include-all-firms` flag
- **Targets:** Top contacts from firms with zero Tier 1/2 contacts
- **Priority:** CEOs, CFOs, Directors prioritized

## Command-Line Options

```bash
# Standard filtering
python3 tiered_filter.py

# Include contacts from excluded firms (Tier 3)
python3 tiered_filter.py --include-all-firms

# Discover and fill emails
python3 tiered_filter.py --find-emails

# Combine both features
python3 tiered_filter.py --include-all-firms --find-emails
```

## Optional Features

### Firm Exclusion
- **File:** `input/firm exclusion.csv`
- **Format:** CSV with firm names
- **Effect:** Removes all contacts from listed firms

### Contact Inclusion
- **File:** `input/include_contacts.csv`
- **Format:** CSV with `Institution_Name`, `Full_Name` columns
- **Effect:** Forces specific contacts through filters

## Output Structure

The system generates an Excel file with the following sheets:

1. **Tier1_Key_Contacts** - Senior decision makers
2. **Tier2_Junior_Contacts** - Junior professionals
3. **Tier3_Rescued_Contacts** - Rescued contacts (if enabled)
4. **Processing_Summary** - Statistics and metrics
5. **Input_File_Details** - Source file information
6. **Delta_Analysis** - Detailed filtering decisions
7. **Excluded_Firms_Summary** - Firm exclusion impact
8. **Excluded_Firms_List** - List of completely excluded firms
9. **Included_Firms_List** - List of firms with contacts included
10. **Excluded_Firm_Contacts** - All contacts from excluded firms

---

For detailed filtering logic, see [FILTERING_LOGIC.md](./FILTERING_LOGIC.md).

