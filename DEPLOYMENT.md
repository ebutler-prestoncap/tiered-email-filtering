# Local Deployment Guide

## Quick Start

### 1. Run Setup (One Time)

**Linux/Mac:**
```bash
./setup.sh
```

**Windows:**
```cmd
setup.bat
```

This will:
- Install Python dependencies for the backend
- Install Node.js dependencies for the frontend
- Create necessary directories

### 2. Start the Application

You need **two terminals** running simultaneously:

**Terminal 1 - Backend:**
```bash
./run-backend.sh    # Linux/Mac
# OR
run-backend.bat     # Windows
```

**Terminal 2 - Frontend:**
```bash
./run-frontend.sh   # Linux/Mac
# OR
run-frontend.bat    # Windows
```

### 3. Access the Application

- **Frontend**: Open http://localhost:3000 in your browser
- **Backend API**: Available at http://localhost:5000

## Manual Setup (Alternative)

If the automated scripts don't work, you can set up manually:

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Troubleshooting

### Backend Issues

**Port 5000 already in use:**
- Change the port in `backend/app.py` (last line): `app.run(debug=True, port=5001)`
- Update `frontend/vite.config.ts` proxy target to match

**Python packages not found:**
- Make sure you're in the backend directory
- Try: `pip install --user -r requirements.txt`

### Frontend Issues

**Port 3000 already in use:**
- Vite will automatically use the next available port (3001, 3002, etc.)
- Check the terminal output for the actual URL

**Node modules not found:**
- Run `npm install` in the frontend directory
- Make sure Node.js 16+ is installed

### Database Issues

**Database not created:**
- The database is created automatically on first run
- Location: `backend/data/app.db`
- Make sure the `backend/data/` directory is writable

## Verifying Installation

1. **Backend**: Check http://localhost:5000/api/health
   - Should return: `{"status": "healthy"}`

2. **Frontend**: Open http://localhost:3000
   - Should show the "Process Contacts" page

3. **Test Upload**: Try uploading a sample Excel file
   - The file should appear in the uploaded files list

## Next Steps

1. Upload Excel files with contact data
2. Configure filtering options
3. Process contacts
4. View analytics in the dashboard
5. Download results

## Production Deployment

For production deployment, consider:
- Using a production WSGI server (gunicorn, uwsgi)
- Building the frontend: `cd frontend && npm run build`
- Serving static files with nginx
- Using a production database (PostgreSQL)
- Setting up proper authentication
- Configuring environment variables for secrets

