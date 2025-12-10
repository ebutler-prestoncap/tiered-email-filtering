"""
Flask REST API for tiered email filtering web app.
"""
import os
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import logging

from config import (
    DATABASE_PATH, UPLOAD_FOLDER, RESULTS_FOLDER,
    CORS_ORIGINS, MAX_CONTENT_LENGTH, FILE_RETENTION_DAYS
)
from database import Database
from api.upload_handler import save_uploaded_files, cleanup_files
from api.filter_service import FilterService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
CORS(app, origins=CORS_ORIGINS)

# Initialize database
db = Database(str(DATABASE_PATH))

# Background job processing
def process_job_async(job_id: str, uploaded_files: list, original_filenames: list, settings: dict):
    """Process job in background thread"""
    try:
        db.update_job_status(job_id, "processing")
        
        # Initialize filter service
        filter_service = FilterService(
            input_folder=str(UPLOAD_FOLDER),
            output_folder=str(RESULTS_FOLDER)
        )
        
        # Process contacts
        result = filter_service.process_contacts(uploaded_files, settings, job_id)
        
        # Save analytics to database
        db.save_analytics(job_id, result["analytics"])
        
        # Move output file to results folder with job ID
        output_path = Path(result["output_path"])
        new_output_path = RESULTS_FOLDER / f"{job_id}.xlsx"
        output_path.rename(new_output_path)
        
        # Update job status
        db.update_job_status(job_id, "completed", f"{job_id}.xlsx")
        
        # Cleanup uploaded files
        cleanup_files(uploaded_files)
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
        db.update_job_status(job_id, "failed")
        # Cleanup uploaded files even on error
        try:
            cleanup_files(uploaded_files)
        except:
            pass

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Upload Excel files"""
    try:
        saved_paths, original_names = save_uploaded_files(request, UPLOAD_FOLDER)
        
        # Save file metadata to database
        import uuid
        import os
        file_ids = []
        for i, (path, original_name) in enumerate(zip(saved_paths, original_names)):
            file_id = str(uuid.uuid4())
            file_size = os.path.getsize(path) if os.path.exists(path) else 0
            db.save_uploaded_file(file_id, original_name, path, file_size)
            file_ids.append(file_id)
        
        return jsonify({
            "success": True,
            "files": original_names,
            "paths": saved_paths,
            "fileIds": file_ids
        }), 200
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/process', methods=['POST'])
def process_contacts():
    """Start processing job"""
    try:
        data = request.json
        files = data.get("files", [])  # Can be file paths
        file_ids = data.get("fileIds", [])  # Optional: file IDs from database
        settings = data.get("settings", {})
        
        if not files and not file_ids:
            return jsonify({"success": False, "error": "No files provided"}), 400
        
        # Get full paths for uploaded files
        uploaded_files = []
        original_filenames = []
        all_file_names = []  # For job creation
        
        # Process file IDs first (previously uploaded files)
        if file_ids:
            for file_id in file_ids:
                file_meta = db.get_uploaded_file(file_id)
                if file_meta and Path(file_meta["stored_path"]).exists():
                    uploaded_files.append(file_meta["stored_path"])
                    original_filenames.append(file_meta["original_name"])
                    all_file_names.append(file_meta["original_name"])
                    # Update last used timestamp
                    db.update_file_last_used(file_id)
                else:
                    raise ValueError(f"File ID not found or file missing: {file_id}")
        
        # Process new file paths
        for f in files:
            if not f or f.strip() == '':  # Skip empty placeholders for file IDs
                continue
                
            file_path = None
            original_name = None
            
            # Check if it's already a full path
            if Path(f).is_absolute() and Path(f).exists():
                file_path = str(Path(f))
                original_name = Path(f).name
            else:
                # Assume it's a filename in the upload folder
                file_path_obj = UPLOAD_FOLDER / Path(f).name
                if file_path_obj.exists():
                    file_path = str(file_path_obj)
                    original_name = Path(f).name
                else:
                    raise ValueError(f"Could not find uploaded file: {f} (checked {file_path_obj})")
            
            if file_path:
                uploaded_files.append(file_path)
                original_filenames.append(original_name or Path(file_path).name)
                all_file_names.append(original_name or Path(file_path).name)
        
        if not uploaded_files:
            return jsonify({"success": False, "error": "No valid files found"}), 400
        
        # Create job - store original file names for display
        job_id = db.create_job(settings, all_file_names)
        
        # Start background processing
        thread = threading.Thread(
            target=process_job_async,
            args=(job_id, uploaded_files, original_filenames, settings)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "jobId": job_id,
            "status": "pending"
        }), 200
        
    except Exception as e:
        logger.error(f"Process error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id: str):
    """Get job status and analytics"""
    try:
        job = db.get_job(job_id)
        if not job:
            return jsonify({"success": False, "error": "Job not found"}), 404
        
        response = {
            "success": True,
            "job": {
                "id": job["id"],
                "created_at": job["created_at"],
                "status": job["status"],
                "settings": job["settings"],
                "input_files": job["input_files"]
            }
        }
        
        if job.get("analytics"):
            response["job"]["analytics"] = job["analytics"]
        
        if job["status"] == "completed" and job.get("output_filename"):
            response["job"]["downloadUrl"] = f"/api/jobs/{job_id}/download"
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Get job error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/jobs/<job_id>/download', methods=['GET'])
def download_results(job_id: str):
    """Download Excel results file"""
    try:
        job = db.get_job(job_id)
        if not job:
            return jsonify({"success": False, "error": "Job not found"}), 404
        
        if job["status"] != "completed":
            return jsonify({"success": False, "error": "Job not completed"}), 400
        
        output_file = RESULTS_FOLDER / job["output_filename"]
        if not output_file.exists():
            return jsonify({"success": False, "error": "File not found"}), 404
        
        return send_file(
            str(output_file),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=job["output_filename"]
        )
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all processing jobs"""
    try:
        limit = request.args.get('limit', 50, type=int)
        jobs = db.list_jobs(limit)
        
        return jsonify({
            "success": True,
            "jobs": [
                {
                    "id": job["id"],
                    "created_at": job["created_at"],
                    "status": job["status"],
                    "input_files": job["input_files"],
                    "settings": job["settings"]
                }
                for job in jobs
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"List jobs error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/jobs/<job_id>', methods=['DELETE'])
def delete_job(job_id: str):
    """Delete job and cleanup files"""
    try:
        job = db.get_job(job_id)
        if not job:
            return jsonify({"success": False, "error": "Job not found"}), 404
        
        # Delete output file if exists
        if job.get("output_filename"):
            output_file = RESULTS_FOLDER / job["output_filename"]
            if output_file.exists():
                output_file.unlink()
        
        # Delete from database
        deleted = db.delete_job(job_id)
        
        if deleted:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "error": "Could not delete job"}), 500
        
    except Exception as e:
        logger.error(f"Delete job error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/settings/presets', methods=['GET'])
def get_presets():
    """Get all settings presets"""
    try:
        presets = db.get_presets()
        return jsonify({
            "success": True,
            "presets": presets
        }), 200
    except Exception as e:
        logger.error(f"Get presets error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/settings/presets', methods=['POST'])
def create_preset():
    """Create a new settings preset"""
    try:
        data = request.json
        name = data.get("name")
        settings = data.get("settings")
        
        if not name or not settings:
            return jsonify({"success": False, "error": "Name and settings required"}), 400
        
        preset_id = db.create_preset(name, settings)
        return jsonify({
            "success": True,
            "presetId": preset_id
        }), 201
        
    except Exception as e:
        logger.error(f"Create preset error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/settings/presets/<preset_id>', methods=['PUT'])
def update_preset(preset_id: str):
    """Update a settings preset"""
    try:
        data = request.json
        name = data.get("name")
        settings = data.get("settings")
        
        if name is None and settings is None:
            return jsonify({"success": False, "error": "Name or settings required"}), 400
        
        updated = db.update_preset(preset_id, name=name, settings=settings)
        if updated:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "error": "Could not update preset (may be default or not found)"}), 400
        
    except Exception as e:
        logger.error(f"Update preset error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/settings/presets/<preset_id>', methods=['DELETE'])
def delete_preset(preset_id: str):
    """Delete a settings preset"""
    try:
        deleted = db.delete_preset(preset_id)
        if deleted:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "error": "Could not delete preset (may be default)"}), 400
    except Exception as e:
        logger.error(f"Delete preset error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/files', methods=['GET'])
def list_uploaded_files():
    """List all previously uploaded files"""
    try:
        limit = request.args.get('limit', 100, type=int)
        files = db.list_uploaded_files(limit)
        
        return jsonify({
            "success": True,
            "files": [
                {
                    "id": f["id"],
                    "originalName": f["original_name"],
                    "storedPath": f["stored_path"],
                    "fileSize": f["file_size"],
                    "uploadedAt": f["uploaded_at"],
                    "lastUsedAt": f["last_used_at"]
                }
                for f in files
            ]
        }), 200
    except Exception as e:
        logger.error(f"List files error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # Bind to 0.0.0.0 to allow access from Docker containers
    app.run(debug=True, host='0.0.0.0', port=5000)

