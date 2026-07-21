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
  // 记录已经自动选中的 size，避免重复触发
  const autoSelectedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    models.forEach(m => {
      api.getDownloadStatus(m.name).then((res: any) => {
        if (res.sizes) {
          const updates: Record<string, SizeStatus> = {};
          let firstDownloaded: string | null = null;
          Object.entries(res.sizes).forEach(([sz, st]: [string, any]) => {
            const key = `${m.name}_${sz}`;
            updates[key] = st;
            // 记录第一个已下载的 size（用于自动选中）
            if (st.status === 'completed' && !firstDownloaded) {
              firstDownloaded = sz;
            }
          });
          setSizeStatus(prev => ({ ...prev, ...updates }));
          // 如果当前没有选中任何模型，自动选第一个已下载的
          if (firstDownloaded && selectedModels.length === 0) {
            const key = `${m.name}_${firstDownloaded}`;
            if (!autoSelectedRef.current.has(key)) {
              autoSelectedRef.current.add(key);
              toggleModel(m.name, firstDownloaded);
            }
          }
        }
      }).catch(() => {});
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
          // 下载完成自动选中
          if (data.status === 'completed') {
            // 异步触发，避免在 ws 回调里更新 store 引起警告
            setTimeout(() => {
              if (!autoSelectedRef.current.has(key)) {
                autoSelectedRef.current.add(key);
                toggleModel(name, size);
              }
            }, 0);
          }
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
        const isDisabled = (m as any).disabled === true;
        // 同模型可能有多个 size 被选中（多选对比）
        const selectedEntries = selectedModels.filter(sm => sm.name === m.name);
        const isActive = selectedEntries.length > 0;
        const firstSelectedSize = selectedEntries[0]?.size;

        return (
          <div key={m.name} className={`border-2 rounded-xl px-4 py-3 space-y-2 ${
            isDisabled ? 'border-gray-200 bg-gray-100/50 opacity-60' : 'border-gray-200 bg-gray-50/50'
          }`}>
            {/* 模型行 */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  if (isDisabled) return;
                  if (isActive) {
                    selectedEntries.forEach(e => toggleModel(m.name, e.size));
                  } else {
                    toggleModel(m.name, m.sizes[0]);
                  }
                }}
                disabled={isDisabled}
                className={`w-5 h-5 rounded-md border-2 flex items-center justify-center text-xs transition-colors shrink-0 ${
                  isActive ? 'bg-violet-500 border-violet-500 text-white'
                  : isDisabled ? 'border-gray-200 text-transparent cursor-not-allowed'
                  : 'border-gray-300 text-transparent hover:border-violet-400 cursor-pointer'
                }`}
                aria-label={isActive ? '取消所有选择' : isDisabled ? '不可用' : '选择此模型'}
              >
                ✓
              </button>
              <span className={`font-semibold text-[15px] ${isActive ? 'text-gray-900' : isDisabled ? 'text-gray-400' : 'text-gray-700'}`}>
                {m.display_name}
              </span>
              {isDisabled && (
                <span className="text-[10px] text-gray-400 ml-1">（暂不可用）</span>
              )}
              {isActive && selectedEntries.length > 1 && (
                <span className="text-[10px] text-violet-500 ml-1">已选 {selectedEntries.length} 个规格</span>
              )}
              <span className="ml-auto text-[10px] text-gray-400">
                {activeDownload && activeDownload.startsWith(m.name + '_') ? '下载中…' : ''}
              </span>
            </div>

            {isDisabled && (
              <div className="ml-8 text-[11px] text-gray-400">
                此模型暂不兼容当前环境，可手动从 <a className="text-violet-400 underline" href="https://github.com/index-tts/index-tts" target="_blank" rel="noreferrer">github.com/index-tts</a> 单独部署
              </div>
            )}

            {/* Size 选择行（disabled 模型不显示） */}
            {!isDisabled && (
            <div className="ml-8 flex flex-wrap items-center gap-2">
              {m.sizes.map(size => {
                const key = `${m.name}_${size}`;
                const st = sizeStatus[key];
                // 改用 some 判断该 size 是否被选中（支持多选）
                const isSelected = selectedEntries.some(e => e.size === size);
                const isDownloaded = st?.status === 'completed';
                const isDownloading = st?.downloading;
                const isFailed = st?.status === 'error';

                return (
                  <div key={size} className="flex items-center gap-1">
                    {/* Size pill：
                        - 紫色填充 = 选中用于生成
                        - 白色边框 = 已下载但未选中（可点击选中）
                        - 虚线灰色 = 未下载（禁用）
                        - ✓ 表示"可用"（已下载），跟选中无关 */}
                    <button
                      onClick={(e) => { e.stopPropagation(); toggleModel(m.name, size); }}
                      disabled={!isDownloaded}
                      className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-colors flex items-center gap-1 ${
                        isSelected
                          ? 'bg-violet-500 text-white border-violet-500'
                          : isDownloaded
                            ? 'border-gray-300 text-gray-700 bg-white hover:border-violet-400 hover:bg-violet-50 cursor-pointer'
                            : 'border-dashed border-gray-300 text-gray-400 bg-gray-50 cursor-not-allowed'
                      }`}
                      title={
                        isDownloading ? '下载中…' :
                        isFailed ? `下载失败: ${st?.error || ''}` :
                        !isDownloaded ? '未下载（点击📥下载）' :
                        isSelected ? '已选中，再次点击取消' : '已下载可用，点击选中'
                      }
                    >
                      {size}
                      {/* 可用标记（独立于选中状态） */}
                      {isDownloaded && !isSelected && <span className="text-green-500 ml-0.5">✓</span>}
                    </button>

                    {/* 下载状态指示 */}
                    {isDownloading && (
                      <span className="text-xs text-blue-500 font-mono">{st?.progress || 0}%</span>
                    )}
                    {isFailed && (
                      <span className="text-xs text-red-400" title={st?.error || '失败'}>⚠</span>
                    )}

                    {/* 下载按钮（未下载时显示） */}
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
            )}

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
