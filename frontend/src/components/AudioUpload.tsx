import { useState, useRef } from 'react';
import { api } from '../api/client';
import { useStore } from '../store';

interface Props {
  onAsrResult?: (text: string) => void;
}

export function AudioUpload({ onAsrResult }: Props) {
  const setReferenceAudio = useStore(s => s.setReferenceAudio);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [asrText, setAsrText] = useState('');
  const [audioUrl, setAudioUrl] = useState('');
  const [serverPath, setServerPath] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = async (f: File) => {
    setFile(f);
    setUploading(true);
    setAsrText('');
    const url = URL.createObjectURL(f);
    setAudioUrl(url);

    try {
      // 1. 上传参考音频到服务端（持久化）
      const uploadRes = await api.uploadReference(f);
      setServerPath(uploadRes.path);
      setReferenceAudio(f, uploadRes.path);

      // 2. 同时做 ASR 识别
      const asrRes = await api.uploadForAsr(f);
      setAsrText(asrRes.text || '');
      onAsrResult?.(asrRes.text || '');
    } catch (e: any) {
      setAsrText(`（处理失败: ${e.message || e}）`);
    } finally {
      setUploading(false);
    }
  };

  const clear = () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setFile(null);
    setAsrText('');
    setAudioUrl('');
    setServerPath(null);
    setReferenceAudio(null, null);
  };

  return (
    <div className="space-y-1">
      <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">参考音频</label>

      {!file ? (
        <div
          onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleFile(f); }}
          onDragOver={e => e.preventDefault()}
          onClick={() => fileRef.current?.click()}
          className="border-2 border-dashed border-gray-300 rounded-2xl p-8 bg-gray-50/50 text-center cursor-pointer hover:border-violet-400 transition-colors"
        >
          <div className="text-3xl mb-2">📁</div>
          <div className="text-sm text-gray-500">拖拽音频到此处，或点击上传</div>
          <div className="text-xs text-gray-300 mt-1">支持 WAV / MP3 / FLAC，建议 3-15 秒</div>
          <input ref={fileRef} type="file" accept="audio/*" className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />
        </div>
      ) : (
        <div className="border-2 border-violet-200 rounded-2xl p-4 bg-violet-50/30">
          <div className="flex items-center gap-3">
            <span className="text-lg">🎵</span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-gray-900 truncate">{file.name}</div>
              <div className="text-xs text-gray-400">{(file.size / 1024).toFixed(0)} KB</div>
            </div>
            <button onClick={clear} className="text-red-400 hover:text-red-600 text-lg">✕</button>
          </div>
          {audioUrl && <audio controls className="w-full mt-2 h-8" src={audioUrl} />}
          {serverPath && (
            <div className="text-xs text-green-600 mt-1">✓ 已上传到服务端</div>
          )}
        </div>
      )}

      {uploading && <div className="text-xs text-blue-500 animate-pulse">⏳ 正在上传和识别...</div>}

      {asrText && asrText !== '（识别失败）' && (
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
          <button
            onClick={() => onAsrResult?.(asrText)}
            className="text-xs text-violet-500 mt-1 font-medium hover:text-violet-700"
          >
            📋 填入合成文本
          </button>
        </div>
      )}
    </div>
  );
}
