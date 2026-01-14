import { useCallback, useState } from 'react';
import FileValidationModal from './FileValidationModal';
import type { FileValidationResult } from '../services/api';
import './FileUpload.css';

// Extended file info that includes validation result
export interface ValidatedFile {
  file: File;
  validation: FileValidationResult;
}

interface FileUploadProps {
  onFilesSelected: (files: File[], validations?: FileValidationResult[]) => void;
  uploadedFiles: File[];
  onRemoveFile: (index: number) => void;
  // Optional: get validation info for a file
  getFileValidation?: (file: File) => FileValidationResult | undefined;
}

export default function FileUpload({
  onFilesSelected,
  uploadedFiles,
  onRemoveFile,
  getFileValidation,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files).filter(
      file => file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
    );

    if (files.length > 0) {
      // Open validation modal for first file
      setPendingFile(files[0]);
    }
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const validFiles = files.filter(
      file => file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
    );

    if (validFiles.length > 0) {
      // Open validation modal for the file
      setPendingFile(validFiles[0]);
      // Reset input to allow selecting the same file again
      e.target.value = '';
    } else if (files.length > 0) {
      alert('Please select Excel files (.xlsx or .xls)');
      e.target.value = '';
    }
  }, []);

  const handleValidationConfirm = useCallback((file: File, validation: FileValidationResult) => {
    // Check if file already exists
    const isDuplicate = uploadedFiles.some(
      existingFile => existingFile.name === file.name && existingFile.size === file.size
    );

    if (!isDuplicate) {
      onFilesSelected([file], [validation]);
    }
    setPendingFile(null);
  }, [onFilesSelected, uploadedFiles]);

  const handleValidationCancel = useCallback(() => {
    setPendingFile(null);
  }, []);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="file-upload">
      <div
        className={`upload-area ${isDragging ? 'dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-input"
          multiple
          accept=".xlsx,.xls"
          onChange={handleFileInput}
          className="file-input"
        />
        <label htmlFor="file-input" className="upload-label">
          <div className="upload-icon">📁</div>
          <div className="upload-text">
            <strong>Drop Excel files here</strong> or click to browse
          </div>
          <div className="upload-hint">Supports .xlsx and .xls files</div>
        </label>
      </div>

      {uploadedFiles.length > 0 ? (
        <div className="uploaded-files">
          <h3>Uploaded Files ({uploadedFiles.length})</h3>
          <div className="file-list">
            {uploadedFiles.map((file, index) => {
              const validation = getFileValidation?.(file);
              return (
                <div key={`${file.name}-${index}`} className="file-item">
                  <div className="file-info-content">
                    <span className="file-name">{file.name}</span>
                    <span className="file-size">{formatFileSize(file.size)}</span>
                    {validation && (
                      <div className="file-validation-badges">
                        {validation.contacts_sheet && (
                          <span className="validation-badge contacts">
                            ✓ Contacts
                          </span>
                        )}
                        {validation.accounts_sheet && (
                          <span className="validation-badge accounts">
                            ✓ Accounts
                          </span>
                        )}
                        {validation.can_merge_aum && (
                          <span className="validation-badge aum">
                            ✓ AUM
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  <button
                    className="file-remove"
                    onClick={() => onRemoveFile(index)}
                    aria-label="Remove file"
                  >
                    ×
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="uploaded-files-placeholder">
          <p className="placeholder-text">No files uploaded yet</p>
        </div>
      )}

      {/* Validation modal */}
      {pendingFile && (
        <FileValidationModal
          file={pendingFile}
          onConfirm={handleValidationConfirm}
          onCancel={handleValidationCancel}
        />
      )}
    </div>
  );
}
