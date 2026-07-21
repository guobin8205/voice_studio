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

  // 克隆（multipart 上传）
  clone: (file: File, req: Omit<GenerateRequest, 'top_p'>) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('model', req.model);
    fd.append('size', req.size);
    fd.append('text', req.text);
    fd.append('language', req.language);
    if (req.dialect) fd.append('dialect', req.dialect);
    if (req.emotion) fd.append('emotion', req.emotion);
    fd.append('speed', String(req.speed));
    fd.append('pitch', String(req.pitch));
    fd.append('temperature', String(req.temperature));
    return fetch(`${BASE}/clone`, { method: 'POST', body: fd }).then(r => r.ok ? r.json() : Promise.reject(new Error(r.statusText)));
  },

  // 单独上传参考音频（用于先上传再克隆）
  uploadReference: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return fetch(`${BASE}/upload-reference`, { method: 'POST', body: fd })
      .then(r => r.ok ? r.json() : Promise.reject(new Error(r.statusText))) as Promise<{ path: string; filename: string; size: number }>;
  },

  // ASR（multipart）
  uploadForAsr: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return fetch(`${BASE}/asr`, { method: 'POST', body: fd })
      .then(r => r.ok ? r.json() : Promise.reject(new Error(r.statusText))) as Promise<{ text: string; language: string; duration_seconds: number }>;
  },

  // Voices
  listVoices: (type?: string, search?: string) =>
    request<VoiceRecord[]>(`/voices?${new URLSearchParams({ ...(type && { type }), ...(search && { search }) })}`),
  getVoice: (id: string) => request<VoiceRecord>(`/voices/${id}`),
  createVoice: (data: Partial<VoiceRecord>) =>
    request<VoiceRecord>('/voices', { method: 'POST', body: JSON.stringify(data) }),
  deleteVoice: (id: string) => request<{ deleted: string }>(`/voices/${id}`, { method: 'DELETE' }),
};
