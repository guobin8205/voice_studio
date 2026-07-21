import { useState, useRef, useEffect } from 'react';
import { useStore } from '../store';
import { api } from '../api/client';

interface SizeStatus {
  downloading: boolean;
  progress: number;
  status: string;
  phase?: string;
  phase_message?: string;
  error?: string | null;
}

export function ModelSelector() {
  const models = useStore(s => s.models);
  const selectedModels = useStore(s => s.selectedModels);
  const toggleModel = useStore(s => s.toggleModel);
  const [sizeStatus, setSizeStatus] = useState<Record<string, SizeStatus>>({});
  const [activeDownload, setActiveDownload] = useState<string | null>(null);
  const wsRefs = useRef<Record<string, WebSocket>>({});

  useEffect(() => {
    models.forEach(m => {
      api.getDownloadStatus(m.name).then((res: any) => {
        if (res.sizes) {
          const updates: Record<string, SizeStatus> = {};
          Object.entries(res.sizes).forEach(([sz, st]: [string, any]) => {
            updates[`${m.name}_${sz}`] = st;
          });
          setSizeStatus(prev => ({ ...prev, ...updates }));
        }
      }).catch(() => {});
    });
  }, [models]);

  useEffect(() => {
    return () => {
      Object.values(wsRefs.current).forEach(ws => { try { ws.close(); } catch {} });
    };
  }, []);

  const startDownload = (name: string, size: string) => {
    const key = `${name}_${size}`;
    if (activeDownload !== null) return;
    const current = sizeStatus[key];
    if (current?.downloading || current?.status === 'completed') return;

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
          <div key={m.name} className="border-2 border-gray-200 rounded-xl bg-gray-50/50 px-4 py-3 space-y-2">
            {/* 模型行 */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  if (isActive) toggleModel(m.name, activeSize!);
                  else toggleModel(m.name, m.sizes[0]);
                }}
                className={`w-5 h-5 rounded-md border-2 flex items-center justify-center text-xs transition-colors shrink-0 ${
                  isActive ? 'bg-violet-500 border-violet-500 text-white' : 'border-gray-300 text-transparent hover:border-violet-400'
                }`}
                aria-label={isActive ? '取消选择' : '选择此模型'}
              >
                ✓
              </button>
              <span className={`font-semibold text-[15px] ${isActive ? 'text-gray-900' : 'text-gray-700'}`}>
                {m.display_name}
              </span>
              <span className="ml-auto text-[10px] text-gray-400">
                {activeDownload && activeDownload.startsWith(m.name + '_') ? '下载中…' : ''}
              </span>
            </div>

            {/* Size 选择行 */}
            <div className="ml-8 flex flex-wrap items-center gap-2">
              {m.sizes.map(size => {
                const key = `${m.name}_${size}`;
                const st = sizeStatus[key];
                const isSelected = isActive && activeSize === size;
                const isDownloaded = st?.status === 'completed';
                const isDownloading = st?.downloading;
                const isFailed = st?.status === 'error';

                return (
                  <div key={size} className="flex items-center gap-1">
                    {/* Size pill - 点击切换选中 */}
                    <button
                      onClick={(e) => { e.stopPropagation(); toggleModel(m.name, size); }}
                      disabled={!isDownloaded && !isDownloading}
                      className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-colors ${
                        isSelected
                          ? 'bg-violet-500 text-white border-violet-500'
                          : isDownloaded
                            ? 'border-gray-200 text-gray-700 bg-white hover:border-violet-300 cursor-pointer'
                            : 'border-dashed border-gray-300 text-gray-400 bg-gray-50 cursor-not-allowed'
                      }`}
                      title={
                        isDownloading ? '下载中…' :
                        isFailed ? `下载失败: ${st?.error || ''}` :
                        !isDownloaded ? '未下载' :
                        isSelected ? '已选中，点击取消' : '已下载，点击选中'
                      }
                    >
                      {size}
                    </button>

                    {/* 下载状态指示 */}
                    {isDownloading && (
                      <span className="text-xs text-blue-500 font-mono">{st?.progress || 0}%</span>
                    )}
                    {isDownloaded && !isDownloading && (
                      <span className="text-xs text-green-500" title="已下载">✓</span>
                    )}
                    {isFailed && (
                      <span className="text-xs text-red-400" title={st?.error || '失败'}>⚠</span>
                    )}

                    {/* 下载按钮 */}
                    {!isDownloaded && !isDownloading && (
                      <button
                        onClick={(e) => { e.stopPropagation(); startDownload(m.name, size); }}
                        disabled={activeDownload !== null}
                        className={`text-sm px-1 transition-opacity ${
                          activeDownload !== null
                            ? 'text-gray-300 cursor-not-allowed opacity-50'
                            : 'text-violet-500 hover:text-violet-700'
                        }`}
                        title={activeDownload !== null ? '正在下载其他模型' : '下载此规格'}
                      >
                        📥
                      </button>
                    )}
                  </div>
                );
              })}
            </div>

            {/* 进度条 / 错误 */}
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
                      <div key={sz} className="space-y-0.5">
                        {st.phase_message && <div className="text-[11px] text-gray-500 truncate">{st.phase_message}</div>}
                        <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full transition-all duration-300 ${
                            st.phase === 'installing_package' ? 'bg-amber-500' : 'bg-blue-500'
                          }`} style={{ width: `${st.progress}%` }} />
                        </div>
                      </div>
                    );
                  }
                  if (st.status === 'error') {
                    return <div key={sz} className="text-[11px] text-red-400 truncate">{sz}: {st.error}</div>;
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
