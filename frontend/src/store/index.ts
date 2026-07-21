import { create } from 'zustand';
import type { ModelInfo, SystemStatus, GenerateResponse, VoiceRecord } from '../types';
import { api } from '../api/client';

interface ModelOverride {
  speed: number;
  pitch: number;
  temperature: number;
  top_p: number;
}

interface AppState {
  models: ModelInfo[];
  loadedModel: { name: string; size: string } | null;
  systemStatus: SystemStatus | null;

  language: string;
  dialect: string;
  text: string;
  prompt: string;
  emotion: string;
  speed: number;
  pitch: number;
  temperature: number;
  top_p: number;

  selectedModels: { name: string; size: string }[];
  results: Record<string, GenerateResponse>;

  // Phase 3: debug console
  loadedVoice: VoiceRecord | null;
  modelOverrides: Record<string, ModelOverride>;

  fetchModels: () => Promise<void>;
  fetchSystemStatus: () => Promise<void>;
  generate: () => Promise<void>;
  saveVoice: (name: string, type: 'prompt' | 'clone', referenceAudio?: string) => Promise<void>;
  setInput: (key: string, value: string | number) => void;
  toggleModel: (name: string, size: string) => void;
  loadVoice: (voice: VoiceRecord) => void;
  setModelOverride: (modelName: string, key: keyof ModelOverride, value: number) => void;
}

const defaultOverride = (): ModelOverride => ({ speed: 1.0, pitch: 0, temperature: 0.4, top_p: 0.9 });

export const useStore = create<AppState>((set, get) => ({
  models: [],
  loadedModel: null,
  systemStatus: null,
  language: 'zh',
  dialect: '普通话',
  text: '',
  prompt: '',
  emotion: '',
  speed: 1.0,
  pitch: 0,
  temperature: 0.4,
  top_p: 0.9,
  selectedModels: [],
  results: {},
  loadedVoice: null,
  modelOverrides: {},

  fetchModels: async () => {
    const models = await api.getModels();
    set({ models });
    if (get().selectedModels.length === 0 && models.length > 0) {
      set({ selectedModels: [{ name: models[0].name, size: models[0].sizes[0] }] });
    }
  },

  fetchSystemStatus: async () => {
    const status = await api.getSystemStatus();
    set({ systemStatus: status });
  },

  generate: async () => {
    const state = get();
    const results: Record<string, GenerateResponse> = {};
    for (const m of state.selectedModels) {
      const ov = state.modelOverrides[m.name] || defaultOverride();
      const resp = await api.generate({
        model: m.name, size: m.size,
        text: state.text, language: state.language,
        dialect: state.dialect, prompt: state.prompt,
        emotion: state.emotion,
        speed: ov.speed, pitch: ov.pitch,
        temperature: ov.temperature, top_p: ov.top_p,
      });
      results[`${m.name}_${m.size}`] = resp;
    }
    set({ results });
  },

  saveVoice: async (name, type, referenceAudio) => {
    const state = get();
    await api.createVoice({
      name,
      type,
      prompt: type === 'prompt' ? state.prompt : undefined,
      reference_audio: referenceAudio,
      params: {
        speed: state.speed,
        pitch: state.pitch,
        temperature: state.temperature,
        top_p: state.top_p,
      },
    });
  },

  setInput: (key, value) => set({ [key]: value } as any),

  toggleModel: (name, size) => {
    const current = get().selectedModels;
    const exists = current.find(m => m.name === name && m.size === size);
    if (exists) {
      set({ selectedModels: current.filter(m => !(m.name === name && m.size === size)) });
    } else {
      set({ selectedModels: [...current, { name, size }] });
      // Initialize override for this model if not already
      if (!get().modelOverrides[name]) {
        set({ modelOverrides: { ...get().modelOverrides, [name]: defaultOverride() } });
      }
    }
  },

  loadVoice: (voice) => {
    set({
      loadedVoice: voice,
      prompt: voice.prompt || '',
      text: '',
      emotion: '',
      results: {},
      modelOverrides: {},
    });
    if (voice.params) {
      set({
        speed: voice.params.speed ?? 1.0,
        pitch: voice.params.pitch ?? 0,
        temperature: voice.params.temperature ?? 0.4,
        top_p: voice.params.top_p ?? 0.9,
      });
    }
  },

  setModelOverride: (modelName, key, value) => {
    const current = get().modelOverrides[modelName] || defaultOverride();
    set({
      modelOverrides: {
        ...get().modelOverrides,
        [modelName]: { ...current, [key]: value },
      },
    });
  },
}));
