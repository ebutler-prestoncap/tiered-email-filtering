import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import FileUpload from '../components/FileUpload';
import ConfigurationPanel from '../components/ConfigurationPanel';
import ProcessingStatus from '../components/ProcessingStatus';
import { uploadFiles, processContacts } from '../services/api';
import type { ProcessingSettings } from '../types';
import './ProcessPage.css';

export default function ProcessPage() {
  const navigate = useNavigate();
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [settings, setSettings] = useState<ProcessingSettings | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<'pending' | 'processing' | 'completed' | 'failed' | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);

  const handleFilesSelected = (files: File[]) => {
    console.log('handleFilesSelected called with:', files.map(f => f.name));
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

  const handleProcess = async () => {
    if (!settings) {
      alert('Please wait for configuration to load');
      return;
    }
    if (uploadedFiles.length === 0) {
      alert('Please upload at least one Excel file');
      return;
    }

    setIsProcessing(true);
    setProcessingStatus('pending');

    try {
      // Upload files
      const uploadResult = await uploadFiles(uploadedFiles);
      
      // Start processing
      const processResult = await processContacts(uploadResult.files, settings);
      
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
          console.error('Error polling job status:', error);
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
      console.error('Processing error:', error);
      setProcessingStatus('failed');
      setIsProcessing(false);
      alert('Failed to process files. Please try again.');
    }
  };

  return (
    <div className="process-page">
      <h1>Process Contacts</h1>
      <p className="page-description">
        Upload Excel files and configure filtering options to process your contact lists.
      </p>

      <ProcessingStatus status={processingStatus} jobId={currentJobId} />

      <div className="process-layout">
        <div className="process-left">
          <FileUpload
            onFilesSelected={handleFilesSelected}
            uploadedFiles={uploadedFiles}
            onRemoveFile={handleRemoveFile}
          />
        </div>

        <div className="process-right">
          {settings ? (
            <ConfigurationPanel
              settings={settings}
              onSettingsChange={setSettings}
              onProcess={handleProcess}
              isProcessing={isProcessing}
            />
          ) : (
            <div className="config-panel">
              <p>Loading configuration...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

