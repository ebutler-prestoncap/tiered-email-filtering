# Tiered Contact Filter

A professional contact filtering tool that processes Excel contact lists and organizes them into prioritized tiers for investment outreach.

## 🌐 Web Application

**New!** A modern web application is now available with:
- Interactive UI for file upload and configuration
- Real-time processing with analytics dashboard
- Processing history and settings presets
- Docker deployment support

**Quick Start (Docker - Recommended):**
```bash
docker compose up --build
```
Access at http://localhost:3000

See [DOCKER.md](./DOCKER.md) for Docker deployment guide or [WEBAPP_README.md](./WEBAPP_README.md) for web app details.

---

## 🚀 CLI Quick Start

1. **Install Requirements**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Add Input Files**: Place Excel files in the `input/` folder

3. **Run Filtering**:
   ```bash
   # Standard filtering
   python3 tiered_filter.py
   
   # Include contacts from excluded firms
   python3 tiered_filter.py --include-all-firms
   
   # Discover firm email schemas and fill missing emails in tiers
   python3 tiered_filter.py --find-emails

   # Combine both (rescue excluded firms and fill emails)
   python3 tiered_filter.py --include-all-firms --find-emails
   ```

4. **Results**: Check the `output/` folder for timestamped results

## ✨ Key Features

- **Three-Tier System**: Tier 1 (Senior), Tier 2 (Junior), Tier 3 (Rescued from excluded firms)
- **Smart Deduplication**: Removes duplicates based on name + firm
- **Firm Limits**: Max 10 Tier 1 + 6 Tier 2 contacts per firm
- **Firm Rescue**: `--include-all-firms` flag rescues top 1-3 contacts from excluded firms
- **Optional Firm Exclusion**: Exclude specific firms using `firm exclusion.csv`
- **Optional Contact Inclusion**: Force specific contacts using `include_contacts.csv`

## 📊 Filtering Logic

### Tier 1: Key Contacts (Senior Decision Makers)
- **Targets**: CIO, Managing Director, Managing Partner, Fund Manager, President
- **Max 10 contacts per firm**
- **No investment team requirement**

### Tier 2: Junior Contacts (Supporting Professionals)  
- **Targets**: Analysts, Associates, Directors, Advisors
- **Max 6 contacts per firm**
- **Must be on investment team**

### Tier 3: Rescued Contacts (--include-all-firms only)
- **Top 1-3 contacts from firms with zero Tier 1/2 contacts**
- **Priority-based selection (CEOs, CFOs, Directors)**
- **Reduces firm exclusion rate from ~40% to ~2.5%**

## 📊 Output Structure

### Excel Sheets:
1. **Tier1_Key_Contacts**: Senior decision makers (680 contacts)
2. **Tier2_Junior_Contacts**: Junior professionals (337 contacts)  
3. **Tier3_Rescued_Contacts**: Rescued contacts (320 contacts) *[with --include-all-firms]*
4. **Processing_Summary**: Statistics and metrics
5. **Delta_Analysis**: Detailed filtering decisions
6. **Excluded_Firms_Analysis**: Firm exclusion impact

## 🚫 Optional Features

### Firm Exclusion
1. Create `input/firm exclusion.csv` with firm names to exclude
2. Run filtering and choose "yes" when prompted

### Contact Inclusion  
1. Create `input/include_contacts.csv` with format:
   ```csv
   Institution_Name,Full_Name
   Goldman Sachs,John Smith
   BlackRock,Jane Doe
   ```
2. Run filtering and choose "yes" when prompted

### Email Discovery and Filling
1. Run with `--find-emails` to enable discovery of firm email schemas from the original input files.
2. The tool learns common domains (e.g., `acme.com`) and local-part patterns (e.g., `first.last`, `fLast`) per firm using existing emails.
3. After tiering, missing emails in Tier 1 and Tier 2 are filled using the detected firm schema(s).
4. Schemas considered:
   - `first.last`, `first_last`, `firstlast`
   - `fLast` (first initial + last), `firstL` (first + last initial)
   - `last.first`, `last_first`, `lastfirst`, `lFirst` (last initial + first)
   - `f.last` (first initial dot last), `f_last` (first initial underscore last), `first_l` (first underscore last initial)

Notes:
- Discovery uses only emails present in your input data; it does not scrape the web.
- If a firm lacks any known emails, no filling occurs for that firm.

## 📈 Results

**Standard Filtering:**
- 1,017 total contacts (680 Tier 1 + 337 Tier 2)
- ~235 firms included, ~168 firms excluded (41.7%)

**With --include-all-firms:**
- 1,337 total contacts (680 Tier 1 + 337 Tier 2 + 320 Rescued)
- ~393 firms included, ~10 firms excluded (2.5%)
- **94% firm rescue rate!**

## 📝 Requirements

- Python 3.7+
- pandas, openpyxl, xlsxwriter

```bash
pip install pandas openpyxl xlsxwriter
```

## 🔧 Advanced Usage

```python
from tiered_filter import TieredFilter

filter_tool = TieredFilter()
output_file = filter_tool.process_contacts(
    user_prefix="My-Contacts",
    enable_firm_exclusion=True,
    enable_contact_inclusion=True,
    include_all_firms=True
)
```

---

*Transforms raw contact databases into actionable, prioritized outreach lists optimized for investment fundraising.*

For detailed feature roadmap and development plans, see [ROADMAP.md](ROADMAP.md).
