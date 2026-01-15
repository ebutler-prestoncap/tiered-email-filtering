import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listJobs, deleteJob } from '@/services/api';
import type { Job } from '@/types';
import { formatDateTimePacific } from '@/utils/dateUtils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, Plus, X, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

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
      if (import.meta.env.DEV) {
        console.error('Delete error:', error);
      }
    }
  };

  const getStatusVariant = (status: string): 'default' | 'secondary' | 'destructive' | 'outline' => {
    switch (status) {
      case 'completed':
        return 'default';
      case 'processing':
        return 'secondary';
      case 'failed':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Processing History</h1>
        <Button onClick={() => navigate('/')}>
          <Plus className="mr-2 h-4 w-4" />
          New Job
        </Button>
      </div>

      {jobs.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-muted-foreground mb-4">No processing jobs yet.</p>
          <Button onClick={() => navigate('/')}>Start Processing</Button>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {jobs.map(job => (
            <Card
              key={job.id}
              className={cn(
                'p-4 transition-colors',
                job.status === 'completed' && 'cursor-pointer hover:bg-muted/50'
              )}
              onClick={() => {
                if (job.status === 'completed') {
                  navigate(`/analytics/${job.id}`);
                }
              }}
            >
              <div className="flex items-start justify-between gap-2 mb-3">
                <Badge
                  variant={getStatusVariant(job.status)}
                  className={cn(
                    job.status === 'completed' && 'bg-green-500 hover:bg-green-500'
                  )}
                >
                  {job.status}
                </Badge>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 text-muted-foreground hover:text-destructive"
                  onClick={(e) => handleDelete(job.id, e)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>

              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  {formatDateTimePacific(job.created_at)}
                </p>
                <p className="text-sm">
                  {job.input_files.length} file{job.input_files.length !== 1 ? 's' : ''}
                </p>

                {job.analytics?.processing_summary && (
                  <div className="flex flex-wrap gap-2 pt-2">
                    <div className="text-xs">
                      <span className="text-muted-foreground">T1:</span>{' '}
                      <span className="font-medium">
                        {job.analytics.processing_summary.tier1_contacts.toLocaleString()}
                      </span>
                    </div>
                    <div className="text-xs">
                      <span className="text-muted-foreground">T2:</span>{' '}
                      <span className="font-medium">
                        {job.analytics.processing_summary.tier2_contacts.toLocaleString()}
                      </span>
                    </div>
                    {job.analytics.processing_summary.tier3_contacts > 0 && (
                      <div className="text-xs">
                        <span className="text-muted-foreground">T3:</span>{' '}
                        <span className="font-medium">
                          {job.analytics.processing_summary.tier3_contacts.toLocaleString()}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {job.status === 'completed' && (
                <div className="flex items-center gap-1 mt-3 text-sm text-primary font-medium">
                  View Analytics
                  <ArrowRight className="h-4 w-4" />
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
