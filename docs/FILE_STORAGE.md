# File Storage Architecture

This document explains how files are stored and managed in the Tiered Email Filtering web application.

## Overview

The application uses a **hybrid storage approach**:
- **File content** is stored on the filesystem (disk)
- **File metadata** is stored in the SQLite database

This design provides better performance, scalability, and easier file management compared to storing large files directly in the database.

## Storage Locations

### Local Development
- **Uploads**: `backend/uploads/`
- **Results**: `backend/results/`
- **Database**: `backend/data/app.db`

### Docker Deployment
- **Uploads**: `/app/uploads` (mounted from `./backend/uploads` on host)
- **Results**: `/app/results` (mounted from `./backend/results` on host)
- **Database**: `/app/data/app.db` (mounted from `./backend/data` on host)

The configuration automatically detects the environment and uses the appropriate paths (see `backend/config.py`).

## File Upload Flow

### 1. File Upload
When a user uploads an Excel file:

```python
# File is saved to disk
file_path = upload_folder / unique_name  # e.g., "a1b2c3d4-e5f6-...xlsx"
file.save(str(file_path))  # ← File content saved to filesystem
```

- Files are saved with UUID-based filenames to avoid conflicts
- Original filename is preserved in metadata
- Files are stored in the `uploads/` directory

### 2. Metadata Storage
After saving the file to disk, metadata is stored in the database:

```python
# Only metadata is saved to database
db.save_uploaded_file(
    file_id=uuid.uuid4(),           # Unique identifier
    original_name="contacts.xlsx",  # User's original filename
    stored_path="/app/uploads/...", # Path to file on disk
    file_size=1234567               # File size in bytes
)
```

## Database Schema

The `uploaded_files` table stores the following metadata:

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT (UUID) | Unique identifier for the file |
| `original_name` | TEXT | Original filename provided by user |
| `stored_path` | TEXT | Full path to file on filesystem |
| `file_size` | INTEGER | File size in bytes |
| `uploaded_at` | TIMESTAMP | When the file was uploaded |
| `last_used_at` | TIMESTAMP | When the file was last used in processing |

**Note**: The actual file content is **NOT** stored in the database.

## File Persistence

### Across Container Restarts
Files persist across Docker container restarts because:
1. Files are stored in mounted volumes (`./backend/uploads:/app/uploads`)
2. The database stores the file paths
3. On restart, the application can locate files using the stored paths

### File Lifecycle
- **Upload**: File saved to disk + metadata saved to database
- **Processing**: File is read from disk using the stored path
- **Retention**: Files are kept indefinitely (no automatic deletion)
- **Reuse**: Files can be selected from "Previously Uploaded Input Lists" for reuse

## File Reuse

Users can reuse previously uploaded files by:
1. Selecting files from the "Previously Uploaded Input Lists" selector
2. Combining multiple previous files together
3. Mixing previous files with new uploads

The system:
- Lists all files from the database where `fileExists === true`
- Allows multiple file selection via checkboxes
- Uses the stored file paths to access files on disk

## File Access

When processing files:

```python
# Get file metadata from database
file_meta = db.get_uploaded_file(file_id)

# Access file using stored path
stored_path = file_meta.get("stored_path")
if Path(stored_path).exists():
    # File exists, can be used for processing
    uploaded_files.append(stored_path)
```

## Benefits of This Architecture

1. **Performance**: No large BLOBs in database, faster queries
2. **Scalability**: Database stays small, files stored efficiently
3. **Flexibility**: Direct filesystem access for file operations
4. **Persistence**: Files survive database operations and container restarts
5. **Management**: Easy to backup, move, or archive files separately

## Backup Considerations

To fully backup the application:

1. **Database**: Backup `backend/data/app.db` (contains all metadata)
2. **Files**: Backup `backend/uploads/` (contains all uploaded files)
3. **Results**: Backup `backend/results/` (contains processed output files)

All three components are needed for a complete backup.

## Troubleshooting

### Files Not Appearing After Restart
- Check that Docker volumes are properly mounted
- Verify `config.py` is using correct paths for your environment
- Ensure files exist on disk (check `fileExists` in database query)

### Files Missing
- Check if files were deleted from filesystem but metadata remains in database
- The frontend filters out files where `fileExists === false`
- Manually clean up orphaned database records if needed

### Path Issues
- In Docker: Files must be in `/app/uploads` (mounted volume)
- Locally: Files must be in `backend/uploads/`
- The config automatically detects the environment

