import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { api } from '../../utils/api';
import StageWrapper from './StageWrapper';

export default function ReleaseStage({ sessionData, updateSessionData, voice, onClose, sessionId, completeStage }) {
  const [artistName, setArtistName] = useState(sessionData.artistName || 'NP22');
  const [trackTitle, setTrackTitle] = useState(sessionData.trackTitle || 'My Track');
  const [genre, setGenre] = useState(sessionData.genre || 'hip hop');
  const [mood, setMood] = useState(sessionData.mood || 'energetic');
  const [releaseDate, setReleaseDate] = useState(sessionData.release_date || new Date().toISOString().split('T')[0]);
  const [lyrics, setLyrics] = useState(sessionData.lyricsData || '');
  const [isrc, setIsrc] = useState(sessionData.isrc || '');
  const [creating, setCreating] = useState(false);
  const [packUrl, setPackUrl] = useState(sessionData.releasePackUrl || null);
  
  // Check if release pack exists in project assets
  const hasReleasePack = sessionData.releasePack || (sessionData.assets?.release_pack);
  
  // AI Cover Art State
  const [coverMood, setCoverMood] = useState(sessionData.mood || 'energetic');
  const [coverGenre, setCoverGenre] = useState(sessionData.genre || 'hip hop');
  const [stylePrompt, setStylePrompt] = useState('');
  const [generatingCover, setGeneratingCover] = useState(false);
  const [coverUrl, setCoverUrl] = useState(sessionData.coverArt || null);
  const [coverPrompt, setCoverPrompt] = useState('');

  const canRelease = sessionData.mixedFile || sessionData.masterFile;

  // Auto-generate ISRC on mount or when title/artist changes
  const generateISRC = () => {
    // Format: USRC1 + 12 digits (country code + registrant code + item code)
    const timestamp = Date.now().toString().slice(-8);
    const random = Math.floor(Math.random() * 10000).toString().padStart(4, '0');
    return `USRC1${timestamp}${random}`;
  };

  // Initialize ISRC if not present
  useEffect(() => {
    if (!isrc && !sessionData.isrc) {
      const newIsrc = generateISRC();
      setIsrc(newIsrc);
    }
  }, []);

  const handleGenerateCover = async () => {
    setGeneratingCover(true);
    
    try {
      voice.speak("Generating cover art...");
      
      // Generate cover art using backend POST /api/release/generate-cover
      const result = await api.generateCoverArt(
        trackTitle,
        artistName,
        sessionId
      );
      
      // Sync with backend project state after cover generation
      await api.syncProject(sessionId, updateSessionData);
      
      if (result.url) {
        setCoverUrl(result.url);
        updateSessionData({ 
          coverArt: result.url,
          artistName,
          trackTitle 
        });
        voice.speak("Cover art generated.");
      }
    } catch (err) {
      console.error('Cover art generation error:', err);
      voice.speak('Failed to generate cover art. Try again.');
    } finally {
      setGeneratingCover(false);
    }
  };

  const handleCreatePack = async () => {
    if (!canRelease) {
      voice.speak('You need a mixed file first');
      return;
    }

    setCreating(true);
    
    try {
      voice.speak("Preparing your release pack...");
      
      // Call POST /api/release/pack with proper payload structure
      const result = await api.createReleasePack(
        sessionId,
        sessionData.mixedFile || sessionData.masterFile,
        coverUrl,
        {
          title: trackTitle,
          artist: artistName,
          genre: genre,
          mood: mood,
          release_date: releaseDate,
          isrc: isrc
        },
        lyrics
      );
      
      // After success, call syncProject
      await api.syncProject(sessionId, updateSessionData);
      
      // Display download link
      const downloadUrl = result.zip_url || result.url;
      setPackUrl(downloadUrl);
      updateSessionData({ 
        releasePackUrl: downloadUrl,
        releaseCompleted: true,
        trackTitle,
        artistName,
        genre,
        mood,
        release_date: releaseDate,
        isrc,
        lyricsData: lyrics
      });
      
      voice.speak("Your release pack is ready to download.");
      
      // Complete the stage
      if (completeStage) {
        await completeStage("release");
      }
    } catch (err) {
      console.error('Release pack creation error:', err);
      voice.speak("I couldn't generate the release pack. Please try again.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <StageWrapper 
      title="Release Pack" 
      icon="📦" 
      onClose={onClose}
      voice={voice}
    >
      <div className="stage-scroll-container">
        <div className="flex flex-col items-center justify-center gap-8 p-6 md:p-10">
        <div className="text-6xl mb-4">
          📦
        </div>

        <div className="w-full max-w-2xl space-y-6">
          {/* Preview Mixed Track */}
          {sessionData.mixedFile && (
            <div className="space-y-2">
              <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
                Preview Final Mixed Track
              </label>
              <audio controls src={sessionData.mixedFile} className="w-full" />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
                Artist Name
              </label>
              <input
                type="text"
                value={artistName}
                onChange={(e) => setArtistName(e.target.value)}
                className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                         text-studio-white font-poppins focus:outline-none focus:border-studio-red"
              />
            </div>

            <div>
              <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
                Track Title
              </label>
              <input
                type="text"
                value={trackTitle}
                onChange={(e) => setTrackTitle(e.target.value)}
                className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                         text-studio-white font-poppins focus:outline-none focus:border-studio-red"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
                Genre
              </label>
              <input
                type="text"
                value={genre}
                onChange={(e) => setGenre(e.target.value)}
                className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                         text-studio-white font-poppins focus:outline-none focus:border-studio-red"
              />
            </div>

            <div>
              <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
                Mood
              </label>
              <input
                type="text"
                value={mood}
                onChange={(e) => setMood(e.target.value)}
                className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                         text-studio-white font-poppins focus:outline-none focus:border-studio-red"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
                Release Date
              </label>
              <input
                type="date"
                value={releaseDate}
                onChange={(e) => setReleaseDate(e.target.value)}
                className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                         text-studio-white font-poppins focus:outline-none focus:border-studio-red"
              />
            </div>

            <div>
              <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
                ISRC
              </label>
              <input
                type="text"
                value={isrc}
                onChange={(e) => setIsrc(e.target.value)}
                className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                         text-studio-white font-poppins focus:outline-none focus:border-studio-red"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
              Lyrics (Optional)
            </label>
            <textarea
              value={lyrics}
              onChange={(e) => setLyrics(e.target.value)}
              rows={4}
              className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                       text-studio-white font-poppins focus:outline-none focus:border-studio-red"
            />
          </div>

          {/* AI Cover Art Section */}
          <div className="space-y-4">
            <h3 className="font-montserrat text-studio-white font-semibold flex items-center gap-2">
              <span>🎨</span> AI Cover Art Generator
            </h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
                  Mood
                </label>
                <select
                  value={coverMood}
                  onChange={(e) => setCoverMood(e.target.value)}
                  className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                           text-studio-white font-poppins focus:outline-none focus:border-purple-500"
                >
                  <option value="energetic">Energetic</option>
                  <option value="melancholic">Melancholic</option>
                  <option value="uplifting">Uplifting</option>
                  <option value="dark">Dark</option>
                  <option value="chill">Chill</option>
                  <option value="aggressive">Aggressive</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
                  Genre
                </label>
                <select
                  value={coverGenre}
                  onChange={(e) => setCoverGenre(e.target.value)}
                  className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                           text-studio-white font-poppins focus:outline-none focus:border-purple-500"
                >
                  <option value="hip-hop">Hip-Hop</option>
                  <option value="pop">Pop</option>
                  <option value="rock">Rock</option>
                  <option value="electronic">Electronic</option>
                  <option value="r&b">R&B</option>
                  <option value="indie">Indie</option>
                </select>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
                Style Prompt (Optional)
              </label>
              <input
                type="text"
                value={stylePrompt}
                onChange={(e) => setStylePrompt(e.target.value)}
                placeholder="e.g., cyberpunk aesthetic, retro 80s, minimalist..."
                className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                         text-studio-white font-poppins focus:outline-none focus:border-purple-500
                         placeholder:text-studio-white/30"
              />
            </div>
            
            <motion.button
              onClick={handleGenerateCover}
              disabled={generatingCover}
              className="w-full py-4 rounded-lg font-montserrat font-semibold bg-gradient-to-r from-purple-600 to-pink-600
                       hover:from-purple-500 hover:to-pink-500 text-studio-white transition-all duration-300
                       disabled:opacity-50 disabled:cursor-not-allowed"
              whileHover={!generatingCover ? { scale: 1.02 } : {}}
              whileTap={!generatingCover ? { scale: 0.98 } : {}}
            >
              {generatingCover ? '✨ Generating AI Cover Art...' : '✨ Generate AI Cover Art'}
            </motion.button>
            
            {/* Cover Preview */}
            <div className="aspect-square w-full max-w-md mx-auto bg-gradient-to-br from-purple-900/20 to-studio-gray/50
                          rounded-lg border border-studio-white/10 flex items-center justify-center overflow-hidden">
              {coverUrl ? (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25, ease: "easeOut" }}
                  className="w-full h-full relative"
                >
                  <img 
                    src={coverUrl} 
                    alt={`${trackTitle} cover art`}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                    <p className="font-montserrat text-lg text-white">{trackTitle}</p>
                    <p className="font-poppins text-sm text-white/60">{artistName}</p>
                  </div>
                </motion.div>
              ) : (
                <div className="text-center p-8">
                  <p className="text-6xl mb-4">🎨</p>
                  <p className="font-montserrat text-lg text-studio-white/60">
                    No cover art yet
                  </p>
                  <p className="font-poppins text-sm text-studio-white/40 mt-2">
                    Generate AI cover art above
                  </p>
                </div>
              )}
            </div>
            
            {coverPrompt && (
              <div className="text-xs text-studio-white/40 font-poppins text-center">
                <p className="mb-1">AI Prompt Used:</p>
                <p className="italic">{coverPrompt}</p>
              </div>
            )}
          </div>

          <motion.button
            onClick={handleCreatePack}
            disabled={!canRelease || creating}
            className={`
              w-full py-4 rounded-lg font-montserrat font-semibold
              transition-all duration-300
              ${canRelease && !creating
                ? 'bg-studio-red hover:bg-studio-red/80 text-studio-white'
                : 'bg-studio-gray text-studio-white/40 cursor-not-allowed'
              }
            `}
            whileHover={canRelease ? { scale: 1.02 } : {}}
            whileTap={canRelease ? { scale: 0.98 } : {}}
          >
            {creating ? 'Generating Release Pack...' : canRelease ? 'Generate Release Pack' : 'Need Master File'}
          </motion.button>

          {(packUrl || hasReleasePack) && (
            <motion.a
              href={packUrl || `/media/${sessionId}/release_pack.zip`}
              download
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="block w-full py-4 bg-studio-gray/50 hover:bg-studio-gray/70
                       text-studio-white font-montserrat text-center rounded-lg
                       border border-studio-white/20"
            >
              📥 Download Release Pack
            </motion.a>
          )}

          <div className="text-xs text-studio-white/40 font-poppins text-center space-y-1">
            <p>Package includes:</p>
            <p>• Master WAV • Cover Art • Metadata JSON</p>
            <p>Ready for DistroKid, Spotify, Apple Music</p>
          </div>
        </div>
        </div>
      </div>
    </StageWrapper>
  );
}
