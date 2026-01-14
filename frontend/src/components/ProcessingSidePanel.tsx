import { useEffect } from 'react';
import './ProcessingSidePanel.css';

interface ProcessingSidePanelProps {
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | null;
  jobId: string | null;
  onClose?: () => void;
  onCancel?: () => void;
}

export default function ProcessingSidePanel({ status, jobId, onClose, onCancel }: ProcessingSidePanelProps) {
  useEffect(() => {
    // Auto-close after 5 seconds if completed
    if (status === 'completed' && onClose) {
      const timer = setTimeout(() => {
        onClose();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [status, onClose]);

  if (!status || !jobId) return null;

  const statusMessages = {
    pending: 'Job queued for processing...',
    processing: 'Processing contacts...',
    completed: 'Processing completed!',
    failed: 'Processing failed',
    cancelled: 'Processing cancelled',
  };

  const statusIcons = {
    pending: '⏳',
    processing: '⚙️',
    completed: '✅',
    failed: '❌',
    cancelled: '🚫',
  };

  return (
    <div className={`processing-bar ${status}`}>
      <div className="processing-bar-content">
        <div className="processing-bar-left">
          <span className="processing-bar-icon">{statusIcons[status]}</span>
          <span className="processing-bar-message">{statusMessages[status]}</span>
          {status === 'processing' && (
            <div className="processing-bar-progress">
              <div className="processing-bar-progress-fill"></div>
            </div>
          )}
        </div>
        <div className="processing-bar-right">
          {status === 'processing' && onCancel && (
            <button 
              className="processing-bar-cancel" 
              onClick={onCancel} 
              aria-label="Cancel"
            >
              Cancel
            </button>
          )}
          {status === 'completed' && (
            <a href={`/analytics/${jobId}`} className="processing-bar-link">
              View Analytics →
            </a>
          )}
          {onClose && (
            <button 
              className="processing-bar-close" 
              onClick={onClose} 
              aria-label="Close"
            >
              ×
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

