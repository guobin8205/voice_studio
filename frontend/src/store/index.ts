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
  generating: boolean;
  generateProgress: string;
  generateError: string | null;

  // 克隆相关
  referenceAudioFile: File | null;
  referenceAudioPath: string | null;

  // Phase 3: debug console
  loadedVoice: VoiceRecord | null;
  modelOverrides: Record<string, ModelOverride>;

  fetchModels: () => Promise<void>;
  fetchSystemStatus: () => Promise<void>;
  generate: () => Promise<void>;
  clone: () => Promise<void>;
  setReferenceAudio: (file: File | null, path: string | null) => void;
  saveVoice: (name: string, type: 'prompt' | 'clone') => Promise<void>;
  setInput: (key: string, value: string | number) => void;
  toggleModel: (name: string, size: string) => void;
  loadVoice: (voice: VoiceRecord) => void;
  setModelOverride: (modelName: string, key: keyof ModelOverride, value: number) => void;
}

const defaultOverride = (): ModelOverride => ({ speed: 1.0, pitch: 0, temperature: 0.4, top_p: 0.9 });

export const useStore = create<AppState>((set, get) => ({
  models: [],
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
  generating: false,
  generateProgress: '',
  generateError: null,
  referenceAudioFile: null,
  referenceAudioPath: null,
  loadedVoice: null,
  modelOverrides: {},

  fetchModels: async () => {
    try {
      const models = await api.getModels();
      set({ models });
      if (get().selectedModels.length === 0 && models.length > 0) {
        set({ selectedModels: [{ name: models[0].name, size: models[0].sizes[0] }] });
      }
    } catch (e) {
      console.warn('Failed to fetch models:', e);
    }
  },

  fetchSystemStatus: async () => {
    try {
      const status = await api.getSystemStatus();
      set({ systemStatus: status });
    } catch (e) {
      console.warn('Failed to fetch system status:', e);
    }
  },

  generate: async () => {
    const state = get();
    set({ generating: true, generateProgress: '', generateError: null, results: {} });
    const results: Record<string, GenerateResponse> = {};

    try {
      for (let i = 0; i < state.selectedModels.length; i++) {
        const m = state.selectedModels[i];
        set({ generateProgress: `正在生成 ${m.name} (${i + 1}/${state.selectedModels.length})...` });
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
      set({ results, generateProgress: '生成完成' });
    } catch (e: any) {
      set({ generateError: e.message || String(e), generateProgress: `❌ 生成失败: ${e.message || e}` });
    } finally {
      set({ generating: false });
    }
  },

  clone: async () => {
    const state = get();
    if (!state.referenceAudioFile) {
      set({ generateError: '请先上传参考音频' });
      return;
    }
    set({ generating: true, generateProgress: '', generateError: null, results: {} });
    const results: Record<string, GenerateResponse> = {};

    try {
      for (let i = 0; i < state.selectedModels.length; i++) {
        const m = state.selectedModels[i];
        set({ generateProgress: `正在克隆 ${m.name} (${i + 1}/${state.selectedModels.length})...` });
        const ov = state.modelOverrides[m.name] || defaultOverride();
        const resp = await api.clone(state.referenceAudioFile, {
          model: m.name, size: m.size,
          text: state.text, language: state.language,
          dialect: state.dialect, emotion: state.emotion,
          speed: ov.speed, pitch: ov.pitch, temperature: ov.temperature,
        });
        results[`${m.name}_${m.size}`] = resp;
      }
      set({ results, generateProgress: '克隆完成' });
    } catch (e: any) {
      set({ generateError: e.message || String(e), generateProgress: `❌ 克隆失败: ${e.message || e}` });
    } finally {
      set({ generating: false });
    }
  },

  setReferenceAudio: (file, path) => set({ referenceAudioFile: file, referenceAudioPath: path }),

  saveVoice: async (name, type) => {
    const state = get();
    await api.createVoice({
      name,
      type,
      prompt: type === 'prompt' ? state.prompt : undefined,
      reference_audio: type === 'clone' ? state.referenceAudioPath || undefined : undefined,
      params: {
        speed: state.speed,
        pitch: state.pitch,
        temperature: state.temperature,
        top_p: state.top_p,
      },
    });
  },

  setInput: (key, value) => set({ [key]: value } as Partial<AppState> as any),

  toggleModel: (name, size) => {
    const current = get().selectedModels;
    const exists = current.find(m => m.name === name && m.size === size);
    if (exists) {
      set({ selectedModels: current.filter(m => !(m.name === name && m.size === size)) });
    } else {
      set({ selectedModels: [...current, { name, size }] });
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
      generateError: null,
      referenceAudioPath: voice.reference_audio || null,
      referenceAudioFile: null,
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
