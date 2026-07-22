import type { GenerateResponse } from '../types';
import { AudioPlayer } from './AudioPlayer';

interface Props {
  modelName: string;
  size: string;
  result?: GenerateResponse;
  paramNote?: string;
}

function fmtMs(ms?: number): string {
  if (!ms) return '';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function OutputCard({ modelName, size, result, paramNote }: Props) {
  return (
    <div className="bg-gray-50 border border-gray-100 rounded-xl p-4">
      <div className="flex justify-between items-center text-sm mb-3">
        <span className="font-bold text-gray-900">{modelName}</span>
        <span className="text-xs text-gray-400">
          {size}
          {paramNote && ` · ${paramNote}`}
          {result?.total_ms && (
            <span className="ml-2 text-violet-500" title={`加载 ${fmtMs(result.load_ms)} + 推理 ${fmtMs(result.inference_ms)}`}>
              ⏱ {fmtMs(result.total_ms)}
            </span>
          )}
        </span>
      </div>
      <AudioPlayer audioPath={result?.audio_path} className="mb-3" />
      <div className="flex gap-4 text-[13px]">
        <span className="text-gray-500 cursor-pointer hover:text-gray-900 font-medium">
          {result ? '💾 保存到库' : '等待生成...'}
        </span>
      </div>
    </div>
  );
}
