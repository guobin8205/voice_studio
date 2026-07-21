import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store';
import { api } from '../api/client';

interface SizeStatus {
  downloading: boolean;
  progress: number;
  status: string;  // not_started | downloading | completed | error
  phase?: string;
  phase_message?: string;
  error?: string | null;
}

export function ModelSelector() {
  const models = useStore(s => s.models);
  const selectedModels = useStore(s => s.selectedModels);
  const toggleModel = useStore(s => s.toggleModel);
  // 每个 size 的下载状态: key = "name_size"
  const [sizeStatus, setSizeStatus] = useState<Record<string, SizeStatus>>({});
  const [activeDownload, setActiveDownload] = useState<string | null>(null);
  const wsRefs = useRef<Record<string, WebSocket>>({});

  // 启动时拉一次状态
  useEffect(() => {
    models.forEach(m => {
      api.getDownloadStatus(m.name).then((res: any) => {
        if (res.sizes) {
          // 新版接口返回所有 size 的状态
          const updates: Record<string, SizeStatus> = {};
          Object.entries(res.sizes).forEach(([sz, st]: [string, any]) => {
            updates[`${m.name}_${sz}`] = st;
          });
          setSizeStatus(prev => ({ ...prev, ...updates }));
        } else if (res.status === 'completed') {
          // 旧版兼容
          setSizeStatus(prev => ({ ...prev, [m.name]: res }));
        }
      }).catch(() => {});
    });
  }, [models]);

  // 卸载时关 ws
  useEffect(() => {
    return () => {
      Object.values(wsRefs.current).forEach(ws => { try { ws.close(); } catch {} });
    };
  }, []);

  const startDownload = (name: string, size: string) => {
    const key = `${name}_${size}`;
    setActiveDownload(key);
    setSizeStatus(prev => ({ ...prev, [key]: { downloading: true, progress: 0, status: 'downloading' } }));
    api.startDownload(name, size).then(() => {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${proto}//${window.location.host}/api/models/${name}/download-progress?size=${encodeURIComponent(size)}`);
      wsRefs.current[key] = ws;
      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          setSizeStatus(prev => ({ ...prev, [key]: data }));
          if (data.status === 'completed' || data.status === 'error') {
            ws.close();
            delete wsRefs.current[key];
            setActiveDownload(null);
          }
        } catch {}
      };
      ws.onerror = () => { setActiveDownload(null); };
    }).catch(() => { setActiveDownload(null); });
  };

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">选择模型对比</div>
      {models.map(m => {
        const activeEntry = selectedModels.find(sm => sm.name === m.name);
        const isActive = !!activeEntry;
        const activeSize = activeEntry?.size;

        return (
          <div key={m.name} className="border-2 border-gray-200 rounded-xl bg-gray-50/50 px-4 py-3.5 space-y-2">
            {/* 模型名 + 主 checkbox */}
            <div className="flex items-center gap-3">
              <div
                onClick={() => {
                  if (isActive) toggleModel(m.name, activeSize!);
                  else toggleModel(m.name, m.sizes[0]);
                }}
                className={`w-5 h-5 rounded-md border-2 flex items-center justify-center text-xs cursor-pointer transition-colors ${
                  isActive ? 'bg-violet-500 border-violet-500 text-white' : 'border-gray-300 text-transparent'
                }`}
              >
                ✓
              </div>
              <span className={`font-semibold text-[15px] ${isActive ? 'text-gray-900' : 'text-gray-400'}`}>
                {m.display_name}
              </span>
            </div>

            {/* 每个 size 一行，带自己的下载状态 */}
            <div className="ml-8 flex flex-wrap gap-2">
              {m.sizes.map(size => {
                const key = `${m.name}_${size}`;
                const st = sizeStatus[key];
                const selected = isActive && activeSize === size;
                const downloaded = st?.status === 'completed';
                const downloading = st?.downloading;
                const failed = st?.status === 'error';

                return (
                  <div key={size} className="flex items-center gap-1">
                    <span
                      onClick={(e) => { e.stopPropagation(); toggleModel(m.name, size); }}
                      className={`text-xs px-3 py-1.5 rounded-full border font-medium cursor-pointer ${
                        selected
                          ? 'bg-violet-500 text-white border-violet-500'
                          : 'border-gray-200 text-gray-500 bg-white hover:border-violet-300'
                      }`}
                      title={downloaded ? '已下载' : downloading ? '下载中' : failed ? '下载失败' : '未下载'}
                    >
                      {size}
                      {downloaded && <span className="ml-1">✓</span>}
                      {failed && <span className="ml-1 text-red-400">⚠</span>}
                    </span>

                    {/* 下载按钮：只在未下载且未下载中时显示 */}
                    {!downloaded && !downloading && (
                      <button
                        onClick={(e) => { e.stopPropagation(); startDownload(m.name, size); }}
                        disabled={activeDownload !== null}
                        className="text-xs text-violet-500 hover:text-violet-700 disabled:text-gray-300 px-1"
                        title={failed ? `失败: ${st?.error || ''}` : '下载此规格'}
                      >
                        📥
                      </button>
                    )}
                    {downloading && (
                      <span className="text-xs text-blue-500">
                        {st?.phase === 'installing_package' ? '📦' : '⏳'} {st?.progress || 0}%
                      </span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* 进度条 / 错误信息 */}
            {m.sizes.some(sz => {
              const st = sizeStatus[`${m.name}_${sz}`];
              return st?.downloading || st?.status === 'error';
            }) && (
              <div className="ml-8 space-y-1">
                {m.sizes.map(sz => {
                  const st = sizeStatus[`${m.name}_${sz}`];
                  if (!st) return null;
                  if (st.downloading) {
                    return (
                      <div key={sz}>
                        {st.phase_message && <div className="text-xs text-gray-500">{st.phase_message}</div>}
                        <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full transition-all duration-300 ${
                            st.phase === 'installing_package' ? 'bg-amber-500' : 'bg-blue-500'
                          }`} style={{ width: `${st.progress}%` }} />
                        </div>
                      </div>
                    );
                  }
                  if (st.status === 'error') {
                    return <div key={sz} className="text-xs text-red-400">{sz}: ⚠ {st.error}</div>;
                  }
                  return null;
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
