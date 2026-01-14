import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import FileUpload from '../components/FileUpload';
import ConfigurationPanel from '../components/ConfigurationPanel';
import ProcessingSidePanel from '../components/ProcessingSidePanel';
import PreviousFilesSelector from '../components/PreviousFilesSelector';
import { uploadFiles, processContacts, listUploadedFiles, cancelJob, type FileValidationResult } from '../services/api';
import { generatePrefixFromFilenames } from '../utils/filenameUtils';
import type { ProcessingSettings } from '../types';
import './ProcessPage.css';

// Store file validations in a map keyed by file name + size
type FileValidationMap = Map<string, FileValidationResult>;

// Info about a previous file
interface PreviousFileInfo {
  id: string;
  originalName: string;
  fileSize: number;
  validation?: FileValidationResult;
}

const getFileKey = (file: File | { name: string; size: number }): string => {
  return `${file.name}-${file.size}`;
};

export default function ProcessPage() {
  const navigate = useNavigate();
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [fileValidations, setFileValidations] = useState<FileValidationMap>(new Map());
  const [selectedPreviousFileIds, setSelectedPreviousFileIds] = useState<string[]>([]);
  const [previousFileInfo, setPreviousFileInfo] = useState<Map<string, PreviousFileInfo>>(new Map());
  const [showProcessingPanel, setShowProcessingPanel] = useState(false);
  // Initialize with default values - ConfigurationPanel will update with preset
  const [settings, setSettings] = useState<ProcessingSettings>({
    includeAllFirms: false,
    findEmails: true,
    firmExclusion: false,
    contactInclusion: false,
    tier1Limit: 10,
    tier2Limit: 6,
    tier3Limit: 3,
    userPrefix: 'Combined-Contacts',
    tier1Filters: {
      includeKeywords: [],
      excludeKeywords: [],
      requireInvestmentTeam: false,
    },
    tier2Filters: {
      includeKeywords: [],
      excludeKeywords: [],
      requireInvestmentTeam: true,
    },
    tier3Filters: {
      includeKeywords: [],
      excludeKeywords: [],
      requireInvestmentTeam: false,
    },
    firmExclusionList: '',
    firmInclusionList: '',
    contactExclusionList: '',
    contactInclusionList: '',
    fieldFilters: [],
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /**
   * Update the output prefix based on selected files
   * @param uploadedFiles - Currently uploaded File objects
   * @param previousFileIds - IDs of selected previous files
   */
  const updatePrefixFromFiles = useCallback(async (
    uploadedFiles: File[],
    previousFileIds: string[]
  ) => {
    try {
      const allFilenames: (File | string)[] = [...uploadedFiles];
      
      // Fetch names of previously selected files
      if (previousFileIds.length > 0) {
        const previousFiles = await listUploadedFiles();
        const selectedPreviousFiles = previousFiles.filter(file =>
          previousFileIds.includes(file.id)
        );
        selectedPreviousFiles.forEach(file => {
          allFilenames.push(file.originalName);
        });
      }
      
      // Generate prefix from all filenames
      if (allFilenames.length > 0) {
        const generatedPrefix = generatePrefixFromFilenames(allFilenames);
        setSettings(prev => ({
          ...prev,
          userPrefix: generatedPrefix,
        }));
      }
    } catch (error) {
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Failed to update prefix from files:', error);
      }
      // If we have uploaded files, still try to generate prefix from them
      if (uploadedFiles.length > 0) {
        const generatedPrefix = generatePrefixFromFilenames(uploadedFiles);
        setSettings(prev => ({
          ...prev,
          userPrefix: generatedPrefix,
        }));
      }
    }
  }, []);

  const handleFilesSelected = (files: File[], validations?: FileValidationResult[]) => {
    setUploadedFiles(prev => {
      // Avoid duplicates by checking file name and size
      const newFiles = files.filter(newFile =>
        !prev.some(existingFile =>
          existingFile.name === newFile.name && existingFile.size === newFile.size
        )
      );
      return [...prev, ...newFiles];
    });

    // Store validations if provided
    if (validations && validations.length > 0) {
      setFileValidations(prev => {
        const newMap = new Map(prev);
        files.forEach((file, index) => {
          if (validations[index]) {
            newMap.set(getFileKey(file), validations[index]);
          }
        });
        return newMap;
      });
    }
  };

  const handleRemoveFile = (index: number) => {
    setUploadedFiles(prev => {
      const fileToRemove = prev[index];
      // Also remove validation
      if (fileToRemove) {
        setFileValidations(prevValidations => {
          const newMap = new Map(prevValidations);
          newMap.delete(getFileKey(fileToRemove));
          return newMap;
        });
      }
      return prev.filter((_, i) => i !== index);
    });
  };

  const getFileValidation = useCallback((file: File): FileValidationResult | undefined => {
    return fileValidations.get(getFileKey(file));
  }, [fileValidations]);

  // Handle validation results from previous files selector
  const handlePreviousFileValidated = useCallback((
    fileId: string,
    validation: FileValidationResult,
    fileInfo: { id: string; originalName: string; fileSize: number }
  ) => {
    setPreviousFileInfo(prev => {
      const newMap = new Map(prev);
      newMap.set(fileId, {
        id: fileInfo.id,
        originalName: fileInfo.originalName,
        fileSize: fileInfo.fileSize,
        validation
      });
      return newMap;
    });
  }, []);

  // Get selected previous files with their info
  const selectedPreviousFiles = selectedPreviousFileIds
    .map(id => previousFileInfo.get(id))
    .filter((info): info is PreviousFileInfo => info !== undefined);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const handleRemovePreviousFile = (fileId: string) => {
    setSelectedPreviousFileIds(prev => prev.filter(id => id !== fileId));
  };

  // Auto-update prefix when files or previous file selection changes
  useEffect(() => {
    if (uploadedFiles.length > 0 || selectedPreviousFileIds.length > 0) {
      updatePrefixFromFiles(uploadedFiles, selectedPreviousFileIds);
    }
  }, [uploadedFiles, selectedPreviousFileIds, updatePrefixFromFiles]);

  const handleProcess = async () => {
    if (uploadedFiles.length === 0 && selectedPreviousFileIds.length === 0) {
      alert('Please upload at least one Excel file or select previously uploaded files');
      return;
    }

    setIsProcessing(true);
    setProcessingStatus('pending');
    setShowProcessingPanel(true);

    try {
      let filePaths: string[] = [];
      let fileIds: string[] = [];
      
      // Upload new files if any
      if (uploadedFiles.length > 0) {
        const uploadResult = await uploadFiles(uploadedFiles);
        filePaths = uploadResult.paths || uploadResult.files;
        fileIds = uploadResult.fileIds || [];
      }
      
      // Combine new file IDs with previously selected file IDs
      const allFileIds = [...fileIds, ...selectedPreviousFileIds];
      
      // Start processing - pass filePaths for new files and fileIds for all files
      const processResult = await processContacts(
        filePaths, 
        settings, 
        allFileIds.length > 0 ? allFileIds : undefined
      );
      
      setCurrentJobId(processResult.jobId);
      setProcessingStatus('processing');

      // Poll for job completion
      pollIntervalRef.current = setInterval(async () => {
        try {
          const { getJob } = await import('../services/api');
          const job = await getJob(processResult.jobId);
          
          if (job.status === 'completed') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setProcessingStatus('completed');
            setIsProcessing(false);
            // Navigate to analytics after a short delay
            setTimeout(() => {
              navigate(`/analytics/${processResult.jobId}`);
            }, 2000);
          } else if (job.status === 'failed' || job.status === 'cancelled') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setProcessingStatus(job.status);
            setIsProcessing(false);
          }
        } catch (error) {
          // Error logged to console for debugging in development
          if (import.meta.env.DEV) {
            console.error('Error polling job status:', error);
          }
        }
      }, 2000);

      // Clear interval after 5 minutes (timeout)
      setTimeout(() => {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
        if (processingStatus === 'processing') {
          setProcessingStatus('failed');
          setIsProcessing(false);
        }
      }, 5 * 60 * 1000);

    } catch (error) {
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Processing error:', error);
      }
      setProcessingStatus('failed');
      setIsProcessing(false);
      alert('Failed to process files. Please try again.');
    }
  };

  const handleCancel = async () => {
    if (!currentJobId) return;
    
    try {
      await cancelJob(currentJobId);
      
      // Stop polling
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      
      // Update status
      setProcessingStatus('cancelled');
      setIsProcessing(false);
    } catch (error) {
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Error cancelling job:', error);
      }
      alert('Failed to cancel job. Please try again.');
    }
  };

  return (
    <div className={`process-page ${showProcessingPanel ? 'with-processing-bar' : ''}`}>
      {showProcessingPanel && (
        <ProcessingSidePanel
          status={processingStatus}
          jobId={currentJobId}
          onClose={() => setShowProcessingPanel(false)}
          onCancel={handleCancel}
        />
      )}
      
      <h1>Process Contacts</h1>
      <p className="page-description">
        Select previously uploaded input lists and/or upload new Excel files, then configure filtering options to process your contact lists.
      </p>

      <div className="process-layout">
        <div className="process-left">
          <PreviousFilesSelector
            selectedFileIds={selectedPreviousFileIds}
            onSelectionChange={setSelectedPreviousFileIds}
            onFileValidated={handlePreviousFileValidated}
          />
          <FileUpload
            onFilesSelected={handleFilesSelected}
            uploadedFiles={uploadedFiles}
            onRemoveFile={handleRemoveFile}
            getFileValidation={getFileValidation}
          />

          {/* Show selected previous files */}
          {selectedPreviousFiles.length > 0 && (
            <div className="selected-previous-files">
              <h3>Selected Previous Files ({selectedPreviousFiles.length})</h3>
              <div className="file-list">
                {selectedPreviousFiles.map((fileInfo) => (
                  <div key={fileInfo.id} className="file-item previous-file">
                    <div className="file-info-content">
                      <span className="file-name">{fileInfo.originalName}</span>
                      <span className="file-size">{formatFileSize(fileInfo.fileSize)}</span>
                      {fileInfo.validation && (
                        <div className="file-validation-badges">
                          {fileInfo.validation.contacts_sheet && (
                            <span className="validation-badge contacts">
                              ✓ Contacts
                            </span>
                          )}
                          {fileInfo.validation.accounts_sheet && (
                            <span className="validation-badge accounts">
                              ✓ Accounts
                            </span>
                          )}
                          {fileInfo.validation.can_merge_aum && (
                            <span className="validation-badge aum">
                              ✓ AUM
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    <button
                      className="file-remove"
                      onClick={() => handleRemovePreviousFile(fileInfo.id)}
                      aria-label="Remove file"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="process-right">
          <ConfigurationPanel
            settings={settings}
            onSettingsChange={setSettings}
            onProcess={handleProcess}
            isProcessing={isProcessing}
          />
        </div>
      </div>
    </div>
  );
}

