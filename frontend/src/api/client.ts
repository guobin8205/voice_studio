import type { ModelInfo, SystemStatus, GenerateRequest, GenerateResponse, VoiceRecord } from '../types';

const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json();
}

export const api = {
  // Models
  getModels: () => request<ModelInfo[]>('/models'),
  getModelStatus: (name: string) => request<{ name: string; loaded: boolean; size: string | null }>(`/models/${name}/status`),
  loadModel: (name: string, size: string) =>
    request<{ name: string; size: string; loaded: boolean }>(`/models/${name}/load`, { method: 'POST', body: JSON.stringify({ size }) }),
  unloadModel: (name: string) =>
    request<{ name: string; loaded: boolean }>(`/models/${name}/unload`, { method: 'POST' }),

  // Model download
  getDownloadStatus: (name: string) =>
    request<{ name: string; downloading: boolean; progress: number; status: string; error: string | null }>(`/models/${name}/download-status`),
  startDownload: (name: string) =>
    request<{ name: string; message: string }>(`/models/${name}/download`, { method: 'POST' }),
  downloadProgressWS: (name: string) =>
    new WebSocket(`ws://${window.location.host}/api/models/${name}/download-progress`),

  // System
  getSystemStatus: () => request<SystemStatus>('/system/status'),

  // TTS
  generate: (req: GenerateRequest) =>
    request<GenerateResponse>('/generate', { method: 'POST', body: JSON.stringify(req) }),

  // Voices
  listVoices: (type?: string, search?: string) =>
    request<VoiceRecord[]>(`/voices?${new URLSearchParams({ ...(type && { type }), ...(search && { search }) })}`),
  getVoice: (id: string) => request<VoiceRecord>(`/voices/${id}`),
  createVoice: (data: Partial<VoiceRecord>) =>
    request<VoiceRecord>('/voices', { method: 'POST', body: JSON.stringify(data) }),
  deleteVoice: (id: string) => request<{ deleted: string }>(`/voices/${id}`, { method: 'DELETE' }),
};
