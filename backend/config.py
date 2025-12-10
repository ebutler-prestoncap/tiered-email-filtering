"""
Configuration settings for the web app backend.
"""
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"

# Database
DATABASE_PATH = BACKEND_DIR / "data" / "app.db"

# File storage
UPLOAD_FOLDER = BACKEND_DIR / "uploads"
RESULTS_FOLDER = BACKEND_DIR / "results"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
RESULTS_FOLDER.mkdir(parents=True, exist_ok=True)

# File retention (days)
FILE_RETENTION_DAYS = 7

# Flask settings
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

# CORS settings
CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]  # React dev servers

# Max file size (50MB)
MAX_CONTENT_LENGTH = 50 * 1024 * 1024

