import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listJobs, deleteJob } from '../services/api';
import type { Job } from '../types';
import { formatDateTimePacific } from '../utils/dateUtils';
import './HistoryPage.css';

export default function HistoryPage() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      setLoading(true);
      const jobsData = await listJobs(50);
      setJobs(jobsData);
    } catch (error) {
      console.error('Failed to load jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (jobId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this job?')) {
      return;
    }

    try {
      await deleteJob(jobId);
      setJobs(jobs.filter(j => j.id !== jobId));
    } catch (error) {
      alert('Failed to delete job');
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Delete error:', error);
      }
    }
  };


  if (loading) {
    return <div className="history-page">Loading...</div>;
  }

  return (
    <div className="history-page">
      <div className="history-header">
        <h1>Processing History</h1>
        <button className="new-job-button" onClick={() => navigate('/')}>
          New Job
        </button>
      </div>

      {jobs.length === 0 ? (
        <div className="empty-state">
          <p>No processing jobs yet.</p>
          <button onClick={() => navigate('/')}>Start Processing</button>
        </div>
      ) : (
        <div className="jobs-grid">
          {jobs.map(job => (
            <div
              key={job.id}
              className="job-card"
              onClick={() => {
                if (job.status === 'completed') {
                  navigate(`/analytics/${job.id}`);
                }
              }}
            >
              <div className="job-header">
                <div className="job-status" data-status={job.status}>
                  {job.status}
                </div>
                <button
                  className="job-delete"
                  onClick={(e) => handleDelete(job.id, e)}
                  aria-label="Delete job"
                >
                  ×
                </button>
              </div>
              <div className="job-content">
                <div className="job-date">{formatDateTimePacific(job.created_at)}</div>
                <div className="job-files">
                  {job.input_files.length} file{job.input_files.length !== 1 ? 's' : ''}
                </div>
                {job.analytics?.processing_summary && (
                  <div className="job-stats">
                    <div className="job-stat">
                      <span className="stat-label">Tier 1:</span>
                      <span className="stat-value">
                        {job.analytics.processing_summary.tier1_contacts.toLocaleString()}
                      </span>
                    </div>
                    <div className="job-stat">
                      <span className="stat-label">Tier 2:</span>
                      <span className="stat-value">
                        {job.analytics.processing_summary.tier2_contacts.toLocaleString()}
                      </span>
                    </div>
                    {job.analytics.processing_summary.tier3_contacts > 0 && (
                      <div className="job-stat">
                        <span className="stat-label">Tier 3:</span>
                        <span className="stat-value">
                          {job.analytics.processing_summary.tier3_contacts.toLocaleString()}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
              {job.status === 'completed' && (
                <div className="job-action">
                  View Analytics →
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

