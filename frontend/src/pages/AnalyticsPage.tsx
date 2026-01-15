import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getJob, downloadResults, createPreset, downloadIndividualFile } from '@/services/api';
import type { Job, FirmTypeBreakdownEntry, FileInZipEntry } from '@/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Loader2, ArrowLeft, Download, Save, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

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
  const [expandedFirmType, setExpandedFirmType] = useState<string | null>(null);

  useEffect(() => {
    if (jobId) {
      loadJob();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      if (import.meta.env.DEV) {
        console.error('Failed to load job:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  const getTimestamp = (date: Date): string => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${year}${month}${day}_${hours}${minutes}${seconds}`;
  };

  const getUserPrefix = (): string => {
    const prefix = job?.settings?.userPrefix || 'Combined-Contacts';
    return prefix.replace(/[^a-zA-Z0-9_-]/g, '_').substring(0, 50);
  };

  const handleDownload = async () => {
    if (!jobId) return;

    try {
      const blob = await downloadResults(jobId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;

      const prefix = getUserPrefix();
      const timestamp = job?.created_at
        ? getTimestamp(new Date(job.created_at))
        : getTimestamp(new Date());

      const isSeparated = job?.analytics?.is_separated_by_firm_type || job?.settings?.separateByFirmType;
      const extension = isSeparated ? '.zip' : '.xlsx';
      a.download = `${prefix}_${timestamp}${extension}`;

      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Failed to download file');
      if (import.meta.env.DEV) {
        console.error('Download error:', err);
      }
    }
  };

  const handleDownloadIndividualFile = async (filename: string) => {
    if (!jobId) return;

    try {
      const blob = await downloadIndividualFile(jobId, filename);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Failed to download file');
      if (import.meta.env.DEV) {
        console.error('Download individual file error:', err);
      }
    }
  };

  const handleExportDelta = async (tier: 'tier1' | 'tier2' | 'tier3') => {
    if (!jobId || !analytics?.delta_analysis) return;

    try {
      const deltaData = analytics.delta_analysis;
      const tierRemoved = deltaData.filter((item: any) =>
        item.PROCESSING_STATUS === 'Removed' &&
        (tier === 'tier1' ? item.TIER === 'Tier 1' : tier === 'tier2' ? item.TIER === 'Tier 2' : item.TIER === 'Tier 3')
      );

      if (tierRemoved.length === 0) {
        alert(`No removed contacts found for ${tier.toUpperCase()}`);
        return;
      }

      const headers = Object.keys(tierRemoved[0]);
      const csvRows = [
        headers.join(','),
        ...tierRemoved.map((row: any) =>
          headers.map(header => {
            const value = row[header] || '';
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
      if (import.meta.env.DEV) {
        console.error('Export error:', err);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="space-y-4">
        <p className="text-destructive">{error || 'Job not found'}</p>
        <Button onClick={() => navigate('/')}>Back to Process</Button>
      </div>
    );
  }

  const analytics = job.analytics;
  const summary = analytics?.processing_summary;

  const getRemovedCount = (tier: string) => {
    if (!analytics?.delta_analysis || !Array.isArray(analytics.delta_analysis)) return 0;
    return analytics.delta_analysis.filter((item: any) =>
      item.PROCESSING_STATUS === 'Removed' && item.TIER === tier
    ).length;
  };

  const getAllRemovedContacts = () => {
    if (!analytics?.delta_analysis || !Array.isArray(analytics.delta_analysis)) return [];
    return analytics.delta_analysis.filter((item: any) =>
      item.PROCESSING_STATUS === 'Removed'
    );
  };

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

      const headers = Object.keys(allRemoved[0]);
      const csvRows = [
        headers.join(','),
        ...allRemoved.map((row: any) =>
          headers.map(header => {
            const value = row[header] || '';
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
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" onClick={() => navigate('/history')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <h1 className="text-2xl font-bold">Analytics</h1>
        </div>
        {job.status === 'completed' && (
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => setShowPresetModal(true)}>
              <Save className="h-4 w-4 mr-2" />
              Save as Preset
            </Button>
            {analytics?.premier_file && (
              <Button
                variant="outline"
                onClick={() => handleDownloadIndividualFile(analytics.premier_file!)}
              >
                <Download className="h-4 w-4 mr-2" />
                Download Premier
              </Button>
            )}
            <Button onClick={handleDownload}>
              <Download className="h-4 w-4 mr-2" />
              {(analytics?.is_separated_by_firm_type || job.settings?.separateByFirmType) ? 'Download All (ZIP)' : 'Download Excel'}
            </Button>
          </div>
        )}
      </div>

      {/* Preset Save Modal */}
      <Dialog open={showPresetModal} onOpenChange={setShowPresetModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Filter as Preset</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Save the current filter configuration as a reusable preset.
          </p>
          <Input
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
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowPresetModal(false); setPresetName(''); }}>
              Cancel
            </Button>
            <Button onClick={handleSaveAsPreset} disabled={!presetName.trim() || savingPreset}>
              {savingPreset ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Saving...
                </>
              ) : (
                'Save Preset'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Preset Save Message */}
      {presetSaveMessage && (
        <div className={cn(
          'p-3 rounded-md text-sm',
          presetSaveMessage.type === 'success' ? 'bg-green-500/10 text-green-600' : 'bg-destructive/10 text-destructive'
        )}>
          {presetSaveMessage.text}
        </div>
      )}

      {summary && (
        <div className="space-y-6">
          {/* Pipeline Flow Visualization */}
          {analytics?.pipeline_flow && (
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-2">Processing Pipeline</h2>
              <p className="text-sm text-muted-foreground mb-4">
                Visual representation of contacts flowing through each processing stage.
              </p>
              <div className="flex flex-wrap items-center gap-2 overflow-x-auto">
                <div className="flex flex-col items-center p-3 rounded-lg bg-muted min-w-[100px]">
                  <span className="text-xs text-muted-foreground">Input</span>
                  <span className="text-lg font-bold">{analytics.pipeline_flow.input_raw.toLocaleString()}</span>
                </div>
                <span className="text-muted-foreground">→</span>
                <div className="flex flex-col items-center p-3 rounded-lg bg-blue-500/10 min-w-[100px]">
                  <span className="text-xs text-muted-foreground">Dedup</span>
                  <span className="text-lg font-bold">{analytics.pipeline_flow.after_dedup.toLocaleString()}</span>
                  <Badge variant="secondary" className="text-xs mt-1">
                    -{(analytics.pipeline_flow.input_raw - analytics.pipeline_flow.after_dedup).toLocaleString()}
                  </Badge>
                </div>
                <span className="text-muted-foreground">→</span>
                <div className="flex flex-col items-center p-3 rounded-lg bg-orange-500/10 min-w-[100px]">
                  <span className="text-xs text-muted-foreground">Removals</span>
                  <span className="text-lg font-bold">{analytics.pipeline_flow.after_removals.toLocaleString()}</span>
                  {analytics.pipeline_flow.after_dedup - analytics.pipeline_flow.after_removals > 0 && (
                    <Badge variant="secondary" className="text-xs mt-1">
                      -{(analytics.pipeline_flow.after_dedup - analytics.pipeline_flow.after_removals).toLocaleString()}
                    </Badge>
                  )}
                </div>
                {analytics.pipeline_flow.premier_extracted !== null && analytics.pipeline_flow.premier_extracted > 0 && (
                  <>
                    <span className="text-muted-foreground">→</span>
                    <div className="flex flex-col items-center p-3 rounded-lg bg-purple-500/10 min-w-[100px]">
                      <span className="text-xs text-muted-foreground">Top 25</span>
                      <span className="text-lg font-bold">{analytics.pipeline_flow.after_premier?.toLocaleString() ?? '-'}</span>
                      <Badge className="bg-purple-500 text-xs mt-1">
                        Premier: {analytics.pipeline_flow.premier_extracted.toLocaleString()}
                      </Badge>
                    </div>
                  </>
                )}
                <span className="text-muted-foreground">→</span>
                <div className="flex flex-col items-center p-3 rounded-lg bg-green-500/10 min-w-[100px]">
                  <span className="text-xs text-muted-foreground">Tiers</span>
                  <span className="text-lg font-bold">
                    {(analytics.pipeline_flow.tier1_output + analytics.pipeline_flow.tier2_output + analytics.pipeline_flow.tier3_output).toLocaleString()}
                  </span>
                  <div className="flex gap-1 mt-1 text-xs">
                    <Badge variant="outline">T1: {analytics.pipeline_flow.tier1_output.toLocaleString()}</Badge>
                    <Badge variant="outline">T2: {analytics.pipeline_flow.tier2_output.toLocaleString()}</Badge>
                    {analytics.pipeline_flow.tier3_output > 0 && (
                      <Badge variant="outline">T3: {analytics.pipeline_flow.tier3_output.toLocaleString()}</Badge>
                    )}
                  </div>
                </div>
                <span className="text-muted-foreground">→</span>
                <div className="flex flex-col items-center p-3 rounded-lg bg-green-500/20 border border-green-500/50 min-w-[100px]">
                  <span className="text-xs text-muted-foreground">Output</span>
                  <span className="text-lg font-bold text-green-600">{analytics.pipeline_flow.total_output.toLocaleString()}</span>
                </div>
              </div>
            </Card>
          )}

          {/* Processing Summary */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4">Processing Summary</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="p-4 rounded-lg bg-muted">
                <p className="text-sm text-muted-foreground">Input Files</p>
                <p className="text-2xl font-bold">{summary.input_files_count}</p>
              </div>
              <div className="p-4 rounded-lg bg-muted">
                <p className="text-sm text-muted-foreground">Total Raw Contacts</p>
                <p className="text-2xl font-bold">{summary.total_raw_contacts.toLocaleString()}</p>
              </div>
              <div className="p-4 rounded-lg bg-muted">
                <p className="text-sm text-muted-foreground">Unique Contacts</p>
                <p className="text-2xl font-bold">{summary.unique_contacts_after_dedup.toLocaleString()}</p>
              </div>
              <div className="p-4 rounded-lg bg-muted">
                <p className="text-sm text-muted-foreground">Total Filtered</p>
                <p className="text-2xl font-bold">{summary.total_filtered_contacts.toLocaleString()}</p>
              </div>
              <div className="p-4 rounded-lg bg-muted">
                <p className="text-sm text-muted-foreground">Tier 1 Contacts</p>
                <p className="text-2xl font-bold">{summary.tier1_contacts.toLocaleString()}</p>
              </div>
              <div className="p-4 rounded-lg bg-muted">
                <p className="text-sm text-muted-foreground">Tier 2 Contacts</p>
                <p className="text-2xl font-bold">{summary.tier2_contacts.toLocaleString()}</p>
              </div>
              {summary.tier3_contacts > 0 && (
                <div className="p-4 rounded-lg bg-muted">
                  <p className="text-sm text-muted-foreground">Tier 3 Contacts</p>
                  <p className="text-2xl font-bold">{summary.tier3_contacts.toLocaleString()}</p>
                </div>
              )}
              <div className="p-4 rounded-lg bg-muted">
                <p className="text-sm text-muted-foreground">Retention Rate</p>
                <p className="text-2xl font-bold">{summary.retention_rate.toFixed(1)}%</p>
              </div>
            </div>
          </Card>

          {/* Removal List Stats */}
          {analytics?.removal_list_stats && analytics.removal_list_stats.total_removed > 0 && (
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-4">Removal List Summary</h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {analytics.removal_list_stats.account_removal.applied && (
                  <>
                    <div className="p-4 rounded-lg bg-muted">
                      <p className="text-sm text-muted-foreground">Account List</p>
                      <p className="text-sm font-medium truncate">
                        {analytics.removal_list_stats.account_removal.list_name || 'Uploaded list'}
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-muted">
                      <p className="text-sm text-muted-foreground">Accounts Matched</p>
                      <p className="text-2xl font-bold">
                        {analytics.removal_list_stats.account_removal.accounts_matched?.toLocaleString() || 0}
                      </p>
                    </div>
                  </>
                )}
                {analytics.removal_list_stats.contact_removal.applied && (
                  <>
                    <div className="p-4 rounded-lg bg-muted">
                      <p className="text-sm text-muted-foreground">Contact List</p>
                      <p className="text-sm font-medium truncate">
                        {analytics.removal_list_stats.contact_removal.list_name || 'Uploaded list'}
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-muted">
                      <p className="text-sm text-muted-foreground">Email Matches</p>
                      <p className="text-2xl font-bold">
                        {analytics.removal_list_stats.contact_removal.email_matches?.toLocaleString() || 0}
                      </p>
                    </div>
                  </>
                )}
                <div className="p-4 rounded-lg bg-destructive/10">
                  <p className="text-sm text-muted-foreground">Total Removed by Lists</p>
                  <p className="text-2xl font-bold text-destructive">
                    {analytics.removal_list_stats.total_removed?.toLocaleString() || 0}
                  </p>
                </div>
              </div>
            </Card>
          )}

          {/* Firm Type Breakdown */}
          {(analytics?.is_separated_by_firm_type || job.settings?.separateByFirmType) && (
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-2">Output Files by Firm Type</h2>
              {analytics?.firm_type_breakdown && analytics.firm_type_breakdown.length > 0 ? (
                <>
                  <p className="text-sm text-muted-foreground mb-4">
                    Your results have been separated into {analytics.firm_type_breakdown.length} files by firm type.
                  </p>
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {analytics.firm_type_breakdown.map((entry: FirmTypeBreakdownEntry) => {
                      const fileEntry = analytics.files_in_zip?.find(
                        (f: FileInZipEntry) => f.firmTypeGroup === entry.firmTypeGroup
                      );
                      const isExpanded = expandedFirmType === entry.firmTypeGroup;

                      return (
                        <Card
                          key={entry.firmTypeGroup}
                          className={cn(
                            'p-4 cursor-pointer transition-colors hover:bg-muted/50',
                            isExpanded && 'ring-2 ring-primary'
                          )}
                          onClick={() => setExpandedFirmType(isExpanded ? null : entry.firmTypeGroup)}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium">{entry.displayName}</span>
                            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                          </div>
                          <p className="text-2xl font-bold mb-2">{entry.totalContacts.toLocaleString()}</p>
                          <div className="flex gap-2 text-xs">
                            <Badge variant="outline">T1: {entry.tier1Contacts.toLocaleString()}</Badge>
                            <Badge variant="outline">T2: {entry.tier2Contacts.toLocaleString()}</Badge>
                            {entry.tier3Contacts > 0 && (
                              <Badge variant="outline">T3: {entry.tier3Contacts.toLocaleString()}</Badge>
                            )}
                          </div>
                          {isExpanded && fileEntry && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="w-full mt-4"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDownloadIndividualFile(fileEntry.filename);
                              }}
                            >
                              <Download className="h-4 w-4 mr-2" />
                              Download {entry.displayName}
                            </Button>
                          )}
                        </Card>
                      );
                    })}
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Separate by Firm Type was enabled, but no contacts passed the filters.
                </p>
              )}
            </Card>
          )}

          {/* Input File Details */}
          {analytics?.input_file_details && analytics.input_file_details.length > 0 && (
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-4">Input File Details</h2>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>File Name</TableHead>
                    <TableHead className="text-right">Contacts</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {analytics.input_file_details.map((file, index) => {
                    let fileName = file.file.includes('/') || file.file.includes('\\')
                      ? file.file.split(/[/\\]/).pop() || file.file
                      : file.file;

                    const isUuid = fileName.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\./i);
                    if (isUuid && job?.input_files && job.input_files.length > index) {
                      fileName = job.input_files[index];
                    }

                    const displayName = fileName.includes('/') || fileName.includes('\\')
                      ? fileName.split(/[/\\]/).pop() || fileName
                      : fileName;

                    return (
                      <TableRow key={index}>
                        <TableCell className="font-medium">{displayName}</TableCell>
                        <TableCell className="text-right">{file.contacts.toLocaleString()}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Card>
          )}

          {/* Delta Analysis / Removed Contacts */}
          {analytics?.delta_analysis && Array.isArray(analytics.delta_analysis) && analytics.delta_analysis.length > 0 && (
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-4">Removed Contacts by Tier</h2>

              {(() => {
                const breakdown = getTierBreakdown();
                const totalRemoved = breakdown.tier1 + breakdown.tier2 + breakdown.tier3;
                if (totalRemoved === 0) return null;

                return (
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
                    <div className="p-4 rounded-lg bg-muted">
                      <p className="text-sm text-muted-foreground">Tier 1 Removed</p>
                      <p className="text-2xl font-bold">{breakdown.tier1.toLocaleString()}</p>
                    </div>
                    <div className="p-4 rounded-lg bg-muted">
                      <p className="text-sm text-muted-foreground">Tier 2 Removed</p>
                      <p className="text-2xl font-bold">{breakdown.tier2.toLocaleString()}</p>
                    </div>
                    {breakdown.tier3 > 0 && (
                      <div className="p-4 rounded-lg bg-muted">
                        <p className="text-sm text-muted-foreground">Tier 3 Removed</p>
                        <p className="text-2xl font-bold">{breakdown.tier3.toLocaleString()}</p>
                      </div>
                    )}
                    <div className="p-4 rounded-lg bg-destructive/10">
                      <p className="text-sm text-muted-foreground">Total Removed</p>
                      <p className="text-2xl font-bold text-destructive">{totalRemoved.toLocaleString()}</p>
                    </div>
                  </div>
                );
              })()}

              {/* Top Removal Reasons */}
              {(() => {
                const topReasons = getTopRemovalReasons(10);
                if (topReasons.length === 0) return null;

                return (
                  <div className="mb-6">
                    <h3 className="font-medium mb-3">Top Removal Reasons</h3>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Reason</TableHead>
                          <TableHead className="text-right">Count</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {topReasons.map((item, index) => (
                          <TableRow key={index}>
                            <TableCell>{item.reason}</TableCell>
                            <TableCell className="text-right">{item.count.toLocaleString()}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                );
              })()}

              {/* Export Buttons */}
              <div className="space-y-3">
                {getAllRemovedContacts().length > 0 && (
                  <Button variant="outline" className="w-full" onClick={handleExportAllRemoved}>
                    <Download className="h-4 w-4 mr-2" />
                    Export All Removed Contacts ({getAllRemovedContacts().length.toLocaleString()})
                  </Button>
                )}
                <div className="flex flex-wrap gap-2">
                  {getRemovedCount('Tier 1') > 0 && (
                    <Button variant="outline" size="sm" onClick={() => handleExportDelta('tier1')}>
                      Export T1 Removed ({getRemovedCount('Tier 1')})
                    </Button>
                  )}
                  {getRemovedCount('Tier 2') > 0 && (
                    <Button variant="outline" size="sm" onClick={() => handleExportDelta('tier2')}>
                      Export T2 Removed ({getRemovedCount('Tier 2')})
                    </Button>
                  )}
                  {getRemovedCount('Tier 3') > 0 && (
                    <Button variant="outline" size="sm" onClick={() => handleExportDelta('tier3')}>
                      Export T3 Removed ({getRemovedCount('Tier 3')})
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          )}

          {/* Excluded Firms Summary */}
          {analytics?.excluded_firms_summary && (
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-4">Excluded Firms Summary</h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-4">
                <div className="p-4 rounded-lg bg-muted">
                  <p className="text-sm text-muted-foreground">Total Firms</p>
                  <p className="text-2xl font-bold">
                    {analytics.excluded_firms_summary.total_firms_after_dedup.toLocaleString()}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-muted">
                  <p className="text-sm text-muted-foreground">Included Firms</p>
                  <p className="text-2xl font-bold">
                    {analytics.excluded_firms_summary.included_firms_count.toLocaleString()}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-muted">
                  <p className="text-sm text-muted-foreground">Excluded Firms</p>
                  <p className="text-2xl font-bold">
                    {analytics.excluded_firms_summary.completely_excluded_firms_count.toLocaleString()}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-muted">
                  <p className="text-sm text-muted-foreground">Exclusion Rate</p>
                  <p className="text-2xl font-bold">
                    {analytics.excluded_firms_summary.exclusion_rate_firms.toFixed(1)}%
                  </p>
                </div>
              </div>
              {analytics?.excluded_firms_list && analytics.excluded_firms_list.length > 0 && (
                <Button variant="outline" className="w-full" onClick={handleExportExcludedFirms}>
                  <Download className="h-4 w-4 mr-2" />
                  Export Excluded Firms ({analytics.excluded_firms_list.length.toLocaleString()})
                </Button>
              )}
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
