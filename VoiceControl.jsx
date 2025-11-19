import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Voice Control Component for Label-in-a-Box v4
 * Controls all AI voice interactions with subtitles, mute, volume
 * PHASE 3: Single global Audio instance, voice selector, fixed controls
 */

// Global audio instance - only ONE can exist at a time
let globalVoiceAudio = null;

// Global functions for playing/stopping voice
function playVoice(url, volume = 1, text = '', voiceName = '') {
  // Stop any currently playing audio
  if (globalVoiceAudio) {
    globalVoiceAudio.pause();
    globalVoiceAudio.currentTime = 0;
    globalVoiceAudio = null;
  }

  // Create new Audio instance
  globalVoiceAudio = new Audio(url);
  globalVoiceAudio.volume = volume;
  globalVoiceAudio.muted = false;
  
  // Store text and voice name for subtitle display
  if (window.setVoiceSubtitle) {
    window.setVoiceSubtitle(text, voiceName);
  }

  // Handle playback end
  globalVoiceAudio.onended = () => {
    if (window.setVoiceSubtitle) {
      window.setVoiceSubtitle('', '');
    }
    globalVoiceAudio = null;
  };

  // Handle errors
  globalVoiceAudio.onerror = () => {
    if (window.setVoiceSubtitle) {
      window.setVoiceSubtitle('', '');
    }
    globalVoiceAudio = null;
  };

  // Play audio
  globalVoiceAudio.play().catch(err => {
    console.error('Audio play failed:', err);
    globalVoiceAudio = null;
    if (window.setVoiceSubtitle) {
      window.setVoiceSubtitle('', '');
    }
  });
}

function stopVoice() {
  if (globalVoiceAudio) {
    globalVoiceAudio.pause();
    globalVoiceAudio.currentTime = 0;
    globalVoiceAudio = null;
  }
  if (window.setVoiceSubtitle) {
    window.setVoiceSubtitle('', '');
  }
}

export default function VoiceControl() {
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(0.8);
  const [currentSubtitle, setCurrentSubtitle] = useState('');
  const [currentVoice, setCurrentVoice] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);

  // Expose subtitle setter to global scope
  useEffect(() => {
    window.setVoiceSubtitle = (text, voiceName) => {
      setCurrentSubtitle(text);
      setCurrentVoice(voiceName);
      setIsPlaying(!!text);
    };

    // Expose global play/stop functions
    window.playVoiceGlobal = playVoice;
    window.stopVoiceGlobal = stopVoice;
    window.getGlobalVoiceAudio = () => globalVoiceAudio;

    return () => {
      delete window.setVoiceSubtitle;
      delete window.playVoiceGlobal;
      delete window.stopVoiceGlobal;
      delete window.getGlobalVoiceAudio;
    };
  }, []);

  // Update global audio volume when state changes
  useEffect(() => {
    if (globalVoiceAudio) {
      globalVoiceAudio.volume = volume;
    }
  }, [volume]);

  // Update global audio mute when state changes
  useEffect(() => {
    if (globalVoiceAudio) {
      globalVoiceAudio.muted = isMuted;
    }
  }, [isMuted]);

  // Monitor audio state
  useEffect(() => {
    const checkAudioState = () => {
      if (globalVoiceAudio) {
        setIsPlaying(!globalVoiceAudio.paused && globalVoiceAudio.currentTime > 0);
      } else {
        setIsPlaying(false);
      }
    };

    const interval = setInterval(checkAudioState, 100);
    return () => clearInterval(interval);
  }, []);

  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (globalVoiceAudio) {
      globalVoiceAudio.volume = newVolume;
    }
  };

  const toggleMute = () => {
    const newMuted = !isMuted;
    setIsMuted(newMuted);
    if (globalVoiceAudio) {
      globalVoiceAudio.muted = newMuted;
    }
  };

  const stopCurrent = () => {
    stopVoice();
  };

  // Ensure default persona is always set for voice system without UI
  useEffect(() => {
    window.selectedVoicePersona = 'nova';
    return () => {
      delete window.selectedVoicePersona;
    };
  }, []);

  return (
    <div className="voice-controls">
      {/* Subtitle Display */}
      <AnimatePresence>
        {currentSubtitle && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="mb-4 max-w-md"
          >
            <div className="bg-gradient-to-r from-gray-900/95 to-black/95 backdrop-blur-xl rounded-2xl p-4 border border-red-500/30 shadow-2xl shadow-red-500/20">
              {currentVoice && (
                <div className="text-red-400 text-[0.68rem] font-semibold mb-2 flex items-center gap-2">
                  <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                  {currentVoice}
                </div>
              )}
              <p className="text-white text-[0.8rem] leading-relaxed voice-subtitle">
                {currentSubtitle}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Voice Controls */}
      <div className="bg-gray-900/90 backdrop-blur-xl rounded-2xl p-2 border border-gray-700 shadow-xl">
        <div className="flex items-center gap-3">
          {/* Stop Button */}
          <button
            onClick={stopCurrent}
            disabled={!isPlaying && !currentSubtitle}
            className={`p-3 rounded-xl transition-all border ${
              (isPlaying || currentSubtitle)
                ? 'bg-red-500/20 hover:bg-red-500/30 border-red-500/50'
                : 'bg-gray-800/50 border-gray-700 opacity-50 cursor-not-allowed'
            }`}
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
          <div className="flex items-center gap-2 px-2 flex-1">
            <div className="voice-slider-wrap w-full max-w-[140px]">
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={volume}
                onChange={handleVolumeChange}
                className="w-full h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-red-500"
              />
            </div>
            <span className="text-xs text-gray-400 w-10 text-right">
              {Math.round(volume * 100)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
