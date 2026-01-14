import { useState, useEffect, useCallback } from 'react';
import { listUploadedFiles, validateUploadedFile, type FileValidationResult } from '../services/api';
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
  onFileValidated?: (fileId: string, validation: FileValidationResult, fileInfo: UploadedFile) => void;
}

export default function PreviousFilesSelector({
  selectedFileIds,
  onSelectionChange,
  onFileValidated
}: PreviousFilesSelectorProps) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [fileValidations, setFileValidations] = useState<Map<string, FileValidationResult>>(new Map());
  const [loadingValidations, setLoadingValidations] = useState<Set<string>>(new Set());
  const [isOpen, setIsOpen] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  const loadValidationForFile = useCallback(async (fileId: string, fileInfo: UploadedFile) => {
    setLoadingValidations(prev => new Set(prev).add(fileId));

    try {
      const validation = await validateUploadedFile(fileId);
      setFileValidations(prev => {
        const newMap = new Map(prev);
        newMap.set(fileId, validation);
        return newMap;
      });

      // Notify parent of validation result
      if (onFileValidated) {
        onFileValidated(fileId, validation, fileInfo);
      }
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error(`Failed to validate file ${fileId}:`, error);
      }
    } finally {
      setLoadingValidations(prev => {
        const newSet = new Set(prev);
        newSet.delete(fileId);
        return newSet;
      });
    }
  }, [onFileValidated]);

  useEffect(() => {
    const loadFiles = async () => {
      setIsLoading(true);
      try {
        const uploadedFiles = await listUploadedFiles();
        // Only show files that exist and can be selected
        const availableFiles = uploadedFiles.filter(file => file.fileExists !== false);
        setFiles(availableFiles);

        // Start loading validations for all files
        availableFiles.forEach(file => {
          // Don't reload if already loading or loaded
          if (!loadingValidations.has(file.id) && !fileValidations.has(file.id)) {
            loadValidationForFile(file.id, file);
          }
        });
      } catch (error) {
        // Error logged to console for debugging in development
        if (import.meta.env.DEV) {
          console.error('Failed to load uploaded files:', error);
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  const renderValidationBadges = (fileId: string) => {
    const validation = fileValidations.get(fileId);
    const isLoadingVal = loadingValidations.has(fileId);

    if (isLoadingVal) {
      return <span className="validation-loading">Validating...</span>;
    }

    if (!validation) {
      return null;
    }

    return (
      <div className="file-validation-badges">
        {validation.contacts_sheet && (
          <span className="validation-badge contacts">
            ✓ Contacts ({validation.sheets.find(s => s.name === validation.contacts_sheet)?.row_count?.toLocaleString() || '?'})
          </span>
        )}
        {validation.accounts_sheet && (
          <span className="validation-badge accounts">
            ✓ Accounts ({validation.sheets.find(s => s.name === validation.accounts_sheet)?.row_count?.toLocaleString() || '?'})
          </span>
        )}
        {validation.can_merge_aum && (
          <span className="validation-badge aum">
            ✓ AUM
          </span>
        )}
        {!validation.can_process && (
          <span className="validation-badge error">
            ✗ Invalid
          </span>
        )}
      </div>
    );
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
          Previously Uploaded Input Lists
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
            <div className="selector-empty">
              <p>No previously uploaded files</p>
              <p className="selector-empty-hint">Upload files to see them here for future use</p>
            </div>
          ) : (
            <div className="selector-list">
              {files.map((file) => {
                const validation = fileValidations.get(file.id);
                const isInvalid = validation && !validation.can_process;

                return (
                  <label
                    key={file.id}
                    className={`selector-item ${isInvalid ? 'file-invalid' : ''}`}
                    htmlFor={`file-checkbox-${file.id}`}
                  >
                    <input
                      id={`file-checkbox-${file.id}`}
                      type="checkbox"
                      checked={selectedFileIds.includes(file.id)}
                      onChange={() => handleToggleFile(file.id)}
                      className="selector-checkbox"
                      disabled={isInvalid}
                    />
                    <div className="selector-item-content">
                      <div className="selector-item-name">
                        {file.originalName}
                      </div>
                      {renderValidationBadges(file.id)}
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
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
