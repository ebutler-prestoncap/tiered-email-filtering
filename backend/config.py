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
# In Docker, code is mounted at /app, so we need to handle both cases
# Check if we're in Docker by checking if config.py is in /app directory
_config_file_dir = Path(__file__).parent
_docker_data_path = Path("/app/data/app.db")
if str(_config_file_dir) == "/app" or (Path("/app").exists() and Path("/app/data").exists()):
    # Running in Docker container - use mounted volume path
    DATABASE_PATH = _docker_data_path
else:
    # Running locally - use relative path from project root
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

