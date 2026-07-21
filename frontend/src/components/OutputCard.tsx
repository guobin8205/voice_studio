import type { GenerateResponse } from '../types';

interface Props {
  modelName: string;
  size: string;
  result?: GenerateResponse;
  paramNote?: string;
}

export function OutputCard({ modelName, size, result, paramNote }: Props) {
  return (
    <div className="bg-gray-50 border border-gray-100 rounded-xl p-4">
      <div className="flex justify-between items-center text-sm mb-3">
        <span className="font-bold text-gray-900">{modelName}</span>
        <span className="text-xs text-gray-400">{size}{paramNote && ` · ${paramNote}`}</span>
      </div>
      <div className="h-10 bg-white border border-gray-100 rounded-lg flex items-center px-3.5 mb-3">
        {result ? (
          <div className="flex items-end gap-0.5 h-7 w-full">
            {Array.from({ length: 20 }).map((_, i) => (
              <div
                key={i}
                className="flex-1 rounded-sm bg-gray-800"
                style={{ height: `${20 + Math.sin(i * 0.8) * 15 + Math.random() * 25}%`, minHeight: 3 }}
              />
            ))}
          </div>
        ) : (
          <span className="text-xs text-gray-300">等待生成...</span>
        )}
      </div>
      <div className="flex gap-4 text-[13px]">
        <span className="text-gray-500 cursor-pointer hover:text-gray-900 font-medium">▶ 播放</span>
        <span className="text-gray-500 cursor-pointer hover:text-gray-900 font-medium">💾 保存</span>
      </div>
    </div>
  );
}
