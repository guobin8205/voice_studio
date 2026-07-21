import { useRef, useEffect, useState, useCallback } from 'react';

interface Props {
  audioPath?: string;
  className?: string;
}

export function AudioPlayer({ audioPath, className = '' }: Props) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState('');

  useEffect(() => {
    if (audioPath) {
      // If it's a server path, proxy through API
      const url = audioPath.startsWith('http') || audioPath.startsWith('blob')
        ? audioPath
        : `/api/audio/${encodeURIComponent(audioPath)}`;
      setAudioUrl(url);
    }
  }, [audioPath]);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
    } else {
      audio.play().catch(() => {});
    }
    setPlaying(!playing);
  }, [playing]);

  const onTimeUpdate = () => {
    const audio = audioRef.current;
    if (!audio) return;
    setCurrentTime(audio.currentTime);
    drawWaveform(audio.currentTime / (audio.duration || 1));
  };

  const onLoaded = () => {
    const audio = audioRef.current;
    if (!audio) return;
    setDuration(audio.duration);
  };

  const onEnded = () => setPlaying(false);

  // Simple waveform drawing
  const drawWaveform = (progress: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const bars = 40;
    const barW = (w / bars) * 0.7;
    const gap = (w / bars) * 0.3;

    for (let i = 0; i < bars; i++) {
      // Generate pseudo waveform heights (consistent pattern)
      const seed = Math.sin(i * 0.6) * 0.5 + Math.sin(i * 1.7) * 0.3 + Math.sin(i * 3.1) * 0.2;
      const height = Math.abs(seed) * h * 0.8 + h * 0.05;

      const x = i * (barW + gap);
      const y = (h - height) / 2;

      // Color: purple for played, gray for remaining
      const playedPct = i / bars;
      ctx.fillStyle = playedPct <= progress ? '#5b3fd4' : '#e2e8f0';
      ctx.fillRect(x, y, barW, height);
    }

    // Progress line
    const lineX = progress * w;
    ctx.strokeStyle = '#5b3fd4';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(lineX, 0);
    ctx.lineTo(lineX, h);
    ctx.stroke();
  };

  useEffect(() => {
    if (audioRef.current && duration > 0) {
      drawWaveform(currentTime / (duration || 1));
    }
  }, [currentTime, duration]);

  const formatTime = (t: number) => {
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

  return (
    <div className={`${className}`}>
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={onTimeUpdate}
        onLoadedMetadata={onLoaded}
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
        <canvas
          ref={canvasRef}
          width={200}
          height={32}
          className="flex-1 h-8 rounded cursor-pointer"
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const pct = (e.clientX - rect.left) / rect.width;
            if (audioRef.current) {
              audioRef.current.currentTime = pct * (audioRef.current.duration || 0);
            }
          }}
        />
        <span className="text-xs text-gray-400 font-mono w-16 text-right">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>
    </div>
  );
}
