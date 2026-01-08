import { useState, useEffect } from 'react';
import { listUploadedFiles } from '../services/api';
import { formatDateTimePacific } from '../utils/dateUtils';
import './PreviousFilesSelector.css';

interface UploadedFile {
  id: string;
  originalName: string;
  storedPath: string;
  fileSize: number;
  uploadedAt: string;
  lastUsedAt: string | null;
  fileExists?: boolean;
}

interface PreviousFilesSelectorProps {
  selectedFileIds: string[];
  onSelectionChange: (fileIds: string[]) => void;
}

export default function PreviousFilesSelector({ selectedFileIds, onSelectionChange }: PreviousFilesSelectorProps) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    setIsLoading(true);
    try {
      const uploadedFiles = await listUploadedFiles();
      setFiles(uploadedFiles);
    } catch (error) {
      console.error('Failed to load uploaded files:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleFile = (fileId: string) => {
    if (selectedFileIds.includes(fileId)) {
      onSelectionChange(selectedFileIds.filter(id => id !== fileId));
    } else {
      onSelectionChange([...selectedFileIds, fileId]);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };


  return (
    <div className="previous-files-selector">
      <button
        className="selector-toggle"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <span className="selector-icon">📂</span>
        <span className="selector-label">
          Previously Uploaded Files
          {selectedFileIds.length > 0 && (
            <span className="selected-count"> ({selectedFileIds.length} selected)</span>
          )}
        </span>
        <span className={`selector-arrow ${isOpen ? 'open' : ''}`}>▼</span>
      </button>

      {isOpen && (
        <div className="selector-dropdown">
          {isLoading ? (
            <div className="selector-loading">Loading files...</div>
          ) : files.length === 0 ? (
            <div className="selector-empty">No previously uploaded files</div>
          ) : (
            <div className="selector-list">
              {files.map((file) => (
                <label 
                  key={file.id} 
                  className={`selector-item ${file.fileExists === false ? 'file-processed' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={selectedFileIds.includes(file.id)}
                    onChange={() => handleToggleFile(file.id)}
                    disabled={file.fileExists === false}
                    className="selector-checkbox"
                  />
                  <div className="selector-item-content">
                    <div className="selector-item-name">
                      {file.originalName}
                      {file.fileExists === false && (
                        <span className="file-processed-badge" title="File has been processed and is no longer available for reprocessing">
                          (Processed)
                        </span>
                      )}
                    </div>
                    <div className="selector-item-meta">
                      <span>{formatFileSize(file.fileSize)}</span>
                      <span className="selector-item-separator">•</span>
                      <span>{formatDateTimePacific(file.uploadedAt)}</span>
                      {file.lastUsedAt && (
                        <>
                          <span className="selector-item-separator">•</span>
                          <span>Last used: {formatDateTimePacific(file.lastUsedAt)}</span>
                        </>
                      )}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

