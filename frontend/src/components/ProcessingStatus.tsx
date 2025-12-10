import './ProcessingStatus.css';

interface ProcessingStatusProps {
  status: 'pending' | 'processing' | 'completed' | 'failed' | null;
  jobId: string | null;
}

export default function ProcessingStatus({ status, jobId }: ProcessingStatusProps) {
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
    <div className={`processing-status ${status}`}>
      <div className="status-content">
        <span className="status-icon">{statusIcons[status]}</span>
        <span className="status-message">{statusMessages[status]}</span>
        {status === 'completed' && (
          <a href={`/analytics/${jobId}`} className="status-link">
            View Analytics →
          </a>
        )}
      </div>
      {status === 'processing' && (
        <div className="status-progress">
          <div className="progress-bar"></div>
        </div>
      )}
    </div>
  );
}

