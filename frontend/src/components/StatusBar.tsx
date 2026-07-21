import { useEffect } from 'react';
import { useStore } from '../store';

export function StatusBar() {
  const systemStatus = useStore(s => s.systemStatus);
  const fetchSystemStatus = useStore(s => s.fetchSystemStatus);

  useEffect(() => {
    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const gpu = systemStatus?.gpu;
  const model = systemStatus?.model;

  return (
    <div className="bg-gray-50 rounded-xl p-3.5 text-xs text-gray-400 space-y-1">
      {gpu?.available ? (
        <div className="flex justify-between">
          <span>🖥️ GPU</span>
          <span className="text-gray-700 font-medium">{gpu.used_gb}/{gpu.total_gb} GB</span>
        </div>
      ) : (
        <div>🖥️ GPU N/A</div>
      )}
      {model?.loaded ? (
        <div className="flex justify-between">
          <span>📦 模型</span>
          <span className="text-gray-700 font-medium">{model.name} · {model.size}</span>
        </div>
      ) : (
        <div>📦 未加载</div>
      )}
    </div>
  );
}
