import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../utils/api';

// Keep Web Speech API for recognition only
let synthesis = null;
if ('speechSynthesis' in window) {
  synthesis = window.speechSynthesis;
}

export const useVoice = (sessionId = null) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [recognition, setRecognition] = useState(null);
  const [lastIntent, setLastIntent] = useState(null);
  const isMutedRef = useRef(false);
  const isPausedRef = useRef(false);

  useEffect(() => {
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognitionInstance = new SpeechRecognition();
      
      recognitionInstance.continuous = true;
      recognitionInstance.interimResults = true;
      recognitionInstance.lang = 'en-US';

      recognitionInstance.onresult = (event) => {
        let interim = '';
        let final = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcriptPiece = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            final += transcriptPiece;
          } else {
            interim += transcriptPiece;
          }
        }

        setInterimTranscript(interim);
        if (final) {
          setTranscript((prev) => prev + ' ' + final);
        }
      };

      recognitionInstance.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
      };

      recognitionInstance.onend = () => {
        setIsListening(false);
      };

      setRecognition(recognitionInstance);
    }

    return () => {
      if (recognition) {
        recognition.stop();
      }
    };
  }, []);

  const startListening = useCallback(() => {
    if (recognition && !isListening) {
      recognition.start();
      setIsListening(true);
      setTranscript('');
      setInterimTranscript('');
    }
  }, [recognition, isListening]);

  const stopListening = useCallback(() => {
    if (recognition && isListening) {
      recognition.stop();
      setIsListening(false);
    }
  }, [recognition, isListening]);

  const speak = useCallback(async (text, persona = null) => {
    try {
      // Use selected persona from VoiceControl if available, otherwise use passed persona or default to "nova"
      const selectedPersona = window.selectedVoicePersona || persona || "nova";

      // Call backend POST /api/voices/say with { text, persona, session_id }
      const result = await api.voiceSpeak(selectedPersona, text, sessionId);
      
      // Parse returned MP3 URL
      if (result && result.url) {
        // Use global audio system from VoiceControl
        if (window.playVoiceGlobal) {
          // Get current volume from global audio if available, otherwise use 1.0
          const globalAudio = window.getGlobalVoiceAudio ? window.getGlobalVoiceAudio() : null;
          const currentVolume = globalAudio ? globalAudio.volume : 1.0;
          
          // Play using global system
          window.playVoiceGlobal(result.url, currentVolume, text, selectedPersona);
          
          // Return promise that resolves when audio ends
          return new Promise((resolve, reject) => {
            const checkEnded = setInterval(() => {
              const audio = window.getGlobalVoiceAudio ? window.getGlobalVoiceAudio() : null;
              if (!audio || audio.ended || audio.paused) {
                clearInterval(checkEnded);
                if (audio && audio.ended) {
                  resolve();
                } else if (audio && audio.error) {
                  reject(new Error('Audio playback error'));
                } else {
                  resolve();
                }
              }
            }, 100);
            
            // Timeout after 30 seconds
            setTimeout(() => {
              clearInterval(checkEnded);
              resolve();
            }, 30000);
          });
        } else {
          // Fallback if VoiceControl not loaded yet
          throw new Error('Voice system not initialized');
        }
      }
      throw new Error('No audio URL returned from backend');
    } catch (err) {
      console.error('Voice speak failed:', err);
      // No fallback - backend voice system required
      throw err;
    }
  }, [sessionId]);

  const stopSpeaking = useCallback(async () => {
    // Call backend /api/voices/stop endpoint
    try {
      await api.voiceStop(sessionId);
    } catch (err) {
      console.error('Backend voice stop failed:', err);
    }
    // Use global stop function
    if (window.stopVoiceGlobal) {
      window.stopVoiceGlobal();
    }
  }, [sessionId]);

  const muteSpeaking = useCallback(async () => {
    // Call backend /api/voices/mute endpoint
    try {
      await api.voiceMute(sessionId);
    } catch (err) {
      console.error('Backend voice mute failed:', err);
    }
    // Apply change to global audio
    isMutedRef.current = true;
    const globalAudio = window.getGlobalVoiceAudio ? window.getGlobalVoiceAudio() : null;
    if (globalAudio) {
      globalAudio.muted = true;
    }
  }, [sessionId]);

  const unmuteSpeaking = useCallback(() => {
    isMutedRef.current = false;
    const globalAudio = window.getGlobalVoiceAudio ? window.getGlobalVoiceAudio() : null;
    if (globalAudio) {
      globalAudio.muted = false;
    }
  }, []);

  const pauseSpeaking = useCallback(async () => {
    // Call backend /api/voices/pause endpoint
    try {
      await api.voicePause(sessionId);
    } catch (err) {
      console.error('Backend voice pause failed:', err);
    }
    // Apply change to global audio
    const globalAudio = window.getGlobalVoiceAudio ? window.getGlobalVoiceAudio() : null;
    if (globalAudio && !globalAudio.paused) {
      globalAudio.pause();
      isPausedRef.current = true;
    }
  }, [sessionId]);

  const resumeSpeaking = useCallback(() => {
    const globalAudio = window.getGlobalVoiceAudio ? window.getGlobalVoiceAudio() : null;
    if (globalAudio && globalAudio.paused) {
      globalAudio.play();
      isPausedRef.current = false;
    }
  }, []);

  const processCommand = useCallback(async (command) => {
    if (!sessionId) {
      console.warn('No session ID provided for intent processing');
      return null;
    }

    try {
      const result = await api.processIntent(sessionId, command);
      setLastIntent(result);

      if (result.voice_response) {
        await speak(result.voice_response);
      }

      return result;
    } catch (err) {
      console.error('Failed to process intent:', err);
      await speak("Sorry, I didn't understand that command.");
      return null;
    }
  }, [sessionId, speak]);

  const listenForCommand = useCallback(async () => {
    if (!recognition) return;

    return new Promise((resolve) => {
      const handleResult = async (event) => {
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            const command = event.results[i][0].transcript;
            recognition.stop();
            
            const intent = await processCommand(command);
            resolve(intent);
            return;
          }
        }
      };

      recognition.onresult = handleResult;
      recognition.start();
      setIsListening(true);
    });
  }, [recognition, processCommand]);

  return {
    isListening,
    transcript,
    interimTranscript,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
    muteSpeaking,
    unmuteSpeaking,
    pauseSpeaking,
    resumeSpeaking,
    processCommand,
    listenForCommand,
    lastIntent,
    isSupported: !!recognition,
  };
};
