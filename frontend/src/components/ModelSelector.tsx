import { useState, useEffect, useRef } from 'react';
import { useStore } from '../store';
import { api } from '../api/client';

interface DownloadState {
  downloading: boolean;
  progress: number;
  status: string;
  error: string | null;
}

export function ModelSelector() {
  const models = useStore(s => s.models);
  const selectedModels = useStore(s => s.selectedModels);
  const toggleModel = useStore(s => s.toggleModel);
  const [downloads, setDownloads] = useState<Record<string, DownloadState>>({});
  const wsRefs = useRef<Record<string, WebSocket>>({});

  // Poll download status on mount
  useEffect(() => {
    models.forEach(m => {
      api.getDownloadStatus(m.name).then(s => {
        setDownloads(prev => ({ ...prev, [m.name]: s }));
      });
    });
  }, [models]);

  const startDownload = (name: string) => {
    setDownloads(prev => ({ ...prev, [name]: { downloading: true, progress: 0, status: 'downloading', error: null } }));
    api.startDownload(name).then(() => {
      // Connect WebSocket for progress
      const ws = api.downloadProgressWS(name);
      wsRefs.current[name] = ws;
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        setDownloads(prev => ({ ...prev, [name]: data }));
        if (data.status === 'completed' || data.status === 'error') {
          ws.close();
        }
      };
    }).catch(err => {
      setDownloads(prev => ({ ...prev, [name]: { downloading: false, progress: 0, status: 'error', error: err.message } }));
    });
  };

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">选择模型对比</div>
      {models.map(m => {
        const isActive = selectedModels.some(sm => sm.name === m.name);
        const activeSize = selectedModels.find(sm => sm.name === m.name)?.size;
        const dl = downloads[m.name];

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
              <div className="ml-auto flex items-center gap-2">
                {dl?.status === 'completed' ? (
                  <span className="text-xs text-green-500 font-medium">✓ 已下载</span>
                ) : dl?.downloading ? (
                  <span className="text-xs text-blue-500 font-medium">下载中 {dl.progress}%</span>
                ) : (
                  <button
                    onClick={(e) => { e.stopPropagation(); startDownload(m.name); }}
                    className="text-xs text-violet-500 hover:text-violet-700 font-medium px-2 py-1 rounded-lg hover:bg-violet-50 transition-colors"
                  >
                    📥 下载
                  </button>
                )}
                {dl?.status === 'error' && (
                  <span className="text-xs text-red-400" title={dl.error || ''}>⚠️</span>
                )}
              </div>
            </div>
            {/* Progress bar */}
            {dl?.downloading && (
              <div className="mt-1 mx-4">
                <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all duration-300"
                    style={{ width: `${dl.progress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
