import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getJob, downloadResults, createPreset } from '../services/api';
import type { Job } from '../types';
import './AnalyticsPage.css';

export default function AnalyticsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPresetModal, setShowPresetModal] = useState(false);
  const [presetName, setPresetName] = useState('');
  const [savingPreset, setSavingPreset] = useState(false);
  const [presetSaveMessage, setPresetSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (jobId) {
      loadJob();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]); // loadJob is stable and doesn't need to be in deps

  const loadJob = async () => {
    if (!jobId) return;
    
    try {
      setLoading(true);
      const jobData = await getJob(jobId);
      setJob(jobData);
      setError(null);
    } catch (err) {
      setError('Failed to load job data');
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Failed to load job:', err);
      }
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
      
      // Generate filename using same method as CSV exports (user prefix from settings)
      const prefix = getUserPrefix();
      // Get timestamp from job creation date or use current date (format: YYYYMMDD_HHMMSS)
      const getTimestamp = (date: Date): string => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${year}${month}${day}_${hours}${minutes}${seconds}`;
      };
      const timestamp = job?.created_at 
        ? getTimestamp(new Date(job.created_at))
        : getTimestamp(new Date());
      a.download = `${prefix}_${timestamp}.xlsx`;
      
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Failed to download file');
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Download error:', err);
      }
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
      const prefix = getUserPrefix();
      a.download = `${prefix}_Removed_${tier.toUpperCase()}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert(`Failed to export ${tier} delta list`);
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Export error:', err);
      }
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
  
  // Get user prefix from job settings for export filenames
  const getUserPrefix = (): string => {
    const prefix = job?.settings?.userPrefix || 'Combined-Contacts';
    // Sanitize prefix for filename (remove invalid characters)
    return prefix.replace(/[^a-zA-Z0-9_-]/g, '_').substring(0, 50);
  };
  
  // Get removed contacts count for each tier from delta analysis
  const getRemovedCount = (tier: string) => {
    if (!analytics?.delta_analysis || !Array.isArray(analytics.delta_analysis)) return 0;
    return analytics.delta_analysis.filter((item: any) => 
      item.PROCESSING_STATUS === 'Removed' && item.TIER === tier
    ).length;
  };

  // Get all removed contacts
  const getAllRemovedContacts = () => {
    if (!analytics?.delta_analysis || !Array.isArray(analytics.delta_analysis)) return [];
    return analytics.delta_analysis.filter((item: any) => 
      item.PROCESSING_STATUS === 'Removed'
    );
  };

  // Get top removal reasons
  const getTopRemovalReasons = (limit: number = 10) => {
    const removed = getAllRemovedContacts();
    if (removed.length === 0) return [];
    
    const reasonCounts: Record<string, number> = {};
    removed.forEach((item: any) => {
      const reason = item.FILTER_REASON || 'Unknown reason';
      reasonCounts[reason] = (reasonCounts[reason] || 0) + 1;
    });
    
    return Object.entries(reasonCounts)
      .map(([reason, count]) => ({ reason, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, limit);
  };

  // Get per-tier breakdown
  const getTierBreakdown = () => {
    const removed = getAllRemovedContacts();
    if (removed.length === 0) return { tier1: 0, tier2: 0, tier3: 0 };
    
    return {
      tier1: removed.filter((item: any) => item.TIER === 'Tier 1').length,
      tier2: removed.filter((item: any) => item.TIER === 'Tier 2').length,
      tier3: removed.filter((item: any) => item.TIER === 'Tier 3').length,
    };
  };

  const handleExportAllRemoved = async () => {
    if (!jobId || !analytics?.delta_analysis) return;
    
    try {
      const allRemoved = getAllRemovedContacts();
      
      if (allRemoved.length === 0) {
        alert('No removed contacts found');
        return;
      }
      
      // Convert to CSV
      const headers = Object.keys(allRemoved[0]);
      const csvRows = [
        headers.join(','),
        ...allRemoved.map((row: any) => 
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
      const prefix = getUserPrefix();
      a.download = `${prefix}_All_Removed_Contacts.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Failed to export all removed contacts');
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Export error:', err);
      }
    }
  };

  const handleExportExcludedFirms = () => {
    if (!jobId || !analytics?.excluded_firms_list || analytics.excluded_firms_list.length === 0) return;

    try {
      const csvContent = [
        'Firm Name',
        ...analytics.excluded_firms_list.map((firm: string) => {
          // Escape commas and quotes in CSV
          if (firm.includes(',') || firm.includes('"')) {
            return `"${firm.replace(/"/g, '""')}"`;
          }
          return firm;
        })
      ].join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const prefix = getUserPrefix();
      a.download = `${prefix}_Excluded_Firms.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Failed to export excluded firms');
      // Error logged to console for debugging in development
      if (import.meta.env.DEV) {
        console.error('Export error:', err);
      }
    }
  };

  const handleSaveAsPreset = async () => {
    if (!job?.settings || !presetName.trim()) return;

    setSavingPreset(true);
    setPresetSaveMessage(null);

    try {
      await createPreset(presetName.trim(), job.settings);
      setPresetSaveMessage({ type: 'success', text: `Preset "${presetName.trim()}" saved successfully!` });
      setPresetName('');
      setShowPresetModal(false);
      // Clear success message after 3 seconds
      setTimeout(() => setPresetSaveMessage(null), 3000);
    } catch (err) {
      setPresetSaveMessage({ type: 'error', text: 'Failed to save preset. Please try again.' });
      if (import.meta.env.DEV) {
        console.error('Save preset error:', err);
      }
    } finally {
      setSavingPreset(false);
    }
  };

  return (
    <div className="analytics-page">
      <div className="analytics-header">
        <button className="back-button" onClick={() => navigate('/history')}>
          ← Back to History
        </button>
        <h1>Analytics</h1>
        <div className="header-actions">
          {job.status === 'completed' && (
            <>
              <button className="save-preset-button" onClick={() => setShowPresetModal(true)}>
                Save as Preset
              </button>
              <button className="download-button" onClick={handleDownload}>
                Download Excel
              </button>
            </>
          )}
        </div>
      </div>

      {/* Preset Save Modal */}
      {showPresetModal && (
        <div className="modal-overlay" onClick={() => setShowPresetModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Save Filter as Preset</h3>
            <p>Save the current filter configuration as a reusable preset.</p>
            <input
              type="text"
              className="preset-name-input"
              placeholder="Enter preset name"
              value={presetName}
              onChange={(e) => setPresetName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && presetName.trim()) {
                  handleSaveAsPreset();
                }
              }}
              autoFocus
            />
            <div className="modal-actions">
              <button
                className="cancel-button"
                onClick={() => {
                  setShowPresetModal(false);
                  setPresetName('');
                }}
              >
                Cancel
              </button>
              <button
                className="save-button"
                onClick={handleSaveAsPreset}
                disabled={!presetName.trim() || savingPreset}
              >
                {savingPreset ? 'Saving...' : 'Save Preset'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preset Save Message */}
      {presetSaveMessage && (
        <div className={`preset-message ${presetSaveMessage.type}`}>
          {presetSaveMessage.text}
        </div>
      )}

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
              {(() => {
                const breakdown = getTierBreakdown();
                const totalRemoved = breakdown.tier1 + breakdown.tier2 + breakdown.tier3;
                if (totalRemoved > 0) {
                  return (
                    <>
                      <div className="summary-card">
                        <div className="summary-label">Tier 1 Removed</div>
                        <div className="summary-value">{breakdown.tier1.toLocaleString()}</div>
                      </div>
                      <div className="summary-card">
                        <div className="summary-label">Tier 2 Removed</div>
                        <div className="summary-value">{breakdown.tier2.toLocaleString()}</div>
                      </div>
                      {breakdown.tier3 > 0 && (
                        <div className="summary-card">
                          <div className="summary-label">Tier 3 Removed</div>
                          <div className="summary-value">{breakdown.tier3.toLocaleString()}</div>
                        </div>
                      )}
                      <div className="summary-card">
                        <div className="summary-label">Total Removed</div>
                        <div className="summary-value">{totalRemoved.toLocaleString()}</div>
                      </div>
                    </>
                  );
                }
                return null;
              })()}
              {analytics?.excluded_firms_list && analytics.excluded_firms_list.length > 0 && (
                <div className="summary-card">
                  <div className="summary-label">Firms Removed</div>
                  <div className="summary-value">{analytics.excluded_firms_list.length.toLocaleString()}</div>
                </div>
              )}
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
                  {analytics.input_file_details.map((file, index) => {
                    // Extract filename from path if needed
                    let fileName = file.file.includes('/') || file.file.includes('\\')
                      ? file.file.split(/[/\\]/).pop() || file.file
                      : file.file;
                    
                    // Check if it's a UUID filename - if so, try to get original name from job input_files
                    const isUuid = fileName.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\./i);
                    if (isUuid && job?.input_files && job.input_files.length > index) {
                      // Use the original filename from job input_files
                      fileName = job.input_files[index];
                    }
                    
                    // Extract just the filename if it's still a path
                    const displayName = fileName.includes('/') || fileName.includes('\\')
                      ? fileName.split(/[/\\]/).pop() || fileName
                      : fileName;
                    
                    return (
                      <tr key={index}>
                        <td>{displayName}</td>
                        <td>{file.contacts.toLocaleString()}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </section>
          )}

          {analytics?.delta_analysis && Array.isArray(analytics.delta_analysis) && analytics.delta_analysis.length > 0 && (
            <section className="details-section">
              <h2>Removed Contacts by Tier</h2>
              <p className="section-description">
                Statistics and export options for contacts removed during filtering.
              </p>
              
              {/* Per Tier Breakdown */}
              {(() => {
                const breakdown = getTierBreakdown();
                const totalRemoved = breakdown.tier1 + breakdown.tier2 + breakdown.tier3;
                if (totalRemoved === 0) return null;
                
                return (
                  <div className="summary-grid" style={{ marginBottom: '2rem' }}>
                    <div className="summary-card">
                      <div className="summary-label">Tier 1 Removed</div>
                      <div className="summary-value">{breakdown.tier1.toLocaleString()}</div>
                    </div>
                    <div className="summary-card">
                      <div className="summary-label">Tier 2 Removed</div>
                      <div className="summary-value">{breakdown.tier2.toLocaleString()}</div>
                    </div>
                    {breakdown.tier3 > 0 && (
                      <div className="summary-card">
                        <div className="summary-label">Tier 3 Removed</div>
                        <div className="summary-value">{breakdown.tier3.toLocaleString()}</div>
                      </div>
                    )}
                    <div className="summary-card">
                      <div className="summary-label">Total Removed</div>
                      <div className="summary-value">{totalRemoved.toLocaleString()}</div>
                    </div>
                  </div>
                );
              })()}

              {/* Top Removal Reasons */}
              {(() => {
                const topReasons = getTopRemovalReasons(10);
                if (topReasons.length === 0) return null;
                
                return (
                  <div style={{ marginBottom: '2rem' }}>
                    <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: '600' }}>Top Removal Reasons</h3>
                    <table className="details-table">
                      <thead>
                        <tr>
                          <th>Reason</th>
                          <th>Count</th>
                        </tr>
                      </thead>
                      <tbody>
                        {topReasons.map((item, index) => (
                          <tr key={index}>
                            <td>{item.reason}</td>
                            <td>{item.count.toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                );
              })()}

              {/* Export Buttons */}
              <div className="export-buttons">
                {getAllRemovedContacts().length > 0 && (
                  <button
                    className="export-button"
                    onClick={handleExportAllRemoved}
                    style={{ marginBottom: '1rem', width: '100%' }}
                  >
                    Export All Removed Contacts ({getAllRemovedContacts().length.toLocaleString()})
                  </button>
                )}
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
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
              {analytics?.excluded_firms_list && analytics.excluded_firms_list.length > 0 && (
                <div className="export-buttons" style={{ marginTop: '1.5rem' }}>
                  <button
                    className="export-button"
                    onClick={handleExportExcludedFirms}
                    style={{ width: '100%' }}
                  >
                    Export Excluded Firms ({analytics.excluded_firms_list.length.toLocaleString()})
                  </button>
                </div>
              )}
            </section>
          )}
        </div>
      )}
    </div>
  );
}

