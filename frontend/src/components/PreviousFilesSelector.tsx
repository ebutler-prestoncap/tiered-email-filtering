import { useState, useEffect, useCallback } from 'react';
import { listUploadedFiles, validateUploadedFile, type FileValidationResult, type UploadedFile } from '../services/api';
import { formatDateTimePacific } from '../utils/dateUtils';
import './PreviousFilesSelector.css';

interface PreviousFilesSelectorProps {
  isOpen: boolean;
  onClose: () => void;
  selectedFileIds: string[];
  onSelectionChange: (fileIds: string[]) => void;
  onFileValidated?: (fileId: string, validation: FileValidationResult, fileInfo: UploadedFile) => void;
}

export default function PreviousFilesSelector({
  isOpen,
  onClose,
  selectedFileIds,
  onSelectionChange,
  onFileValidated
}: PreviousFilesSelectorProps) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [fileValidations, setFileValidations] = useState<Map<string, FileValidationResult>>(new Map());
  const [loadingValidations, setLoadingValidations] = useState<Set<string>>(new Set());
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

        // Use cached validation or load validation for files without it
        const newValidations = new Map<string, FileValidationResult>();
        const filesToValidate: UploadedFile[] = [];

        availableFiles.forEach(file => {
          if (file.validation) {
            // Use cached validation
            newValidations.set(file.id, file.validation);
            // Notify parent of validation result
            if (onFileValidated) {
              onFileValidated(file.id, file.validation, file);
            }
          } else if (!loadingValidations.has(file.id) && !fileValidations.has(file.id)) {
            // Queue for validation
            filesToValidate.push(file);
          }
        });

        // Update state with cached validations
        if (newValidations.size > 0) {
          setFileValidations(prev => {
            const merged = new Map(prev);
            newValidations.forEach((val, key) => merged.set(key, val));
            return merged;
          });
        }

        // Load validation for files without cached validation
        filesToValidate.forEach(file => {
          loadValidationForFile(file.id, file);
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
            Contacts ({validation.sheets.find(s => s.name === validation.contacts_sheet)?.row_count?.toLocaleString() || '?'})
          </span>
        )}
        {validation.accounts_sheet && (
          <span className="validation-badge accounts">
            Accounts ({validation.sheets.find(s => s.name === validation.accounts_sheet)?.row_count?.toLocaleString() || '?'})
          </span>
        )}
        {validation.can_merge_aum && (
          <span className="validation-badge aum">
            AUM
          </span>
        )}
        {!validation.can_process && (
          <span className="validation-badge error">
            Invalid
          </span>
        )}
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="previous-files-modal-overlay" onClick={onClose}>
      <div className="previous-files-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Select Previous Uploads</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            x
          </button>
        </div>

        <div className="modal-content">
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
                    className={`selector-item ${isInvalid ? 'file-invalid' : ''} ${selectedFileIds.includes(file.id) ? 'selected' : ''}`}
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
                        <span className="selector-item-separator">-</span>
                        <span>{formatDateTimePacific(file.uploadedAt)}</span>
                      </div>
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <span className="selected-count">
            {selectedFileIds.length} file{selectedFileIds.length !== 1 ? 's' : ''} selected
          </span>
          <button className="modal-done-button" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
