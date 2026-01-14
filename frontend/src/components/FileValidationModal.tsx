import { useState, useEffect, useCallback } from 'react';
import { validateFile, type FileValidationResult, type SheetValidation } from '../services/api';
import './FileValidationModal.css';

interface FileValidationModalProps {
  file: File;
  onConfirm: (file: File, validation: FileValidationResult) => void;
  onCancel: () => void;
}

export default function FileValidationModal({ file, onConfirm, onCancel }: FileValidationModalProps) {
  const [isValidating, setIsValidating] = useState(true);
  const [validation, setValidation] = useState<FileValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runValidation = useCallback(async () => {
    setIsValidating(true);
    setError(null);

    try {
      const result = await validateFile(file);
      setValidation(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to validate file');
    } finally {
      setIsValidating(false);
    }
  }, [file]);

  useEffect(() => {
    runValidation();
  }, [runValidation]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getSheetIcon = (sheet: SheetValidation) => {
    if (sheet.type === 'accounts' && sheet.valid) return { icon: 'check', color: 'green' };
    if (sheet.type === 'contacts' && sheet.valid) return { icon: 'check', color: 'green' };
    if (sheet.type === 'metadata') return { icon: 'info', color: 'gray' };
    if (sheet.type === 'error' || !sheet.valid) return { icon: 'error', color: 'red' };
    if (sheet.type === 'unknown') return { icon: 'question', color: 'orange' };
    return { icon: 'check', color: 'gray' };
  };

  const getSheetTypeLabel = (type: string) => {
    switch (type) {
      case 'accounts': return 'Accounts Sheet';
      case 'contacts': return 'Contacts Sheet';
      case 'metadata': return 'Metadata';
      case 'unknown': return 'Unknown';
      case 'empty': return 'Empty';
      case 'error': return 'Error';
      default: return type;
    }
  };

  const handleConfirm = () => {
    if (validation) {
      onConfirm(file, validation);
    }
  };

  // Check if confirmation should be disabled
  const isConfirmDisabled = !validation || !validation.can_process;

  // Get reason for disabled state
  const getDisabledReason = () => {
    if (!validation) return '';
    if (!validation.contacts_sheet && validation.accounts_sheet) {
      return 'Cannot process: File contains only accounts data. A contacts sheet is required.';
    }
    if (!validation.can_process) {
      return 'Cannot process: No valid contacts sheet found.';
    }
    return '';
  };

  return (
    <div className="validation-modal-overlay" onClick={onCancel}>
      <div className="validation-modal" onClick={(e) => e.stopPropagation()}>
        <div className="validation-modal-header">
          <h2>Validate File</h2>
          <button className="close-button" onClick={onCancel}>&times;</button>
        </div>

        <div className="validation-modal-content">
          {/* File info */}
          <div className="file-info-section">
            <div className="file-icon">
              <span className="file-emoji">📊</span>
            </div>
            <div className="file-details">
              <h3>{file.name}</h3>
              <span className="file-size">{formatFileSize(file.size)}</span>
            </div>
          </div>

          {/* Validation state */}
          {isValidating && (
            <div className="validation-loading">
              <div className="spinner"></div>
              <p>Analyzing file structure...</p>
            </div>
          )}

          {error && (
            <div className="validation-error">
              <span className="error-icon">!</span>
              <p>{error}</p>
              <button className="retry-button" onClick={runValidation}>Retry</button>
            </div>
          )}

          {validation && !isValidating && (
            <>
              {/* Summary status */}
              <div className={`validation-status ${validation.can_process ? 'status-success' : 'status-error'}`}>
                <span className="status-icon">
                  {validation.can_process ? '✓' : '✗'}
                </span>
                <div className="status-text">
                  <strong>{validation.can_process ? 'File is valid' : 'File cannot be processed'}</strong>
                  <p>{validation.summary}</p>
                </div>
              </div>

              {/* Sheets section */}
              <div className="sheets-section">
                <h4>Detected Sheets</h4>
                <div className="sheets-list">
                  {validation.sheets.map((sheet, index) => {
                    const { icon, color } = getSheetIcon(sheet);
                    return (
                      <div key={index} className={`sheet-item sheet-${color}`}>
                        <div className="sheet-header">
                          <span className={`sheet-icon icon-${icon}`}>
                            {icon === 'check' && '✓'}
                            {icon === 'error' && '✗'}
                            {icon === 'info' && 'ℹ'}
                            {icon === 'question' && '?'}
                          </span>
                          <div className="sheet-info">
                            <span className="sheet-name">{sheet.name}</span>
                            <span className="sheet-type">{getSheetTypeLabel(sheet.type)}</span>
                          </div>
                          <div className="sheet-stats">
                            <span className="row-count">{sheet.row_count.toLocaleString()} rows</span>
                            <span className="confidence">{Math.round(sheet.confidence * 100)}% match</span>
                          </div>
                        </div>

                        {/* Schema details for accounts/contacts */}
                        {(sheet.type === 'accounts' || sheet.type === 'contacts') && sheet.schema_details && (
                          <div className="schema-details">
                            {sheet.columns_found.length > 0 && (
                              <div className="columns-found">
                                <span className="label">Columns found:</span>
                                <div className="column-tags">
                                  {sheet.columns_found.map((col, i) => (
                                    <span key={i} className="column-tag found">
                                      {col.expected}
                                      {col.expected !== col.found && ` (${col.found})`}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {sheet.columns_missing.length > 0 && (
                              <div className="columns-missing">
                                <span className="label">Missing:</span>
                                <div className="column-tags">
                                  {sheet.columns_missing.map((col, i) => (
                                    <span key={i} className="column-tag missing">{col}</span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* AUM indicator for accounts sheet */}
                            {sheet.type === 'accounts' && sheet.schema_details.aum_column && (
                              <div className="aum-indicator">
                                <span className="aum-badge">AUM Available</span>
                                <span className="aum-column">Column: {sheet.schema_details.aum_column}</span>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Errors and warnings */}
                        {sheet.errors.length > 0 && (
                          <div className="sheet-errors">
                            {sheet.errors.map((err, i) => (
                              <div key={i} className="error-item">
                                <span className="error-bullet">!</span> {err}
                              </div>
                            ))}
                          </div>
                        )}

                        {sheet.warnings.length > 0 && (
                          <div className="sheet-warnings">
                            {sheet.warnings.map((warn, i) => (
                              <div key={i} className="warning-item">
                                <span className="warning-bullet">⚠</span> {warn}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* AUM merge status */}
              {validation.accounts_sheet && validation.contacts_sheet && (
                <div className={`aum-merge-status ${validation.can_merge_aum ? 'can-merge' : 'cannot-merge'}`}>
                  <span className="merge-icon">{validation.can_merge_aum ? '🔗' : '⛓️‍💥'}</span>
                  <div className="merge-info">
                    <strong>
                      {validation.can_merge_aum
                        ? 'AUM data can be merged with contacts'
                        : 'Cannot merge AUM data'}
                    </strong>
                    <p>
                      {validation.can_merge_aum
                        ? 'Both sheets have FIRM_ID columns that can be used to link account AUM data with contacts.'
                        : 'Missing FIRM_ID column in one or both sheets. AUM-based filtering will not be available.'}
                    </p>
                  </div>
                </div>
              )}

              {/* File-level warnings */}
              {validation.warnings.length > 0 && (
                <div className="file-warnings">
                  <h4>Warnings</h4>
                  {validation.warnings.map((warn, i) => (
                    <div key={i} className="warning-item">
                      <span className="warning-bullet">⚠</span> {warn}
                    </div>
                  ))}
                </div>
              )}

              {/* File-level errors */}
              {validation.errors.length > 0 && (
                <div className="file-errors">
                  <h4>Errors</h4>
                  {validation.errors.map((err, i) => (
                    <div key={i} className="error-item">
                      <span className="error-bullet">!</span> {err}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        <div className="validation-modal-footer">
          {isConfirmDisabled && validation && (
            <p className="disabled-reason">{getDisabledReason()}</p>
          )}
          <div className="button-group">
            <button className="cancel-button" onClick={onCancel}>
              Cancel
            </button>
            <button
              className="confirm-button"
              onClick={handleConfirm}
              disabled={isConfirmDisabled || isValidating}
            >
              {isValidating ? 'Validating...' : 'Confirm & Add File'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
