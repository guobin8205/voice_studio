import { useState, useRef, useCallback } from 'react';
import { api } from '../api/client';

interface Props {
  onAsrResult?: (text: string) => void;
  onAudioChange?: (path: string) => void;
}

export function AudioUpload({ onAsrResult, onAudioChange }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [asrText, setAsrText] = useState('');
  const [audioPath, setAudioPath] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (f: File) => {
    setFile(f);
    setUploading(true);
    setAsrText('');

    // Create local preview
    const url = URL.createObjectURL(f);
    setAudioPath(url);

    // Upload to backend for ASR
    try {
      const formData = new FormData();
      formData.append('file', f);
      const result = await fetch('/api/asr', { method: 'POST', body: formData }).then(r => r.json());
      setAsrText(result.text || '');
      onAsrResult?.(result.text || '');
      onAudioChange?.(url);
    } catch {
      setAsrText('（识别失败）');
    } finally {
      setUploading(false);
    }
  }, [onAsrResult, onAudioChange]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const onFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  }, [handleFile]);

  return (
    <div className="space-y-1">
      <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">参考音频</label>

      {!file ? (
        <div
          onDrop={onDrop}
          onDragOver={e => e.preventDefault()}
          onClick={() => fileRef.current?.click()}
          className="border-2 border-dashed border-gray-300 rounded-2xl p-8 bg-gray-50/50 text-center cursor-pointer hover:border-violet-400 transition-colors"
        >
          <div className="text-3xl mb-2">📁</div>
          <div className="text-sm text-gray-500">拖拽音频到此处，或点击上传</div>
          <div className="text-xs text-gray-300 mt-1">支持 WAV / MP3 / FLAC，建议 3-15 秒</div>
          <input ref={fileRef} type="file" accept="audio/*" className="hidden" onChange={onFileSelect} />
        </div>
      ) : (
        <div className="border-2 border-violet-200 rounded-2xl p-4 bg-violet-50/30">
          <div className="flex items-center gap-3">
            <span className="text-lg">🎵</span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-gray-900 truncate">{file.name}</div>
              <div className="text-xs text-gray-400">{(file.size / 1024).toFixed(0)} KB</div>
            </div>
            <button
              onClick={() => { setFile(null); setAsrText(''); setAudioPath(''); }}
              className="text-red-400 hover:text-red-600 text-lg"
            >
              ✕
            </button>
          </div>
          {audioPath && (
            <audio controls className="w-full mt-2 h-8" src={audioPath} />
          )}
        </div>
      )}

      {uploading && (
        <div className="text-xs text-blue-500 animate-pulse">⏳ 正在识别...</div>
      )}

      {asrText && (
        <div className="bg-green-50/50 border-2 border-green-200 rounded-xl p-3">
          <div className="flex justify-between text-xs mb-2">
            <span className="font-semibold text-green-700">📝 ASR 识别结果</span>
          </div>
          <textarea
            className="w-full border border-green-200 rounded-lg p-2 text-sm bg-white resize-none"
            rows={2}
            value={asrText}
            onChange={e => setAsrText(e.target.value)}
          />
          {onAsrResult && (
            <button
              onClick={() => onAsrResult(asrText)}
              className="text-xs text-violet-500 mt-1 font-medium hover:text-violet-700"
            >
              📋 填入合成文本
            </button>
          )}
        </div>
      )}
    </div>
  );
}
