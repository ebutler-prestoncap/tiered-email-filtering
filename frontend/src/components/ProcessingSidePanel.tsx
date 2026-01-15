import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Clock, Loader2, CheckCircle2, XCircle, Ban, X, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProcessingSidePanelProps {
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | null;
  jobId: string | null;
  onClose?: () => void;
  onCancel?: () => void;
  progressText?: string;
  progressPercent?: number;
}

export default function ProcessingSidePanel({
  status,
  jobId,
  onClose,
  onCancel,
  progressText,
  progressPercent
}: ProcessingSidePanelProps) {
  useEffect(() => {
    if (status === 'completed' && onClose) {
      const timer = setTimeout(() => {
        onClose();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [status, onClose]);

  if (!status || !jobId) return null;

  const getStatusMessage = (): string => {
    if (status === 'processing' && progressText) {
      return progressText;
    }
    const defaultMessages: Record<string, string> = {
      pending: 'Job queued for processing...',
      processing: 'Processing contacts...',
      completed: 'Processing completed!',
      failed: 'Processing failed',
      cancelled: 'Processing cancelled',
    };
    return defaultMessages[status] || 'Unknown status';
  };

  const statusConfig = {
    pending: { icon: Clock, className: 'text-muted-foreground' },
    processing: { icon: Loader2, className: 'text-blue-500 animate-spin' },
    completed: { icon: CheckCircle2, className: 'text-green-500' },
    failed: { icon: XCircle, className: 'text-destructive' },
    cancelled: { icon: Ban, className: 'text-muted-foreground' },
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div className={cn(
      'fixed bottom-4 right-4 z-50 w-96 rounded-lg border bg-background shadow-lg p-4',
      status === 'completed' && 'border-green-500',
      status === 'failed' && 'border-destructive'
    )}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1">
          <Icon className={cn('h-5 w-5 mt-0.5 shrink-0', config.className)} />
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm">{getStatusMessage()}</p>
            {status === 'processing' && (
              <Progress value={progressPercent ?? 0} className="mt-2 h-1.5" />
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {status === 'processing' && onCancel && (
            <Button variant="outline" size="sm" onClick={onCancel}>
              Cancel
            </Button>
          )}
          {status === 'completed' && (
            <Button variant="default" size="sm" asChild>
              <Link to={`/analytics/${jobId}`}>
                View
                <ArrowRight className="ml-1 h-3 w-3" />
              </Link>
            </Button>
          )}
          {onClose && (
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
