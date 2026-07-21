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
}

export interface GenerateResponse {
  audio_path: string;
  duration: number;
  sample_rate: number;
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
