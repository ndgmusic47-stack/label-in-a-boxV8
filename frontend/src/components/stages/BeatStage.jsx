import { useState } from 'react';
import { motion } from 'framer-motion';
import { api } from '../../utils/api';
import StageWrapper from './StageWrapper';
import WavesurferPlayer from '../WavesurferPlayer';

export default function BeatStage({ sessionId, sessionData, updateSessionData, voice, onClose }) {
  const [mood, setMood] = useState(sessionData.mood || 'energetic');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleCreate = async () => {
    setLoading(true);
    setError(null);
    
    try {
      voice.speak(`Creating a ${mood} beat for you...`);
      
      // Call beat creation API with correct format
      const result = await api.createBeat(mood, sessionData.genre || 'hip hop', 120, null, sessionId);
      
      // Sync with backend project state
      await api.syncProject(sessionId, updateSessionData);
      
      updateSessionData({ 
        mood: mood,
      });
      voice.speak('Your beat is ready! Check it out.');
    } catch (err) {
      setError(err.message);
      voice.speak('Sorry, there was an error creating the beat.');
    } finally {
      setLoading(false);
    }
  };

  const handleVoiceCommand = (transcript) => {
    const lowerTranscript = transcript.toLowerCase();
    
    if (lowerTranscript.includes('create') || lowerTranscript.includes('make')) {
      const moods = ['energetic', 'chill', 'dark', 'happy', 'sad', 'aggressive'];
      const foundMood = moods.find(m => lowerTranscript.includes(m));
      
      if (foundMood) {
        setMood(foundMood);
        setTimeout(() => handleCreate(), 500);
      } else {
        handleCreate();
      }
    }
  };

  return (
    <StageWrapper 
      title="Create Beat" 
      icon="🎵" 
      onClose={onClose}
      voice={voice}
      onVoiceCommand={handleVoiceCommand}
    >
      <div className="stage-scroll-container">
        <div className="flex flex-col items-center justify-center gap-8 p-6 md:p-10">
        <div className="text-6xl mb-4">
          🎵
        </div>

        <div className="w-full max-w-md space-y-6">
          <div>
            <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
              Mood
            </label>
            <input
              type="text"
              value={mood}
              onChange={(e) => setMood(e.target.value)}
              className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                       text-studio-white font-poppins focus:outline-none focus:border-studio-red
                       transition-colors"
              placeholder="energetic, chill, dark..."
            />
          </div>

          <motion.button
            onClick={handleCreate}
            disabled={loading}
            className="w-full py-4 bg-studio-red hover:bg-studio-red/80 disabled:bg-studio-gray
                     text-studio-white font-montserrat font-semibold rounded-lg
                     transition-all duration-300"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {loading ? 'Creating...' : 'Generate Beat'}
          </motion.button>

          {error && (
            <p className="text-red-400 text-sm text-center">{error}</p>
          )}

          {sessionData.beatFile && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 bg-studio-gray/30 rounded-lg border border-studio-white/10"
            >
              <p className="text-sm text-studio-white/80 mb-3 font-montserrat">Beat Ready!</p>
              <WavesurferPlayer url={sessionData.beatFile} color="#EF4444" height={100} />
            </motion.div>
          )}
        </div>

        <p className="text-sm text-studio-white/40 font-poppins text-center max-w-md">
          Try saying: "Create an energetic beat" or "Make a chill vibe"
        </p>
        </div>
      </div>
    </StageWrapper>
  );
}
