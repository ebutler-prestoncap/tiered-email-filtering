import { useState, useEffect } from 'react';
import { listJobs, downloadResults } from '@/services/api';
import type { Job } from '@/types';
import { formatDateTimePacific } from '@/utils/dateUtils';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

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

      const completedJobs = jobsData
        .filter(job => {
          return job.status === 'completed' && job.output_filename;
        })
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

      setJobs(completedJobs);
    } catch (error) {
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
      const blob = await downloadResults(job.id);
      const fileName = job.output_filename || `processed-${job.id}.xlsx`;
      const file = new File([blob], fileName, { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

      onSelectFile(file);
      onClose();
      setSelectedJobId(null);
    } catch (error) {
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

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Select Previously Processed File</DialogTitle>
        </DialogHeader>

        <div className="py-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
              Loading processed files...
            </div>
          ) : jobs.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground">No previously processed files available</p>
              <p className="text-sm text-muted-foreground mt-1">
                Process some files first to see them here. Only completed jobs with output files are shown.
              </p>
            </div>
          ) : (
            <ScrollArea className="h-[400px] pr-4">
              <div className="space-y-2">
                {jobs.map((job) => (
                  <div
                    key={job.id}
                    className={cn(
                      'flex items-center justify-between gap-4 p-3 rounded-lg border',
                      selectedJobId === job.id && 'bg-muted'
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">{getJobDisplayName(job)}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                        <span>Processed: {formatDateTimePacific(job.created_at)}</span>
                        {job.analytics?.processing_summary && (
                          <>
                            <span>•</span>
                            <span>
                              {job.analytics.processing_summary.total_filtered_contacts.toLocaleString()} contacts
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleSelectJob(job)}
                      disabled={isDownloading}
                    >
                      {selectedJobId === job.id && isDownloading ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                          Loading...
                        </>
                      ) : (
                        'Use This File'
                      )}
                    </Button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
