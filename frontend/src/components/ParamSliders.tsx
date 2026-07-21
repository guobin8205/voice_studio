import { useStore } from '../store';

const PARAMS = [
  { key: 'speed', label: '语速', min: 0.5, max: 2.0, step: 0.1, defaultVal: 1.0 },
  { key: 'pitch', label: '音高', min: -12, max: 12, step: 1, defaultVal: 0 },
  { key: 'temperature', label: '温度', min: 0.1, max: 1.0, step: 0.1, defaultVal: 0.4 },
  { key: 'top_p', label: 'Top‑P', min: 0.1, max: 1.0, step: 0.05, defaultVal: 0.9 },
];

export function ParamSliders() {
  const setInput = useStore(s => s.setInput);
  const values = useStore(s => ({
    speed: s.speed, pitch: s.pitch, temperature: s.temperature, top_p: s.top_p,
  }));

  return (
    <div className="space-y-3">
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">参数</div>
      {PARAMS.map(p => {
        const val = (values as any)[p.key];
        const pct = ((val - p.min) / (p.max - p.min)) * 100;
        return (
          <div key={p.key} className="flex items-center gap-3">
            <span className="text-[13px] text-gray-500 font-medium w-12 shrink-0">{p.label}</span>
            <div className="flex-1 h-1.5 rounded-full bg-gray-100 relative">
              <div className="h-full rounded-full bg-gray-800" style={{ width: `${pct}%` }} />
            </div>
            <span className="text-[13px] font-semibold text-gray-900 w-8 text-right">{val}</span>
          </div>
        );
      })}
    </div>
  );
}
