import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Link } from 'react-router-dom';
import { Clock, Loader2, CheckCircle2, XCircle, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProcessingStatusProps {
  status: 'pending' | 'processing' | 'completed' | 'failed' | null;
  jobId: string | null;
}

export default function ProcessingStatus({ status, jobId }: ProcessingStatusProps) {
  if (!status || !jobId) return null;

  const statusConfig = {
    pending: {
      icon: Clock,
      message: 'Job queued for processing...',
      variant: 'secondary' as const,
      className: 'text-muted-foreground',
    },
    processing: {
      icon: Loader2,
      message: 'Processing contacts...',
      variant: 'secondary' as const,
      className: 'text-blue-500 animate-spin',
    },
    completed: {
      icon: CheckCircle2,
      message: 'Processing completed!',
      variant: 'secondary' as const,
      className: 'text-green-500',
    },
    failed: {
      icon: XCircle,
      message: 'Processing failed',
      variant: 'destructive' as const,
      className: 'text-destructive',
    },
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <Card className={cn(
      'p-4',
      status === 'completed' && 'border-green-500 bg-green-500/10',
      status === 'failed' && 'border-destructive bg-destructive/10'
    )}>
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Icon className={cn('h-5 w-5', config.className)} />
          <span className="font-medium">{config.message}</span>
        </div>
        {status === 'completed' && (
          <Link
            to={`/analytics/${jobId}`}
            className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
          >
            View Analytics
            <ArrowRight className="h-4 w-4" />
          </Link>
        )}
      </div>
      {status === 'processing' && (
        <Progress value={33} className="mt-3 h-1" />
      )}
    </Card>
  );
}
