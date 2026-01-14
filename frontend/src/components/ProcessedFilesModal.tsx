import { useState, useEffect } from 'react';
import { listJobs, downloadResults } from '../services/api';
import type { Job } from '../types';
import { formatDateTimePacific } from '../utils/dateUtils';
import './ProcessedFilesModal.css';

interface ProcessedFilesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectFile: (file: File) => void;
}

export default function ProcessedFilesModal({ isOpen, onClose, onSelectFile }: ProcessedFilesModalProps) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadJobs();
    }
  }, [isOpen]);

  const loadJobs = async () => {
    setIsLoading(true);
    try {
      const jobsData = await listJobs(100);
      
      // Filter to only completed jobs with output_filename
      const completedJobs = jobsData
        .filter(job => {
          return job.status === 'completed' && job.output_filename;
        })
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      
      setJobs(completedJobs);
    } catch (error) {
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Failed to load processed jobs:', error);
      }
      setJobs([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectJob = async (job: Job) => {
    if (!job.id || !job.output_filename) return;
    
    setIsDownloading(true);
    setSelectedJobId(job.id);
    
    try {
      // Download the file as blob
      const blob = await downloadResults(job.id);
      
      // Convert blob to File object
      const fileName = job.output_filename || `processed-${job.id}.xlsx`;
      const file = new File([blob], fileName, { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      
      // Call the callback with the file
      onSelectFile(file);
      
      // Close modal
      onClose();
      setSelectedJobId(null);
    } catch (error) {
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Failed to download file:', error);
      }
      alert('Failed to download processed file. Please try again.');
    } finally {
      setIsDownloading(false);
      setSelectedJobId(null);
    }
  };

  const getJobDisplayName = (job: Job): string => {
    if (job.input_files && job.input_files.length > 0) {
      const firstFile = job.input_files[0];
      const fileName = firstFile.includes('/') || firstFile.includes('\\') 
        ? firstFile.split(/[/\\]/).pop() || firstFile
        : firstFile;
      const baseName = fileName.replace(/\.(xlsx|xls)$/i, '');
      if (job.input_files.length > 1) {
        return `${baseName} (+${job.input_files.length - 1} more)`;
      }
      return baseName;
    }
    return `Job ${job.id.substring(0, 8)}`;
  };

  if (!isOpen) return null;

  return (
    <div className="processed-files-modal-overlay" onClick={onClose}>
      <div className="processed-files-modal" onClick={(e) => e.stopPropagation()}>
        <div className="processed-files-modal-header">
          <h2>Select Previously Processed File</h2>
          <button className="processed-files-modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="processed-files-modal-content">
          {isLoading ? (
            <div className="processed-files-modal-loading">Loading processed files...</div>
          ) : jobs.length === 0 ? (
            <div className="processed-files-modal-empty">
              <p>No previously processed files available</p>
              <p className="processed-files-modal-empty-hint">
                Process some files first to see them here. Only completed jobs with output files are shown.
              </p>
            </div>
          ) : (
            <div className="processed-files-modal-list">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className={`processed-files-modal-item ${selectedJobId === job.id ? 'downloading' : ''}`}
                >
                  <div className="processed-files-modal-item-content">
                    <div className="processed-files-modal-item-name">{getJobDisplayName(job)}</div>
                    <div className="processed-files-modal-item-meta">
                      <span>Processed: {formatDateTimePacific(job.created_at)}</span>
                      {job.analytics?.processing_summary && (
                        <>
                          <span className="processed-files-modal-item-separator">•</span>
                          <span>
                            {job.analytics.processing_summary.total_filtered_contacts.toLocaleString()} contacts
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <button
                    className="processed-files-modal-item-button"
                    onClick={() => handleSelectJob(job)}
                    disabled={isDownloading}
                  >
                    {selectedJobId === job.id && isDownloading ? 'Loading...' : 'Use This File'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

