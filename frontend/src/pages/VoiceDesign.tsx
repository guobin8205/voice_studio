import { useEffect, useState } from 'react';
import { useStore } from '../store';
import { ModelSelector } from '../components/ModelSelector';
import { ParamSliders } from '../components/ParamSliders';
import { OutputCard } from '../components/OutputCard';
import { LanguageDialectSelect } from '../components/LanguageDialectSelect';

export function VoiceDesign() {
  const fetchModels = useStore(s => s.fetchModels);
  const text = useStore(s => s.text);
  const prompt = useStore(s => s.prompt);
  const setInput = useStore(s => s.setInput);
  const generate = useStore(s => s.generate);
  const saveVoice = useStore(s => s.saveVoice);
  const results = useStore(s => s.results);
  const selectedModels = useStore(s => s.selectedModels);
  const generating = useStore(s => s.generating);
  const generateProgress = useStore(s => s.generateProgress);
  const generateError = useStore(s => s.generateError);
  const [voiceName, setVoiceName] = useState('');

  useEffect(() => { fetchModels(); }, [fetchModels]);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-[28px] font-bold text-gray-900 tracking-tight">✨ 声音设计</h1>
        <p className="text-[15px] text-gray-400 mt-1.5 leading-relaxed">
          用自然语言描述你想要的说话者，选择模型即时试听对比，满意后保存为通用音色。
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 p-7 shadow-sm">
        <div className="flex gap-8">
          <div className="flex-1 space-y-5">
            <LanguageDialectSelect />

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                音色描述 <span className="font-normal normal-case text-gray-300">— 用自然语言描述说话者特征（性别/年龄/语调/情感）</span>
              </label>
              <textarea
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 resize-none focus:outline-none focus:border-violet-500 focus:bg-white transition-colors"
                rows={4}
                placeholder="例如：温柔知性的女声，像深夜电台主播，语速适中带着一点沙哑的质感&#10;或英文：a warm gentle female voice with a calm and soothing tone"
                value={prompt}
                onChange={e => setInput('prompt', e.target.value)}
              />
              <p className="text-[12px] text-gray-400 leading-relaxed">
                💡 <b>Qwen3-TTS</b>（VoiceDesign 模型）：凭描述创造全新音色，每次结果可能不同<br/>
                💡 <b>VoxCPM2</b>：纯自然语言描述生成全新音色（支持中英文），无需参考音频
              </p>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">合成文本</label>
              <textarea
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 resize-none focus:outline-none focus:border-violet-500 focus:bg-white transition-colors"
                rows={3}
                placeholder="输入要说的文本..."
                value={text}
                onChange={e => setInput('text', e.target.value)}
              />
            </div>

            <ParamSliders />

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
            <button
              onClick={generate}
              disabled={selectedModels.length === 0 || !text || generating}
              className="w-full py-3.5 rounded-xl bg-violet-500 hover:bg-violet-600 disabled:bg-gray-200 text-white font-semibold text-[15px] transition-colors"
            >
              {generating ? `⏳ ${generateProgress}` : `🎤 生成对比（${selectedModels.length} 个模型）`}
            </button>
            {generateError && (
              <div className="text-xs text-red-500 bg-red-50 p-2 rounded">❌ {generateError}</div>
            )}

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">生成结果</label>
              {selectedModels.map(m => (
                <OutputCard
                  key={`${m.name}_${m.size}`}
                  modelName={m.name}
                  size={m.size}
                  result={results[`${m.name}_${m.size}`]}
                />
              ))}
            </div>

            <p className="text-[13px] text-gray-400">
              💡 保存的是提示词，不是模型输出 — 通用音色，所有模型都能用。
            </p>
            {Object.keys(results).length > 0 && (
              <button
                onClick={async () => {
                  if (!voiceName.trim()) {
                    alert('请先输入音色名称');
                    return;
                  }
                  await saveVoice(voiceName.trim(), 'prompt');
                  alert(`音色「${voiceName.trim()}」已保存到音色库`);
                }}
                disabled={!voiceName.trim()}
                className="w-full py-3 rounded-xl bg-green-500 hover:bg-green-600 disabled:bg-gray-200 disabled:cursor-not-allowed text-white font-semibold text-[15px] transition-colors"
              >
                💾 保存当前音色到库
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
