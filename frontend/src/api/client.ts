import type { ModelInfo, SystemStatus, GenerateRequest, GenerateResponse, GenerateEvent, VoiceRecord } from '../types';

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

/**
 * SSE 流式生成：通过 fetch + ReadableStream 接收 /api/generate-stream 的事件。
 * onEvent 在每个事件（loading/generating/done/error）时回调。
 * 返回一个 abort 函数，调用它会中止请求。
 */
function generateStreamSSE(
  req: GenerateRequest,
  onEvent: (ev: GenerateEvent) => void,
  onError: (e: Error) => void,
): () => void {
  const controller = new AbortController();
  fetch(`${BASE}/generate-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal: controller.signal,
  }).then(async res => {
    if (!res.ok || !res.body) {
      onError(new Error(`HTTP ${res.status}`));
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      // SSE 事件以 \n\n 分隔
      let idx;
      while ((idx = buf.indexOf('\n\n')) >= 0) {
        const chunk = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const line = chunk.split('\n').find(l => l.startsWith('data:'));
        if (!line) continue;
        const json = line.slice(5).trim();
        try {
          onEvent(JSON.parse(json));
        } catch (e) {
          // 忽略解析失败
        }
      }
    }
  }).catch(e => {
    if (e.name !== 'AbortError') onError(e);
  });
  return () => controller.abort();
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
  getDownloadStatus: (name: string, size?: string) =>
    request<any>(`/models/${name}/download-status${size ? `?size=${encodeURIComponent(size)}` : ''}`),
  startDownload: (name: string, size?: string) =>
    request<{ name: string; sizes_started: string[]; message: string }>(`/models/${name}/download${size ? `?size=${encodeURIComponent(size)}` : ''}`, { method: 'POST' }),
  downloadProgressWS: (name: string, size?: string) =>
    new WebSocket(`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/models/${name}/download-progress${size ? `?size=${encodeURIComponent(size)}` : ''}`),

  // System
  getSystemStatus: () => request<SystemStatus>('/system/status'),

  // TTS
  generate: (req: GenerateRequest) =>
    request<GenerateResponse>('/generate', { method: 'POST', body: JSON.stringify(req) }),

  // SSE 流式生成（带进度反馈）
  generateStream: generateStreamSSE,

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
