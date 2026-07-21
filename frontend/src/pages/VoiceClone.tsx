import { useEffect, useState } from 'react';
import { useStore } from '../store';
import { ModelSelector } from '../components/ModelSelector';
import { ParamSliders } from '../components/ParamSliders';
import { OutputCard } from '../components/OutputCard';
import { LanguageDialectSelect } from '../components/LanguageDialectSelect';
import { AudioUpload } from '../components/AudioUpload';

export function VoiceClone() {
  const speed = useStore(s => s.speed);
  const pitch = useStore(s => s.pitch);
  const temperature = useStore(s => s.temperature);
  const topP = useStore(s => s.top_p);
  const setInput = useStore(s => s.setInput);
  const text = useStore(s => s.text);
  const emotion = useStore(s => s.emotion);
  const fetchModels = useStore(s => s.fetchModels);
  const clone = useStore(s => s.clone);
  const saveVoice = useStore(s => s.saveVoice);
  const results = useStore(s => s.results);
  const selectedModels = useStore(s => s.selectedModels);
  const generating = useStore(s => s.generating);
  const generateProgress = useStore(s => s.generateProgress);
  const generateError = useStore(s => s.generateError);
  const referenceAudioFile = useStore(s => s.referenceAudioFile);

  const [voiceName, setVoiceName] = useState('');

  useEffect(() => { fetchModels(); }, [fetchModels]);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-[28px] font-bold text-gray-900 tracking-tight">🎭 声音克隆</h1>
        <p className="text-[15px] text-gray-400 mt-1.5 leading-relaxed">
          上传一段参考音频，多模型同时提取音色特征并合成对比，满意后保存为可复用的通用音色。
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 p-7 shadow-sm">
        <div className="flex gap-8">
          <div className="flex-1 space-y-5">
            <LanguageDialectSelect />
            <AudioUpload onAsrResult={t => setInput('text', t)} />

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">合成文本</label>
              <textarea
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 resize-none focus:outline-none focus:border-violet-500 focus:bg-white transition-colors"
                rows={3}
                placeholder="输入要说的文本，或使用 ASR 自动填入..."
                value={text}
                onChange={e => setInput('text', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                情感 <span className="font-normal normal-case text-gray-300">— 可选</span>
              </label>
              <input
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 focus:outline-none focus:border-violet-500 focus:bg-white transition-colors"
                placeholder="留空则中性，如'平静中带着一丝严肃'..."
                value={emotion}
                onChange={e => setInput('emotion', e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                音色名称 <span className="font-normal normal-case text-gray-300">— 保存用</span>
              </label>
              <input
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 focus:outline-none focus:border-violet-500 focus:bg-white transition-colors"
                placeholder="给这个音色起个名字..."
                value={voiceName}
                onChange={e => setVoiceName(e.target.value)}
              />
            </div>
          </div>

          <div className="flex-1 space-y-5">
            <ModelSelector />
            <ParamSliders />
            <button
              onClick={clone}
              disabled={selectedModels.length === 0 || !text || generating || !referenceAudioFile}
              className="w-full py-3.5 rounded-xl bg-violet-500 hover:bg-violet-600 disabled:bg-gray-200 text-white font-semibold text-[15px] transition-colors"
            >
              {generating ? `⏳ ${generateProgress}` : `🎭 克隆对比（${selectedModels.length} 个模型）`}
            </button>
            {!referenceAudioFile && (
              <div className="text-xs text-amber-600">⚠️ 请先上传参考音频</div>
            )}
            {generateError && (
              <div className="text-xs text-red-500 bg-red-50 p-2 rounded">❌ {generateError}</div>
            )}

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">克隆结果</label>
              {selectedModels.map(m => (
                <OutputCard key={`${m.name}_${m.size}`} modelName={m.name} size={m.size} result={results[`${m.name}_${m.size}`]} />
              ))}
            </div>

            {Object.keys(results).length > 0 && (
              <button
                onClick={async () => {
                  const name = voiceName || '未命名克隆';
                  await saveVoice(name, 'clone');
                  alert(`克隆音色「${name}」已保存到音色库`);
                }}
                className="w-full py-3 rounded-xl bg-green-500 hover:bg-green-600 text-white font-semibold text-[15px] transition-colors"
              >
                💾 保存当前克隆到音色库
              </button>
            )}

            <p className="text-[13px] text-gray-400">
              💡 保存的是原始参考音频 — 所有模型可各自提取嵌入，通用复用。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
