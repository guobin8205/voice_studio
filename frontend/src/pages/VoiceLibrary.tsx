import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../store';
import { api } from '../api/client';
import type { VoiceRecord } from '../types';

export function VoiceLibrary() {
  const [voices, setVoices] = useState<VoiceRecord[]>([]);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [error, setError] = useState<string | null>(null);
  const fetchModels = useStore(s => s.fetchModels);
  const loadVoice = useStore(s => s.loadVoice);
  const navigate = useNavigate();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  const loadVoices = (s: string, t: string) => {
    api.listVoices(t || undefined, s || undefined)
      .then(data => { setVoices(data); setError(null); })
      .catch(e => { setError(e.message || '加载失败'); setVoices([]); });
  };

  useEffect(() => { fetchModels(); loadVoices('', ''); }, [fetchModels]);

  // 防抖搜索
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => loadVoices(search, typeFilter), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [search, typeFilter]);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-[28px] font-bold text-gray-900 tracking-tight">📚 音色库</h1>
        <p className="text-[15px] text-gray-400 mt-1.5 leading-relaxed">
          所有音色均为通用资产，不绑定特定模型。可搜索筛选，一键加载到调试台，导出为生产包。
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-100 p-7 shadow-sm">
        <div className="flex gap-3 mb-5">
          <input
            className="flex-1 border-2 border-gray-200 rounded-xl px-4 py-3 text-[15px] bg-gray-50/50 focus:outline-none focus:border-violet-500 transition-colors"
            placeholder="🔍 搜索音色名称、描述..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <select
            className="border-2 border-gray-200 rounded-xl px-4 py-3 text-sm bg-gray-50/50 text-gray-500 cursor-pointer"
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value)}
          >
            <option value="">全部类型</option>
            <option value="prompt">提示词</option>
            <option value="clone">克隆</option>
          </select>
        </div>

        {error && <div className="text-xs text-red-500 bg-red-50 p-2 rounded mb-3">❌ {error}</div>}

        <div className="space-y-3">
          {voices.length === 0 && !error && (
            <div className="text-center text-gray-300 py-12 text-sm">暂无音色，去声音设计或声音克隆创建吧</div>
          )}
          {voices.map(v => (
            <div
              key={v.id}
              className="border border-gray-100 rounded-2xl p-5 flex gap-4 items-center hover:border-gray-200 transition-colors"
            >
              <div className={`w-11 h-11 rounded-full flex items-center justify-center text-xl shrink-0 ${v.type === 'prompt' ? 'bg-violet-50' : 'bg-pink-50'}`}>
                {v.type === 'prompt' ? '🎙️' : '🎭'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[15px] font-semibold text-gray-900">{v.name}</div>
                <div className="text-[13px] text-gray-400 mt-0.5">
                  {v.type === 'prompt' ? `📝 ${v.prompt || ''}` : `📁 ${v.reference_audio?.split(/[\\/]/).pop() || ''}`}
                </div>
                <div className="text-xs text-green-600 mt-1 font-medium">
                  {v.type === 'prompt'
                    ? '✓ 通用 · 所有模型可用'
                    : v.embeddings
                      ? `🧬 嵌入缓存：${Object.entries(v.embeddings).filter(([, p]) => p).map(([k]) => k).join(' · ') || '未提取'}`
                      : '🧬 嵌入未提取'}
                </div>
              </div>
              <span className={`text-[11px] font-semibold px-3 py-1.5 rounded-full ${v.type === 'prompt' ? 'bg-violet-50 text-violet-600' : 'bg-pink-50 text-pink-600'}`}>
                {v.type === 'prompt' ? '提示词' : '克隆'}
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => { loadVoice(v); navigate('/debug'); }}
                  className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-violet-50 text-violet-600 hover:bg-violet-100 transition-colors"
                >
                  🔬 加载调试
                </button>
                <a
                  href={`/api/voices/${v.id}/export`}
                  className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-gray-50 text-sm"
                  title="导出"
                  download
                >
                  📦
                </a>
                <button
                  onClick={async () => {
                    if (confirm(`删除音色「${v.name}」？`)) {
                      try {
                        await api.deleteVoice(v.id);
                        loadVoices(search, typeFilter);
                      } catch (e: any) {
                        alert(`删除失败: ${e.message}`);
                      }
                    }
                  }}
                  className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-gray-50 text-sm"
                  title="删除"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>

        {voices.length > 0 && (
          <div className="text-[13px] text-gray-400 text-center mt-5 pt-4 border-t border-gray-50">
            共 {voices.length} 个音色
          </div>
        )}
      </div>
    </div>
  );
}
