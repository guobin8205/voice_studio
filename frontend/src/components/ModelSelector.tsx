import { useState } from 'react';
import { useStore } from '../store';
import { api } from '../api/client';

export function ModelSelector() {
  const models = useStore(s => s.models);
  const selectedModels = useStore(s => s.selectedModels);
  const toggleModel = useStore(s => s.toggleModel);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [downloaded, setDownloaded] = useState<Set<string>>(new Set());

  const startDownload = async (name: string) => {
    setDownloading(name);
    setDownloadProgress(0);
    try {
      // Start download
      await api.startDownload(name);

      // Poll progress via WebSocket
      const ws = api.downloadProgressWS(name);
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        setDownloadProgress(data.progress || 0);
        if (data.status === 'completed') {
          setDownloaded(prev => new Set(prev).add(name));
          setDownloading(null);
          ws.close();
        } else if (data.status === 'error') {
          setDownloading(null);
          ws.close();
          alert(`下载失败: ${data.error || '未知错误'}`);
        }
      };
    } catch (e: any) {
      setDownloading(null);
      alert(`下载启动失败: ${e.message}`);
    }
  };

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">选择模型对比</div>
      {models.map(m => {
        const isActive = selectedModels.some(sm => sm.name === m.name);
        const activeSize = selectedModels.find(sm => sm.name === m.name)?.size;
        const isDownloading = downloading === m.name;
        const isDownloaded = downloaded.has(m.name);

        return (
          <div key={m.name}>
            <div
              className={`flex items-center gap-3 px-4 py-3.5 border-2 rounded-xl cursor-pointer transition-colors ${
                isActive ? 'border-violet-500 bg-violet-50/50' : 'border-gray-200 bg-gray-50/50 hover:border-gray-300'
              }`}
            >
              <div
                onClick={() => toggleModel(m.name, m.sizes[0])}
                className={`w-5 h-5 rounded-md border-2 flex items-center justify-center text-xs transition-colors ${
                  isActive ? 'bg-violet-500 border-violet-500 text-white' : 'border-gray-300 text-transparent'
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
                      ? 'bg-violet-500 text-white border-violet-500'
                      : 'border-gray-200 text-gray-500 bg-white'
                  }`}
                >
                  {size}
                </span>
              ))}
              <div className="ml-auto">
                {isDownloaded ? (
                  <span className="text-xs text-green-500 font-medium">✓ 已下载</span>
                ) : isDownloading ? (
                  <span className="text-xs text-blue-500 font-medium">⏳ {downloadProgress}%</span>
                ) : (
                  <button
                    onClick={(e) => { e.stopPropagation(); startDownload(m.name); }}
                    className="text-xs text-violet-500 hover:text-violet-700 font-medium px-2 py-1 rounded-lg hover:bg-violet-50 transition-colors"
                  >
                    📥 下载模型
                  </button>
                )}
              </div>
            </div>
            {isDownloading && (
              <div className="mt-1 mx-4">
                <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full transition-all duration-300" style={{ width: `${downloadProgress}%` }} />
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
