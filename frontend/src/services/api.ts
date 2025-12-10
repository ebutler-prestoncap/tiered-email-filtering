/**
 * API client for backend communication
 */
import axios from 'axios';
import type { ProcessingSettings, Job, Analytics, SettingsPreset, ApiResponse } from '../types';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadFiles = async (files: File[]): Promise<{ files: string[]; paths: string[] }> => {
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
  settings: ProcessingSettings
): Promise<{ jobId: string; status: string }> => {
  const response = await api.post<{ success: boolean; jobId: string; status: string }>('/process', {
    files,
    settings,
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

