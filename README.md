# Consolidated Tiered Contact Filter

## 🚀 Current System (Unified & Stable)

This project uses a **stable unified filtering tool** that has been tested and proven reliable for contact processing.

### 📁 Active Files
- **`unified_tiered_filter.py`** - **RECOMMENDED** Main filtering tool (stable, tested)
- **`consolidated_tiered_filter.py`** - Alternative implementation (experimental)
- **`README_CONSOLIDATED.md`** - Documentation for both tools
- **`requirements.txt`** - Python dependencies

### 🗂️ Directory Structure
```
tiered-email-filtering/
├── unified_tiered_filter.py         # RECOMMENDED - Stable main tool
├── consolidated_tiered_filter.py    # Experimental alternative
├── README_CONSOLIDATED.md           # Full documentation  
├── requirements.txt                 # Dependencies
├── input/                          # Place Excel files here
├── output/                         # Results saved here
└── archive/                        # Legacy files (archived)
    ├── legacy_filters/             # Old filtering scripts
    ├── comparison_tools/           # Analysis utilities  
    ├── documentation/              # Old documentation
    └── ARCHIVE_SUMMARY.md          # Archive details
```

## 🎯 Quick Start

1. **Install Requirements**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Add Input Files**: Place Excel files in the `input/` folder

3. **Run Filtering** (Recommended):
   ```bash
   python3 unified_tiered_filter.py
   ```
   
   *Alternative (experimental):*
   ```bash
   python3 consolidated_tiered_filter.py
   ```

4. **Results**: Check the `output/` folder for timestamped results

## ✨ Key Features

- ✅ **Unified Logic**: Single tool handles all contact types  
- ✅ **Smart Deduplication**: Removes duplicates by name + firm
- ✅ **Two-Tier System**: Key contacts (Tier 1) vs Junior contacts (Tier 2)
- ✅ **Email Pattern Extraction**: Analyzes full dataset to extract firm email patterns
- ✅ **Missing Email Filling**: Uses patterns to fill missing emails
- ✅ **Firm Limits**: Max 10 Tier 1 + 6 Tier 2 contacts per firm
- ✅ **Multiple Input Support**: Combines multiple Excel files automatically
- ✅ **Optional Firm Exclusion**: Exclude specific firms using `firm exclusion.csv`

## 📊 Filtering Logic

### Tier 1: Key Contacts
- **No investment team requirement** (prioritizes important titles)
- Max 10 contacts per firm
- Targets: CIO, Managing Director, Head of Investments, Portfolio Manager, etc.

### Tier 2: Junior Contacts  
- **Must be on investment team** (prevents overly broad filtering)
- Max 6 contacts per firm
- Targets: Analysts, Associates, Directors, Advisors, etc.

## 🗄️ Archived Components

All legacy filtering tools have been archived in the `archive/` folder:
- **17 Python files** moved to organized subdirectories
- **4 documentation files** preserved for reference
- **Complete functionality** available if needed for reference

See `archive/ARCHIVE_SUMMARY.md` for detailed archive information.

## 📖 Full Documentation

For complete usage instructions, see **`README_CONSOLIDATED.md`**

---

*This consolidated system replaces all previous filtering tools with a single, unified approach that maintains functionality while dramatically simplifying the codebase.*
