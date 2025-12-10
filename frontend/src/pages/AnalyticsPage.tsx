import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getJob, downloadResults } from '../services/api';
import type { Job, Analytics } from '../types';
import './AnalyticsPage.css';

export default function AnalyticsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (jobId) {
      loadJob();
    }
  }, [jobId]);

  const loadJob = async () => {
    if (!jobId) return;
    
    try {
      setLoading(true);
      const jobData = await getJob(jobId);
      setJob(jobData);
      setError(null);
    } catch (err) {
      setError('Failed to load job data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!jobId) return;
    
    try {
      const blob = await downloadResults(jobId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = job?.output_filename || 'results.xlsx';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Failed to download file');
      console.error(err);
    }
  };

  const handleExportDelta = async (tier: 'tier1' | 'tier2' | 'tier3') => {
    if (!jobId || !analytics?.delta_analysis) return;
    
    try {
      // Create CSV from delta analysis for the specified tier
      const deltaData = analytics.delta_analysis;
      const tierRemoved = deltaData.filter((item: any) => 
        item.PROCESSING_STATUS === 'Removed' && 
        (tier === 'tier1' ? item.TIER === 'Tier 1' : tier === 'tier2' ? item.TIER === 'Tier 2' : item.TIER === 'Tier 3')
      );
      
      if (tierRemoved.length === 0) {
        alert(`No removed contacts found for ${tier.toUpperCase()}`);
        return;
      }
      
      // Convert to CSV
      const headers = Object.keys(tierRemoved[0]);
      const csvRows = [
        headers.join(','),
        ...tierRemoved.map((row: any) => 
          headers.map(header => {
            const value = row[header] || '';
            // Escape commas and quotes in CSV
            if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
              return `"${value.replace(/"/g, '""')}"`;
            }
            return value;
          }).join(',')
        )
      ];
      
      const csvContent = csvRows.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `removed_contacts_${tier}_${jobId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert(`Failed to export ${tier} delta list`);
      console.error(err);
    }
  };

  if (loading) {
    return <div className="analytics-page">Loading...</div>;
  }

  if (error || !job) {
    return (
      <div className="analytics-page">
        <p>{error || 'Job not found'}</p>
        <button onClick={() => navigate('/')}>Back to Process</button>
      </div>
    );
  }

  const analytics = job.analytics;
  const summary = analytics?.processing_summary;

  return (
    <div className="analytics-page">
      <div className="analytics-header">
        <button className="back-button" onClick={() => navigate('/history')}>
          ← Back to History
        </button>
        <h1>Analytics</h1>
        {job.status === 'completed' && (
          <button className="download-button" onClick={handleDownload}>
            Download Excel
          </button>
        )}
      </div>

      {summary && (
        <div className="analytics-content">
          <section className="summary-section">
            <h2>Processing Summary</h2>
            <div className="summary-grid">
              <div className="summary-card">
                <div className="summary-label">Input Files</div>
                <div className="summary-value">{summary.input_files_count}</div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Total Raw Contacts</div>
                <div className="summary-value">{summary.total_raw_contacts.toLocaleString()}</div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Unique Contacts</div>
                <div className="summary-value">{summary.unique_contacts_after_dedup.toLocaleString()}</div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Tier 1 Contacts</div>
                <div className="summary-value">{summary.tier1_contacts.toLocaleString()}</div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Tier 2 Contacts</div>
                <div className="summary-value">{summary.tier2_contacts.toLocaleString()}</div>
              </div>
              {summary.tier3_contacts > 0 && (
                <div className="summary-card">
                  <div className="summary-label">Tier 3 Contacts</div>
                  <div className="summary-value">{summary.tier3_contacts.toLocaleString()}</div>
                </div>
              )}
              <div className="summary-card">
                <div className="summary-label">Total Filtered</div>
                <div className="summary-value">{summary.total_filtered_contacts.toLocaleString()}</div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Retention Rate</div>
                <div className="summary-value">{summary.retention_rate.toFixed(1)}%</div>
              </div>
            </div>
          </section>

          {analytics?.input_file_details && analytics.input_file_details.length > 0 && (
            <section className="details-section">
              <h2>Input File Details</h2>
              <table className="details-table">
                <thead>
                  <tr>
                    <th>File Name</th>
                    <th>Contacts</th>
                  </tr>
                </thead>
                <tbody>
                  {analytics.input_file_details.map((file, index) => (
                    <tr key={index}>
                      <td>{file.file}</td>
                      <td>{file.contacts.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {analytics?.excluded_firms_list && analytics.excluded_firms_list.length > 0 && (
            <section className="details-section">
              <h2>Removed Firms</h2>
              <div className="firms-list-container">
                <p className="section-description">
                  Total firms removed: {analytics.excluded_firms_list.length}
                </p>
                <div className="firms-list">
                  {analytics.excluded_firms_list.map((firm, index) => (
                    <span key={index} className="firm-tag">
                      {firm}
                    </span>
                  ))}
                </div>
              </div>
            </section>
          )}

          {analytics?.delta_analysis && Array.isArray(analytics.delta_analysis) && analytics.delta_analysis.length > 0 && (
            <section className="details-section">
              <h2>Removed Contacts by Tier</h2>
              <p className="section-description">
                Export lists of contacts removed from each tier during filtering.
              </p>
              <div className="export-buttons">
                {getRemovedCount('Tier 1') > 0 && (
                  <button
                    className="export-button"
                    onClick={() => handleExportDelta('tier1')}
                  >
                    Export Tier 1 Removed ({getRemovedCount('Tier 1')})
                  </button>
                )}
                {getRemovedCount('Tier 2') > 0 && (
                  <button
                    className="export-button"
                    onClick={() => handleExportDelta('tier2')}
                  >
                    Export Tier 2 Removed ({getRemovedCount('Tier 2')})
                  </button>
                )}
                {getRemovedCount('Tier 3') > 0 && (
                  <button
                    className="export-button"
                    onClick={() => handleExportDelta('tier3')}
                  >
                    Export Tier 3 Removed ({getRemovedCount('Tier 3')})
                  </button>
                )}
              </div>
            </section>
          )}

          {analytics?.excluded_firms_summary && (
            <section className="details-section">
              <h2>Excluded Firms Summary</h2>
              <div className="summary-grid">
                <div className="summary-card">
                  <div className="summary-label">Total Firms</div>
                  <div className="summary-value">
                    {analytics.excluded_firms_summary.total_firms_after_dedup.toLocaleString()}
                  </div>
                </div>
                <div className="summary-card">
                  <div className="summary-label">Included Firms</div>
                  <div className="summary-value">
                    {analytics.excluded_firms_summary.included_firms_count.toLocaleString()}
                  </div>
                </div>
                <div className="summary-card">
                  <div className="summary-label">Excluded Firms</div>
                  <div className="summary-value">
                    {analytics.excluded_firms_summary.completely_excluded_firms_count.toLocaleString()}
                  </div>
                </div>
                <div className="summary-card">
                  <div className="summary-label">Exclusion Rate</div>
                  <div className="summary-value">
                    {analytics.excluded_firms_summary.exclusion_rate_firms.toFixed(1)}%
                  </div>
                </div>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}

