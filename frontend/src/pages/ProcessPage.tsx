import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import FileUpload from '@/components/FileUpload';
import ConfigurationPanel from '@/components/ConfigurationPanel';
import ProcessingSidePanel from '@/components/ProcessingSidePanel';
import PreviousFilesSelector from '@/components/PreviousFilesSelector';
import { uploadFiles, processContacts, listUploadedFiles, cancelJob, type FileValidationResult } from '@/services/api';
import { generatePrefixFromFilenames } from '@/utils/filenameUtils';
import type { ProcessingSettings } from '@/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { FolderOpen, X } from 'lucide-react';

type FileValidationMap = Map<string, FileValidationResult>;

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
  const [showPreviousFilesModal, setShowPreviousFilesModal] = useState(false);
  const [settings, setSettings] = useState<ProcessingSettings>({
    includeAllFirms: false,
    findEmails: true,
    firmExclusion: false,
    contactInclusion: false,
    tier1Limit: 10,
    tier2Limit: 6,
    tier3Limit: 3,
    userPrefix: 'Combined-Contacts',
    tier1Filters: { includeKeywords: [], excludeKeywords: [], requireInvestmentTeam: false },
    tier2Filters: { includeKeywords: [], excludeKeywords: [], requireInvestmentTeam: true },
    tier3Filters: { includeKeywords: [], excludeKeywords: [], requireInvestmentTeam: false },
    firmExclusionList: '',
    firmInclusionList: '',
    contactExclusionList: '',
    contactInclusionList: '',
    fieldFilters: [],
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [progressText, setProgressText] = useState<string | undefined>(undefined);
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const updatePrefixFromFiles = useCallback(async (
    uploadedFiles: File[],
    previousFileIds: string[]
  ) => {
    try {
      const allFilenames: (File | string)[] = [...uploadedFiles];
      if (previousFileIds.length > 0) {
        const previousFiles = await listUploadedFiles();
        const selectedPreviousFiles = previousFiles.filter(file => previousFileIds.includes(file.id));
        selectedPreviousFiles.forEach(file => allFilenames.push(file.originalName));
      }
      if (allFilenames.length > 0) {
        const generatedPrefix = generatePrefixFromFilenames(allFilenames);
        setSettings(prev => ({ ...prev, userPrefix: generatedPrefix }));
      }
    } catch (error) {
      if (import.meta.env.DEV) console.error('Failed to update prefix from files:', error);
      if (uploadedFiles.length > 0) {
        const generatedPrefix = generatePrefixFromFilenames(uploadedFiles);
        setSettings(prev => ({ ...prev, userPrefix: generatedPrefix }));
      }
    }
  }, []);

  const handleFilesSelected = (files: File[], validations?: FileValidationResult[]) => {
    setUploadedFiles(prev => {
      const newFiles = files.filter(newFile =>
        !prev.some(existingFile => existingFile.name === newFile.name && existingFile.size === newFile.size)
      );
      return [...prev, ...newFiles];
    });
    if (validations && validations.length > 0) {
      setFileValidations(prev => {
        const newMap = new Map(prev);
        files.forEach((file, index) => {
          if (validations[index]) newMap.set(getFileKey(file), validations[index]);
        });
        return newMap;
      });
    }
  };

  const handleRemoveFile = (index: number) => {
    setUploadedFiles(prev => {
      const fileToRemove = prev[index];
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

  const handlePreviousFileValidated = useCallback((
    fileId: string,
    validation: FileValidationResult,
    fileInfo: { id: string; originalName: string; fileSize: number }
  ) => {
    setPreviousFileInfo(prev => {
      const newMap = new Map(prev);
      newMap.set(fileId, { ...fileInfo, validation });
      return newMap;
    });
  }, []);

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
    setProgressText(undefined);
    setProgressPercent(0);

    try {
      let filePaths: string[] = [];
      let fileIds: string[] = [];

      if (uploadedFiles.length > 0) {
        const uploadResult = await uploadFiles(uploadedFiles);
        filePaths = uploadResult.paths || uploadResult.files;
        fileIds = uploadResult.fileIds || [];
      }

      const allFileIds = [...fileIds, ...selectedPreviousFileIds];
      const processResult = await processContacts(filePaths, settings, allFileIds.length > 0 ? allFileIds : undefined);

      setCurrentJobId(processResult.jobId);
      setProcessingStatus('processing');

      pollIntervalRef.current = setInterval(async () => {
        try {
          const { getJob } = await import('@/services/api');
          const job = await getJob(processResult.jobId);

          if (job.progress_text) setProgressText(job.progress_text);
          if (job.progress_percent !== undefined) setProgressPercent(job.progress_percent);

          if (job.status === 'completed') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setProcessingStatus('completed');
            setIsProcessing(false);
            setTimeout(() => navigate(`/analytics/${processResult.jobId}`), 2000);
          } else if (job.status === 'failed' || job.status === 'cancelled') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setProcessingStatus(job.status);
            setIsProcessing(false);
          }
        } catch (error) {
          if (import.meta.env.DEV) console.error('Error polling job status:', error);
        }
      }, 2000);

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
      if (import.meta.env.DEV) console.error('Processing error:', error);
      setProcessingStatus('failed');
      setIsProcessing(false);
      alert('Failed to process files. Please try again.');
    }
  };

  const handleCancel = async () => {
    if (!currentJobId) return;
    try {
      await cancelJob(currentJobId);
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      setProcessingStatus('cancelled');
      setIsProcessing(false);
    } catch (error) {
      if (import.meta.env.DEV) console.error('Error cancelling job:', error);
      alert('Failed to cancel job. Please try again.');
    }
  };

  return (
    <div className="space-y-6">
      {showProcessingPanel && (
        <ProcessingSidePanel
          status={processingStatus}
          jobId={currentJobId}
          onClose={() => setShowProcessingPanel(false)}
          onCancel={handleCancel}
          progressText={progressText}
          progressPercent={progressPercent}
        />
      )}

      <PreviousFilesSelector
        isOpen={showPreviousFilesModal}
        onClose={() => setShowPreviousFilesModal(false)}
        selectedFileIds={selectedPreviousFileIds}
        onSelectionChange={setSelectedPreviousFileIds}
        onFileValidated={handlePreviousFileValidated}
      />

      <div>
        <h1 className="text-3xl font-bold mb-2">Process Contacts</h1>
        <p className="text-muted-foreground">
          Upload Excel files or select from previous uploads, then configure filtering options.
        </p>
      </div>

      <div className="space-y-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Input Files</h2>
            <Button variant="outline" onClick={() => setShowPreviousFilesModal(true)}>
              <FolderOpen className="mr-2 h-4 w-4" />
              Select Previous Uploads
              {selectedPreviousFileIds.length > 0 && (
                <Badge variant="secondary" className="ml-2">{selectedPreviousFileIds.length}</Badge>
              )}
            </Button>
          </div>

          <FileUpload
            onFilesSelected={handleFilesSelected}
            uploadedFiles={uploadedFiles}
            onRemoveFile={handleRemoveFile}
            getFileValidation={getFileValidation}
          />

          {selectedPreviousFiles.length > 0 && (
            <div className="space-y-3">
              <h3 className="font-medium">Selected Previous Files ({selectedPreviousFiles.length})</h3>
              <div className="space-y-2">
                {selectedPreviousFiles.map((fileInfo) => (
                  <Card key={fileInfo.id} className="flex items-center gap-4 p-4 bg-muted/30">
                    <div className="flex-1 flex flex-col gap-1 min-w-0">
                      <span className="text-sm font-medium break-words">{fileInfo.originalName}</span>
                      <span className="text-xs text-muted-foreground">{formatFileSize(fileInfo.fileSize)}</span>
                      {fileInfo.validation && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {fileInfo.validation.contacts_sheet && (
                            <Badge variant="secondary" className="bg-green-500/15 text-green-600 text-xs">Contacts</Badge>
                          )}
                          {fileInfo.validation.accounts_sheet && (
                            <Badge variant="secondary" className="bg-blue-500/15 text-blue-600 text-xs">Accounts</Badge>
                          )}
                          {fileInfo.validation.can_merge_aum && (
                            <Badge variant="secondary" className="bg-purple-500/15 text-purple-600 text-xs">AUM</Badge>
                          )}
                        </div>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      onClick={() => handleRemovePreviousFile(fileInfo.id)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>

        <ConfigurationPanel
          settings={settings}
          onSettingsChange={setSettings}
          onProcess={handleProcess}
          isProcessing={isProcessing}
        />
      </div>
    </div>
  );
}
