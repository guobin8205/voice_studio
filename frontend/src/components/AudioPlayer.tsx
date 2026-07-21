import { useRef, useEffect, useState, useCallback } from 'react';

interface Props {
  audioPath?: string;
  className?: string;
}

export function AudioPlayer({ audioPath, className = '' }: Props) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState('');

  useEffect(() => {
    if (audioPath) {
      // 后端返回的路径直接传给 /api/audio/，让后端解析
      // 用相对文件名（basename）避免路径穿越检查失败
      const filename = audioPath.split(/[\\/]/).pop() || audioPath;
      setAudioUrl(`/api/audio/${encodeURIComponent(filename)}`);
      setPlaying(false);
      setCurrentTime(0);
    } else {
      setAudioUrl('');
    }
  }, [audioPath]);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      audio.play().catch(() => {});
    } else {
      audio.pause();
    }
  }, []);

  const onTimeUpdate = () => {
    const audio = audioRef.current;
    if (!audio) return;
    setCurrentTime(audio.currentTime);
  };

  const onLoaded = () => {
    const audio = audioRef.current;
    if (!audio) return;
    setDuration(audio.duration || 0);
  };

  // 用真实的播放/暂停事件驱动 UI 状态
  const onPlay = () => setPlaying(true);
  const onPause = () => setPlaying(false);
  const onEnded = () => setPlaying(false);

  const formatTime = (t: number) => {
    if (!isFinite(t)) return '0:00';
    const m = Math.floor(t / 60);
    const s = Math.floor(t % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  if (!audioUrl) {
    return (
      <div className={`${className} flex items-center justify-center h-10 bg-gray-50 border border-gray-100 rounded-lg text-xs text-gray-300`}>
        等待生成...
      </div>
    );
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className={`${className}`}>
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={onTimeUpdate}
        onLoadedMetadata={onLoaded}
        onPlay={onPlay}
        onPause={onPause}
        onEnded={onEnded}
        preload="auto"
      />
      <div className="flex items-center gap-3">
        <button
          onClick={togglePlay}
          className="w-8 h-8 flex items-center justify-center rounded-full bg-violet-500 hover:bg-violet-600 text-white text-sm shrink-0 transition-colors"
        >
          {playing ? '⏸' : '▶'}
        </button>
        <div
          className="flex-1 h-2 bg-gray-100 rounded-full relative cursor-pointer"
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const pct = (e.clientX - rect.left) / rect.width;
            if (audioRef.current && duration > 0) {
              audioRef.current.currentTime = pct * duration;
            }
          }}
        >
          <div className="h-full bg-violet-500 rounded-full" style={{ width: `${progress}%` }} />
        </div>
        <span className="text-xs text-gray-400 font-mono w-20 text-right shrink-0">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>
    </div>
  );
}
