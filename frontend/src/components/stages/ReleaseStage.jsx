import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { api } from '../../utils/api';
import { handlePaywall } from '../../utils/paywall';
import StageWrapper from './StageWrapper';

export default function ReleaseStage({ sessionData, updateSessionData, voice, onClose, onNext, sessionId, completeStage, openUpgradeModal }) {
  // Form inputs
  const [trackTitle, setTrackTitle] = useState(sessionData.trackTitle || sessionData.metadata?.track_title || '');
  const [artistName, setArtistName] = useState(sessionData.artistName || sessionData.metadata?.artist_name || 'NP22');
  const [genre, setGenre] = useState(sessionData.genre || sessionData.metadata?.genre || 'hip hop');
  const [mood, setMood] = useState(sessionData.mood || sessionData.metadata?.mood || 'energetic');
  const [releaseDate, setReleaseDate] = useState(sessionData.release_date || new Date().toISOString().split('T')[0]);
  const [explicit, setExplicit] = useState(sessionData.explicit || false);
  const [coverStyle, setCoverStyle] = useState('realistic');
  
  // Cover art generation
  const [coverImages, setCoverImages] = useState([]);
  const [selectedCover, setSelectedCover] = useState(null);
  const [generatingCover, setGeneratingCover] = useState(false);
  
  // Release pack data
  const [releasePack, setReleasePack] = useState(null);
  const [loadingPack, setLoadingPack] = useState(false);
  
  // Generation states
  const [generatingCopy, setGeneratingCopy] = useState(false);
  const [generatingMetadata, setGeneratingMetadata] = useState(false);
  const [generatingLyricsPDF, setGeneratingLyricsPDF] = useState(false);
  
  // Genre and mood options
  const genreOptions = ['hip hop', 'pop', 'rock', 'electronic', 'r&b', 'indie', 'country', 'jazz', 'classical'];
  const moodOptions = ['energetic', 'melancholic', 'uplifting', 'dark', 'chill', 'aggressive', 'romantic', 'nostalgic'];
  const styleOptions = [
    { value: 'realistic', label: 'Realistic' },
    { value: 'abstract', label: 'Abstract' },
    { value: 'cinematic', label: 'Cinematic' },
    { value: 'illustrated', label: 'Illustrated' },
    { value: 'purple-gold aesthetic', label: 'Purple-Gold Aesthetic' }
  ];

  // Ensure we use the correct sessionId from props
  const currentSessionId = sessionId;

  // Load existing data from session
  useEffect(() => {
    if (sessionData.metadata) {
      if (sessionData.metadata.track_title) setTrackTitle(sessionData.metadata.track_title);
      if (sessionData.metadata.artist_name) setArtistName(sessionData.metadata.artist_name);
      if (sessionData.metadata.genre) setGenre(sessionData.metadata.genre);
      if (sessionData.metadata.mood) setMood(sessionData.metadata.mood);
    }
  }, [sessionData]);

  // Fetch release pack data
  const fetchReleasePack = async () => {
    if (!currentSessionId) return;
    
    setLoadingPack(true);
    try {
      const pack = await api.getReleasePack(currentSessionId);
      if (pack) {
        setReleasePack(pack);
        
        // Set cover art if available
        if (pack.coverArt) {
          setSelectedCover(pack.coverArt);
        }
      }
    } catch (err) {
      console.error('Failed to fetch release pack:', err);
    } finally {
      setLoadingPack(false);
    }
  };

  // Load release pack on mount and when sessionId changes
  useEffect(() => {
    if (currentSessionId) {
      fetchReleasePack();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSessionId]);

  // Helper to get complete URL for files
  const getFileUrl = (filePath) => {
    if (!filePath) return null;
    // If already a complete URL, return as is
    if (filePath.startsWith('http://') || filePath.startsWith('https://')) {
      return filePath;
    }
    // If starts with /media, prepend API base
    if (filePath.startsWith('/media')) {
      return `/api${filePath}`;
    }
    // Otherwise, assume it's a relative path
    return `/api${filePath}`;
  };

  const handleGenerateCover = async () => {
    if (!trackTitle || !artistName) {
      voice.speak('Please enter track title and artist name first');
      return;
    }

    setGeneratingCover(true);
    try {
      voice.speak("Generating cover art...");
      const result = await api.generateReleaseCover(currentSessionId, trackTitle, artistName, genre, mood, coverStyle);
      
      if (result.data && result.data.images && result.data.images.length > 0) {
        setCoverImages(result.data.images);
        setSelectedCover(result.data.images[0]);
        // Auto-select first cover
        await api.selectReleaseCover(currentSessionId, result.data.images[0]);
        // Refresh release pack
        await fetchReleasePack();
        voice.speak(`Generated ${result.data.images.length} cover art options`);
      } else {
        voice.speak('Failed to generate cover art');
      }
    } catch (err) {
      console.error('Cover generation error:', err);
      voice.speak('Failed to generate cover art. Try again.');
    } finally {
      setGeneratingCover(false);
    }
  };

  const handleGenerateCopy = async () => {
    if (!trackTitle || !artistName) {
      voice.speak('Please enter track title and artist name first');
      return;
    }

    setGeneratingCopy(true);
    try {
      voice.speak("Generating release copy...");
      const lyrics = sessionData.lyricsData || sessionData.lyrics || '';
      await api.generateReleaseCopy(currentSessionId, trackTitle, artistName, genre, mood, lyrics);
      
      // Refresh release pack
      await fetchReleasePack();
      voice.speak("Release copy generated");
    } catch (err) {
      console.error('Copy generation error:', err);
      voice.speak('Failed to generate release copy');
    } finally {
      setGeneratingCopy(false);
    }
  };

  const handleGenerateMetadata = async () => {
    setGeneratingMetadata(true);
    try {
      const result = await api.generateReleaseMetadata(
        currentSessionId, trackTitle, artistName, mood, genre, explicit, releaseDate
      );
      
      // PHASE 8.4: Check for paywall
      if (openUpgradeModal && !handlePaywall(result, openUpgradeModal)) {
        setGeneratingMetadata(false);
        return;
      }
      
      // Refresh release pack
      await fetchReleasePack();
      voice.speak("Metadata generated");
    } catch (err) {
      console.error('Metadata generation error:', err);
      
      // PHASE 8.4: Check for paywall error
      if (openUpgradeModal && err.isPaywall && err.errorData) {
        if (!handlePaywall(err.errorData, openUpgradeModal)) {
          setGeneratingMetadata(false);
          return;
        }
      }
      
      voice.speak('Failed to generate metadata');
    } finally {
      setGeneratingMetadata(false);
    }
  };

  const handleGenerateLyricsPDF = async () => {
    try {
      const lyrics = sessionData.lyricsData || sessionData.lyrics || '';
      if (!lyrics || !lyrics.trim()) {
        voice.speak('No lyrics found to generate PDF');
        return;
      }
      
      setGeneratingLyricsPDF(true);
      await api.generateLyricsPDF(currentSessionId, trackTitle, artistName, lyrics);
      
      // Refresh release pack
      await fetchReleasePack();
      voice.speak("Lyrics PDF generated");
    } catch (err) {
      console.error('Lyrics PDF generation error:', err);
      voice.speak('Failed to generate lyrics PDF');
    } finally {
      setGeneratingLyricsPDF(false);
    }
  };

  const handleSelectCover = async (url) => {
    setSelectedCover(url);
    try {
      await api.selectReleaseCover(currentSessionId, url);
      // Refresh release pack
      await fetchReleasePack();
    } catch (err) {
      console.error('Failed to select cover:', err);
    }
  };

  const handleDownloadAll = async () => {
    try {
      voice.speak("Preparing release pack...");
      const result = await api.downloadAllReleaseFiles(currentSessionId);
      if (result && result.zip_url) {
        const zipUrl = getFileUrl(result.zip_url);
        // Trigger download
        window.open(zipUrl, '_blank');
        // Mark release stage as complete ONLY after successful ZIP generation
        if (completeStage) {
          completeStage('release');
        }
        voice.speak("Release pack ready");
      }
    } catch (err) {
      console.error('ZIP generation error:', err);
      voice.speak('Failed to generate release pack');
    }
  };

  const coverArtUrl = releasePack?.coverArt ? getFileUrl(releasePack.coverArt) : null;

  return (
    <StageWrapper 
      title="Release Pack" 
      icon="📦" 
      onClose={onClose}
      onNext={onNext}
      voice={voice}
    >
      <div className="stage-scroll-container">
        <div className="flex flex-col gap-8 p-6 md:p-10 max-w-4xl mx-auto">
          
          {/* Cover Art Preview Section */}
          <div className="space-y-4">
            <h2 className="text-lg text-studio-gold font-montserrat font-semibold">Cover Art Preview</h2>
            
            {coverImages.length > 0 ? (
              <div className="grid grid-cols-2 gap-4">
                {coverImages.map((url, index) => (
                  <motion.div
                    key={index}
                    onClick={() => handleSelectCover(url)}
                    className={`aspect-square rounded-xl overflow-hidden border-2 cursor-pointer transition-all ${
                      selectedCover === url 
                        ? 'border-studio-red' 
                        : 'border-transparent hover:border-studio-white/40'
                    }`}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <img src={getFileUrl(url)} alt={`Cover option ${index + 1}`} className="w-full h-full object-cover" />
                  </motion.div>
                ))}
              </div>
            ) : coverArtUrl ? (
              <div className="aspect-square max-w-md mx-auto rounded-lg overflow-hidden border border-studio-white/10">
                <img src={coverArtUrl} alt="Selected cover art" className="w-full h-full object-cover" />
              </div>
            ) : (
              <div className="aspect-square max-w-md mx-auto bg-studio-gray/30 rounded-lg border border-studio-white/10 flex items-center justify-center">
                <p className="text-sm text-studio-white/60 font-poppins">No cover art generated yet</p>
              </div>
            )}
          </div>

          {/* Form Inputs */}
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-studio-white/60 font-montserrat mb-2">
                  Track Title
                </label>
                <input
                  type="text"
                  value={trackTitle}
                  onChange={(e) => setTrackTitle(e.target.value)}
                  className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                           text-studio-white font-poppins focus:outline-none focus:border-studio-red"
                  placeholder="Enter track title"
                />
              </div>

              <div>
                <label className="block text-xs text-studio-white/60 font-montserrat mb-2">
                  Artist Name
                </label>
                <input
                  type="text"
                  value={artistName}
                  onChange={(e) => setArtistName(e.target.value)}
                  className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                           text-studio-white font-poppins focus:outline-none focus:border-studio-red"
                  placeholder="Enter artist name"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-studio-white/60 font-montserrat mb-2">
                  Genre
                </label>
                <select
                  value={genre}
                  onChange={(e) => setGenre(e.target.value)}
                  className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                           text-studio-white font-poppins focus:outline-none focus:border-studio-red"
                >
                  {genreOptions.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs text-studio-white/60 font-montserrat mb-2">
                  Mood
                </label>
                <select
                  value={mood}
                  onChange={(e) => setMood(e.target.value)}
                  className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                           text-studio-white font-poppins focus:outline-none focus:border-studio-red"
                >
                  {moodOptions.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-studio-white/60 font-montserrat mb-2">
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
                <label className="block text-xs text-studio-white/60 font-montserrat mb-2">
                  Explicit
                </label>
                <div className="flex items-center gap-4 mt-2">
                  <button
                    onClick={() => setExplicit(true)}
                    className={`px-6 py-3 rounded-lg font-poppins transition-all ${
                      explicit 
                        ? 'bg-studio-red text-studio-white' 
                        : 'bg-studio-gray/50 text-studio-white/60 hover:bg-studio-gray/70'
                    }`}
                  >
                    Yes
                  </button>
                  <button
                    onClick={() => setExplicit(false)}
                    className={`px-6 py-3 rounded-lg font-poppins transition-all ${
                      !explicit 
                        ? 'bg-studio-red text-studio-white' 
                        : 'bg-studio-gray/50 text-studio-white/60 hover:bg-studio-gray/70'
                    }`}
                  >
                    No
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Cover Style Selection */}
          <div>
            <label className="block text-xs text-studio-white/60 font-montserrat mb-2">
              Cover Art Style
            </label>
            <select
              value={coverStyle}
              onChange={(e) => setCoverStyle(e.target.value)}
              className="w-full px-4 py-3 bg-studio-gray/50 border border-studio-white/20 rounded-lg
                       text-studio-white font-poppins focus:outline-none focus:border-studio-red"
            >
              {styleOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <motion.button
              onClick={handleGenerateCover}
              disabled={generatingCover || !trackTitle || !artistName}
              className="w-full py-4 rounded-lg font-montserrat font-semibold bg-gradient-to-r from-purple-600 to-pink-600
                       hover:from-purple-500 hover:to-pink-500 text-studio-white transition-all duration-300
                       disabled:opacity-50 disabled:cursor-not-allowed"
              whileHover={!generatingCover ? { scale: 1.02 } : {}}
              whileTap={!generatingCover ? { scale: 0.98 } : {}}
            >
              {generatingCover ? '✨ Generating...' : '✨ Generate Cover Art'}
            </motion.button>

            <motion.button
              onClick={handleGenerateCopy}
              disabled={generatingCopy || !trackTitle || !artistName}
              className="w-full py-4 rounded-lg font-montserrat font-semibold bg-gradient-to-r from-blue-600 to-cyan-600
                       hover:from-blue-500 hover:to-cyan-500 text-studio-white transition-all duration-300
                       disabled:opacity-50 disabled:cursor-not-allowed"
              whileHover={!generatingCopy ? { scale: 1.02 } : {}}
              whileTap={!generatingCopy ? { scale: 0.98 } : {}}
            >
              {generatingCopy ? '📝 Generating...' : '📝 Generate Release Copy'}
            </motion.button>
          </div>

          {/* Additional Action Buttons */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <motion.button
              onClick={handleGenerateLyricsPDF}
              disabled={generatingLyricsPDF || (!sessionData.lyricsData && !sessionData.lyrics)}
              className="w-full py-3 rounded-lg font-montserrat font-semibold bg-studio-gray/50
                       hover:bg-studio-gray/70 text-studio-white transition-all duration-300
                       disabled:opacity-50 disabled:cursor-not-allowed"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {generatingLyricsPDF ? '📄 Generating...' : '📄 Generate Lyrics PDF'}
            </motion.button>

            <motion.button
              onClick={handleGenerateMetadata}
              disabled={generatingMetadata || !trackTitle || !artistName}
              className="w-full py-3 rounded-lg font-montserrat font-semibold bg-studio-gray/50
                       hover:bg-studio-gray/70 text-studio-white transition-all duration-300
                       disabled:opacity-50 disabled:cursor-not-allowed"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {generatingMetadata ? '📋 Generating...' : '📋 Generate Metadata'}
            </motion.button>
          </div>

          {/* Release Pack Files Section */}
          <div className="space-y-6 border-t border-studio-white/10 pt-6">
            <h3 className="text-lg text-studio-gold font-montserrat mb-2">
              Your Release Pack
            </h3>
            <p className="text-sm text-studio-white/70 font-poppins mb-4">
              Everything you need to publish: artwork, metadata, audio, and lyrics.
            </p>

            {loadingPack ? (
              <p className="text-sm text-studio-white/60 font-poppins">Loading release pack...</p>
            ) : releasePack && (
              <div className="space-y-4">
                {/* Cover Art */}
                {releasePack.coverArt && (
                  <div className="space-y-2">
                    <h4 className="text-sm text-studio-white/90 font-montserrat">Cover Art</h4>
                    <div className="aspect-square max-w-xs rounded-lg overflow-hidden border border-studio-white/10">
                      <img 
                        src={getFileUrl(releasePack.coverArt)} 
                        alt="Release cover art" 
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          console.error('Failed to load cover art:', releasePack.coverArt);
                          e.target.style.display = 'none';
                        }}
                      />
                    </div>
                    <a 
                      href={getFileUrl(releasePack.coverArt)} 
                      download 
                      className="underline text-studio-gold text-sm hover:text-studio-gold/80"
                    >
                      Download Cover Art
                    </a>
                  </div>
                )}

                {/* Release Copy */}
                {releasePack.releaseCopy && (
                  <div className="space-y-2">
                    <h4 className="text-sm text-studio-white/90 font-montserrat">Release Copy</h4>
                    <div className="space-y-2">
                      {releasePack.releaseCopy.description && (
                        <a
                          href={getFileUrl(releasePack.releaseCopy.description)}
                          download
                          className="block px-4 py-2 bg-studio-gray/30 hover:bg-studio-gray/50 rounded-lg
                                   text-studio-white font-poppins text-sm transition-all underline text-studio-gold"
                        >
                          Download Release Description
                        </a>
                      )}
                      {releasePack.releaseCopy.pitch && (
                        <a
                          href={getFileUrl(releasePack.releaseCopy.pitch)}
                          download
                          className="block px-4 py-2 bg-studio-gray/30 hover:bg-studio-gray/50 rounded-lg
                                   text-studio-white font-poppins text-sm transition-all underline text-studio-gold"
                        >
                          Download Press Pitch
                        </a>
                      )}
                      {releasePack.releaseCopy.tagline && (
                        <a
                          href={getFileUrl(releasePack.releaseCopy.tagline)}
                          download
                          className="block px-4 py-2 bg-studio-gray/30 hover:bg-studio-gray/50 rounded-lg
                                   text-studio-white font-poppins text-sm transition-all underline text-studio-gold"
                        >
                          Download Tagline
                        </a>
                      )}
                    </div>
                  </div>
                )}

                {/* Metadata */}
                {releasePack.metadataFile && (
                  <div className="space-y-2">
                    <h4 className="text-sm text-studio-white/90 font-montserrat">Metadata</h4>
                    <a
                      href={getFileUrl(releasePack.metadataFile)}
                      download
                      className="block px-4 py-2 bg-studio-gray/30 hover:bg-studio-gray/50 rounded-lg
                               text-studio-white font-poppins text-sm transition-all underline text-studio-gold"
                    >
                      Download Metadata
                    </a>
                  </div>
                )}

                {/* Lyrics PDF */}
                {releasePack.lyricsPdf && (
                  <div className="space-y-2">
                    <h4 className="text-sm text-studio-white/90 font-montserrat">Lyrics PDF</h4>
                    <a
                      href={getFileUrl(releasePack.lyricsPdf)}
                      download
                      className="block px-4 py-2 bg-studio-gray/30 hover:bg-studio-gray/50 rounded-lg
                               text-studio-white font-poppins text-sm transition-all underline text-studio-gold"
                    >
                      Download Lyrics PDF
                    </a>
                  </div>
                )}

                {/* Release Audio */}
                {releasePack.releaseAudio && (
                  <div className="space-y-2">
                    <h4 className="text-sm text-studio-white/90 font-montserrat">Final Release Audio</h4>
                    <a
                      href={getFileUrl(releasePack.releaseAudio)}
                      download
                      className="block px-4 py-2 bg-studio-gray/30 hover:bg-studio-gray/50 rounded-lg
                               text-studio-white font-poppins text-sm transition-all underline text-studio-gold"
                    >
                      Download Release Audio
                    </a>
                  </div>
                )}

                {!releasePack.coverArt && !releasePack.releaseCopy && !releasePack.metadataFile && !releasePack.lyricsPdf && !releasePack.releaseAudio && (
                  <p className="text-sm text-studio-white/60 font-poppins">No release files yet. Generate cover art, metadata, copy, or lyrics to see files here.</p>
                )}
              </div>
            )}
          </div>

          {/* Download All Button */}
          <div className="border-t border-studio-white/10 pt-6">
            <motion.button
              onClick={handleDownloadAll}
              className="w-full py-4 rounded-lg font-montserrat font-semibold bg-studio-red
                       hover:bg-studio-red/80 text-studio-white transition-all duration-300"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              📦 Download All (ZIP)
            </motion.button>
          </div>

        </div>
      </div>
    </StageWrapper>
  );
}
