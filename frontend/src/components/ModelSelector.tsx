import { useStore } from '../store';

export function ModelSelector() {
  const models = useStore(s => s.models);
  const selectedModels = useStore(s => s.selectedModels);
  const toggleModel = useStore(s => s.toggleModel);

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">选择模型对比</div>
      {models.map(m => {
        const isActive = selectedModels.some(sm => sm.name === m.name);
        const activeSize = selectedModels.find(sm => sm.name === m.name)?.size;
        return (
          <div
            key={m.name}
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
          </div>
        );
      })}
    </div>
  );
}
