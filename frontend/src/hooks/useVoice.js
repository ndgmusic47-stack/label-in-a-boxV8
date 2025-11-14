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

  const speak = useCallback(async (text, persona = "nova") => {
    try {
      // Stop any currently playing audio to prevent overlapping
      if (window.currentVoiceAudio) {
        window.currentVoiceAudio.pause();
        window.currentVoiceAudio.currentTime = 0;
        window.currentVoiceAudio = null;
      }

      // Call backend POST /api/voices/say with { text, persona, session_id }
      const result = await api.voiceSpeak(persona, text, sessionId);
      
      // Parse returned MP3 URL
      if (result && result.url) {
        // Instantiate a new HTMLAudioElement and play the audio
        const audio = new Audio(result.url);
        audio.volume = isMutedRef.current ? 0 : 1.0;
        
        // Store reference to global audio element (ensure only one plays at a time)
        window.currentVoiceAudio = audio;
        
        // Play audio
        await audio.play();
        
        return new Promise((resolve, reject) => {
          audio.onended = () => {
            window.currentVoiceAudio = null;
            resolve();
          };
          audio.onerror = (err) => {
            window.currentVoiceAudio = null;
            reject(err);
          };
        });
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
    // Apply change to window.currentVoiceAudio
    if (window.currentVoiceAudio) {
      window.currentVoiceAudio.pause();
      window.currentVoiceAudio.currentTime = 0;
      window.currentVoiceAudio = null;
    }
  }, [sessionId]);

  const muteSpeaking = useCallback(async () => {
    // Call backend /api/voices/mute endpoint
    try {
      await api.voiceMute(sessionId);
    } catch (err) {
      console.error('Backend voice mute failed:', err);
    }
    // Apply change to window.currentVoiceAudio
    isMutedRef.current = true;
    if (window.currentVoiceAudio) {
      window.currentVoiceAudio.volume = 0;
    }
  }, [sessionId]);

  const unmuteSpeaking = useCallback(() => {
    isMutedRef.current = false;
    if (window.currentVoiceAudio) {
      window.currentVoiceAudio.volume = 1.0;
    }
  }, []);

  const pauseSpeaking = useCallback(async () => {
    // Call backend /api/voices/pause endpoint
    try {
      await api.voicePause(sessionId);
    } catch (err) {
      console.error('Backend voice pause failed:', err);
    }
    // Apply change to window.currentVoiceAudio
    if (window.currentVoiceAudio && !window.currentVoiceAudio.paused) {
      window.currentVoiceAudio.pause();
      isPausedRef.current = true;
    }
  }, [sessionId]);

  const resumeSpeaking = useCallback(() => {
    if (window.currentVoiceAudio && window.currentVoiceAudio.paused) {
      window.currentVoiceAudio.play();
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
