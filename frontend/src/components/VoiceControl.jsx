import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Voice Control Component for Label-in-a-Box v4
 * Controls all AI voice interactions with subtitles, mute, volume
 */
export default function VoiceControl() {
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(0.8);
  const [currentSubtitle, setCurrentSubtitle] = useState('');
  const [currentVoice, setCurrentVoice] = useState(null);
  const [audioQueue, setAudioQueue] = useState([]);
  const audioRef = useRef(null);

  // Global voice playback function
  useEffect(() => {
    window.playVoice = (voiceData) => {
      if (voiceData && voiceData.file_url) {
        setAudioQueue(prev => [...prev, voiceData]);
      } else if (voiceData && voiceData.text) {
        // Text-only mode (when TTS unavailable)
        setCurrentSubtitle(voiceData.text);
        setCurrentVoice(voiceData.name || voiceData.voice);
        setTimeout(() => {
          setCurrentSubtitle('');
          setCurrentVoice(null);
        }, 4000);
      }
    };

    window.stopVoice = () => {
      // Stop window.currentVoiceAudio if it exists
      if (window.currentVoiceAudio) {
        window.currentVoiceAudio.pause();
        window.currentVoiceAudio.currentTime = 0;
        window.currentVoiceAudio = null;
      }
      // Also stop audioRef if it exists
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
      setAudioQueue([]);
      setCurrentSubtitle('');
      setCurrentVoice(null);
    };

    return () => {
      delete window.playVoice;
      delete window.stopVoice;
    };
  }, []);

  const playNext = useCallback((queueOverride = null) => {
    const queue = queueOverride || audioQueue;
    if (queue.length === 0) return;

    // Stop any currently playing audio before playing new one
    if (window.currentVoiceAudio) {
      window.currentVoiceAudio.pause();
      window.currentVoiceAudio.currentTime = 0;
      window.currentVoiceAudio = null;
    }

    const nextVoice = queue[0];
    setCurrentVoice(nextVoice.name || nextVoice.voice);
    setCurrentSubtitle(nextVoice.text);

    if (nextVoice.file_url) {
      // Create new Audio instance and assign to window.currentVoiceAudio
      const audio = new Audio(nextVoice.file_url);
      audio.volume = isMuted ? 0 : volume;
      window.currentVoiceAudio = audio;
      audioRef.current = audio;
      
      const handleEnded = () => {
        setAudioQueue(prev => {
          const newQueue = prev.slice(1);
          setCurrentSubtitle('');
          setCurrentVoice(null);
          
          // Clear window.currentVoiceAudio
          if (window.currentVoiceAudio) {
            window.currentVoiceAudio = null;
          }
          
          // Play next in queue if there's more
          if (newQueue.length > 0) {
            setTimeout(() => {
              playNext(newQueue);
            }, 300);
          }
          
          return newQueue;
        });
      };
      
      audio.onended = handleEnded;
      audio.onerror = () => {
        setAudioQueue(prev => prev.slice(1));
        setCurrentSubtitle('');
        setCurrentVoice(null);
        window.currentVoiceAudio = null;
      };
      
      audio.play().catch(err => {
        console.error('Audio play failed:', err);
        window.currentVoiceAudio = null;
      });
    }
  }, [audioQueue, isMuted, volume]);

  // Process audio queue
  useEffect(() => {
    if (audioQueue.length > 0 && !audioRef.current?.src) {
      playNext();
    }
  }, [audioQueue, playNext]);

  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    // Update window.currentVoiceAudio volume
    if (window.currentVoiceAudio) {
      window.currentVoiceAudio.volume = isMuted ? 0 : newVolume;
    }
    // Also update audioRef if it exists
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : newVolume;
    }
  };

  const toggleMute = () => {
    const newMuted = !isMuted;
    setIsMuted(newMuted);
    // Update window.currentVoiceAudio volume
    if (window.currentVoiceAudio) {
      window.currentVoiceAudio.volume = newMuted ? 0 : volume;
    }
    // Also update audioRef if it exists
    if (audioRef.current) {
      audioRef.current.volume = newMuted ? 0 : volume;
    }
  };

  const stopCurrent = () => {
    // Call window.stopVoice which handles window.currentVoiceAudio
    window.stopVoice();
  };

  const pauseCurrent = () => {
    // Pause window.currentVoiceAudio if it exists
    if (window.currentVoiceAudio && !window.currentVoiceAudio.paused) {
      window.currentVoiceAudio.pause();
    }
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause();
    }
  };

  return (
    <div className="fixed bottom-24 right-8 z-50">
      {/* Subtitle Display */}
      <AnimatePresence>
        {currentSubtitle && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="mb-4 max-w-md"
          >
            <div className="bg-gradient-to-r from-gray-900/95 to-black/95 backdrop-blur-xl rounded-2xl p-5 border border-red-500/30 shadow-2xl shadow-red-500/20">
              {currentVoice && (
                <div className="text-red-400 text-xs font-semibold mb-2 flex items-center gap-2">
                  <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                  {currentVoice}
                </div>
              )}
              <p className="text-white text-sm leading-relaxed">
                {currentSubtitle}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Voice Controls */}
      <div className="bg-gray-900/90 backdrop-blur-xl rounded-2xl p-4 border border-gray-700 shadow-xl">
        <div className="flex items-center gap-3">
          {/* Stop Button */}
          <button
            onClick={stopCurrent}
            disabled={!currentSubtitle}
            className={`p-3 rounded-xl transition-all ${
              currentSubtitle
                ? 'bg-red-500/20 hover:bg-red-500/30 border-red-500/50'
                : 'bg-gray-800/50 border-gray-700 opacity-50 cursor-not-allowed'
            } border`}
            title="Stop Voice"
          >
            <svg className="w-4 h-4 text-red-400" fill="currentColor" viewBox="0 0 20 20">
              <rect x="6" y="6" width="8" height="8" />
            </svg>
          </button>

          {/* Mute/Unmute */}
          <button
            onClick={toggleMute}
            className="p-3 rounded-xl bg-gray-800/50 hover:bg-gray-700 border border-gray-700 transition-all"
            title={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted ? (
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" clipRule="evenodd" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
              </svg>
            ) : (
              <svg className="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              </svg>
            )}
          </button>

          {/* Volume Slider */}
          <div className="flex items-center gap-2 px-3">
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={volume}
              onChange={handleVolumeChange}
              className="w-24 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-red-500"
            />
            <span className="text-xs text-gray-400 w-8 text-right">
              {Math.round(volume * 100)}%
            </span>
          </div>
        </div>
      </div>

      {/* Hidden Audio Element */}
      <audio
        ref={audioRef}
        className="hidden"
      />
    </div>
  );
}
