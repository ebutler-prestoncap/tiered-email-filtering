"""
Flask REST API for tiered email filtering web app.
"""
import os
import io
import threading
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import logging

from config import (
    DATABASE_PATH, UPLOAD_FOLDER, RESULTS_FOLDER,
    CORS_ORIGINS, MAX_CONTENT_LENGTH, FILE_RETENTION_DAYS,
    JOB_PROCESSING_TIMEOUT_SECONDS, JOB_STARTUP_CLEANUP_THRESHOLD_SECONDS
)
from database import Database
from api.upload_handler import save_uploaded_files, cleanup_files
from api.filter_service import FilterService
from api.excel_validator import validate_excel_file

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
CORS(app, origins=CORS_ORIGINS)

# Initialize database
db = Database(str(DATABASE_PATH))

# Track active jobs: {job_id: {"thread": Thread, "cancel_event": Event, "start_time": datetime}}
active_jobs = {}
active_jobs_lock = threading.Lock()

# Background job processing
def process_job_async(job_id: str, uploaded_files: list, original_filenames: list, settings: dict, cancel_event: threading.Event):
    """Process job in background thread with cancellation and timeout support"""
    start_time = datetime.now()
    logger.info(f"Job {job_id} started processing at {start_time}")
    
    try:
        db.update_job_status(job_id, "processing")
        logger.info(f"Job {job_id} status updated to 'processing'")
        
        # Check for cancellation before starting
        if cancel_event.is_set():
            logger.info(f"Job {job_id} was cancelled before processing started")
            db.update_job_status(job_id, "cancelled")
            return
        
        # Initialize filter service
        logger.info(f"Job {job_id} initializing FilterService")
        filter_service = FilterService(
            input_folder=str(UPLOAD_FOLDER),
            output_folder=str(RESULTS_FOLDER)
        )
        
        # Check timeout
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed > JOB_PROCESSING_TIMEOUT_SECONDS:
            logger.warning(f"Job {job_id} exceeded timeout ({elapsed:.1f}s > {JOB_PROCESSING_TIMEOUT_SECONDS}s)")
            db.update_job_status(job_id, "failed")
            return
        
        # Check for cancellation
        if cancel_event.is_set():
            logger.info(f"Job {job_id} was cancelled during initialization")
            db.update_job_status(job_id, "cancelled")
            return
        
        # Create progress callback
        def progress_callback(text: str, percent: int = 0):
            try:
                db.update_job_progress(job_id, text, percent)
            except Exception as e:
                logger.warning(f"Failed to update job progress: {e}")

        # Process contacts with cancellation support
        logger.info(f"Job {job_id} starting contact processing for {len(uploaded_files)} file(s)")
        try:
            result = filter_service.process_contacts(
                uploaded_files, settings, job_id, original_filenames,
                cancel_event, progress_callback
            )
        except RuntimeError as e:
            if "cancelled" in str(e).lower():
                logger.info(f"Job {job_id} was cancelled during processing")
                db.update_job_status(job_id, "cancelled")
                return
            else:
                raise  # Re-raise if it's a different RuntimeError
        
        # Check for cancellation after processing
        if cancel_event.is_set():
            logger.info(f"Job {job_id} was cancelled after processing")
            db.update_job_status(job_id, "cancelled")
            return
        
        # Check timeout
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed > JOB_PROCESSING_TIMEOUT_SECONDS:
            logger.warning(f"Job {job_id} exceeded timeout after processing ({elapsed:.1f}s > {JOB_PROCESSING_TIMEOUT_SECONDS}s)")
            db.update_job_status(job_id, "failed")
            return
        
        # Save analytics to database
        logger.info(f"Job {job_id} saving analytics to database")
        db.save_analytics(job_id, result["analytics"])
        
        # Get the generated output filename (preserves user prefix)
        output_filename = result.get("output_filename")
        if not output_filename:
            # Fallback: extract from path if filename not in result
            output_path = Path(result["output_path"])
            output_filename = output_path.name
        
        # Move output file to results folder, keeping the original filename
        output_path = Path(result["output_path"])
        new_output_path = RESULTS_FOLDER / output_filename
        output_path.rename(new_output_path)
        logger.info(f"Job {job_id} output file moved to {new_output_path}")
        
        # Update job status with the proper output filename (includes user prefix)
        db.update_job_status(job_id, "completed", output_filename)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Job {job_id} completed successfully in {elapsed:.1f}s. Files kept for potential reuse.")
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.error(f"Error processing job {job_id} after {elapsed:.1f}s: {e}", exc_info=True)
        db.update_job_status(job_id, "failed")
        # Don't delete files on error either - keep them for potential retry or reuse
        logger.info(f"Job {job_id} failed. Files kept for potential reuse.")
    finally:
        # Clean up active_jobs tracking
        with active_jobs_lock:
            if job_id in active_jobs:
                del active_jobs[job_id]
                logger.debug(f"Job {job_id} removed from active_jobs tracking")

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Upload Excel files and validate them"""
    try:
        saved_paths, original_names = save_uploaded_files(request, UPLOAD_FOLDER)

        # Save file metadata to database with validation
        import uuid
        import os
        file_ids = []
        validations = []
        for i, (path, original_name) in enumerate(zip(saved_paths, original_names)):
            file_id = str(uuid.uuid4())
            file_size = os.path.getsize(path) if os.path.exists(path) else 0

            # Validate file and cache result
            try:
                validation_result = validate_excel_file(path)
                validation_result['file_size'] = file_size
                validation_result['original_name'] = original_name
                validation_result['file_id'] = file_id
            except Exception as val_error:
                logger.warning(f"Could not validate file {original_name}: {val_error}")
                validation_result = None

            db.save_uploaded_file(file_id, original_name, path, file_size, validation_result)
            file_ids.append(file_id)
            validations.append(validation_result)

        return jsonify({
            "success": True,
            "files": original_names,
            "paths": saved_paths,
            "fileIds": file_ids,
            "validations": validations
        }), 200
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        # Sanitize error message to prevent information leakage
        error_msg = "Failed to upload files"
        if isinstance(e, ValueError):
            error_msg = str(e)  # ValueError messages are usually safe
        return jsonify({"success": False, "error": error_msg}), 400


@app.route('/api/validate-file', methods=['POST'])
def validate_file():
    """
    Validate an uploaded Excel file and detect sheets.
    Accepts file upload directly for validation before saving.
    """
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({"success": False, "error": "No file selected"}), 400

        # Validate file extension
        if not (file.filename.lower().endswith('.xlsx') or file.filename.lower().endswith('.xls')):
            return jsonify({"success": False, "error": "Only Excel files (.xlsx, .xls) are supported"}), 400

        # Save file temporarily for validation
        import uuid
        import os
        temp_filename = f"validate_{uuid.uuid4()}.xlsx"
        temp_path = UPLOAD_FOLDER / temp_filename

        try:
            file.save(str(temp_path))
            file_size = temp_path.stat().st_size

            # Validate the file
            validation_result = validate_excel_file(str(temp_path))
            validation_result['file_size'] = file_size
            validation_result['original_name'] = file.filename

            return jsonify({
                "success": True,
                "validation": validation_result
            }), 200

        finally:
            # Clean up temp file
            if temp_path.exists():
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.warning(f"Could not delete temp validation file: {e}")

    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to validate file"}), 400


@app.route('/api/validate-uploaded/<file_id>', methods=['GET'])
def validate_uploaded_file(file_id: str):
    """
    Validate a previously uploaded file by its ID.
    Returns cached validation if available, otherwise validates and caches.
    """
    try:
        file_meta = db.get_uploaded_file(file_id)
        if not file_meta:
            return jsonify({"success": False, "error": "File not found"}), 404

        # Check for cached validation first
        cached_validation = file_meta.get("validation_result")
        if cached_validation:
            # Parse if it's a string (shouldn't be, but just in case)
            import json
            if isinstance(cached_validation, str):
                cached_validation = json.loads(cached_validation)
            # Ensure file_id is set
            cached_validation['file_id'] = file_id
            return jsonify({
                "success": True,
                "validation": cached_validation,
                "cached": True
            }), 200

        stored_path = file_meta.get("stored_path")
        if not stored_path or not Path(stored_path).exists():
            return jsonify({"success": False, "error": "File no longer exists on disk"}), 404

        # Validate the file
        validation_result = validate_excel_file(stored_path)
        validation_result['original_name'] = file_meta.get('original_name', '')
        validation_result['file_size'] = file_meta.get('file_size', 0)
        validation_result['file_id'] = file_id

        # Cache the validation result
        db.update_file_validation(file_id, validation_result)

        return jsonify({
            "success": True,
            "validation": validation_result,
            "cached": False
        }), 200

    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to validate file"}), 500

@app.route('/api/process', methods=['POST'])
def process_contacts():
    """Start processing job"""
    try:
        if not request.json:
            return jsonify({"success": False, "error": "Invalid request: JSON body required"}), 400
        
        data = request.json
        files = data.get("files", [])  # Can be file paths
        file_ids = data.get("fileIds", [])  # Optional: file IDs from database
        settings = data.get("settings", {})
        
        if not files and not file_ids:
            return jsonify({"success": False, "error": "No files provided"}), 400
        
        # Validate settings is a dict
        if not isinstance(settings, dict):
            return jsonify({"success": False, "error": "Invalid settings format"}), 400
        
        # Get full paths for uploaded files
        uploaded_files = []
        original_filenames = []
        all_file_names = []  # For job creation
        
        # Process file IDs first (previously uploaded files)
        if file_ids:
            if not isinstance(file_ids, list):
                return jsonify({"success": False, "error": "Invalid fileIds format"}), 400
            
            logger.info(f"Processing {len(file_ids)} file ID(s) for previously uploaded files")
            logger.info(f"Current UPLOAD_FOLDER: {UPLOAD_FOLDER}")
            
            for file_id in file_ids:
                if not isinstance(file_id, str) or not file_id.strip():
                    logger.warning(f"Skipping invalid file_id: {file_id}")
                    continue
                
                file_meta = db.get_uploaded_file(file_id)
                if not file_meta:
                    logger.warning(f"File ID {file_id} not found in database")
                    continue
                
                stored_path = file_meta.get("stored_path")
                if not stored_path:
                    logger.warning(f"File ID {file_id} has no stored_path in metadata")
                    continue
                
                logger.debug(f"Processing file_id {file_id}: stored_path={stored_path}, original_name={file_meta.get('original_name')}")
                stored_path_obj = Path(stored_path)
                file_found = False
                
                # First, try the stored path as-is
                resolved_stored = stored_path_obj.resolve()
                if resolved_stored.exists():
                    logger.debug(f"Stored path exists: {resolved_stored}")
                    try:
                        # Validate path is within upload folder to prevent path traversal
                        resolved_stored.relative_to(UPLOAD_FOLDER.resolve())
                        uploaded_files.append(str(resolved_stored))
                        file_found = True
                        logger.info(f"Successfully located file {file_id} at {resolved_stored}")
                    except ValueError:
                        # Path exists but is outside upload folder - try to find it in current upload folder
                        logger.info(f"Stored path {stored_path} exists but is outside current upload folder ({UPLOAD_FOLDER}), trying to locate file by name")
                        filename = stored_path_obj.name
                        # Try to find the file in the current upload folder by filename
                        potential_path = UPLOAD_FOLDER / filename
                        if potential_path.exists():
                            uploaded_files.append(str(potential_path.resolve()))
                            file_found = True
                            logger.info(f"Found file {filename} in current upload folder at {potential_path}")
                        else:
                            logger.warning(f"File {filename} not found in current upload folder at {potential_path}")
                else:
                    logger.warning(f"Stored path does not exist: {resolved_stored}")
                    # Try to find the file in the current upload folder by filename
                    filename = stored_path_obj.name
                    potential_path = UPLOAD_FOLDER / filename
                    if potential_path.exists():
                        uploaded_files.append(str(potential_path.resolve()))
                        file_found = True
                        logger.info(f"Found file {filename} in current upload folder at {potential_path} (stored path was invalid)")
                    else:
                        logger.warning(f"File {filename} not found in current upload folder at {potential_path}")
                
                if file_found:
                    original_filenames.append(file_meta.get("original_name", ""))
                    all_file_names.append(file_meta.get("original_name", ""))
                    # Update last used timestamp
                    db.update_file_last_used(file_id)
                else:
                    logger.error(f"Could not locate file for ID {file_id} (stored_path: {stored_path}, current upload folder: {UPLOAD_FOLDER})")
        
        # Process new file paths - only allow files in upload folder
        if files:
            if not isinstance(files, list):
                return jsonify({"success": False, "error": "Invalid files format"}), 400
            
            for f in files:
                if not f or not isinstance(f, str) or f.strip() == '':
                    continue
                
                # Prevent path traversal - only allow filenames, not paths
                file_name = Path(f).name  # Extract just the filename
                file_path_obj = UPLOAD_FOLDER / file_name
                
                # Validate path is within upload folder
                try:
                    file_path_obj.resolve().relative_to(UPLOAD_FOLDER.resolve())
                except ValueError:
                    logger.warning(f"Path traversal attempt detected: {f}")
                    continue
                
                if file_path_obj.exists():
                    file_path_str = str(file_path_obj)
                    uploaded_files.append(file_path_str)
                    original_filenames.append(file_name)
                    all_file_names.append(file_name)
        
        if not uploaded_files:
            error_details = []
            if file_ids:
                error_details.append(f"{len(file_ids)} file ID(s) provided but none could be located")
            if files:
                error_details.append(f"{len(files)} file path(s) provided but none were found")
            error_msg = "No valid files found. " + ". ".join(error_details) if error_details else "No valid files found"
            logger.error(error_msg)
            return jsonify({"success": False, "error": error_msg}), 400
        
        # Deduplicate file names (in case same file was added via both fileIds and files)
        unique_file_names = []
        seen_names = set()
        for name in all_file_names:
            if name not in seen_names:
                unique_file_names.append(name)
                seen_names.add(name)
        
        # Create job - store original file names for display
        job_id = db.create_job(settings, unique_file_names)
        logger.info(f"Created job {job_id} for {len(unique_file_names)} file(s)")
        
        # Create cancellation event for this job
        cancel_event = threading.Event()
        
        # Start background processing
        thread = threading.Thread(
            target=process_job_async,
            args=(job_id, uploaded_files, original_filenames, settings, cancel_event)
        )
        thread.daemon = True
        
        # Track active job
        with active_jobs_lock:
            active_jobs[job_id] = {
                "thread": thread,
                "cancel_event": cancel_event,
                "start_time": datetime.now()
            }
        
        thread.start()
        logger.info(f"Started background thread for job {job_id}")
        
        return jsonify({
            "success": True,
            "jobId": job_id,
            "status": "pending"
        }), 200
        
    except Exception as e:
        logger.error(f"Process error: {e}", exc_info=True)
        # Don't expose internal error details to client
        return jsonify({"success": False, "error": "Failed to process files. Please try again."}), 400

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
                "input_files": job["input_files"],
                "output_filename": job.get("output_filename"),
                "progress_text": job.get("progress_text"),
                "progress_percent": job.get("progress_percent", 0)
            }
        }

        if job.get("analytics"):
            response["job"]["analytics"] = job["analytics"]

        if job["status"] == "completed" and job.get("output_filename"):
            response["job"]["downloadUrl"] = f"/api/jobs/{job_id}/download"

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Get job error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to retrieve job information"}), 500

@app.route('/api/jobs/<job_id>/download', methods=['GET'])
def download_results(job_id: str):
    """Download Excel results file (or zip for separated firm type jobs)"""
    try:
        job = db.get_job(job_id)
        if not job:
            return jsonify({"success": False, "error": "Job not found"}), 404

        if job["status"] != "completed":
            return jsonify({"success": False, "error": "Job not completed"}), 400

        output_file = RESULTS_FOLDER / job["output_filename"]
        if not output_file.exists():
            return jsonify({"success": False, "error": "File not found"}), 404

        # Determine mimetype based on file extension
        if job["output_filename"].endswith('.zip'):
            mimetype = 'application/zip'
        else:
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        return send_file(
            str(output_file),
            mimetype=mimetype,
            as_attachment=True,
            download_name=job["output_filename"]
        )

    except Exception as e:
        logger.error(f"Download error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to download file"}), 500


@app.route('/api/jobs/<job_id>/download/<filename>', methods=['GET'])
def download_individual_file(job_id: str, filename: str):
    """Download individual file from a separated firm type job's zip or standalone file"""
    import zipfile

    try:
        job = db.get_job(job_id)
        if not job:
            return jsonify({"success": False, "error": "Job not found"}), 404

        if job["status"] != "completed":
            return jsonify({"success": False, "error": "Job not completed"}), 400

        output_file = RESULTS_FOLDER / job["output_filename"]
        if not output_file.exists():
            return jsonify({"success": False, "error": "File not found"}), 404

        # Sanitize filename to prevent path traversal
        safe_filename = Path(filename).name

        # First check if this is a standalone file (e.g., Premier file)
        standalone_file = RESULTS_FOLDER / safe_filename
        if standalone_file.exists() and standalone_file.is_file():
            return send_file(
                str(standalone_file),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=safe_filename
            )

        # Otherwise check if it's a zip file and extract from it
        if not job["output_filename"].endswith('.zip'):
            return jsonify({"success": False, "error": "File not found"}), 404

        # Extract the requested file from the zip
        try:
            with zipfile.ZipFile(str(output_file), 'r') as zipf:
                if safe_filename not in zipf.namelist():
                    return jsonify({"success": False, "error": "File not found in archive"}), 404

                file_data = zipf.read(safe_filename)

                return send_file(
                    io.BytesIO(file_data),
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    download_name=safe_filename
                )
        except zipfile.BadZipFile:
            return jsonify({"success": False, "error": "Invalid archive file"}), 500

    except Exception as e:
        logger.error(f"Individual file download error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to download file"}), 500


@app.route('/api/jobs/<job_id>/files', methods=['GET'])
def list_files_in_job(job_id: str):
    """List files in a separated firm type job's zip"""
    import zipfile

    try:
        job = db.get_job(job_id)
        if not job:
            return jsonify({"success": False, "error": "Job not found"}), 404

        if job["status"] != "completed":
            return jsonify({"success": False, "error": "Job not completed"}), 400

        output_file = RESULTS_FOLDER / job["output_filename"]
        if not output_file.exists():
            return jsonify({"success": False, "error": "File not found"}), 404

        # Check if it's a zip file
        if not job["output_filename"].endswith('.zip'):
            # Single file job
            return jsonify({
                "success": True,
                "isSeparatedByFirmType": False,
                "files": [{
                    "filename": job["output_filename"],
                    "size": output_file.stat().st_size
                }]
            }), 200

        # List files in zip
        try:
            with zipfile.ZipFile(str(output_file), 'r') as zipf:
                files = []
                for info in zipf.infolist():
                    files.append({
                        "filename": info.filename,
                        "size": info.file_size,
                        "compressedSize": info.compress_size
                    })

                return jsonify({
                    "success": True,
                    "isSeparatedByFirmType": True,
                    "files": files
                }), 200
        except zipfile.BadZipFile:
            return jsonify({"success": False, "error": "Invalid archive file"}), 500

    except Exception as e:
        logger.error(f"List files error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to list files"}), 500

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
                    "settings": job["settings"],
                    "output_filename": job.get("output_filename")
                }
                for job in jobs
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"List jobs error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to list jobs"}), 500

@app.route('/api/jobs/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id: str):
    """Cancel a processing job"""
    try:
        job = db.get_job(job_id)
        if not job:
            return jsonify({"success": False, "error": "Job not found"}), 404
        
        # Check if job is in a cancellable state
        if job["status"] not in ["pending", "processing"]:
            return jsonify({
                "success": False,
                "error": f"Job cannot be cancelled (current status: {job['status']})"
            }), 400
        
        # Set cancellation event if job is active
        with active_jobs_lock:
            if job_id in active_jobs:
                active_jobs[job_id]["cancel_event"].set()
                logger.info(f"Job {job_id} cancellation requested")
            else:
                # Job might have just completed or failed, but update status anyway
                logger.info(f"Job {job_id} cancellation requested but not in active_jobs (may have just completed)")
        
        # Update job status to cancelled
        db.update_job_status(job_id, "cancelled")
        logger.info(f"Job {job_id} status updated to 'cancelled'")
        
        return jsonify({"success": True}), 200
        
    except Exception as e:
        logger.error(f"Cancel job error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to cancel job"}), 500

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
        logger.error(f"Delete job error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to delete job"}), 500

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
        if not request.json:
            return jsonify({"success": False, "error": "Invalid request: JSON body required"}), 400
        
        data = request.json
        name = data.get("name")
        settings = data.get("settings")
        
        if not name or not isinstance(name, str) or not name.strip():
            return jsonify({"success": False, "error": "Valid preset name required"}), 400
        
        if not settings or not isinstance(settings, dict):
            return jsonify({"success": False, "error": "Valid settings dictionary required"}), 400
        
        preset_id = db.create_preset(name, settings)
        return jsonify({
            "success": True,
            "presetId": preset_id
        }), 201
        
    except Exception as e:
        logger.error(f"Create preset error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to create preset"}), 500

@app.route('/api/settings/presets/<preset_id>', methods=['PUT'])
def update_preset(preset_id: str):
    """Update a settings preset"""
    try:
        if not request.json:
            return jsonify({"success": False, "error": "Invalid request: JSON body required"}), 400
        
        data = request.json
        name = data.get("name")
        settings = data.get("settings")
        
        if name is not None and (not isinstance(name, str) or not name.strip()):
            return jsonify({"success": False, "error": "Invalid preset name"}), 400
        
        if settings is not None and not isinstance(settings, dict):
            return jsonify({"success": False, "error": "Invalid settings format"}), 400
        
        if name is None and settings is None:
            return jsonify({"success": False, "error": "Name or settings required"}), 400
        
        updated = db.update_preset(preset_id, name=name, settings=settings)
        if updated:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "error": "Could not update preset (may be default or not found)"}), 400
        
    except Exception as e:
        logger.error(f"Update preset error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to update preset"}), 500

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
        logger.error(f"Delete preset error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to delete preset"}), 500


@app.route('/api/settings/presets/<preset_id>/default', methods=['POST'])
def set_default_preset(preset_id: str):
    """Set a preset as the default"""
    try:
        success = db.set_default_preset(preset_id)
        if success:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "error": "Preset not found"}), 404
    except Exception as e:
        logger.error(f"Set default preset error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to set default preset"}), 500


@app.route('/api/files', methods=['GET'])
def list_uploaded_files():
    """List all previously uploaded files with cached validation"""
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
                    "lastUsedAt": f["last_used_at"],
                    "fileExists": Path(f["stored_path"]).exists() if f.get("stored_path") else False,
                    "validation": f.get("validation_result")
                }
                for f in files
            ]
        }), 200
    except Exception as e:
        logger.error(f"List files error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to list files"}), 500


@app.route('/api/files/backfill-validation', methods=['POST'])
def backfill_file_validation():
    """Validate all previously uploaded files that don't have cached validation"""
    try:
        files = db.get_files_without_validation()
        validated_count = 0
        failed_count = 0
        results = []

        for f in files:
            file_id = f["id"]
            stored_path = f.get("stored_path")

            if not stored_path or not Path(stored_path).exists():
                results.append({
                    "id": file_id,
                    "originalName": f.get("original_name", ""),
                    "status": "skipped",
                    "reason": "File no longer exists"
                })
                continue

            try:
                validation_result = validate_excel_file(stored_path)
                validation_result['original_name'] = f.get('original_name', '')
                validation_result['file_size'] = f.get('file_size', 0)
                validation_result['file_id'] = file_id

                db.update_file_validation(file_id, validation_result)
                validated_count += 1
                results.append({
                    "id": file_id,
                    "originalName": f.get("original_name", ""),
                    "status": "validated",
                    "canProcess": validation_result.get("can_process", False)
                })
            except Exception as val_error:
                logger.warning(f"Could not validate file {file_id}: {val_error}")
                failed_count += 1
                results.append({
                    "id": file_id,
                    "originalName": f.get("original_name", ""),
                    "status": "failed",
                    "reason": str(val_error)
                })

        return jsonify({
            "success": True,
            "totalFiles": len(files),
            "validatedCount": validated_count,
            "failedCount": failed_count,
            "skippedCount": len(files) - validated_count - failed_count,
            "results": results
        }), 200
    except Exception as e:
        logger.error(f"Backfill validation error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to backfill validation"}), 500

# Removal list endpoints
@app.route('/api/removal-lists', methods=['GET'])
def get_removal_lists():
    """Get all removal lists, optionally filtered by type"""
    try:
        list_type = request.args.get('type')  # 'account' or 'contact'
        limit = request.args.get('limit', 50, type=int)
        lists = db.list_removal_lists(list_type, limit)

        return jsonify({
            "success": True,
            "lists": [
                {
                    "id": r["id"],
                    "listType": r["list_type"],
                    "originalName": r["original_name"],
                    "storedPath": r["stored_path"],
                    "fileSize": r["file_size"],
                    "entryCount": r["entry_count"],
                    "isActive": r["is_active"],
                    "uploadedAt": r["uploaded_at"],
                    "lastUsedAt": r["last_used_at"],
                    "fileExists": Path(r["stored_path"]).exists() if r.get("stored_path") else False
                }
                for r in lists
            ]
        }), 200
    except Exception as e:
        logger.error(f"Get removal lists error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to get removal lists"}), 500

@app.route('/api/removal-lists/active', methods=['GET'])
def get_active_removal_lists():
    """Get the currently active removal lists (one per type)"""
    try:
        account_list = db.get_active_removal_list('account')
        contact_list = db.get_active_removal_list('contact')

        result = {
            "success": True,
            "accountRemovalList": None,
            "contactRemovalList": None
        }

        if account_list:
            result["accountRemovalList"] = {
                "id": account_list["id"],
                "listType": account_list["list_type"],
                "originalName": account_list["original_name"],
                "entryCount": account_list["entry_count"],
                "uploadedAt": account_list["uploaded_at"],
                "fileExists": Path(account_list["stored_path"]).exists() if account_list.get("stored_path") else False
            }

        if contact_list:
            result["contactRemovalList"] = {
                "id": contact_list["id"],
                "listType": contact_list["list_type"],
                "originalName": contact_list["original_name"],
                "entryCount": contact_list["entry_count"],
                "uploadedAt": contact_list["uploaded_at"],
                "fileExists": Path(contact_list["stored_path"]).exists() if contact_list.get("stored_path") else False
            }

        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Get active removal lists error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to get active removal lists"}), 500

@app.route('/api/removal-lists/upload', methods=['POST'])
def upload_removal_list():
    """Upload a new removal list (CSV file)"""
    import uuid
    import csv

    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400

        file = request.files['file']
        list_type = request.form.get('listType')  # 'account' or 'contact'

        if not file.filename:
            return jsonify({"success": False, "error": "No file selected"}), 400

        if list_type not in ['account', 'contact']:
            return jsonify({"success": False, "error": "Invalid list type. Must be 'account' or 'contact'"}), 400

        # Validate file extension
        if not file.filename.lower().endswith('.csv'):
            return jsonify({"success": False, "error": "Only CSV files are supported"}), 400

        # Generate unique filename
        list_id = str(uuid.uuid4())
        original_name = file.filename
        file_extension = Path(original_name).suffix
        stored_filename = f"removal_{list_type}_{list_id}{file_extension}"
        stored_path = UPLOAD_FOLDER / stored_filename

        # Save file
        file.save(str(stored_path))
        file_size = stored_path.stat().st_size

        # Count entries in the CSV
        entry_count = 0
        try:
            with open(stored_path, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # For account lists, count by Account Name
                    # For contact lists, count by Email or Contact Name
                    if list_type == 'account':
                        if row.get('Account Name') or row.get('account') or row.get('ACCOUNT NAME'):
                            entry_count += 1
                    else:  # contact
                        if row.get('Email') or row.get('email') or row.get('EMAIL') or row.get('Contact Name'):
                            entry_count += 1
        except Exception as e:
            logger.warning(f"Could not count entries in removal list: {e}")
            # Try counting lines as fallback
            with open(stored_path, 'r', encoding='utf-8-sig') as f:
                entry_count = sum(1 for _ in f) - 1  # Subtract header row

        # Save metadata to database (this will deactivate any existing list of the same type)
        db.save_removal_list(list_id, list_type, original_name, str(stored_path), file_size, entry_count)

        logger.info(f"Uploaded {list_type} removal list: {original_name} ({entry_count} entries)")

        return jsonify({
            "success": True,
            "listId": list_id,
            "listType": list_type,
            "originalName": original_name,
            "entryCount": entry_count,
            "fileSize": file_size
        }), 201

    except Exception as e:
        logger.error(f"Upload removal list error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to upload removal list"}), 500

@app.route('/api/removal-lists/<list_id>/active', methods=['PUT'])
def update_removal_list_status(list_id: str):
    """Activate or deactivate a removal list"""
    try:
        if not request.json:
            return jsonify({"success": False, "error": "Invalid request: JSON body required"}), 400

        is_active = request.json.get('isActive', True)

        if not isinstance(is_active, bool):
            return jsonify({"success": False, "error": "isActive must be a boolean"}), 400

        updated = db.update_removal_list_active(list_id, is_active)

        if updated:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "error": "Removal list not found"}), 404

    except Exception as e:
        logger.error(f"Update removal list status error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to update removal list status"}), 500

@app.route('/api/removal-lists/<list_id>', methods=['DELETE'])
def delete_removal_list(list_id: str):
    """Delete a removal list"""
    try:
        # Get list info to delete file
        lists = db.list_removal_lists()
        list_info = next((r for r in lists if r['id'] == list_id), None)

        if list_info and list_info.get('stored_path'):
            stored_path = Path(list_info['stored_path'])
            if stored_path.exists():
                stored_path.unlink()

        deleted = db.delete_removal_list(list_id)

        if deleted:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "error": "Removal list not found"}), 404

    except Exception as e:
        logger.error(f"Delete removal list error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to delete removal list"}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

def cleanup_stuck_jobs():
    """Mark jobs stuck in 'processing' state as failed on startup"""
    try:
        logger.info("Checking for stuck jobs on startup...")
        jobs = db.list_jobs(limit=100)  # Get recent jobs
        
        threshold_time = datetime.now() - timedelta(seconds=JOB_STARTUP_CLEANUP_THRESHOLD_SECONDS)
        stuck_count = 0
        
        for job in jobs:
            if job["status"] == "processing":
                # Parse created_at timestamp
                try:
                    created_at = datetime.strptime(job["created_at"], "%Y-%m-%d %H:%M:%S")
                    if created_at < threshold_time:
                        logger.warning(f"Found stuck job {job['id']} (created at {job['created_at']}, threshold: {threshold_time})")
                        db.update_job_status(job["id"], "failed")
                        stuck_count += 1
                except (ValueError, KeyError) as e:
                    logger.warning(f"Could not parse timestamp for job {job.get('id', 'unknown')}: {e}")
                    # If we can't parse the timestamp, mark as failed to be safe
                    db.update_job_status(job["id"], "failed")
                    stuck_count += 1
        
        if stuck_count > 0:
            logger.info(f"Marked {stuck_count} stuck job(s) as failed during startup cleanup")
        else:
            logger.info("No stuck jobs found during startup cleanup")
            
    except Exception as e:
        logger.error(f"Error during startup cleanup: {e}", exc_info=True)

# Run startup cleanup
cleanup_stuck_jobs()

if __name__ == '__main__':
    # Bind to 0.0.0.0 to allow access from Docker containers
    app.run(debug=True, host='0.0.0.0', port=5000)

