# Tiered Contact Filter

## 🚀 Overview

A professional contact filtering tool that processes Excel contact lists and organizes them into a two-tier structure optimized for investment outreach. The system intelligently removes duplicates, applies firm exclusions, forces contact inclusions, and provides detailed analytics.

## ✨ Key Features

### Core Filtering
- ✅ **Two-Tier System**: Separates key contacts (Tier 1) from junior contacts (Tier 2)
- ✅ **Smart Deduplication**: Removes duplicates based on name + firm combination
- ✅ **Firm Limits**: Max 10 Tier 1 + 6 Tier 2 contacts per firm
- ✅ **Multiple Input Support**: Combines multiple Excel files automatically

### Advanced Control
- ✅ **Optional Firm Exclusion**: Exclude specific firms using `firm exclusion.csv`
- ✅ **Optional Contact Inclusion**: Force specific individuals through filters using `include_contacts.csv`
- ✅ **Email Pattern Extraction**: Analyzes datasets to extract firm email patterns
- ✅ **Missing Email Filling**: Uses patterns to fill missing emails

### Professional Output
- ✅ **Comprehensive Analytics**: Detailed statistics and processing metrics
- ✅ **Excel Output**: Multi-sheet workbooks with summaries and analysis
- ✅ **Audit Trail**: Complete delta analysis showing filtering decisions

## 🗂️ Project Structure

```
tiered-email-filtering/
├── tiered_filter.py              # Main filtering tool
├── requirements.txt              # Python dependencies
├── input/                       # Place Excel files here
│   ├── firm exclusion.csv       # Optional: firms to exclude
│   └── include_contacts.csv     # Optional: contacts to force through filters
├── output/                      # Results saved here
├── tests/                       # Test files and demos
│   └── demo_firm_exclusion.py   # Demo script
└── archive/                     # Legacy files and previous runs
    └── legacy_filters/          # Old filtering implementations
```

## 🎯 Quick Start

1. **Install Requirements**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Add Input Files**: Place Excel files in the `input/` folder

3. **Run Filtering**:
   ```bash
   python3 tiered_filter.py
   ```

4. **Results**: Check the `output/` folder for timestamped results

## 📊 Filtering Logic

### Tier 1: Key Contacts (Senior Decision Makers)
- **No investment team requirement** (prioritizes important titles)
- **Max 10 contacts per firm**
- **Targets**: CIO, Managing Director, Head of Investments, Portfolio Manager, President

### Tier 2: Junior Contacts (Supporting Professionals)
- **Must be on investment team** (prevents overly broad filtering)
- **Max 6 contacts per firm**
- **Targets**: Analysts, Associates, Directors, Advisors

## 🚫 Firm Exclusion Feature

### Setup
1. Place a file named `firm exclusion.csv` in the `/input` folder
2. List firm names to exclude, one per line
3. Run the filtering tool and choose "yes" when prompted

### How It Works
- **Case-insensitive matching**: "Goldman Sachs" matches "goldman sachs" in data
- **Applied after deduplication**: Ensures clean exclusion without double-counting
- **Complete firm exclusion**: All contacts from excluded firms are removed
- **Detailed reporting**: Shows which excluded firms were found and removed

## ✅ Contact Inclusion Feature

### Setup
1. Place a file named `include_contacts.csv` in the `/input` folder
2. Use format: `Institution_Name,Full_Name` (with header row)
3. List specific individuals to force through filters
4. Run the filtering tool and choose "yes" when prompted

### How It Works
- **Individual targeting**: Targets specific people, not entire firms
- **Bypass all filters**: Forces contacts through regardless of job title/team requirements
- **Smart tier placement**: Places contacts in appropriate tier based on job title patterns
- **Applied after standard filtering**: Adds missing contacts to existing results
- **Comprehensive tracking**: Shows how many contacts were forced through filters

### Example Format
```csv
Institution_Name,Full_Name
Goldman Sachs,John Smith
BlackRock,Jane Doe
```

## 📈 Data Processing Pipeline

```
Input Files → Combine → Standardize Columns → Remove Duplicates → [Optional: Firm Exclusion]
     ↓
Extract Email Patterns → Apply Tier 1 Filter → Apply Tier 2 Filter → [Optional: Contact Inclusion]
     ↓
Fill Missing Emails → Generate Output with Comprehensive Analytics
```

## 📊 Output Structure

### Excel Sheets:
1. **Tier1_Key_Contacts**: Senior professionals with priority access
2. **Tier2_Junior_Contacts**: Junior professionals with investment team focus
3. **Processing_Summary**: Comprehensive statistics and metrics including:
   - Firm exclusion impact (firms/contacts removed)
   - Contact inclusion impact (contacts forced through filters)
   - Average and median contacts per firm (before filtering and per tier)
   - Processing pipeline metrics
   - Email availability statistics
4. **Input_File_Details**: Source file breakdown
5. **Excluded_Firms_Analysis**: Complete analysis of excluded firms
6. **Delta_Analysis**: Detailed breakdown of why contacts were included/excluded

## 🧪 Testing

Run the demo to see all advanced features in action:
```bash
python3 tests/demo_firm_exclusion.py
```

This will generate four output files showing different configurations:
- **With-Exclusion**: Firms removed, standard filtering
- **With-Inclusion**: Standard filtering + forced contacts  
- **With-Both**: Firms removed + forced contacts
- **Standard**: Baseline with no special processing

## 📋 Example Usage

### Single File Input
```
input/
└── Institutional_Contact_List.xlsx

Output: "Institutional_Contact_List_Tiered_List_[timestamp].xlsx"
```

### Multiple Files Input
```
input/
├── Family_Office_Contacts.xlsx
├── Institutional_Contacts.xlsx
└── Additional_Contacts.xlsx

Output: "Combined-Contacts_Tiered_List_[timestamp].xlsx"
```

## 📝 Requirements

- Python 3.7+
- pandas
- openpyxl
- xlsxwriter

Install with:
```bash
pip install pandas openpyxl xlsxwriter
```

## 🔧 Advanced Features

### Programmatic Usage
```python
from tiered_filter import TieredFilter

filter_tool = TieredFilter()
output_file = filter_tool.process_contacts(
    user_prefix="My-Contacts",
    enable_firm_exclusion=True,
    enable_contact_inclusion=True
)
```

### Custom Input/Output Folders
```python
filter_tool = TieredFilter(
    input_folder="custom_input",
    output_folder="custom_output"
)
```

## 📊 Analytics & Metrics

The system provides comprehensive analytics including:

- **Processing Metrics**: Raw contacts, duplicates removed, retention rates
- **Firm Statistics**: Unique firms, average/median contacts per firm
- **Tier Analysis**: Contacts and firms per tier with distribution metrics
- **Exclusion Impact**: Detailed breakdown of firm exclusion effects
- **Inclusion Impact**: Tracking of contacts forced through filters
- **Email Intelligence**: Pattern extraction and missing email filling statistics

## 🗄️ Legacy Files

Previous implementations and tools are archived in `/archive/legacy_filters/`:
- `consolidated_tiered_filter.py` - Alternative implementation (experimental)
- `unified_tiered_filter.py` - Original stable version (renamed to `tiered_filter.py`)

## 🎯 Business Impact

**Investment Outreach Optimization:**
- **Quality over Quantity**: Prioritizes decision makers
- **Firm Coverage**: Ensures broad institutional reach
- **Contact Hierarchy**: Clear senior vs junior segmentation
- **Data Quality**: Pattern-based email completion and validation

---

*This system transforms raw contact databases into actionable, prioritized outreach lists optimized for investment fundraising and relationship building.*