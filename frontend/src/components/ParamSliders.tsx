import { useStore } from '../store';

const PARAMS = [
  { key: 'speed', label: '语速', min: 0.5, max: 2.0, step: 0.1 },
  { key: 'pitch', label: '音高', min: -12, max: 12, step: 1 },
  { key: 'temperature', label: '温度', min: 0.1, max: 1.0, step: 0.1 },
  { key: 'top_p', label: 'Top‑P', min: 0.1, max: 1.0, step: 0.05 },
] as const;

export function ParamSliders() {
  const speed = useStore(s => s.speed);
  const pitch = useStore(s => s.pitch);
  const temperature = useStore(s => s.temperature);
  const topP = useStore(s => s.top_p);
  const setInput = useStore(s => s.setInput);

  const values: Record<string, number> = { speed, pitch, temperature, top_p: topP };

  return (
    <div className="space-y-3">
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">参数</div>
      {PARAMS.map(p => {
        const val = values[p.key];
        const pct = ((val - p.min) / (p.max - p.min)) * 100;
        return (
          <div key={p.key} className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-gray-500 font-medium">{p.label}</span>
              <span className="text-[13px] font-semibold text-gray-900">{val}</span>
            </div>
            <input
              type="range"
              min={p.min}
              max={p.max}
              step={p.step}
              value={val}
              onChange={e => setInput(p.key, parseFloat(e.target.value))}
              className="w-full accent-violet-500 cursor-pointer"
              style={{
                background: `linear-gradient(to right, #8b5cf6 ${pct}%, #e5e7eb ${pct}%)`,
                height: '6px',
                borderRadius: '3px',
                appearance: 'none',
                WebkitAppearance: 'none',
              }}
            />
          </div>
        );
      })}
    </div>
  );
}
