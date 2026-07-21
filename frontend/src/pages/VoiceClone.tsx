import { useEffect } from 'react';
import { useStore } from '../store';
import { ModelSelector } from '../components/ModelSelector';
import { ParamSliders } from '../components/ParamSliders';
import { OutputCard } from '../components/OutputCard';

export function VoiceClone() {
  const { fetchModels, text, emotion, setInput, generate, results, selectedModels } = useStore();

  useEffect(() => { fetchModels(); }, []);

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
          {/* Left */}
          <div className="flex-1 space-y-5">
            <div className="flex gap-4">
              <div className="flex-1 space-y-1">
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">语言</label>
                <div className="border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 select-none">中文 ▾</div>
              </div>
              <div className="flex-1 space-y-1">
                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">方言</label>
                <div className="border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 select-none">普通话 ▾</div>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">参考音频</label>
              <div className="border-2 border-dashed border-gray-300 rounded-2xl p-8 bg-gray-50/50 text-center cursor-pointer hover:border-violet-400 transition-colors">
                <div className="text-3xl mb-2">📁</div>
                <div className="text-sm text-gray-500">拖拽音频到此处，或点击上传</div>
                <div className="text-xs text-gray-300 mt-1">支持 WAV / MP3 / FLAC，建议 3-15 秒</div>
              </div>
            </div>

            <div className="bg-green-50/50 border-2 border-green-200 rounded-xl p-3.5">
              <div className="flex justify-between text-xs mb-2">
                <span className="font-semibold text-green-700">📝 ASR 自动识别</span>
                <span className="text-gray-400 cursor-pointer">🔄 重新识别</span>
              </div>
              <textarea
                className="w-full border border-green-200 rounded-lg p-2 text-sm bg-white resize-none"
                rows={2}
                placeholder="上传音频后自动识别..."
              />
              <div className="text-xs text-violet-500 mt-1 cursor-pointer font-medium">📋 填入上方合成文本</div>
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
              />
            </div>
          </div>

          {/* Right */}
          <div className="flex-1 space-y-5">
            <ModelSelector />
            <ParamSliders />
            <button
              onClick={generate}
              disabled={selectedModels.length === 0 || !text}
              className="w-full py-3.5 rounded-xl bg-violet-500 hover:bg-violet-600 disabled:bg-gray-200 text-white font-semibold text-[15px] transition-colors"
            >
              🎭 克隆对比（{selectedModels.length} 个模型）
            </button>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">克隆结果</label>
              {selectedModels.map(m => (
                <OutputCard key={`${m.name}_${m.size}`} modelName={m.name} size={m.size} result={results[`${m.name}_${m.size}`]} />
              ))}
            </div>

            <p className="text-[13px] text-gray-400">
              💡 保存的是原始参考音频 — 所有模型可各自提取嵌入，通用复用。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
