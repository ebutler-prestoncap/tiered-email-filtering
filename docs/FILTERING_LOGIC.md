# Tiered Email Filtering - Complete Filtering Logic Documentation

## Overview

This document provides a comprehensive outline of all inclusions, exclusions, and filtering criteria used in the tiered contact filtering system. The system processes investment contact lists and organizes them into prioritized tiers for outreach.

---

## Table of Contents

1. [Pre-Filtering Steps](#pre-filtering-steps)
2. [Tier 1 - Key Contacts](#tier-1---key-contacts)
3. [Tier 2 - Junior Contacts](#tier-2---junior-contacts)
4. [Tier 3 - Rescued Contacts](#tier-3---rescued-contacts)
5. [Email Discovery & Filling](#email-discovery--filling)
6. [Priority Scoring System](#priority-scoring-system)
7. [Firm-Based Limits](#firm-based-limits)

---

## Pre-Filtering Steps

These steps are applied to all contacts before tier-specific filtering.

### 1. Column Standardization

**Purpose:** Normalize column names across different input file formats.

**Standard Mappings:**
- `NAME` ← `NAME`, `name`, `Key Contact`, `contact name`, `contact_name`, `Full Name`, `Full_Name`, `full name`, `full_name`
- `INVESTOR` ← `INVESTOR`, `investor`, `Institution Name`, `institution_name`, `firm`, `company`
- `JOB_TITLE` ← `JOB TITLE`, `Job title`, `job_title`, `position`
- `EMAIL` ← `EMAIL`, `email`, `Email`, `email address`
- `ROLE` ← `ROLE`, `role`
- `CONTACT_ID` ← `CONTACT_ID`, `contact_id`, `id`

**Name Processing:**
- Combines `First Name` + `Last Name` to create `NAME` where missing
- Splits `NAME` back to `First Name`/`Last Name` where components are missing
- Filters out single-character values (Y, N, T, F) that are likely boolean flags

### 2. Deduplication

**Purpose:** Remove duplicate contacts based on name + firm combination.

**Criteria:**
- **Match Key:** `NAME` (normalized, lowercase, trimmed) + `INVESTOR` (normalized, lowercase, trimmed)
- **Method:** Case-insensitive matching with whitespace normalization
- **Behavior:** Keeps first occurrence, removes subsequent duplicates

**Exclusions:**
- None (all duplicates removed)

### 3. Firm Exclusion (Optional)

**Purpose:** Exclude entire firms from processing.

**Configuration:**
- **File:** `input/firm exclusion.csv`
- **Format:** CSV file with firm names (one per line or column)
- **Activation:** User prompt during execution (yes/no)

**Behavior:**
- All contacts from listed firms are excluded from all tiers
- Applied after deduplication, before tier filtering
- Excluded firms are tracked in `Excluded_Firms_Analysis` output sheet

**Exclusions:**
- Entire firms listed in exclusion file
- All contacts from excluded firms (regardless of tier eligibility)

### 4. Contact Inclusion (Optional)

**Purpose:** Force specific contacts through filters even if they don't match tier criteria.

**Configuration:**
- **File:** `input/include_contacts.csv`
- **Format:** CSV with columns: `Institution_Name`, `Full_Name`
- **Activation:** User prompt during execution (yes/no)

**Behavior:**
- Contacts matching inclusion list are added to appropriate tier based on job title patterns
- If contact matches Tier 1 patterns → added to Tier 1
- Otherwise → added to Tier 2 (bypasses investment team requirement)
- Applied after tier filtering, before firm limits

**Inclusions:**
- Specific contacts listed in inclusion file
- Contacts bypass normal tier criteria if in inclusion list

---

## Tier 1 - Key Contacts

**Target:** Senior decision makers and key investment professionals

**Maximum Contacts per Firm:** 10

**Investment Team Requirement:** ❌ NO (not required)

### Inclusion Criteria

**Job Title Must Match (at least one):**
- `cio` or `c.i.o.` or `c.i.o`
- `chief investment officer` (with optional 's' or 't' suffix)
- `deputy chief investment officer` or `deputy cio`
- `head of investments` or `head of investment`
- `head of alternatives` or `head of alternative`
- `head of alternative investments` or `head of alternative investment`
- `head of private markets` or `head of private market`
- `head of private equity`
- `head of private debt`
- `head of private credit`
- `head of multi-asset` or `head of multi asset`
- `head of hedge funds` or `head of hedge fund`
- `head of hedge fund research`
- `head of research`
- `head of manager research`
- `head of manager selection`
- `investment director` or `investment directors`
- `director of investments` or `director of investment`
- `portfolio manager` or `portfolio managers`
- `fund manager` or `fund managers`
- `investment manager` or `investment managers`
- `investment analyst`
- `research analyst`
- `senior investment officer`
- `investment officer`
- `investment strategist`
- `asset allocation`
- `multi-manager` or `multi manager`
- `manager research`
- `due diligence`
- `managing director` or `managing directors`
- `managing partner` or `managing partners`
- `executive director` or `executive directors`
- `senior portfolio manager` or `senior portfolio managers`
- `president` or `presidents`
- `vice president` or `vice presidents`
- `senior vice president` or `senior vice presidents`
- `executive vice president` or `executive vice presidents`

**Pattern:** Case-insensitive regex matching using word boundaries. Supports optional spaces/hyphens in terms like "multi-asset" and "multi-manager".

### Exclusion Criteria

**Job Title Must NOT Contain:**
- `operations` or `operation`
- `hr` or `human resources` or `human resource`
- `investor relations` or `investor relation`
- `client relations` or `client relation`
- `marketing`
- `sales`
- `compliance`
- `technology`
- `administrator`
- `assistant`
- `secretary`
- `receptionist`
- `intern`
- `trainee`

**Pattern:** Case-insensitive regex matching using word boundaries

### Priority Keywords (for ranking within firm limits)

Higher priority contacts are selected first when firm limit is reached:
1. `cio` or `chief investment officer` or `deputy chief investment officer` (+100 points)
2. `managing director`, `managing partner`, `president` (+80 points)
3. `portfolio manager`, `fund manager`, `head of investments`, `head of investment`, `head of alternatives`, `head of alternative investments`, `head of private markets`, `head of private equity`, `head of private debt`, `head of private credit`, `head of multi-asset`, `head of hedge funds`, `head of hedge fund research`, `head of research`, `head of manager research`, `head of manager selection`, `investment director`, `director of investments` (+60 points)
4. Other matching titles including `investment analyst`, `research analyst`, `senior investment officer`, `investment officer`, `investment strategist`, `asset allocation`, `multi-manager`, `manager research`, `due diligence` (+40 points)
5. Additional bonuses: `investment` (+20), `portfolio` (+15)

---

## Tier 2 - Junior Contacts

**Target:** Junior investment professionals and supporting roles

**Maximum Contacts per Firm:** 6

**Investment Team Requirement:** ✅ YES (required)

### Inclusion Criteria

**Job Title Must Match (at least one):**
- `director`
- `associate director`
- `vice president`
- `investment analyst`
- `research analyst`
- `portfolio analyst`
- `senior analyst`
- `investment advisor`
- `principal`
- `associate`
- `coordinator`
- `specialist`
- `advisor`
- `analyst`

**Pattern:** Case-insensitive regex matching using word boundaries

**Role Requirement:**
- `ROLE` field must contain `investment team` OR `investment`
- This is a **hard requirement** - contacts without investment team role are excluded

### Exclusion Criteria

**Job Title Must NOT Contain:**
- All Tier 1 exclusion terms (operations, hr, marketing, sales, etc.)
- **PLUS** Tier 1 inclusion terms (to prevent overlap):
  - `cio` or `chief investment officer`
  - `managing director`
  - `executive director`
  - `president`
  - `senior vice president`
  - `executive vice president`

**Pattern:** Case-insensitive regex matching using word boundaries

**Additional Exclusion:**
- Contacts without `investment team` or `investment` in ROLE field

### Priority Keywords (for ranking within firm limits)

Higher priority contacts are selected first when firm limit is reached:
1. `director` (+40 points)
2. `vice president` (+40 points)
3. `investment analyst`, `research analyst` (+40 points)
4. `principal`, `associate` (+40 points)
5. Additional bonuses: `investment` (+20), `portfolio` (+15)

---

## Tier 3 - Rescued Contacts

**Target:** Top contacts from firms with zero contacts in Tiers 1/2

**Activation:** Requires `--include-all-firms` flag

**Maximum Contacts per Firm:** 1-3 (configurable, default: 3)

**Investment Team Requirement:** ❌ NO (not required)

### Inclusion Criteria

**Firm Eligibility:**
- Firm must have **zero contacts** in both Tier 1 and Tier 2 after standard filtering
- Firm must have at least one contact in deduplicated dataset

**Contact Selection:**
- Top 1-3 contacts per firm based on priority scoring
- Only contacts with priority score > 0 are rescued (avoids completely irrelevant contacts)

### Priority Scoring (for rescue ranking)

**High Priority (+100 points):**
- `ceo`, `chief executive`, `managing director`, `managing partner`

**Very High Priority (+90 points):**
- `cfo`, `chief financial`, `cio`, `chief investment`

**High Priority (+80 points):**
- `coo`, `chief operating`, `president`, `chairman`, `chair`

**Medium Priority (+60 points):**
- `director`, `partner`, `vice president`

**Lower Priority (+40 points):**
- `manager`, `head of`

**Low Priority (+20 points):**
- `analyst`, `associate`

**Bonus Points:**
- `investment` in job title (+15)
- `portfolio` in job title (+10)
- `fund` in job title (+10)

### Exclusion Criteria

**Firm-Level:**
- Firms that already have contacts in Tier 1 or Tier 2

**Contact-Level:**
- Contacts with priority score = 0 (completely irrelevant titles)

---

## Email Discovery & Filling

**Activation:** Requires `--find-emails` flag

**Purpose:** Discover firm email schemas from input data and fill missing emails in Tier 1 and Tier 2.

### Email Schema Discovery

**Process:**
1. Extract all existing emails from standardized input dataset
2. Group by firm (INVESTOR field)
3. Identify common email domains per firm (top 3 domains)
4. Detect local-part patterns by comparing email addresses to contact names

**Supported Email Patterns:**
- `first.last` - e.g., `john.smith@firm.com`
- `first_last` - e.g., `john_smith@firm.com`
- `firstlast` - e.g., `johnsmith@firm.com`
- `fLast` - e.g., `jsmith@firm.com` (first initial + last name)
- `firstL` - e.g., `johns@firm.com` (first name + last initial)
- `last.first` - e.g., `smith.john@firm.com`
- `last_first` - e.g., `smith_john@firm.com`
- `lastfirst` - e.g., `smithjohn@firm.com`
- `lFirst` - e.g., `sjohn@firm.com` (last initial + first name)
- `f.last` - e.g., `j.smith@firm.com` (first initial dot last)
- `f_last` - e.g., `j_smith@firm.com` (first initial underscore last)
- `first_l` - e.g., `john_s@firm.com` (first underscore last initial)

**Pattern Detection:**
- Compares email local-part to name-derived patterns
- Selects most common pattern(s) per firm (top 3)
- Falls back to `first.last` if no pattern detected

### Email Filling

**Process:**
1. For contacts in Tier 1 and Tier 2 with missing emails
2. Extract first and last name from contact
3. Look up firm's detected email patterns and domains
4. Generate email candidates using detected patterns
5. Fill email using most common pattern/domain combination

**Email Status Annotation:**
- `existing` - Email was present in original input
- `estimated` - Email was filled using detected schema
- `missing` - No email available (no schema detected or name insufficient)

**Email Schema Annotation:**
- Pattern code used for estimated emails (e.g., `first.last`, `fLast`)

**Limitations:**
- Only fills emails for firms with detected schemas
- Requires valid first and last name for contact
- Does not validate email addresses (no web scraping or verification)

---

## Priority Scoring System

Priority scores determine contact ranking within each firm when firm limits are reached.

### Tier 1 Priority Scoring

**Base Scores:**
- CIO/Chief Investment Officer: +100
- Managing Director/Managing Partner/President: +80
- Portfolio Manager/Fund Manager/Head of Investments/Head of Research/Head of Private Markets/Investment Director: +60
- Other matching titles: +40

**Bonus Points:**
- `investment` in job title: +20
- `portfolio` in job title: +15

### Tier 2 Priority Scoring

**Base Scores:**
- Director/Vice President/Investment Analyst/Research Analyst/Principal/Associate: +40

**Bonus Points:**
- `investment` in job title: +20
- `portfolio` in job title: +15

### Tier 3 Priority Scoring

See [Tier 3 - Rescued Contacts](#tier-3---rescued-contacts) section above.

---

## Firm-Based Limits

**Purpose:** Prevent over-representation of large firms and ensure diversity in contact lists.

### Tier 1 Limits

- **Maximum:** 10 contacts per firm
- **Selection:** Highest priority contacts selected first
- **Behavior:** If firm has 15 eligible contacts, top 10 by priority are included

### Tier 2 Limits

- **Maximum:** 6 contacts per firm
- **Selection:** Highest priority contacts selected first
- **Behavior:** If firm has 10 eligible contacts, top 6 by priority are included

### Tier 3 Limits

- **Maximum:** 1-3 contacts per firm (default: 3)
- **Selection:** Highest priority contacts selected first
- **Behavior:** Only applies to firms with zero contacts in Tiers 1/2

### Cross-Tier Behavior

- **No Duplicates:** A contact cannot appear in multiple tiers
- **Independent Limits:** Tier 1 and Tier 2 limits are independent (firm can have 10 Tier 1 + 6 Tier 2 = 16 total contacts)
- **Tier 3 Addition:** Tier 3 contacts are additional (firm can have 10 Tier 1 + 6 Tier 2 + 3 Tier 3 = 19 total contacts)

---

## Summary of Exclusions

### Global Exclusions (All Tiers)

1. **Duplicate Contacts:** Removed based on name + firm match
2. **Excluded Firms:** All contacts from firms in `firm exclusion.csv` (if enabled)
3. **Invalid Names:** Single-character values (Y, N, T, F) filtered out

### Tier 1 Exclusions

1. **Job Title Exclusions:** Operations, HR, marketing, sales, compliance, technology, administrative roles
2. **Firm Limit:** Contacts beyond top 10 per firm (by priority)

### Tier 2 Exclusions

1. **Job Title Exclusions:** All Tier 1 exclusions PLUS Tier 1 inclusion terms (cio, managing director, president, etc.)
2. **Role Requirement:** Contacts without `investment team` or `investment` in ROLE field
3. **Firm Limit:** Contacts beyond top 6 per firm (by priority)

### Tier 3 Exclusions

1. **Firm Eligibility:** Firms that already have contacts in Tier 1 or Tier 2
2. **Priority Requirement:** Contacts with priority score = 0
3. **Firm Limit:** Contacts beyond top 3 per firm (by priority)

---

## Summary of Inclusions

### Global Inclusions

1. **Contact Inclusion List:** Contacts in `include_contacts.csv` bypass normal tier criteria (if enabled)

### Tier 1 Inclusions

1. **Senior Titles:** CIO, Managing Director, Managing Partner, Portfolio Manager, Fund Manager, President, Head of Investments/Research/Private Markets, etc.
2. **No Role Requirement:** Investment team membership not required

### Tier 2 Inclusions

1. **Junior Titles:** Director, Associate Director, Vice President, Analyst, Associate, Principal, Advisor, etc.
2. **Investment Team Required:** Must have `investment team` or `investment` in ROLE field

### Tier 3 Inclusions

1. **Rescued Contacts:** Top 1-3 contacts from firms with zero Tier 1/2 contacts
2. **Priority-Based:** Selected by priority scoring (CEOs, CFOs, Directors prioritized)

---

## Processing Flow

1. **Load & Standardize:** Load Excel files, standardize columns, process names
2. **Deduplicate:** Remove duplicates based on name + firm
3. **Firm Exclusion:** Remove contacts from excluded firms (if enabled)
4. **Tier 1 Filtering:** Apply Tier 1 criteria, apply firm limits (10 max)
5. **Tier 2 Filtering:** Apply Tier 2 criteria, apply firm limits (6 max)
6. **Contact Inclusion:** Add forced contacts to appropriate tiers (if enabled)
7. **Email Discovery:** Extract email schemas from input (if enabled)
8. **Email Filling:** Fill missing emails in Tier 1/2 using schemas (if enabled)
9. **Tier 3 Rescue:** Rescue top contacts from excluded firms (if enabled)
10. **Output Generation:** Create Excel file with all tiers and analysis sheets

---

*Last Updated: 2025-12-03*

