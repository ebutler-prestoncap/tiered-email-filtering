/**
 * API client for backend communication
 */
import axios from 'axios';
import type { ProcessingSettings, Job, SettingsPreset } from '../types';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadFiles = async (files: File[]): Promise<{ files: string[]; paths: string[]; fileIds: string[] }> => {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });

  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const processContacts = async (
  files: string[],
  settings: ProcessingSettings,
  fileIds?: string[]
): Promise<{ jobId: string; status: string }> => {
  const response = await api.post<{ success: boolean; jobId: string; status: string }>('/process', {
    files,
    settings,
    fileIds,
  });

  if (!response.data.success) {
    throw new Error('Failed to start processing');
  }

  return {
    jobId: response.data.jobId,
    status: response.data.status,
  };
};

export const getJob = async (jobId: string): Promise<Job> => {
  const response = await api.get<{ success: boolean; job: Job }>(`/jobs/${jobId}`);
  
  if (!response.data.success || !response.data.job) {
    throw new Error('Job not found');
  }

  return response.data.job;
};

export const listJobs = async (limit: number = 50): Promise<Job[]> => {
  const response = await api.get<{ success: boolean; jobs: Job[] }>('/jobs', {
    params: { limit },
  });

  if (!response.data.success) {
    throw new Error('Failed to list jobs');
  }

  return response.data.jobs;
};

export const cancelJob = async (jobId: string): Promise<void> => {
  const response = await api.post<{ success: boolean }>(`/jobs/${jobId}/cancel`);
  
  if (!response.data.success) {
    throw new Error('Failed to cancel job');
  }
};

export const deleteJob = async (jobId: string): Promise<void> => {
  const response = await api.delete<{ success: boolean }>(`/jobs/${jobId}`);
  
  if (!response.data.success) {
    throw new Error('Failed to delete job');
  }
};

export const downloadResults = async (jobId: string): Promise<Blob> => {
  const response = await api.get(`/jobs/${jobId}/download`, {
    responseType: 'blob',
  });

  return response.data;
};

export const getPresets = async (): Promise<SettingsPreset[]> => {
  const response = await api.get<{ success: boolean; presets: SettingsPreset[] }>('/settings/presets');
  
  if (!response.data.success) {
    throw new Error('Failed to get presets');
  }

  return response.data.presets;
};

export const createPreset = async (name: string, settings: ProcessingSettings): Promise<string> => {
  const response = await api.post<{ success: boolean; presetId: string }>('/settings/presets', {
    name,
    settings,
  });

  if (!response.data.success) {
    throw new Error('Failed to create preset');
  }

  return response.data.presetId;
};

export const updatePreset = async (
  presetId: string,
  name?: string,
  settings?: ProcessingSettings
): Promise<void> => {
  const response = await api.put<{ success: boolean }>(`/settings/presets/${presetId}`, {
    name,
    settings,
  });
  
  if (!response.data.success) {
    throw new Error('Failed to update preset');
  }
};

export const deletePreset = async (presetId: string): Promise<void> => {
  const response = await api.delete<{ success: boolean }>(`/settings/presets/${presetId}`);
  
  if (!response.data.success) {
    throw new Error('Failed to delete preset');
  }
};

export interface UploadedFile {
  id: string;
  originalName: string;
  storedPath: string;
  fileSize: number;
  uploadedAt: string;
  lastUsedAt: string | null;
  fileExists?: boolean;
}

export const listUploadedFiles = async (limit: number = 100): Promise<UploadedFile[]> => {
  const response = await api.get<{ success: boolean; files: UploadedFile[] }>('/files', {
    params: { limit },
  });

  if (!response.data.success) {
    throw new Error('Failed to list uploaded files');
  }

  return response.data.files;
};

// Removal list types and functions
export interface RemovalList {
  id: string;
  listType: 'account' | 'contact';
  originalName: string;
  storedPath?: string;
  fileSize: number;
  entryCount: number;
  isActive: boolean;
  uploadedAt: string;
  lastUsedAt: string | null;
  fileExists?: boolean;
}

export interface ActiveRemovalLists {
  accountRemovalList: RemovalList | null;
  contactRemovalList: RemovalList | null;
}

export const getRemovalLists = async (listType?: 'account' | 'contact', limit: number = 50): Promise<RemovalList[]> => {
  const params: { type?: string; limit: number } = { limit };
  if (listType) {
    params.type = listType;
  }

  const response = await api.get<{ success: boolean; lists: RemovalList[] }>('/removal-lists', { params });

  if (!response.data.success) {
    throw new Error('Failed to get removal lists');
  }

  return response.data.lists;
};

export const getActiveRemovalLists = async (): Promise<ActiveRemovalLists> => {
  const response = await api.get<{ success: boolean; accountRemovalList: RemovalList | null; contactRemovalList: RemovalList | null }>('/removal-lists/active');

  if (!response.data.success) {
    throw new Error('Failed to get active removal lists');
  }

  return {
    accountRemovalList: response.data.accountRemovalList,
    contactRemovalList: response.data.contactRemovalList,
  };
};

export const uploadRemovalList = async (file: File, listType: 'account' | 'contact'): Promise<{
  listId: string;
  listType: string;
  originalName: string;
  entryCount: number;
  fileSize: number;
}> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('listType', listType);

  const response = await api.post('/removal-lists/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  if (!response.data.success) {
    throw new Error('Failed to upload removal list');
  }

  return {
    listId: response.data.listId,
    listType: response.data.listType,
    originalName: response.data.originalName,
    entryCount: response.data.entryCount,
    fileSize: response.data.fileSize,
  };
};

export const updateRemovalListStatus = async (listId: string, isActive: boolean): Promise<void> => {
  const response = await api.put<{ success: boolean }>(`/removal-lists/${listId}/active`, { isActive });

  if (!response.data.success) {
    throw new Error('Failed to update removal list status');
  }
};

export const deleteRemovalList = async (listId: string): Promise<void> => {
  const response = await api.delete<{ success: boolean }>(`/removal-lists/${listId}`);

  if (!response.data.success) {
    throw new Error('Failed to delete removal list');
  }
};

// Firm type separated file functions
export interface FileInJob {
  filename: string;
  size: number;
  compressedSize?: number;
}

export interface JobFilesResponse {
  isSeparatedByFirmType: boolean;
  files: FileInJob[];
}

export const listFilesInJob = async (jobId: string): Promise<JobFilesResponse> => {
  const response = await api.get<{ success: boolean; isSeparatedByFirmType: boolean; files: FileInJob[] }>(`/jobs/${jobId}/files`);

  if (!response.data.success) {
    throw new Error('Failed to list files in job');
  }

  return {
    isSeparatedByFirmType: response.data.isSeparatedByFirmType,
    files: response.data.files
  };
};

export const downloadIndividualFile = async (jobId: string, filename: string): Promise<Blob> => {
  const response = await api.get(`/jobs/${jobId}/download/${encodeURIComponent(filename)}`, {
    responseType: 'blob'
  });
  return response.data;
};

// File validation types and functions
export interface SheetValidation {
  name: string;
  type: 'accounts' | 'contacts' | 'metadata' | 'unknown' | 'empty' | 'error';
  confidence: number;
  valid: boolean;
  row_count: number;
  column_count?: number;
  columns?: string[];
  columns_found: Array<{ expected: string; found: string }>;
  columns_missing: string[];
  errors: string[];
  warnings: string[];
  schema_details?: {
    aum_column?: string | null;
    firm_id_column?: string | null;
    firm_name_column?: string | null;
    name_column?: string | null;
    email_column?: string | null;
    investor_column?: string | null;
    job_title_column?: string | null;
  };
}

export interface FileValidationResult {
  valid: boolean;
  can_process: boolean;
  file_name: string;
  original_name?: string;
  file_size?: number;
  file_id?: string;
  sheets: SheetValidation[];
  accounts_sheet: string | null;
  contacts_sheet: string | null;
  can_merge_aum: boolean;
  summary: string;
  errors: string[];
  warnings: string[];
}

export const validateFile = async (file: File): Promise<FileValidationResult> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<{ success: boolean; validation: FileValidationResult; error?: string }>(
    '/validate-file',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  if (!response.data.success) {
    throw new Error(response.data.error || 'Failed to validate file');
  }

  return response.data.validation;
};

export const validateUploadedFile = async (fileId: string): Promise<FileValidationResult> => {
  const response = await api.get<{ success: boolean; validation: FileValidationResult; error?: string }>(
    `/validate-uploaded/${fileId}`
  );

  if (!response.data.success) {
    throw new Error(response.data.error || 'Failed to validate file');
  }

  return response.data.validation;
};

