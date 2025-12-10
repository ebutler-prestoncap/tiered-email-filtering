import { useCallback, useState } from 'react';
import './FileUpload.css';

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
  uploadedFiles: File[];
  onRemoveFile: (index: number) => void;
}

export default function FileUpload({ onFilesSelected, uploadedFiles, onRemoveFile }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);

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
      onFilesSelected(files);
    }
  }, [onFilesSelected]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const validFiles = files.filter(
      file => file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
    );
    
    if (validFiles.length > 0) {
      console.log('Files selected:', validFiles.map(f => f.name));
      onFilesSelected(validFiles);
      // Reset input to allow selecting the same file again
      e.target.value = '';
    } else if (files.length > 0) {
      alert('Please select Excel files (.xlsx or .xls)');
      e.target.value = '';
    }
  }, [onFilesSelected]);

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
            {uploadedFiles.map((file, index) => (
              <div key={`${file.name}-${index}`} className="file-item">
                <span className="file-name">{file.name}</span>
                <span className="file-size">{formatFileSize(file.size)}</span>
                <button
                  className="file-remove"
                  onClick={() => onRemoveFile(index)}
                  aria-label="Remove file"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="uploaded-files-placeholder">
          <p className="placeholder-text">No files uploaded yet</p>
        </div>
      )}
    </div>
  );
}

