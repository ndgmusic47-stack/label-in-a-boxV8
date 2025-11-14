import { useState } from 'react';
import { motion } from 'framer-motion';
import { api } from '../../utils/api';
import StageWrapper from './StageWrapper';

export default function LyricsStage({ sessionId, sessionData, updateSessionData, voice, onClose }) {
  const [theme, setTheme] = useState('');
  const [loading, setLoading] = useState(false);
  const [lyrics, setLyrics] = useState(null);

  const handleGenerate = async () => {
    setLoading(true);
    
    try {
      voice.speak(`Writing lyrics about ${theme || 'the vibe'}...`);
      
      // Generate lyrics
      const result = await api.generateLyrics(
        sessionData.genre || 'hip hop',
        sessionData.mood || 'energetic',
        theme,
        sessionId
      );
      
      // Sync with backend project state
      await api.syncProject(sessionId, updateSessionData);
      
      setLyrics(result.lyrics);
      updateSessionData({ lyricsData: result.lyrics });
      voice.speak('Here are your lyrics. Let me read them to you.');
    } catch (err) {
      voice.speak('Sorry, couldn\'t generate lyrics right now.');
    } finally {
      setLoading(false);
    }
  };

  // Removed auto-scroll effect - lyrics display statically without auto-reading

  return (
    <StageWrapper 
      title="Write Lyrics" 
      icon="📝" 
      onClose={onClose}
      voice={voice}
    >
      <div className="stage-scroll-container">
        {!lyrics ? (
          <div className="flex flex-col items-center justify-center gap-8 p-6 md:p-10">
            {/* Beat Player */}
            {sessionData.beatFile && (
              <div className="w-full max-w-2xl">
                <audio controls src={sessionData.beatFile} autoPlay loop className="w-full opacity-70" />
              </div>
            )}

            <div className="w-full max-w-2xl space-y-6">
              <div className="text-6xl text-center mb-4">
                📝
              </div>

              <div>
                <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
                  Theme (optional)
                </label>
                <input
                  type="text"
                  value={theme}
                  onChange={(e) => setTheme(e.target.value)}
                  className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                           text-studio-white font-poppins focus:outline-none focus:border-studio-red"
                  placeholder="success, love, struggle..."
                />
              </div>

              <motion.button
                onClick={handleGenerate}
                disabled={loading}
                className="w-full py-4 bg-studio-red hover:bg-studio-red/80 disabled:bg-studio-gray
                         text-studio-white font-montserrat font-semibold rounded-lg"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {loading ? 'Writing...' : 'Generate Lyrics'}
              </motion.button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-8 p-6 md:p-10">
            {/* Beat Player */}
            {sessionData.beatFile && (
              <div className="w-full max-w-2xl">
                <audio controls src={sessionData.beatFile} className="w-full opacity-70" />
              </div>
            )}
            
            <div className="w-full max-w-2xl space-y-6">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
                className="bg-studio-gray/30 rounded-lg border border-studio-white/10 p-8 text-center"
              >
                <div className="space-y-8">
                  {lyrics.verse && (
                    <div className="lyrics-section">
                      <h3 className="text-studio-red font-montserrat font-semibold text-lg mb-4">Verse</h3>
                      <div className="space-y-2">
                        {lyrics.verse.split('\n').map((line, idx) => (
                          <p key={idx} className="text-studio-white font-poppins text-base leading-relaxed">
                            {line || '\u00A0'}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                  {lyrics.chorus && (
                    <div className="lyrics-section">
                      <h3 className="text-studio-red font-montserrat font-semibold text-lg mb-4">Chorus</h3>
                      <div className="space-y-2">
                        {lyrics.chorus.split('\n').map((line, idx) => (
                          <p key={idx} className="text-studio-white font-poppins text-base leading-relaxed">
                            {line || '\u00A0'}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                  {lyrics.bridge && (
                    <div className="lyrics-section">
                      <h3 className="text-studio-red font-montserrat font-semibold text-lg mb-4">Bridge</h3>
                      <div className="space-y-2">
                        {lyrics.bridge.split('\n').map((line, idx) => (
                          <p key={idx} className="text-studio-white font-poppins text-base leading-relaxed">
                            {line || '\u00A0'}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
              
              <motion.button
                onClick={() => setLyrics(null)}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
                className="w-full py-3 px-6 bg-studio-gray hover:bg-studio-gray/80
                         text-studio-white font-montserrat rounded-lg"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                Generate New Lyrics
              </motion.button>
            </div>
          </div>
        )}
      </div>
    </StageWrapper>
  );
}

