import { useEffect } from 'react';
import './ProcessingSidePanel.css';

interface ProcessingSidePanelProps {
  status: 'pending' | 'processing' | 'completed' | 'failed' | null;
  jobId: string | null;
  onClose?: () => void;
}

export default function ProcessingSidePanel({ status, jobId, onClose }: ProcessingSidePanelProps) {
  useEffect(() => {
    // Auto-close after 3 seconds if completed
    if (status === 'completed' && onClose) {
      const timer = setTimeout(() => {
        onClose();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [status, onClose]);

  if (!status || !jobId) return null;

  const statusMessages = {
    pending: 'Job queued for processing...',
    processing: 'Processing contacts...',
    completed: 'Processing completed!',
    failed: 'Processing failed',
  };

  const statusIcons = {
    pending: '⏳',
    processing: '⚙️',
    completed: '✅',
    failed: '❌',
  };

  return (
    <div className={`processing-side-panel ${status}`}>
      <div className="panel-header">
        <div className="status-content">
          <span className="status-icon">{statusIcons[status]}</span>
          <span className="status-message">{statusMessages[status]}</span>
        </div>
        {onClose && (
          <button className="panel-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        )}
      </div>
      
      {status === 'processing' && (
        <div className="status-progress">
          <div className="progress-bar"></div>
        </div>
      )}
      
      {status === 'completed' && (
        <div className="panel-actions">
          <a href={`/analytics/${jobId}`} className="status-link">
            View Analytics →
          </a>
        </div>
      )}
    </div>
  );
}

