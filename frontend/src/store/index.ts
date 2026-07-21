import { create } from 'zustand';
import type { ModelInfo, SystemStatus, GenerateResponse } from '../types';
import { api } from '../api/client';

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

  fetchModels: () => Promise<void>;
  fetchSystemStatus: () => Promise<void>;
  generate: () => Promise<void>;
  setInput: (key: string, value: string | number) => void;
  toggleModel: (name: string, size: string) => void;
}

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
      const resp = await api.generate({
        model: m.name, size: m.size,
        text: state.text, language: state.language,
        dialect: state.dialect, prompt: state.prompt,
        emotion: state.emotion,
        speed: state.speed, pitch: state.pitch,
        temperature: state.temperature, top_p: state.top_p,
      });
      results[`${m.name}_${m.size}`] = resp;
    }
    set({ results });
  },

  setInput: (key, value) => set({ [key]: value } as any),

  toggleModel: (name, size) => {
    const current = get().selectedModels;
    const exists = current.find(m => m.name === name && m.size === size);
    if (exists) {
      set({ selectedModels: current.filter(m => !(m.name === name && m.size === size)) });
    } else {
      set({ selectedModels: [...current, { name, size }] });
    }
  },
}));
