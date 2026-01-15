import { useCallback, useState } from 'react';
import FileValidationModal from './FileValidationModal';
import type { FileValidationResult } from '@/services/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Upload, X } from 'lucide-react';
import { cn } from '@/lib/utils';

// Extended file info that includes validation result
export interface ValidatedFile {
  file: File;
  validation: FileValidationResult;
}

interface FileUploadProps {
  onFilesSelected: (files: File[], validations?: FileValidationResult[]) => void;
  uploadedFiles: File[];
  onRemoveFile: (index: number) => void;
  // Optional: get validation info for a file
  getFileValidation?: (file: File) => FileValidationResult | undefined;
}

export default function FileUpload({
  onFilesSelected,
  uploadedFiles,
  onRemoveFile,
  getFileValidation,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files).filter(
      file => file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
    );

    if (files.length > 0) {
      // Open validation modal for first file
      setPendingFile(files[0]);
    }
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const validFiles = files.filter(
      file => file.name.endsWith('.xlsx') || file.name.endsWith('.xls')
    );

    if (validFiles.length > 0) {
      // Open validation modal for the file
      setPendingFile(validFiles[0]);
      // Reset input to allow selecting the same file again
      e.target.value = '';
    } else if (files.length > 0) {
      alert('Please select Excel files (.xlsx or .xls)');
      e.target.value = '';
    }
  }, []);

  const handleValidationConfirm = useCallback((file: File, validation: FileValidationResult) => {
    // Check if file already exists
    const isDuplicate = uploadedFiles.some(
      existingFile => existingFile.name === file.name && existingFile.size === file.size
    );

    if (!isDuplicate) {
      onFilesSelected([file], [validation]);
    }
    setPendingFile(null);
  }, [onFilesSelected, uploadedFiles]);

  const handleValidationCancel = useCallback(() => {
    setPendingFile(null);
  }, []);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="mb-8">
      <div
        className={cn(
          'border-2 border-dashed rounded-lg p-12 text-center bg-muted/50 transition-colors cursor-pointer',
          isDragging && 'border-primary bg-primary/5'
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-input"
          multiple
          accept=".xlsx,.xls"
          onChange={handleFileInput}
          className="hidden"
        />
        <label htmlFor="file-input" className="block cursor-pointer">
          <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <div className="text-base mb-2">
            <strong>Drop Excel files here</strong> or click to browse
          </div>
          <div className="text-sm text-muted-foreground">Supports .xlsx and .xls files</div>
        </label>
      </div>

      {uploadedFiles.length > 0 ? (
        <div className="mt-6">
          <h3 className="text-base font-semibold mb-4">Uploaded Files ({uploadedFiles.length})</h3>
          <div className="flex flex-col gap-2">
            {uploadedFiles.map((file, index) => {
              const validation = getFileValidation?.(file);
              return (
                <Card key={`${file.name}-${index}`} className="flex items-center gap-4 p-4">
                  <div className="flex-1 flex flex-col gap-1 min-w-0">
                    <span className="text-sm break-words">{file.name}</span>
                    <span className="text-xs text-muted-foreground">{formatFileSize(file.size)}</span>
                    {validation && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {validation.contacts_sheet && (
                          <Badge variant="secondary" className="bg-green-500/15 text-green-600 hover:bg-green-500/20">
                            ✓ Contacts
                          </Badge>
                        )}
                        {validation.accounts_sheet && (
                          <Badge variant="secondary" className="bg-blue-500/15 text-blue-600 hover:bg-blue-500/20">
                            ✓ Accounts
                          </Badge>
                        )}
                        {validation.can_merge_aum && (
                          <Badge variant="secondary" className="bg-purple-500/15 text-purple-600 hover:bg-purple-500/20">
                            ✓ AUM
                          </Badge>
                        )}
                      </div>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                    onClick={() => onRemoveFile(index)}
                    aria-label="Remove file"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </Card>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="mt-6 p-4 text-center bg-muted/50 rounded-lg border border-dashed">
          <p className="text-sm text-muted-foreground">No files uploaded yet</p>
        </div>
      )}

      {/* Validation modal */}
      {pendingFile && (
        <FileValidationModal
          file={pendingFile}
          onConfirm={handleValidationConfirm}
          onCancel={handleValidationCancel}
        />
      )}
    </div>
  );
}
