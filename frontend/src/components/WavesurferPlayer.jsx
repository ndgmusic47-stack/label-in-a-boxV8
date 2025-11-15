import { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';

export default function WavesurferPlayer({ url, height = 80, color = '#EF4444', onReady }) {
  const containerRef = useRef(null);
  const wavesurferRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    if (!url || !containerRef.current) return;

    // V24: Destroy existing instance before creating new one
    if (wavesurferRef.current) {
      try {
        wavesurferRef.current.destroy();
      } catch (e) {
        console.warn('Error destroying wavesurfer:', e);
      }
      wavesurferRef.current = null;
    }

    // Reset state
    setLoading(true);
    setError(null);
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);

    // V24: Create new instance only after URL is available
    const wavesurfer = WaveSurfer.create({
      container: containerRef.current,
      waveColor: `${color}40`,
      progressColor: color,
      cursorColor: color,
      height,
      barWidth: 2,
      barRadius: 3,
      responsive: true,
      normalize: true,
    });

    wavesurferRef.current = wavesurfer;

    wavesurfer.on('ready', () => {
      setLoading(false);
      setDuration(wavesurfer.getDuration());
      if (onReady) onReady(wavesurfer);
    });

    wavesurfer.on('play', () => setIsPlaying(true));
    wavesurfer.on('pause', () => setIsPlaying(false));
    
    wavesurfer.on('audioprocess', () => {
      setCurrentTime(wavesurfer.getCurrentTime());
    });

    wavesurfer.on('error', (err) => {
      console.error('Wavesurfer error:', err);
      setError('Failed to load audio');
      setLoading(false);
    });

    // V24: Load URL after instance is ready
    wavesurfer.load(url);

    // V24: Cleanup on unmount or URL change
    return () => {
      if (wavesurferRef.current) {
        try {
          wavesurferRef.current.destroy();
        } catch (e) {
          console.warn('Error destroying wavesurfer in cleanup:', e);
        }
        wavesurferRef.current = null;
      }
    };
  }, [url, height, color, onReady]);

  const handlePlayPause = () => {
    if (wavesurferRef.current) {
      wavesurferRef.current.playPause();
    }
  };

  const handleStop = () => {
    if (wavesurferRef.current) {
      wavesurferRef.current.stop();
      setIsPlaying(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-full space-y-3">
      <div 
        ref={containerRef} 
        className="w-full bg-studio-gray/30 rounded-lg overflow-hidden"
      />
      
      {loading && (
        <div className="text-studio-white/60 text-sm text-center">
          Loading waveform...
        </div>
      )}
      
      {error && (
        <div className="text-red-400 text-sm text-center">
          {error}
        </div>
      )}
      
      {!loading && !error && (
        <div className="flex items-center gap-4">
          <button
            onClick={handlePlayPause}
            className="w-12 h-12 rounded-full bg-studio-red hover:bg-studio-red/80 
                     flex items-center justify-center transition-all"
          >
            {isPlaying ? (
              <span className="text-2xl">⏸</span>
            ) : (
              <span className="text-2xl ml-1">▶</span>
            )}
          </button>
          
          <button
            onClick={handleStop}
            className="w-12 h-12 rounded-full bg-studio-gray hover:bg-studio-white/10 
                     flex items-center justify-center transition-all"
          >
            <span className="text-2xl">⏹</span>
          </button>
          
          <div className="flex-1 text-studio-white/80 font-poppins text-sm">
            <span className="font-semibold">{formatTime(currentTime)}</span>
            <span className="mx-2">/</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
