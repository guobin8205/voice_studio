import { useEffect, useState } from 'react';
import { useStore } from '../store';
import { api } from '../api/client';
import type { VoiceRecord } from '../types';
import { OutputCard } from '../components/OutputCard';
import { LanguageDialectSelect } from '../components/LanguageDialectSelect';

const defaultOverride = { speed: 1.0, pitch: 0, temperature: 0.4, top_p: 0.9 };

const PARAM_LABELS: Record<string, string> = { speed: '语速', pitch: '音高', temperature: '温度', top_p: 'Top‑P' };
const PARAM_MIN: Record<string, number> = { speed: 0.5, pitch: -12, temperature: 0.1, top_p: 0.1 };
const PARAM_MAX: Record<string, number> = { speed: 2.0, pitch: 12, temperature: 1.0, top_p: 1.0 };
const PARAM_STEP: Record<string, number> = { speed: 0.1, pitch: 1, temperature: 0.1, top_p: 0.05 };

export function DebugConsole() {
  const fetchModels = useStore(s => s.fetchModels);
  const models = useStore(s => s.models);
  const selectedModels = useStore(s => s.selectedModels);
  const toggleModel = useStore(s => s.toggleModel);
  const text = useStore(s => s.text);
  const prompt = useStore(s => s.prompt);
  const emotion = useStore(s => s.emotion);
  const speed = useStore(s => s.speed);
  const pitch = useStore(s => s.pitch);
  const temperature = useStore(s => s.temperature);
  const topP = useStore(s => s.top_p);
  const setInput = useStore(s => s.setInput);
  const generate = useStore(s => s.generate);
  const results = useStore(s => s.results);
  const loadedVoice = useStore(s => s.loadedVoice);
  const loadVoice = useStore(s => s.loadVoice);
  const modelOverrides = useStore(s => s.modelOverrides);
  const setModelOverride = useStore(s => s.setModelOverride);
  const generating = useStore(s => s.generating);
  const generateProgress = useStore(s => s.generateProgress);
  const generateError = useStore(s => s.generateError);

  const [voices, setVoices] = useState<VoiceRecord[]>([]);
  const [voiceSearch, setVoiceSearch] = useState('');

  useEffect(() => { fetchModels(); }, [fetchModels]);

  useEffect(() => {
    api.listVoices(undefined, voiceSearch || undefined).then(setVoices).catch(() => {});
  }, [voiceSearch]);

  const globalParams = { speed, pitch, temperature, top_p: topP };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-[28px] font-bold text-gray-900 tracking-tight">🔬 调试台</h1>
        <p className="text-[15px] text-gray-400 mt-1.5 leading-relaxed">
          从音色库加载音色，为每个模型独立配置参数，一键横向对比输出效果。
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 p-7 shadow-sm">
        <div className="flex gap-8">
          <div className="flex-1 space-y-5">
            {/* Voice Loader */}
            <div className="bg-amber-50/50 border-2 border-amber-200 rounded-xl p-4">
              <label className="text-xs font-semibold text-amber-700 uppercase tracking-wide">🎙️ 从音色库加载</label>
              <input
                className="w-full mt-2 border-2 border-amber-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-amber-400"
                placeholder="搜索音色..."
                value={voiceSearch}
                onChange={e => setVoiceSearch(e.target.value)}
              />
              {voices.length > 0 && (
                <div className="mt-2 space-y-1 max-h-32 overflow-y-auto">
                  {voices.slice(0, 8).map(v => (
                    <div
                      key={v.id}
                      onClick={() => { loadVoice(v); setVoiceSearch(''); }}
                      className={`px-3 py-1.5 rounded-lg text-sm cursor-pointer transition-colors ${
                        loadedVoice?.id === v.id ? 'bg-amber-100 text-amber-800 font-semibold' : 'hover:bg-amber-50 text-gray-700'
                      }`}
                    >
                      {v.type === 'prompt' ? '🎙️' : '🎭'} {v.name}
                      <span className="text-xs text-gray-400 ml-2">{v.type === 'prompt' ? '提示词' : '克隆'}</span>
                    </div>
                  ))}
                </div>
              )}
              {loadedVoice && (
                <div className="mt-2 text-xs text-amber-600">
                  已加载：{loadedVoice.name} · {loadedVoice.type === 'prompt' ? '提示词音色' : '克隆音色'}
                </div>
              )}
            </div>

            <LanguageDialectSelect />

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">情感</label>
              <input
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 focus:outline-none focus:border-amber-500 transition-colors"
                placeholder="留空则中性..."
                value={emotion}
                onChange={e => setInput('emotion', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">合成文本</label>
              <textarea
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 resize-none focus:outline-none focus:border-amber-500 transition-colors"
                rows={3}
                value={text}
                onChange={e => setInput('text', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                音色描述 <span className="font-normal normal-case text-gray-300">— 自动填充，可修改</span>
              </label>
              <textarea
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 resize-none focus:outline-none focus:border-amber-500 transition-colors"
                rows={2}
                value={prompt}
                onChange={e => setInput('prompt', e.target.value)}
              />
            </div>

            {/* Global params - 真实滑块 */}
            <div className="space-y-3">
              <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">全局参数</div>
              {(['speed', 'pitch', 'temperature', 'top_p'] as const).map(k => {
                const val = globalParams[k];
                const pct = ((val - PARAM_MIN[k]) / (PARAM_MAX[k] - PARAM_MIN[k])) * 100;
                return (
                  <div key={k} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[13px] text-gray-500 font-medium">{PARAM_LABELS[k]}</span>
                      <span className="text-[13px] font-semibold text-gray-900">{val}</span>
                    </div>
                    <input
                      type="range"
                      min={PARAM_MIN[k]}
                      max={PARAM_MAX[k]}
                      step={PARAM_STEP[k]}
                      value={val}
                      onChange={e => setInput(k, parseFloat(e.target.value))}
                      className="w-full accent-amber-500"
                      style={{ background: `linear-gradient(to right, #f59e0b ${pct}%, #e5e7eb ${pct}%)`, height: '6px', borderRadius: '3px', appearance: 'none' }}
                    />
                  </div>
                );
              })}
            </div>
          </div>

          <div className="flex-1 space-y-4">
            <div className="space-y-2">
              <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                选择模型 <span className="font-normal normal-case text-gray-300">— 可多选 · 独立参数覆盖</span>
              </div>
              {models.map(m => {
                const activeEntry = selectedModels.find(sm => sm.name === m.name);
                const isActive = !!activeEntry;
                const activeSize = activeEntry?.size;
                const ov = modelOverrides[m.name] || defaultOverride;
                const hasOverride = modelOverrides[m.name] && (
                  ov.speed !== speed || ov.pitch !== pitch || ov.temperature !== temperature || ov.top_p !== topP
                );

                return (
                  <div key={m.name}>
                    <div
                      className={`flex items-center gap-3 px-4 py-3.5 border-2 rounded-xl cursor-pointer transition-colors ${
                        isActive ? 'border-amber-500 bg-amber-50/30' : 'border-gray-200 bg-gray-50/50 hover:border-gray-300'
                      }`}
                      onClick={() => {
                        // 修复：如果已激活就移除整个模型，否则添加 sizes[0]
                        if (isActive) {
                          toggleModel(m.name, activeSize!);
                        } else {
                          toggleModel(m.name, m.sizes[0]);
                        }
                      }}
                    >
                      <div
                        className={`w-5 h-5 rounded-md border-2 flex items-center justify-center text-xs transition-colors ${
                          isActive ? 'bg-amber-500 border-amber-500 text-white' : 'border-gray-300 text-transparent'
                        }`}
                      >
                        ✓
                      </div>
                      <span className={`font-semibold text-[15px] ${isActive ? 'text-gray-900' : 'text-gray-400'}`}>
                        {m.display_name}
                      </span>
                      {m.sizes.map(size => (
                        <span
                          key={size}
                          onClick={(e) => { e.stopPropagation(); toggleModel(m.name, size); }}
                          className={`text-xs px-3 py-1.5 rounded-full border font-medium cursor-pointer ${
                            isActive && activeSize === size
                              ? 'bg-amber-500 text-white border-amber-500'
                              : 'border-gray-200 text-gray-500 bg-white'
                          }`}
                        >
                          {size}
                        </span>
                      ))}
                      {isActive && (
                        <span className="ml-auto text-xs text-amber-600 font-medium">
                          {hasOverride ? '⚙️ 已覆盖' : '默认参数'}
                        </span>
                      )}
                    </div>

                    {/* 每模型独立参数 - 真实可交互滑块 */}
                    {isActive && (
                      <div className="ml-8 mt-2 p-3 bg-amber-50/30 rounded-lg border border-amber-100 space-y-2">
                        <div className="text-[11px] font-semibold text-amber-700 mb-1">覆盖 {m.display_name} 参数</div>
                        {(['speed', 'pitch', 'temperature', 'top_p'] as const).map(k => {
                          const val = ov[k];
                          const pct = ((val - PARAM_MIN[k]) / (PARAM_MAX[k] - PARAM_MIN[k])) * 100;
                          return (
                            <div key={k} className="space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="text-[11px] text-gray-500">{PARAM_LABELS[k]}</span>
                                <span className="text-[11px] font-semibold text-gray-700">{val}</span>
                              </div>
                              <input
                                type="range"
                                min={PARAM_MIN[k]}
                                max={PARAM_MAX[k]}
                                step={PARAM_STEP[k]}
                                value={val}
                                onChange={e => setModelOverride(m.name, k, parseFloat(e.target.value))}
                                className="w-full accent-amber-500"
                                style={{ background: `linear-gradient(to right, #fbbf24 ${pct}%, #fde68a ${pct}%)`, height: '4px', borderRadius: '2px', appearance: 'none' }}
                              />
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <button
              onClick={generate}
              disabled={selectedModels.length === 0 || !text || generating}
              className="w-full py-3.5 rounded-xl bg-amber-500 hover:bg-amber-600 disabled:bg-gray-200 text-white font-semibold text-[15px] transition-colors"
            >
              {generating ? `⏳ ${generateProgress}` : `🚀 生成对比（${selectedModels.length} 个模型）`}
            </button>
            {generateError && (
              <div className="text-xs text-red-500 bg-red-50 p-2 rounded">❌ {generateError}</div>
            )}

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">📊 输出对比</label>
              {selectedModels.map(m => {
                const ov = modelOverrides[m.name];
                const hasOverride = !!ov && (
                  ov.speed !== speed || ov.pitch !== pitch || ov.temperature !== temperature || ov.top_p !== topP
                );
                return (
                  <OutputCard
                    key={`${m.name}_${m.size}`}
                    modelName={m.name}
                    size={m.size}
                    result={results[`${m.name}_${m.size}`]}
                    paramNote={hasOverride ? `T=${ov!.temperature}（覆盖）` : '默认参数'}
                  />
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
