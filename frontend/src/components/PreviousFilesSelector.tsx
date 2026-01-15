import { useState, useEffect, useCallback } from 'react';
import { listUploadedFiles, validateUploadedFile, type FileValidationResult, type UploadedFile } from '@/services/api';
import { formatDateTimePacific } from '@/utils/dateUtils';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PreviousFilesSelectorProps {
  isOpen: boolean;
  onClose: () => void;
  selectedFileIds: string[];
  onSelectionChange: (fileIds: string[]) => void;
  onFileValidated?: (fileId: string, validation: FileValidationResult, fileInfo: UploadedFile) => void;
}

export default function PreviousFilesSelector({
  isOpen,
  onClose,
  selectedFileIds,
  onSelectionChange,
  onFileValidated
}: PreviousFilesSelectorProps) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [fileValidations, setFileValidations] = useState<Map<string, FileValidationResult>>(new Map());
  const [loadingValidations, setLoadingValidations] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(false);

  const loadValidationForFile = useCallback(async (fileId: string, fileInfo: UploadedFile) => {
    setLoadingValidations(prev => new Set(prev).add(fileId));

    try {
      const validation = await validateUploadedFile(fileId);
      setFileValidations(prev => {
        const newMap = new Map(prev);
        newMap.set(fileId, validation);
        return newMap;
      });

      if (onFileValidated) {
        onFileValidated(fileId, validation, fileInfo);
      }
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error(`Failed to validate file ${fileId}:`, error);
      }
    } finally {
      setLoadingValidations(prev => {
        const newSet = new Set(prev);
        newSet.delete(fileId);
        return newSet;
      });
    }
  }, [onFileValidated]);

  useEffect(() => {
    const loadFiles = async () => {
      setIsLoading(true);
      try {
        const uploadedFiles = await listUploadedFiles();
        const availableFiles = uploadedFiles.filter(file => file.fileExists !== false);
        setFiles(availableFiles);

        const newValidations = new Map<string, FileValidationResult>();
        const filesToValidate: UploadedFile[] = [];

        availableFiles.forEach(file => {
          if (file.validation) {
            newValidations.set(file.id, file.validation);
            if (onFileValidated) {
              onFileValidated(file.id, file.validation, file);
            }
          } else if (!loadingValidations.has(file.id) && !fileValidations.has(file.id)) {
            filesToValidate.push(file);
          }
        });

        if (newValidations.size > 0) {
          setFileValidations(prev => {
            const merged = new Map(prev);
            newValidations.forEach((val, key) => merged.set(key, val));
            return merged;
          });
        }

        filesToValidate.forEach(file => {
          loadValidationForFile(file.id, file);
        });
      } catch (error) {
        if (import.meta.env.DEV) {
          console.error('Failed to load uploaded files:', error);
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleToggleFile = (fileId: string) => {
    if (selectedFileIds.includes(fileId)) {
      onSelectionChange(selectedFileIds.filter(id => id !== fileId));
    } else {
      onSelectionChange([...selectedFileIds, fileId]);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const renderValidationBadges = (fileId: string) => {
    const validation = fileValidations.get(fileId);
    const isLoadingVal = loadingValidations.has(fileId);

    if (isLoadingVal) {
      return (
        <span className="text-xs text-muted-foreground flex items-center gap-1">
          <Loader2 className="h-3 w-3 animate-spin" />
          Validating...
        </span>
      );
    }

    if (!validation) {
      return null;
    }

    return (
      <div className="flex flex-wrap gap-1">
        {validation.contacts_sheet && (
          <Badge variant="secondary" className="bg-green-500/15 text-green-600 text-xs">
            Contacts ({validation.sheets.find(s => s.name === validation.contacts_sheet)?.row_count?.toLocaleString() || '?'})
          </Badge>
        )}
        {validation.accounts_sheet && (
          <Badge variant="secondary" className="bg-blue-500/15 text-blue-600 text-xs">
            Accounts ({validation.sheets.find(s => s.name === validation.accounts_sheet)?.row_count?.toLocaleString() || '?'})
          </Badge>
        )}
        {validation.can_merge_aum && (
          <Badge variant="secondary" className="bg-purple-500/15 text-purple-600 text-xs">
            AUM
          </Badge>
        )}
        {!validation.can_process && (
          <Badge variant="destructive" className="text-xs">
            Invalid
          </Badge>
        )}
      </div>
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Select Previous Uploads</DialogTitle>
        </DialogHeader>

        <div className="py-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
              Loading files...
            </div>
          ) : files.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-muted-foreground">No previously uploaded files</p>
              <p className="text-sm text-muted-foreground mt-1">
                Upload files to see them here for future use
              </p>
            </div>
          ) : (
            <ScrollArea className="h-[400px] pr-4">
              <div className="space-y-2">
                {files.map((file) => {
                  const validation = fileValidations.get(file.id);
                  const isInvalid = validation && !validation.can_process;
                  const isSelected = selectedFileIds.includes(file.id);

                  return (
                    <label
                      key={file.id}
                      htmlFor={`file-checkbox-${file.id}`}
                      className={cn(
                        'flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                        isSelected && 'bg-accent border-primary',
                        isInvalid && 'opacity-50 cursor-not-allowed',
                        !isSelected && !isInvalid && 'hover:bg-muted/50'
                      )}
                    >
                      <Checkbox
                        id={`file-checkbox-${file.id}`}
                        checked={isSelected}
                        onCheckedChange={() => handleToggleFile(file.id)}
                        disabled={isInvalid}
                        className="mt-1"
                      />
                      <div className="flex-1 min-w-0 space-y-1">
                        <p className="font-medium text-sm break-words">{file.originalName}</p>
                        {renderValidationBadges(file.id)}
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span>{formatFileSize(file.fileSize)}</span>
                          <span>-</span>
                          <span>{formatDateTimePacific(file.uploadedAt)}</span>
                        </div>
                      </div>
                    </label>
                  );
                })}
              </div>
            </ScrollArea>
          )}
        </div>

        <DialogFooter className="flex items-center justify-between sm:justify-between">
          <span className="text-sm text-muted-foreground">
            {selectedFileIds.length} file{selectedFileIds.length !== 1 ? 's' : ''} selected
          </span>
          <Button onClick={onClose}>Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
