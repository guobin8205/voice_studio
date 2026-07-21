import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store';
import { api } from '../api/client';

interface DownloadState {
  downloading: boolean;
  progress: number;
  status: string;
  phase?: string;
  phase_message?: string;
  error: string | null;
}

export function ModelSelector() {
  const models = useStore(s => s.models);
  const selectedModels = useStore(s => s.selectedModels);
  const toggleModel = useStore(s => s.toggleModel);
  const [downloads, setDownloads] = useState<Record<string, DownloadState>>({});
  const wsRefs = useRef<Record<string, WebSocket>>({});

  // 检查已下载状态（一次性）
  useEffect(() => {
    models.forEach(m => {
      api.getDownloadStatus(m.name).then(s => {
        if (s.status === 'completed') {
          setDownloads(prev => ({ ...prev, [m.name]: { downloading: false, progress: 100, status: 'completed', error: null } }));
        }
      }).catch(() => {});
    });
  }, [models]);

  // 清理 WebSocket
  useEffect(() => {
    return () => {
      Object.values(wsRefs.current).forEach(ws => {
        try { ws.close(); } catch {}
      });
    };
  }, []);

  const startDownload = (name: string) => {
    setDownloads(prev => ({ ...prev, [name]: { downloading: true, progress: 0, status: 'downloading', error: null } }));
    api.startDownload(name).then(() => {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${proto}//${window.location.host}/api/models/${name}/download-progress`);
      wsRefs.current[name] = ws;
      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          setDownloads(prev => ({ ...prev, [name]: data }));
          if (data.status === 'completed' || data.status === 'error') {
            ws.close();
            delete wsRefs.current[name];
          }
        } catch {}
      };
      ws.onerror = () => {
        setDownloads(prev => ({ ...prev, [name]: { downloading: false, progress: 0, status: 'error', error: 'WebSocket 连接失败' } }));
      };
    }).catch(err => {
      setDownloads(prev => ({ ...prev, [name]: { downloading: false, progress: 0, status: 'error', error: err.message } }));
    });
  };

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">选择模型对比</div>
      {models.map(m => {
        const activeEntry = selectedModels.find(sm => sm.name === m.name);
        const isActive = !!activeEntry;
        const activeSize = activeEntry?.size;
        const dl = downloads[m.name];

        return (
          <div key={m.name}>
            <div
              className={`flex items-center gap-3 px-4 py-3.5 border-2 rounded-xl cursor-pointer transition-colors ${
                isActive ? 'border-violet-500 bg-violet-50/50' : 'border-gray-200 bg-gray-50/50 hover:border-gray-300'
              }`}
              onClick={() => {
                // 修复：已激活就移除该模型的所有 size，否则添加 sizes[0]
                if (isActive) {
                  toggleModel(m.name, activeSize!);
                } else {
                  toggleModel(m.name, m.sizes[0]);
                }
              }}
            >
              <div
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
                {dl?.status === 'completed' ? (
                  <span className="text-xs text-green-500 font-medium">✓ 已就绪</span>
                ) : dl?.downloading ? (
                  <span className="text-xs text-blue-500 font-medium">
                    {dl.phase === 'installing_package' ? '📦 安装包' : '⏳'} {dl.progress}%
                  </span>
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
            {dl?.downloading && (
              <div className="mt-1 mx-4">
                {dl.phase_message && (
                  <div className="text-xs text-gray-500 mb-1">{dl.phase_message}</div>
                )}
                <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      dl.phase === 'installing_package' ? 'bg-amber-500' : 'bg-blue-500'
                    }`}
                    style={{ width: `${dl.progress}%` }}
                  />
                </div>
              </div>
            )}
            {dl?.status === 'error' && dl.error && (
              <div className="mt-1 mx-4 text-xs text-red-400">⚠️ {dl.error}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}
