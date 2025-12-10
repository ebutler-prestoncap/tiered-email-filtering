"""
Handle file uploads for the web app.
"""
import os
import uuid
from pathlib import Path
from typing import List, Tuple
from werkzeug.utils import secure_filename
from flask import Request
import logging

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_files(request: Request, upload_folder: Path) -> Tuple[List[str], List[str]]:
    """
    Save uploaded files to disk.
    
    Returns:
        Tuple of (saved_file_paths, original_filenames)
    """
    saved_paths = []
    original_names = []
    
    if 'files' not in request.files:
        raise ValueError("No files in request")
    
    files = request.files.getlist('files')
    
    if not files or files[0].filename == '':
        raise ValueError("No files selected")
    
    for file in files:
        if file and allowed_file(file.filename):
            # Generate unique filename to avoid conflicts
            original_name = secure_filename(file.filename)
            file_ext = original_name.rsplit('.', 1)[1].lower()
            unique_name = f"{uuid.uuid4()}.{file_ext}"
            
            file_path = upload_folder / unique_name
            file.save(str(file_path))
            
            saved_paths.append(str(file_path))
            original_names.append(original_name)
            logger.info(f"Saved uploaded file: {original_name} -> {file_path}")
        else:
            raise ValueError(f"Invalid file: {file.filename if file else 'None'}")
    
    return saved_paths, original_names

def cleanup_files(file_paths: List[str]):
    """Delete uploaded files"""
    for path in file_paths:
        try:
            os.remove(path)
            logger.info(f"Deleted file: {path}")
        except Exception as e:
            logger.warning(f"Could not delete file {path}: {e}")

