import { useState, useCallback, useEffect } from 'react';
import {
  getRemovalLists,
  getActiveRemovalLists,
  uploadRemovalList,
  updateRemovalListStatus,
  deleteRemovalList,
  type RemovalList,
  type ActiveRemovalLists
} from '@/services/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, Plus, X, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface RemovalListManagerProps {
  showUpload?: boolean;
  onListsChange?: () => void;
}

export default function RemovalListManager({ showUpload = true, onListsChange }: RemovalListManagerProps) {
  const [accountLists, setAccountLists] = useState<RemovalList[]>([]);
  const [contactLists, setContactLists] = useState<RemovalList[]>([]);
  const [activeLists, setActiveLists] = useState<ActiveRemovalLists>({ accountRemovalList: null, contactRemovalList: null });
  const [isUploading, setIsUploading] = useState(false);
  const [uploadType, setUploadType] = useState<'account' | 'contact' | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadLists = useCallback(async () => {
    try {
      setLoading(true);
      const [accountData, contactData, activeData] = await Promise.all([
        getRemovalLists('account'),
        getRemovalLists('contact'),
        getActiveRemovalLists()
      ]);
      setAccountLists(accountData);
      setContactLists(contactData);
      setActiveLists(activeData);
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Failed to load removal lists:', error);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLists();
  }, [loadLists]);

  const handleFileUpload = useCallback(async (file: File, listType: 'account' | 'contact') => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      alert('Please select a CSV file');
      return;
    }

    setIsUploading(true);
    setUploadType(listType);
    try {
      await uploadRemovalList(file, listType);
      await loadLists();
      onListsChange?.();
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Failed to upload removal list:', error);
      }
      alert('Failed to upload removal list');
    } finally {
      setIsUploading(false);
      setUploadType(null);
    }
  }, [loadLists, onListsChange]);

  const handleDragOver = useCallback((e: React.DragEvent, type: 'account' | 'contact') => {
    e.preventDefault();
    setIsDragging(true);
    setUploadType(type);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    setUploadType(null);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, type: 'account' | 'contact') => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files).filter(
      file => file.name.toLowerCase().endsWith('.csv')
    );

    if (files.length > 0) {
      handleFileUpload(files[0], type);
    } else {
      alert('Please drop a CSV file');
    }
  }, [handleFileUpload]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>, type: 'account' | 'contact') => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      handleFileUpload(files[0], type);
      e.target.value = '';
    }
  }, [handleFileUpload]);

  const handleToggleActive = useCallback(async (listId: string, currentlyActive: boolean) => {
    try {
      await updateRemovalListStatus(listId, !currentlyActive);
      await loadLists();
      onListsChange?.();
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Failed to update removal list status:', error);
      }
      alert('Failed to update removal list status');
    }
  }, [loadLists, onListsChange]);

  const handleDelete = useCallback(async (listId: string) => {
    if (!confirm('Are you sure you want to delete this removal list?')) {
      return;
    }

    try {
      await deleteRemovalList(listId);
      await loadLists();
      onListsChange?.();
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('Failed to delete removal list:', error);
      }
      alert('Failed to delete removal list');
    }
  }, [loadLists, onListsChange]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderListSection = (
    title: string,
    type: 'account' | 'contact',
    lists: RemovalList[],
    activeList: RemovalList | null
  ) => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">{title}</h3>

      {showUpload && (
        <div
          className={cn(
            'border-2 border-dashed rounded-lg p-4 text-center transition-colors',
            isDragging && uploadType === type
              ? 'border-primary bg-primary/5'
              : 'border-muted-foreground/25 hover:border-muted-foreground/50'
          )}
          onDragOver={(e) => handleDragOver(e, type)}
          onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e, type)}
        >
          <input
            type="file"
            id={`removal-${type}-input`}
            accept=".csv"
            onChange={(e) => handleFileInput(e, type)}
            className="hidden"
            disabled={isUploading}
          />
          <label
            htmlFor={`removal-${type}-input`}
            className="cursor-pointer flex items-center justify-center gap-2 text-sm text-muted-foreground"
          >
            {isUploading && uploadType === type ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Plus className="h-4 w-4" />
                Upload new {type} removal list (CSV)
              </>
            )}
          </label>
        </div>
      )}

      {activeList ? (
        <Card className="p-4 border-green-500/50 bg-green-500/5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Badge className="bg-green-500 hover:bg-green-500">Active</Badge>
                {!activeList.fileExists && (
                  <Badge variant="destructive" className="gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    Missing
                  </Badge>
                )}
              </div>
              <p className="font-medium truncate">{activeList.originalName}</p>
              <p className="text-sm text-muted-foreground">
                {activeList.entryCount.toLocaleString()} {type === 'account' ? 'accounts' : 'contacts'}
                {' | '}
                Uploaded {formatDate(activeList.uploadedAt)}
              </p>
            </div>
          </div>
        </Card>
      ) : (
        <Card className="p-4 bg-muted/30">
          <p className="text-sm text-muted-foreground text-center">
            No active {type} removal list
          </p>
        </Card>
      )}

      {lists.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">
            History ({lists.length})
          </h4>
          <div className="space-y-2">
            {lists.map(list => (
              <Card
                key={list.id}
                className={cn(
                  'p-3',
                  list.isActive && 'border-green-500/30'
                )}
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{list.originalName}</p>
                    <p className="text-xs text-muted-foreground">
                      {list.entryCount.toLocaleString()} entries | {formatFileSize(list.fileSize)}
                      {' | '}{formatDate(list.uploadedAt)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {list.fileExists ? (
                      <Button
                        variant={list.isActive ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => handleToggleActive(list.id, list.isActive)}
                        className={list.isActive ? 'bg-green-500 hover:bg-green-600' : ''}
                      >
                        {list.isActive ? 'Active' : 'Activate'}
                      </Button>
                    ) : (
                      <Badge variant="secondary" className="text-xs">
                        File missing
                      </Badge>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      onClick={() => handleDelete(list.id)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin mr-2" />
        Loading removal lists...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {renderListSection(
        'Account Removal List',
        'account',
        accountLists,
        activeLists.accountRemovalList
      )}
      {renderListSection(
        'Contact Removal List',
        'contact',
        contactLists,
        activeLists.contactRemovalList
      )}
    </div>
  );
}
