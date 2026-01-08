"""
Database models and operations for the tiered email filtering web app.
Uses SQLite for minimal storage footprint.
"""
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class Database:
    """SQLite database wrapper for jobs, analytics, and settings presets"""
    
    def __init__(self, db_path: str = "backend/data/app.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
        self.init_default_preset()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
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
                FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
        """)
        
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
                last_used_at TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_presets_default ON settings_presets(is_default)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_files_uploaded_at ON uploaded_files(uploaded_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_files_last_used ON uploaded_files(last_used_at)")
        
        conn.commit()
        conn.close()
        logger.info("Database initialized")
    
    def init_default_preset(self):
        """Initialize default settings preset matching CLI defaults"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
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
                conn.commit()
            else:
                logger.info("Default preset already matches CLI defaults")
        else:
            # Create default preset
            preset_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO settings_presets (id, name, is_default, settings)
                VALUES (?, ?, ?, ?)
            """, (preset_id, "Default (CLI Match)", 1, json.dumps(default_settings)))
            conn.commit()
            logger.info("Default preset initialized with CLI matching settings")
        
        conn.close()
    
    def create_job(self, settings: Dict, input_files: List[str]) -> str:
        """Create a new processing job"""
        job_id = str(uuid.uuid4())
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO jobs (id, status, settings, input_files)
            VALUES (?, ?, ?, ?)
        """, (job_id, "pending", json.dumps(settings), json.dumps(input_files)))
        
        conn.commit()
        conn.close()
        return job_id
    
    def update_job_status(self, job_id: str, status: str, output_filename: Optional[str] = None):
        """Update job status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if output_filename:
            cursor.execute("""
                UPDATE jobs SET status = ?, output_filename = ? WHERE id = ?
            """, (status, output_filename, job_id))
        else:
            cursor.execute("""
                UPDATE jobs SET status = ? WHERE id = ?
            """, (status, job_id))
        
        conn.commit()
        conn.close()
    
    def save_analytics(self, job_id: str, analytics: Dict):
        """Save analytics data for a job"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO analytics (
                job_id, processing_summary, input_file_details, delta_analysis,
                delta_summary, filter_breakdown, excluded_firms_summary,
                excluded_firms_list, included_firms_list, excluded_firm_contacts_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            analytics.get("excluded_firm_contacts_count", 0)
        ))
        
        conn.commit()
        conn.close()
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job with analytics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        job_row = cursor.fetchone()
        
        if not job_row:
            conn.close()
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
            job["analytics"] = analytics
        else:
            job["analytics"] = None
        
        conn.close()
        return job
    
    def list_jobs(self, limit: int = 50) -> List[Dict]:
        """List all jobs, most recent first"""
        conn = self.get_connection()
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
        
        conn.close()
        return jobs
    
    def delete_job(self, job_id: str) -> bool:
        """Delete job and its analytics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return deleted
    
    def create_preset(self, name: str, settings: Dict) -> str:
        """Create a new settings preset"""
        preset_id = str(uuid.uuid4())
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO settings_presets (id, name, settings)
            VALUES (?, ?, ?)
        """, (preset_id, name, json.dumps(settings)))
        
        conn.commit()
        conn.close()
        return preset_id
    
    def get_presets(self) -> List[Dict]:
        """Get all presets including default"""
        conn = self.get_connection()
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
        
        conn.close()
        return presets
    
    def update_preset(self, preset_id: str, name: str = None, settings: Dict = None) -> bool:
        """Update a preset's name and/or settings (cannot update default)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if it's the default preset
        cursor.execute("SELECT is_default FROM settings_presets WHERE id = ?", (preset_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        
        if row["is_default"]:
            conn.close()
            return False  # Cannot update default preset
        
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
            conn.close()
            return False
        
        params.append(preset_id)
        query = f"UPDATE settings_presets SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    
    def delete_preset(self, preset_id: str) -> bool:
        """Delete a preset (cannot delete default)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if it's the default preset
        cursor.execute("SELECT is_default FROM settings_presets WHERE id = ?", (preset_id,))
        row = cursor.fetchone()
        if row and row["is_default"]:
            conn.close()
            return False
        
        cursor.execute("DELETE FROM settings_presets WHERE id = ?", (preset_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return deleted
    
    def save_uploaded_file(self, file_id: str, original_name: str, stored_path: str, file_size: int) -> None:
        """Save uploaded file metadata"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO uploaded_files (id, original_name, stored_path, file_size)
            VALUES (?, ?, ?, ?)
        """, (file_id, original_name, stored_path, file_size))
        
        conn.commit()
        conn.close()
    
    def get_uploaded_file(self, file_id: str) -> Optional[Dict]:
        """Get uploaded file metadata"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM uploaded_files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        
        conn.close()
        if row:
            return dict(row)
        return None
    
    def list_uploaded_files(self, limit: int = 100) -> List[Dict]:
        """List all uploaded files, most recent first"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, original_name, stored_path, file_size, uploaded_at, last_used_at
            FROM uploaded_files
            ORDER BY uploaded_at DESC
            LIMIT ?
        """, (limit,))
        
        files = []
        for row in cursor.fetchall():
            file_dict = dict(row)
            # Include file even if it's been deleted (for history/reference)
            # The file may have been processed and cleaned up, but metadata is still useful
            files.append(file_dict)
        
        conn.close()
        return files
    
    def update_file_last_used(self, file_id: str) -> None:
        """Update last_used_at timestamp for a file"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE uploaded_files 
            SET last_used_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (file_id,))
        
        conn.commit()
        conn.close()
    
    def delete_uploaded_file(self, file_id: str) -> bool:
        """Delete uploaded file record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM uploaded_files WHERE id = ?", (file_id,))
        deleted = cursor.rowcount > 0
        
        conn.commit()
        conn.close()
        return deleted

