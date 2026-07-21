import { useEffect } from 'react';
import { useStore } from '../store';
import { ModelSelector } from '../components/ModelSelector';
import { ParamSliders } from '../components/ParamSliders';
import { OutputCard } from '../components/OutputCard';

export function VoiceDesign() {
  const { fetchModels, text, prompt, setInput, generate, results, selectedModels } = useStore();

  useEffect(() => { fetchModels(); }, []);

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
          {/* Left */}
          <div className="flex-1 space-y-5">
            <div className="flex gap-4">
              <div className="flex-1 space-y-1">
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">语言</label>
                <div className="border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 select-none">
                  中文 ▾
                </div>
              </div>
              <div className="flex-1 space-y-1">
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">方言</label>
                <div className="border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 select-none">
                  普通话 ▾
                </div>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                音色描述 <span className="font-normal normal-case text-gray-300">— 提示词，情绪融合其中</span>
              </label>
              <textarea
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 resize-none focus:outline-none focus:border-violet-500 focus:bg-white transition-colors"
                rows={4}
                placeholder="温柔知性的女声，像深夜电台主播，语速适中带着一点沙哑的质感..."
                value={prompt}
                onChange={e => setInput('prompt', e.target.value)}
              />
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
          </div>

          {/* Right */}
          <div className="flex-1 space-y-5">
            <ModelSelector />
            <button
              onClick={generate}
              disabled={selectedModels.length === 0 || !text}
              className="w-full py-3.5 rounded-xl bg-violet-500 hover:bg-violet-600 disabled:bg-gray-200 text-white font-semibold text-[15px] transition-colors"
            >
              🎤 生成对比（{selectedModels.length} 个模型）
            </button>

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
          </div>
        </div>
      </div>
    </div>
  );
}
