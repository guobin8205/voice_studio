export interface ModelInfo {
  name: string;
  display_name: string;
  sizes: string[];
  capabilities: string[];
  supported_languages: string[];
  supported_dialects: string[];
}

export interface ModelStatus {
  name: string;
  loaded: boolean;
  size: string | null;
}

export interface GPUStatus {
  available: boolean;
  total_gb: number;
  used_gb: number;
  utilization_pct: number;
  temperature_c: number;
}

export interface SystemStatus {
  gpu: GPUStatus;
  model: {
    name: string | null;
    size: string | null;
    loaded: boolean;
  };
}

export interface GenerateRequest {
  model: string;
  size: string;
  text: string;
  language: string;
  dialect?: string;
  prompt?: string;
  emotion?: string;
  speed: number;
  pitch: number;
  temperature: number;
  top_p: number;
  extras?: Record<string, unknown>;
}

export interface GenerateResponse {
  audio_path: string;
  duration: number;
  sample_rate: number;
  load_ms?: number;
  inference_ms?: number;
  total_ms?: number;
}

// SSE 推送的生成进度事件
export interface GenerateEvent {
  phase: 'loading' | 'loading_done' | 'generating' | 'done' | 'error';
  elapsed_ms?: number;
  message?: string;
  // phase=done 时填充
  audio_path?: string;
  duration?: number;
  sample_rate?: number;
  load_ms?: number;
  inference_ms?: number;
  total_ms?: number;
  // phase=error 时填充
  status?: number;
}

export interface VoiceRecord {
  id: string;
  name: string;
  type: 'prompt' | 'clone';
  prompt?: string;
  reference_audio?: string;
  embeddings?: Record<string, string | null>;
  params?: Record<string, number>;
  created_at: string;
}
