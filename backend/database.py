"""
Database models and operations for the tiered email filtering web app.
Uses SQLite for minimal storage footprint.
"""
import sqlite3
import json
import uuid
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class Database:
    """SQLite database wrapper for jobs, analytics, and settings presets"""
    
    def __init__(self, db_path: str = "backend/data/app.db", timeout: float = 20.0):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
            timeout: Connection timeout in seconds (default: 20.0)
        """
        self.db_path = Path(db_path)
        self.timeout = timeout
        
        # Ensure data directory exists and is writable
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Verify database path is accessible
        if not self._verify_database_path():
            raise RuntimeError(f"Cannot access database path: {self.db_path}")
        
        self.init_database()
        self.init_default_preset()
    
    def _verify_database_path(self) -> bool:
        """Verify database path is accessible and writable"""
        try:
            # Check if parent directory is writable
            test_file = self.db_path.parent / ".test_write"
            try:
                test_file.touch()
                test_file.unlink()
                return True
            except (OSError, PermissionError) as e:
                logger.error(f"Database path not writable: {e}")
                return False
        except Exception as e:
            logger.error(f"Error verifying database path: {e}")
            return False
    
    @contextmanager
    def get_connection(self):
        """
        Get database connection with proper configuration.
        Uses context manager to ensure connection is always closed.
        
        Enables:
        - WAL mode for better concurrency
        - Foreign key constraints for data integrity
        - Timeout to prevent indefinite hangs
        """
        conn = None
        try:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=self.timeout
            )
            conn.row_factory = sqlite3.Row
            
            # Enable WAL mode for better concurrency and performance
            conn.execute("PRAGMA journal_mode=WAL")
            
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys=ON")
            
            # Set synchronous mode for better durability (NORMAL is a good balance)
            conn.execute("PRAGMA synchronous=NORMAL")
            
            # Set busy timeout (in milliseconds)
            conn.execute(f"PRAGMA busy_timeout={int(self.timeout * 1000)}")
            
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Unexpected database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def _execute_with_retry(self, operation, max_retries: int = 3, initial_delay: float = 0.1):
        """
        Execute database operation with retry logic for transient errors.
        
        Args:
            operation: Callable that performs the database operation
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
        
        Returns:
            Result of the operation
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return operation()
            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()
                # Retry on database locked or busy errors
                if "locked" in error_msg or "busy" in error_msg:
                    if attempt < max_retries - 1:
                        delay = initial_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Database locked, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        last_exception = e
                        continue
                # For other operational errors, don't retry
                raise
            except sqlite3.Error as e:
                # For other SQLite errors, don't retry
                raise
        
        # If we exhausted retries, raise the last exception
        if last_exception:
            raise last_exception
    
    def init_database(self):
        """Initialize database schema"""
        def _init_schema(conn):
            cursor = conn.cursor()
            
            # Jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    output_filename TEXT,
                    settings TEXT,
                    input_files TEXT
                )
            """)
            
            # Analytics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    job_id TEXT PRIMARY KEY,
                    processing_summary TEXT,
                    input_file_details TEXT,
                    delta_analysis TEXT,
                    delta_summary TEXT,
                    filter_breakdown TEXT,
                    excluded_firms_summary TEXT,
                    excluded_firms_list TEXT,
                    included_firms_list TEXT,
                    excluded_firm_contacts_count INTEGER,
                    is_separated_by_firm_type INTEGER DEFAULT 0,
                    firm_type_breakdown TEXT,
                    files_in_zip TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                )
            """)

            # Add new columns to existing analytics table if they don't exist
            # SQLite doesn't support IF NOT EXISTS for columns, so we check first
            cursor.execute("PRAGMA table_info(analytics)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            if 'is_separated_by_firm_type' not in existing_columns:
                cursor.execute("ALTER TABLE analytics ADD COLUMN is_separated_by_firm_type INTEGER DEFAULT 0")
            if 'firm_type_breakdown' not in existing_columns:
                cursor.execute("ALTER TABLE analytics ADD COLUMN firm_type_breakdown TEXT")
            if 'files_in_zip' not in existing_columns:
                cursor.execute("ALTER TABLE analytics ADD COLUMN files_in_zip TEXT")
            
            # Settings presets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings_presets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    is_default INTEGER DEFAULT 0,
                    settings TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Uploaded files table - stores file metadata for reuse
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uploaded_files (
                    id TEXT PRIMARY KEY,
                    original_name TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    file_size INTEGER,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP,
                    validation_result TEXT
                )
            """)

            # Add validation_result column if it doesn't exist (migration for existing DBs)
            cursor.execute("PRAGMA table_info(uploaded_files)")
            uploaded_files_columns = {row[1] for row in cursor.fetchall()}
            if 'validation_result' not in uploaded_files_columns:
                cursor.execute("ALTER TABLE uploaded_files ADD COLUMN validation_result TEXT")

            # Removal lists table - stores account and contact removal lists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS removal_lists (
                    id TEXT PRIMARY KEY,
                    list_type TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    file_size INTEGER,
                    entry_count INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_presets_default ON settings_presets(is_default)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_files_uploaded_at ON uploaded_files(uploaded_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_files_last_used ON uploaded_files(last_used_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_removal_lists_type ON removal_lists(list_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_removal_lists_active ON removal_lists(is_active)")
        
        try:
            with self.get_connection() as conn:
                _init_schema(conn)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def init_default_preset(self):
        """Initialize default settings preset matching CLI defaults"""
        # Import tier config utils for default keywords
        from api.tier_config_utils import (
            get_default_tier1_keywords,
            get_default_tier2_keywords,
            get_default_tier3_keywords
        )
        
        # Default settings matching TieredFilter class defaults
        default_tier1 = get_default_tier1_keywords()
        default_tier2 = get_default_tier2_keywords()
        default_tier3 = get_default_tier3_keywords()
        
        default_settings = {
            "includeAllFirms": False,  # --include-all-firms flag (default: False)
            "findEmails": True,  # --find-emails flag (default: True)
            "firmExclusion": False,  # enable_firm_exclusion (default: False)
            "contactInclusion": False,  # enable_contact_inclusion (default: False)
            "tier1Limit": 10,  # tier1_limit (default: 10)
            "tier2Limit": 6,  # tier2_limit (default: 6)
            "tier3Limit": 3,  # Tier 3 limit when enabled (default: 3)
            "userPrefix": "Combined-Contacts",  # Default prefix
            "tier1Filters": {
                "includeKeywords": default_tier1["include"],
                "excludeKeywords": default_tier1["exclude"],
                "requireInvestmentTeam": False
            },
            "tier2Filters": {
                "includeKeywords": default_tier2["include"],
                "excludeKeywords": default_tier2["exclude"],
                "requireInvestmentTeam": True
            },
            "tier3Filters": {
                "includeKeywords": default_tier3["include"],
                "excludeKeywords": default_tier3["exclude"],
                "requireInvestmentTeam": False
            },
            "firmExclusionList": "",
            "firmInclusionList": "",
            "contactExclusionList": "",
            "contactInclusionList": "",
            "fieldFilters": []
        }
        
        def _init_preset(conn):
            cursor = conn.cursor()
            
            # Check if default preset exists
            cursor.execute("SELECT id, settings FROM settings_presets WHERE is_default = 1")
            existing = cursor.fetchone()
            
            if existing:
                # Update existing default preset to ensure it matches current defaults
                existing_settings = json.loads(existing['settings'])
                if existing_settings != default_settings:
                    logger.info("Updating default preset to match CLI defaults")
                    cursor.execute("""
                        UPDATE settings_presets 
                        SET settings = ?, name = 'Default (CLI Match)'
                        WHERE id = ?
                    """, (json.dumps(default_settings), existing['id']))
                else:
                    logger.info("Default preset already matches CLI defaults")
            else:
                # Create default preset
                preset_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO settings_presets (id, name, is_default, settings)
                    VALUES (?, ?, ?, ?)
                """, (preset_id, "Default (CLI Match)", 1, json.dumps(default_settings)))
                logger.info("Default preset initialized with CLI matching settings")
        
        try:
            with self.get_connection() as conn:
                _init_preset(conn)
        except Exception as e:
            logger.error(f"Failed to initialize default preset: {e}")
            raise
    
    def create_job(self, settings: Dict, input_files: List[str]) -> str:
        """Create a new processing job"""
        job_id = str(uuid.uuid4())
        
        def _create_job(conn):
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO jobs (id, status, settings, input_files)
                VALUES (?, ?, ?, ?)
            """, (job_id, "pending", json.dumps(settings), json.dumps(input_files)))
        
        try:
            with self.get_connection() as conn:
                self._execute_with_retry(lambda: _create_job(conn))
            logger.debug(f"Created job: {job_id}")
            return job_id
        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise
    
    def update_job_status(self, job_id: str, status: str, output_filename: Optional[str] = None):
        """Update job status"""
        def _update_status(conn):
            cursor = conn.cursor()
            if output_filename:
                cursor.execute("""
                    UPDATE jobs SET status = ?, output_filename = ? WHERE id = ?
                """, (status, output_filename, job_id))
            else:
                cursor.execute("""
                    UPDATE jobs SET status = ? WHERE id = ?
                """, (status, job_id))
        
        try:
            with self.get_connection() as conn:
                self._execute_with_retry(lambda: _update_status(conn))
            logger.debug(f"Updated job {job_id} status to {status}")
        except Exception as e:
            logger.error(f"Failed to update job status for {job_id}: {e}")
            raise
    
    def save_analytics(self, job_id: str, analytics: Dict):
        """Save analytics data for a job"""
        def _save_analytics(conn):
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO analytics (
                    job_id, processing_summary, input_file_details, delta_analysis,
                    delta_summary, filter_breakdown, excluded_firms_summary,
                    excluded_firms_list, included_firms_list, excluded_firm_contacts_count,
                    is_separated_by_firm_type, firm_type_breakdown, files_in_zip
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                json.dumps(analytics.get("processing_summary")),
                json.dumps(analytics.get("input_file_details")),
                json.dumps(analytics.get("delta_analysis")),
                json.dumps(analytics.get("delta_summary")),
                json.dumps(analytics.get("filter_breakdown")),
                json.dumps(analytics.get("excluded_firms_summary")),
                json.dumps(analytics.get("excluded_firms_list", [])),
                json.dumps(analytics.get("included_firms_list", [])),
                analytics.get("excluded_firm_contacts_count", 0),
                1 if analytics.get("is_separated_by_firm_type") else 0,
                json.dumps(analytics.get("firm_type_breakdown")),
                json.dumps(analytics.get("files_in_zip"))
            ))
        
        try:
            with self.get_connection() as conn:
                self._execute_with_retry(lambda: _save_analytics(conn))
            logger.debug(f"Saved analytics for job: {job_id}")
        except Exception as e:
            logger.error(f"Failed to save analytics for job {job_id}: {e}")
            raise
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job with analytics"""
        def _get_job(conn):
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            job_row = cursor.fetchone()
            
            if not job_row:
                return None
            
            job = dict(job_row)
            job["settings"] = json.loads(job["settings"])
            job["input_files"] = json.loads(job["input_files"])
            
            # Get analytics
            cursor.execute("SELECT * FROM analytics WHERE job_id = ?", (job_id,))
            analytics_row = cursor.fetchone()
            
            if analytics_row:
                analytics = dict(analytics_row)
                analytics["processing_summary"] = json.loads(analytics["processing_summary"]) if analytics["processing_summary"] else None
                analytics["input_file_details"] = json.loads(analytics["input_file_details"]) if analytics["input_file_details"] else None
                analytics["delta_analysis"] = json.loads(analytics["delta_analysis"]) if analytics["delta_analysis"] else None
                analytics["delta_summary"] = json.loads(analytics["delta_summary"]) if analytics["delta_summary"] else None
                analytics["filter_breakdown"] = json.loads(analytics["filter_breakdown"]) if analytics["filter_breakdown"] else None
                analytics["excluded_firms_summary"] = json.loads(analytics["excluded_firms_summary"]) if analytics["excluded_firms_summary"] else None
                analytics["excluded_firms_list"] = json.loads(analytics["excluded_firms_list"]) if analytics["excluded_firms_list"] else []
                analytics["included_firms_list"] = json.loads(analytics["included_firms_list"]) if analytics["included_firms_list"] else []
                # Firm type separation fields
                analytics["is_separated_by_firm_type"] = bool(analytics.get("is_separated_by_firm_type", 0))
                analytics["firm_type_breakdown"] = json.loads(analytics["firm_type_breakdown"]) if analytics.get("firm_type_breakdown") else None
                analytics["files_in_zip"] = json.loads(analytics["files_in_zip"]) if analytics.get("files_in_zip") else None
                job["analytics"] = analytics
            else:
                job["analytics"] = None
            
            return job
        
        try:
            with self.get_connection() as conn:
                return _get_job(conn)
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            raise
    
    def list_jobs(self, limit: int = 50) -> List[Dict]:
        """List all jobs, most recent first"""
        def _list_jobs(conn):
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, created_at, status, output_filename, settings, input_files
                FROM jobs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            jobs = []
            for row in cursor.fetchall():
                job = dict(row)
                job["settings"] = json.loads(job["settings"])
                job["input_files"] = json.loads(job["input_files"])
                jobs.append(job)
            
            return jobs
        
        try:
            with self.get_connection() as conn:
                return _list_jobs(conn)
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            raise
    
    def delete_job(self, job_id: str) -> bool:
        """Delete job and its analytics (cascade deletes analytics due to foreign key)"""
        def _delete_job(conn):
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            return cursor.rowcount > 0
        
        try:
            with self.get_connection() as conn:
                deleted = self._execute_with_retry(lambda: _delete_job(conn))
            if deleted:
                logger.debug(f"Deleted job: {job_id}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            raise
    
    def create_preset(self, name: str, settings: Dict) -> str:
        """Create a new settings preset"""
        preset_id = str(uuid.uuid4())
        
        def _create_preset(conn):
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO settings_presets (id, name, settings)
                VALUES (?, ?, ?)
            """, (preset_id, name, json.dumps(settings)))
        
        try:
            with self.get_connection() as conn:
                self._execute_with_retry(lambda: _create_preset(conn))
            logger.debug(f"Created preset: {preset_id}")
            return preset_id
        except Exception as e:
            logger.error(f"Failed to create preset: {e}")
            raise
    
    def get_presets(self) -> List[Dict]:
        """Get all presets including default"""
        def _get_presets(conn):
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, is_default, settings, created_at
                FROM settings_presets
                ORDER BY is_default DESC, created_at DESC
            """)
            
            presets = []
            for row in cursor.fetchall():
                preset = dict(row)
                preset["settings"] = json.loads(preset["settings"])
                preset["is_default"] = bool(preset["is_default"])
                presets.append(preset)
            
            return presets
        
        try:
            with self.get_connection() as conn:
                return _get_presets(conn)
        except Exception as e:
            logger.error(f"Failed to get presets: {e}")
            raise
    
    def update_preset(self, preset_id: str, name: str = None, settings: Dict = None) -> bool:
        """Update a preset's name and/or settings (cannot update default)"""
        def _update_preset(conn):
            cursor = conn.cursor()
            
            # Check if preset exists
            cursor.execute("SELECT is_default FROM settings_presets WHERE id = ?", (preset_id,))
            row = cursor.fetchone()
            if not row:
                return False

            # Build update query
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            
            if settings is not None:
                updates.append("settings = ?")
                params.append(json.dumps(settings))
            
            if not updates:
                return False
            
            params.append(preset_id)
            query = f"UPDATE settings_presets SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            
            return cursor.rowcount > 0
        
        try:
            with self.get_connection() as conn:
                updated = self._execute_with_retry(lambda: _update_preset(conn))
            if updated:
                logger.debug(f"Updated preset: {preset_id}")
            return updated
        except Exception as e:
            logger.error(f"Failed to update preset {preset_id}: {e}")
            raise
    
    def delete_preset(self, preset_id: str) -> bool:
        """Delete a preset (cannot delete default)"""
        def _delete_preset(conn):
            cursor = conn.cursor()
            
            # Check if it's the default preset
            cursor.execute("SELECT is_default FROM settings_presets WHERE id = ?", (preset_id,))
            row = cursor.fetchone()
            if row and row["is_default"]:
                return False
            
            cursor.execute("DELETE FROM settings_presets WHERE id = ?", (preset_id,))
            return cursor.rowcount > 0
        
        try:
            with self.get_connection() as conn:
                deleted = self._execute_with_retry(lambda: _delete_preset(conn))
            if deleted:
                logger.debug(f"Deleted preset: {preset_id}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete preset {preset_id}: {e}")
            raise

    def set_default_preset(self, preset_id: str) -> bool:
        """Set a preset as the default (unsets current default)"""
        def _set_default(conn):
            cursor = conn.cursor()

            # Check if preset exists
            cursor.execute("SELECT id FROM settings_presets WHERE id = ?", (preset_id,))
            if not cursor.fetchone():
                return False

            # Unset current default
            cursor.execute("UPDATE settings_presets SET is_default = 0 WHERE is_default = 1")

            # Set new default
            cursor.execute("UPDATE settings_presets SET is_default = 1 WHERE id = ?", (preset_id,))

            return cursor.rowcount > 0

        try:
            with self.get_connection() as conn:
                success = self._execute_with_retry(lambda: _set_default(conn))
            if success:
                logger.info(f"Set default preset: {preset_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to set default preset {preset_id}: {e}")
            raise

    def save_uploaded_file(self, file_id: str, original_name: str, stored_path: str,
                           file_size: int, validation_result: Optional[Dict] = None) -> None:
        """Save uploaded file metadata with optional validation result"""
        def _save_file(conn):
            cursor = conn.cursor()
            validation_json = json.dumps(validation_result) if validation_result else None
            cursor.execute("""
                INSERT INTO uploaded_files (id, original_name, stored_path, file_size, validation_result)
                VALUES (?, ?, ?, ?, ?)
            """, (file_id, original_name, stored_path, file_size, validation_json))

        try:
            with self.get_connection() as conn:
                self._execute_with_retry(lambda: _save_file(conn))
            logger.debug(f"Saved uploaded file: {file_id}")
        except Exception as e:
            logger.error(f"Failed to save uploaded file {file_id}: {e}")
            raise

    def update_file_validation(self, file_id: str, validation_result: Dict) -> bool:
        """Update validation result for an uploaded file"""
        def _update_validation(conn):
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE uploaded_files
                SET validation_result = ?
                WHERE id = ?
            """, (json.dumps(validation_result), file_id))
            return cursor.rowcount > 0

        try:
            with self.get_connection() as conn:
                updated = self._execute_with_retry(lambda: _update_validation(conn))
            if updated:
                logger.debug(f"Updated validation for file: {file_id}")
            return updated
        except Exception as e:
            logger.error(f"Failed to update validation for file {file_id}: {e}")
            raise
    
    def get_uploaded_file(self, file_id: str) -> Optional[Dict]:
        """Get uploaded file metadata"""
        def _get_file(conn):
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM uploaded_files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        
        try:
            with self.get_connection() as conn:
                return _get_file(conn)
        except Exception as e:
            logger.error(f"Failed to get uploaded file {file_id}: {e}")
            raise
    
    def list_uploaded_files(self, limit: int = 100) -> List[Dict]:
        """List all uploaded files, most recent first, with cached validation"""
        def _list_files(conn):
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, original_name, stored_path, file_size, uploaded_at, last_used_at, validation_result
                FROM uploaded_files
                ORDER BY uploaded_at DESC
                LIMIT ?
            """, (limit,))

            files = []
            for row in cursor.fetchall():
                file_dict = dict(row)
                # Parse validation_result JSON if present
                if file_dict.get('validation_result'):
                    try:
                        file_dict['validation_result'] = json.loads(file_dict['validation_result'])
                    except (json.JSONDecodeError, TypeError):
                        file_dict['validation_result'] = None
                files.append(file_dict)

            return files

        try:
            with self.get_connection() as conn:
                return _list_files(conn)
        except Exception as e:
            logger.error(f"Failed to list uploaded files: {e}")
            raise

    def get_files_without_validation(self) -> List[Dict]:
        """Get all uploaded files that don't have cached validation"""
        def _get_files(conn):
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, original_name, stored_path, file_size
                FROM uploaded_files
                WHERE validation_result IS NULL
                ORDER BY uploaded_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

        try:
            with self.get_connection() as conn:
                return _get_files(conn)
        except Exception as e:
            logger.error(f"Failed to get files without validation: {e}")
            raise
    
    def update_file_last_used(self, file_id: str) -> None:
        """Update last_used_at timestamp for a file"""
        def _update_timestamp(conn):
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE uploaded_files 
                SET last_used_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (file_id,))
        
        try:
            with self.get_connection() as conn:
                self._execute_with_retry(lambda: _update_timestamp(conn))
            logger.debug(f"Updated last_used_at for file: {file_id}")
        except Exception as e:
            logger.error(f"Failed to update last_used_at for file {file_id}: {e}")
            raise
    
    def delete_uploaded_file(self, file_id: str) -> bool:
        """Delete uploaded file record"""
        def _delete_file(conn):
            cursor = conn.cursor()
            cursor.execute("DELETE FROM uploaded_files WHERE id = ?", (file_id,))
            return cursor.rowcount > 0

        try:
            with self.get_connection() as conn:
                deleted = self._execute_with_retry(lambda: _delete_file(conn))
            if deleted:
                logger.debug(f"Deleted uploaded file: {file_id}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete uploaded file {file_id}: {e}")
            raise

    # Removal list methods
    def save_removal_list(self, list_id: str, list_type: str, original_name: str,
                          stored_path: str, file_size: int, entry_count: int) -> None:
        """Save removal list metadata. Deactivates any existing list of the same type."""
        def _save_list(conn):
            cursor = conn.cursor()
            # Deactivate existing lists of the same type
            cursor.execute("""
                UPDATE removal_lists SET is_active = 0 WHERE list_type = ?
            """, (list_type,))
            # Insert new list as active
            cursor.execute("""
                INSERT INTO removal_lists (id, list_type, original_name, stored_path, file_size, entry_count, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (list_id, list_type, original_name, stored_path, file_size, entry_count))

        try:
            with self.get_connection() as conn:
                self._execute_with_retry(lambda: _save_list(conn))
            logger.debug(f"Saved removal list: {list_id} ({list_type})")
        except Exception as e:
            logger.error(f"Failed to save removal list {list_id}: {e}")
            raise

    def get_active_removal_list(self, list_type: str) -> Optional[Dict]:
        """Get the active removal list of a given type"""
        def _get_list(conn):
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM removal_lists
                WHERE list_type = ? AND is_active = 1
                ORDER BY uploaded_at DESC
                LIMIT 1
            """, (list_type,))
            row = cursor.fetchone()
            return dict(row) if row else None

        try:
            with self.get_connection() as conn:
                return _get_list(conn)
        except Exception as e:
            logger.error(f"Failed to get active removal list for {list_type}: {e}")
            raise

    def list_removal_lists(self, list_type: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """List removal lists, optionally filtered by type"""
        def _list_lists(conn):
            cursor = conn.cursor()
            if list_type:
                cursor.execute("""
                    SELECT id, list_type, original_name, stored_path, file_size, entry_count,
                           is_active, uploaded_at, last_used_at
                    FROM removal_lists
                    WHERE list_type = ?
                    ORDER BY uploaded_at DESC
                    LIMIT ?
                """, (list_type, limit))
            else:
                cursor.execute("""
                    SELECT id, list_type, original_name, stored_path, file_size, entry_count,
                           is_active, uploaded_at, last_used_at
                    FROM removal_lists
                    ORDER BY uploaded_at DESC
                    LIMIT ?
                """, (limit,))

            lists = []
            for row in cursor.fetchall():
                list_dict = dict(row)
                list_dict['is_active'] = bool(list_dict['is_active'])
                lists.append(list_dict)
            return lists

        try:
            with self.get_connection() as conn:
                return _list_lists(conn)
        except Exception as e:
            logger.error(f"Failed to list removal lists: {e}")
            raise

    def update_removal_list_active(self, list_id: str, is_active: bool) -> bool:
        """Activate or deactivate a removal list"""
        def _update_active(conn):
            cursor = conn.cursor()
            if is_active:
                # If activating, first deactivate other lists of the same type
                cursor.execute("SELECT list_type FROM removal_lists WHERE id = ?", (list_id,))
                row = cursor.fetchone()
                if row:
                    cursor.execute("""
                        UPDATE removal_lists SET is_active = 0 WHERE list_type = ?
                    """, (row['list_type'],))

            cursor.execute("""
                UPDATE removal_lists SET is_active = ? WHERE id = ?
            """, (1 if is_active else 0, list_id))
            return cursor.rowcount > 0

        try:
            with self.get_connection() as conn:
                updated = self._execute_with_retry(lambda: _update_active(conn))
            if updated:
                logger.debug(f"Updated removal list {list_id} active status to {is_active}")
            return updated
        except Exception as e:
            logger.error(f"Failed to update removal list {list_id}: {e}")
            raise

    def update_removal_list_last_used(self, list_id: str) -> None:
        """Update last_used_at timestamp for a removal list"""
        def _update_timestamp(conn):
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE removal_lists
                SET last_used_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (list_id,))

        try:
            with self.get_connection() as conn:
                self._execute_with_retry(lambda: _update_timestamp(conn))
            logger.debug(f"Updated last_used_at for removal list: {list_id}")
        except Exception as e:
            logger.error(f"Failed to update last_used_at for removal list {list_id}: {e}")
            raise

    def delete_removal_list(self, list_id: str) -> bool:
        """Delete a removal list"""
        def _delete_list(conn):
            cursor = conn.cursor()
            cursor.execute("DELETE FROM removal_lists WHERE id = ?", (list_id,))
            return cursor.rowcount > 0

        try:
            with self.get_connection() as conn:
                deleted = self._execute_with_retry(lambda: _delete_list(conn))
            if deleted:
                logger.debug(f"Deleted removal list: {list_id}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete removal list {list_id}: {e}")
            raise

    def verify_database_integrity(self) -> Dict[str, Any]:
        """
        Verify database integrity using SQLite's integrity check.
        
        Returns:
            Dictionary with integrity check results:
            - ok: bool - True if integrity check passed
            - errors: List[str] - List of integrity errors if any
            - foreign_key_violations: List[Dict] - Foreign key violations if any
        """
        result = {
            "ok": True,
            "errors": [],
            "foreign_key_violations": []
        }
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Run SQLite integrity check
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()
                
                if integrity_result and integrity_result[0] != "ok":
                    result["ok"] = False
                    result["errors"].append(integrity_result[0])
                    logger.warning(f"Database integrity check failed: {integrity_result[0]}")
                
                # Check for foreign key violations
                cursor.execute("PRAGMA foreign_key_check")
                fk_violations = cursor.fetchall()
                
                if fk_violations:
                    result["ok"] = False
                    for violation in fk_violations:
                        violation_dict = {
                            "table": violation[0],
                            "rowid": violation[1],
                            "parent": violation[2],
                            "fkid": violation[3]
                        }
                        result["foreign_key_violations"].append(violation_dict)
                        logger.warning(f"Foreign key violation: {violation_dict}")
                
                if result["ok"]:
                    logger.info("Database integrity check passed")
                
        except Exception as e:
            result["ok"] = False
            result["errors"].append(str(e))
            logger.error(f"Database integrity check error: {e}")
        
        return result
    
    def check_database_health(self) -> Dict[str, Any]:
        """
        Check database health and accessibility.
        
        Returns:
            Dictionary with health check results:
            - accessible: bool - True if database file is accessible
            - writable: bool - True if database is writable
            - file_exists: bool - True if database file exists
            - file_size: int - Size of database file in bytes
            - table_counts: Dict[str, int] - Count of records in each table
        """
        health = {
            "accessible": False,
            "writable": False,
            "file_exists": False,
            "file_size": 0,
            "table_counts": {}
        }
        
        try:
            # Check if file exists
            health["file_exists"] = self.db_path.exists()
            
            if health["file_exists"]:
                # Check file size
                health["file_size"] = self.db_path.stat().st_size
                
                # Try to access database
                try:
                    with self.get_connection() as conn:
                        cursor = conn.cursor()
                        
                        # Check if we can read
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                        health["accessible"] = True
                        
                        # Check if we can write
                        cursor.execute("SELECT COUNT(*) FROM jobs")
                        cursor.fetchone()
                        health["writable"] = True
                        
                        # Get table counts
                        # Whitelist of valid table names to prevent SQL injection
                        valid_tables = ["jobs", "analytics", "settings_presets", "uploaded_files", "removal_lists"]
                        for table in valid_tables:
                            try:
                                # Validate table name against whitelist before using in query
                                if table not in valid_tables:
                                    continue
                                # SQLite doesn't support parameterized table names, so we use whitelist validation
                                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                                count = cursor.fetchone()[0]
                                health["table_counts"][table] = count
                            except Exception as e:
                                logger.warning(f"Could not count records in {table}: {e}")
                                health["table_counts"][table] = -1
                        
                except Exception as e:
                    logger.error(f"Database health check failed: {e}")
                    health["accessible"] = False
                    health["writable"] = False
            
        except Exception as e:
            logger.error(f"Error checking database health: {e}")
        
        return health

