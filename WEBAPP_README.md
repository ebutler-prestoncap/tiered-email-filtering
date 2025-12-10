# Tiered Email Filtering - Web App

A modern web application for processing and filtering contact lists with comprehensive analytics and history tracking.

## Features

- **File Upload**: Drag & drop or file picker for multiple Excel files
- **Configuration Presets**: Save and reuse filtering configurations
- **Real-time Processing**: Background job processing with status updates
- **Analytics Dashboard**: Comprehensive analytics displayed in the web UI
- **Processing History**: View and manage all processed jobs
- **Excel Export**: Download contact lists (Tier 1, Tier 2, Tier 3) only
- **Minimal Storage**: Efficient SQLite database with automatic cleanup

## Architecture

- **Backend**: Flask REST API with SQLite database
- **Frontend**: React + TypeScript with Vite
- **Design**: Ultra-minimalist Apple-esque UI

## Setup

### Backend

1. Install Python dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Run the Flask server:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

### Frontend

1. Install Node.js dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Usage

1. **Upload Files**: Drag and drop Excel files or use the file picker
2. **Configure Settings**: Adjust filtering options or select a preset
3. **Process**: Click "Process Contacts" to start processing
4. **View Analytics**: After processing, view detailed analytics in the dashboard
5. **Download Results**: Download Excel file with contact lists only
6. **History**: View all processed jobs in the History page

## Default Settings

The default preset matches the CLI tool behavior:
- Include All Firms: `false`
- Find Emails: `false`
- Firm Exclusion: `false`
- Contact Inclusion: `false`
- Tier 1 Limit: `10`
- Tier 2 Limit: `6`
- Tier 3 Limit: `3`
- Output Prefix: `Combined-Contacts`

## API Endpoints

- `POST /api/upload` - Upload Excel files
- `POST /api/process` - Start processing job
- `GET /api/jobs/:jobId` - Get job status and analytics
- `GET /api/jobs/:jobId/download` - Download Excel results
- `GET /api/jobs` - List all jobs
- `DELETE /api/jobs/:jobId` - Delete job
- `GET /api/settings/presets` - Get all presets
- `POST /api/settings/presets` - Create preset
- `DELETE /api/settings/presets/:presetId` - Delete preset

## Storage

- **Database**: SQLite database at `backend/data/app.db`
- **Uploads**: Temporary files in `backend/uploads/`
- **Results**: Excel files in `backend/results/`
- **Cleanup**: Files are automatically cleaned up after 7 days

## Differences from CLI

- **Excel Output**: Only contains contact lists (Tier1, Tier2, Tier3 sheets)
- **Analytics**: Displayed in web UI, not in Excel
- **History**: All processed jobs are stored with analytics
- **Presets**: Save and reuse configurations

