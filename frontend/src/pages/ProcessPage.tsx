import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import FileUpload from '../components/FileUpload';
import ConfigurationPanel from '../components/ConfigurationPanel';
import ProcessingSidePanel from '../components/ProcessingSidePanel';
import PreviousFilesSelector from '../components/PreviousFilesSelector';
import { uploadFiles, processContacts, listUploadedFiles } from '../services/api';
import { generatePrefixFromFilenames } from '../utils/filenameUtils';
import type { ProcessingSettings } from '../types';
import './ProcessPage.css';

export default function ProcessPage() {
  const navigate = useNavigate();
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [selectedPreviousFileIds, setSelectedPreviousFileIds] = useState<string[]>([]);
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
  const [processingStatus, setProcessingStatus] = useState<'pending' | 'processing' | 'completed' | 'failed' | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);

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

  const handleFilesSelected = (files: File[]) => {
    setUploadedFiles(prev => {
      // Avoid duplicates by checking file name and size
      const newFiles = files.filter(newFile => 
        !prev.some(existingFile => 
          existingFile.name === newFile.name && existingFile.size === newFile.size
        )
      );
      return [...prev, ...newFiles];
    });
  };

  const handleRemoveFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
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
      const pollInterval = setInterval(async () => {
        try {
          const { getJob } = await import('../services/api');
          const job = await getJob(processResult.jobId);
          
          if (job.status === 'completed') {
            clearInterval(pollInterval);
            setProcessingStatus('completed');
            setIsProcessing(false);
            // Navigate to analytics after a short delay
            setTimeout(() => {
              navigate(`/analytics/${processResult.jobId}`);
            }, 2000);
          } else if (job.status === 'failed') {
            clearInterval(pollInterval);
            setProcessingStatus('failed');
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
        clearInterval(pollInterval);
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

  return (
    <div className={`process-page ${showProcessingPanel ? 'with-processing-bar' : ''}`}>
      {showProcessingPanel && (
        <ProcessingSidePanel
          status={processingStatus}
          jobId={currentJobId}
          onClose={() => setShowProcessingPanel(false)}
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
          />
          <FileUpload
            onFilesSelected={handleFilesSelected}
            uploadedFiles={uploadedFiles}
            onRemoveFile={handleRemoveFile}
          />
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

