"""
Configuration settings for the web app backend.
"""
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"

# Database and file storage
# In Docker, code is mounted at /app, so we need to handle both cases
# Check if we're in Docker by checking if config.py is in /app directory
_config_file_dir = Path(__file__).parent
_is_docker = str(_config_file_dir) == "/app" or (Path("/app").exists() and Path("/app/data").exists())

if _is_docker:
    # Running in Docker container - use mounted volume paths
    DATABASE_PATH = Path("/app/data/app.db")
    UPLOAD_FOLDER = Path("/app/uploads")
    RESULTS_FOLDER = Path("/app/results")
else:
    # Running locally - use relative paths from project root
    DATABASE_PATH = BACKEND_DIR / "data" / "app.db"
    UPLOAD_FOLDER = BACKEND_DIR / "uploads"
    RESULTS_FOLDER = BACKEND_DIR / "results"

# Ensure directories exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
RESULTS_FOLDER.mkdir(parents=True, exist_ok=True)

# File retention (days)
FILE_RETENTION_DAYS = 7

# Flask settings
# SECURITY WARNING: In production, SECRET_KEY must be set via environment variable
# The default value below is for development only and should NEVER be used in production
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

# CORS settings
CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]  # React dev servers

# Max file size (50MB)
MAX_CONTENT_LENGTH = 50 * 1024 * 1024

# Job processing timeout (5 minutes)
JOB_PROCESSING_TIMEOUT_SECONDS = 300

# Startup cleanup threshold (10 minutes - for detecting jobs stuck from previous runs)
JOB_STARTUP_CLEANUP_THRESHOLD_SECONDS = 600

