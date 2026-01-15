# Tiered Contact Filter

A professional contact filtering tool that processes Excel contact lists and organizes them into prioritized tiers for investment outreach.

## Quick Start (Docker)

```bash
# Start the application
make up

# Or using docker compose directly
docker compose up -d
```

Access the web app at <http://localhost:5670>

## Features

- **Three-Tier System**: Tier 1 (Senior), Tier 2 (Junior), Tier 3 (Rescued from excluded firms)
- **Smart Deduplication**: Removes duplicates based on name + firm
- **Firm Limits**: Configurable limits per tier (default: 10 Tier 1, 6 Tier 2, 3 Tier 3)
- **Firm Rescue**: Rescue top contacts from firms that would otherwise be excluded
- **Email Discovery**: Auto-detect firm email patterns and fill missing emails
- **Processing History**: Track all processed jobs with analytics
- **Configuration Presets**: Save and reuse filtering configurations

## Web Application

The web app provides:

- Drag & drop file upload for Excel files
- Real-time processing with status updates
- Analytics dashboard with filtering breakdown
- Download results as Excel workbooks
- Processing history and saved presets

### Ports

| Service      | Port | URL                      |
|--------------|------|--------------------------|
| Frontend     | 5670 | <http://localhost:5670>  |
| Backend API  | 5000 | <http://localhost:5000>  |

## Filtering Logic

### Tier 1: Key Contacts (Senior Decision Makers)

- **Targets**: CIO, Managing Director, Managing Partner, Fund Manager, President
- **Default limit**: 10 contacts per firm
- **No investment team requirement**

### Tier 2: Junior Contacts (Supporting Professionals)

- **Targets**: Analysts, Associates, Directors, Advisors
- **Default limit**: 6 contacts per firm
- **Must be on investment team**

### Tier 3: Rescued Contacts

- **Top contacts from firms with zero Tier 1/2 contacts**
- **Priority-based selection (CEOs, CFOs, Directors)**
- **Reduces firm exclusion rate from ~40% to ~2.5%**

## Docker Commands

```bash
make up          # Start services
make down        # Stop services
make logs        # View logs
make rebuild     # Rebuild and restart
make status      # Show service status
make health      # Check backend health
```

## Local Development (Without Docker)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```text
tiered-email-filtering/
├── backend/           # Flask REST API
│   ├── api/           # API routes and services
│   ├── app.py         # Main application
│   ├── database.py    # SQLite database layer
│   └── config.py      # Configuration
├── frontend/          # React + TypeScript + Vite
│   └── src/
│       ├── components/
│       ├── pages/
│       └── services/
├── tiered_filter.py   # Core filtering logic
├── docker-compose.yml # Docker configuration
├── Makefile           # Docker shortcuts
└── docs/              # Additional documentation
```

## Documentation

- [DOCKER.md](./DOCKER.md) - Docker deployment guide
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Production deployment
- [docs/](./docs/) - Detailed documentation

---

*Transforms raw contact databases into actionable, prioritized outreach lists optimized for investment fundraising.*
