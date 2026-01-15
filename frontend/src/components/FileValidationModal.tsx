import { useState, useEffect, useCallback } from 'react';
import { validateFile, type FileValidationResult, type SheetValidation } from '@/services/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Loader2, FileSpreadsheet, Check, X, Info, HelpCircle, AlertTriangle, Link, Unlink } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FileValidationModalProps {
  file: File;
  onConfirm: (file: File, validation: FileValidationResult) => void;
  onCancel: () => void;
}

export default function FileValidationModal({ file, onConfirm, onCancel }: FileValidationModalProps) {
  const [isValidating, setIsValidating] = useState(true);
  const [validation, setValidation] = useState<FileValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runValidation = useCallback(async () => {
    setIsValidating(true);
    setError(null);

    try {
      const result = await validateFile(file);
      setValidation(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to validate file');
    } finally {
      setIsValidating(false);
    }
  }, [file]);

  useEffect(() => {
    runValidation();
  }, [runValidation]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getSheetIcon = (sheet: SheetValidation) => {
    if (sheet.type === 'accounts' && sheet.valid) return { Icon: Check, className: 'text-green-500' };
    if (sheet.type === 'contacts' && sheet.valid) return { Icon: Check, className: 'text-green-500' };
    if (sheet.type === 'metadata') return { Icon: Info, className: 'text-muted-foreground' };
    if (sheet.type === 'error' || !sheet.valid) return { Icon: X, className: 'text-red-500' };
    if (sheet.type === 'unknown') return { Icon: HelpCircle, className: 'text-orange-500' };
    return { Icon: Check, className: 'text-muted-foreground' };
  };

  const getSheetTypeLabel = (type: string) => {
    switch (type) {
      case 'accounts': return 'Accounts Sheet';
      case 'contacts': return 'Contacts Sheet';
      case 'metadata': return 'Metadata';
      case 'unknown': return 'Unknown';
      case 'empty': return 'Empty';
      case 'error': return 'Error';
      default: return type;
    }
  };

  const handleConfirm = () => {
    if (validation) {
      onConfirm(file, validation);
    }
  };

  const isConfirmDisabled = !validation || !validation.can_process;

  const getDisabledReason = () => {
    if (!validation) return '';
    if (!validation.contacts_sheet && validation.accounts_sheet) {
      return 'Cannot process: File contains only accounts data. A contacts sheet is required.';
    }
    if (!validation.can_process) {
      return 'Cannot process: No valid contacts sheet found.';
    }
    return '';
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onCancel()}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Validate File</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* File info */}
          <Card className="flex items-center gap-4 p-4">
            <div className="h-12 w-12 rounded-lg bg-muted flex items-center justify-center">
              <FileSpreadsheet className="h-6 w-6 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium truncate">{file.name}</h3>
              <span className="text-sm text-muted-foreground">{formatFileSize(file.size)}</span>
            </div>
          </Card>

          {/* Validation state */}
          {isValidating && (
            <div className="flex flex-col items-center gap-3 py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Analyzing file structure...</p>
            </div>
          )}

          {error && (
            <Card className="p-4 border-destructive bg-destructive/10">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-destructive" />
                <p className="flex-1 text-sm">{error}</p>
                <Button variant="outline" size="sm" onClick={runValidation}>Retry</Button>
              </div>
            </Card>
          )}

          {validation && !isValidating && (
            <>
              {/* Summary status */}
              <Card className={cn(
                'p-4',
                validation.can_process ? 'border-green-500 bg-green-500/10' : 'border-destructive bg-destructive/10'
              )}>
                <div className="flex items-center gap-3">
                  {validation.can_process ? (
                    <Check className="h-5 w-5 text-green-500" />
                  ) : (
                    <X className="h-5 w-5 text-destructive" />
                  )}
                  <div>
                    <strong>{validation.can_process ? 'File is valid' : 'File cannot be processed'}</strong>
                    <p className="text-sm text-muted-foreground">{validation.summary}</p>
                  </div>
                </div>
              </Card>

              {/* Sheets section */}
              <div className="space-y-3">
                <h4 className="font-medium">Detected Sheets</h4>
                <div className="space-y-2">
                  {validation.sheets.map((sheet, index) => {
                    const { Icon, className } = getSheetIcon(sheet);
                    return (
                      <Card key={index} className="p-3">
                        <div className="flex items-center gap-3">
                          <Icon className={cn('h-4 w-4', className)} />
                          <div className="flex-1 min-w-0">
                            <span className="font-medium text-sm">{sheet.name}</span>
                            <span className="text-xs text-muted-foreground ml-2">{getSheetTypeLabel(sheet.type)}</span>
                          </div>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span>{sheet.row_count.toLocaleString()} rows</span>
                            <span>{Math.round(sheet.confidence * 100)}% match</span>
                          </div>
                        </div>

                        {/* Schema details */}
                        {(sheet.type === 'accounts' || sheet.type === 'contacts') && sheet.schema_details && (
                          <div className="mt-3 space-y-2">
                            {sheet.columns_found.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                <span className="text-xs text-muted-foreground mr-1">Found:</span>
                                {sheet.columns_found.map((col, i) => (
                                  <Badge key={i} variant="secondary" className="text-xs bg-green-500/15 text-green-600">
                                    {col.expected}
                                  </Badge>
                                ))}
                              </div>
                            )}
                            {sheet.columns_missing.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                <span className="text-xs text-muted-foreground mr-1">Missing:</span>
                                {sheet.columns_missing.map((col, i) => (
                                  <Badge key={i} variant="secondary" className="text-xs bg-orange-500/15 text-orange-600">
                                    {col}
                                  </Badge>
                                ))}
                              </div>
                            )}
                            {sheet.type === 'accounts' && sheet.schema_details.aum_column && (
                              <Badge variant="secondary" className="bg-purple-500/15 text-purple-600">
                                AUM: {sheet.schema_details.aum_column}
                              </Badge>
                            )}
                          </div>
                        )}

                        {/* Errors */}
                        {sheet.errors.length > 0 && (
                          <div className="mt-2 space-y-1">
                            {sheet.errors.map((err, i) => (
                              <p key={i} className="text-xs text-destructive">• {err}</p>
                            ))}
                          </div>
                        )}

                        {/* Warnings */}
                        {sheet.warnings.length > 0 && (
                          <div className="mt-2 space-y-1">
                            {sheet.warnings.map((warn, i) => (
                              <p key={i} className="text-xs text-orange-600">⚠ {warn}</p>
                            ))}
                          </div>
                        )}
                      </Card>
                    );
                  })}
                </div>
              </div>

              {/* AUM merge status */}
              {validation.accounts_sheet && validation.contacts_sheet && (
                <Card className={cn(
                  'p-4',
                  validation.can_merge_aum ? 'border-blue-500 bg-blue-500/10' : 'border-muted'
                )}>
                  <div className="flex items-center gap-3">
                    {validation.can_merge_aum ? (
                      <Link className="h-5 w-5 text-blue-500" />
                    ) : (
                      <Unlink className="h-5 w-5 text-muted-foreground" />
                    )}
                    <div>
                      <strong className="text-sm">
                        {validation.can_merge_aum
                          ? 'AUM data can be merged with contacts'
                          : 'Cannot merge AUM data'}
                      </strong>
                      <p className="text-xs text-muted-foreground">
                        {validation.can_merge_aum
                          ? 'Both sheets have FIRM_ID columns for linking.'
                          : 'Missing FIRM_ID column. AUM-based filtering unavailable.'}
                      </p>
                    </div>
                  </div>
                </Card>
              )}

              {/* File-level warnings */}
              {validation.warnings.length > 0 && (
                <div className="space-y-1">
                  <h4 className="text-sm font-medium">Warnings</h4>
                  {validation.warnings.map((warn, i) => (
                    <p key={i} className="text-sm text-orange-600">⚠ {warn}</p>
                  ))}
                </div>
              )}

              {/* File-level errors */}
              {validation.errors.length > 0 && (
                <div className="space-y-1">
                  <h4 className="text-sm font-medium">Errors</h4>
                  {validation.errors.map((err, i) => (
                    <p key={i} className="text-sm text-destructive">• {err}</p>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          {isConfirmDisabled && validation && (
            <p className="text-sm text-destructive mr-auto">{getDisabledReason()}</p>
          )}
          <div className="flex gap-2">
            <Button variant="outline" onClick={onCancel}>Cancel</Button>
            <Button onClick={handleConfirm} disabled={isConfirmDisabled || isValidating}>
              {isValidating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Validating...
                </>
              ) : (
                'Confirm & Add File'
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
