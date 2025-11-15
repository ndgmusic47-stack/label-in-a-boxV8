import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { api } from '../../utils/api';
import StageWrapper from './StageWrapper';

export default function ReleaseStage({ sessionData, updateSessionData, voice, onClose, sessionId, completeStage }) {
  // Form inputs
  const [trackTitle, setTrackTitle] = useState(sessionData.trackTitle || sessionData.metadata?.track_title || '');
  const [artistName, setArtistName] = useState(sessionData.artistName || sessionData.metadata?.artist_name || 'NP22');
  const [genre, setGenre] = useState(sessionData.genre || sessionData.metadata?.genre || 'hip hop');
  const [mood, setMood] = useState(sessionData.mood || sessionData.metadata?.mood || 'energetic');
  const [releaseDate, setReleaseDate] = useState(sessionData.release_date || new Date().toISOString().split('T')[0]);
  const [explicit, setExplicit] = useState(sessionData.explicit || false);
  const [coverStyle, setCoverStyle] = useState('realistic');
  
  // Cover art
  const [coverImages, setCoverImages] = useState([]);
  const [selectedCover, setSelectedCover] = useState(null);
  const [generatingCover, setGeneratingCover] = useState(false);
  
  // Release files state
  const [releaseFiles, setReleaseFiles] = useState([]);
  const [releaseCopyFiles, setReleaseCopyFiles] = useState(null);
  const [generatingCopy, setGeneratingCopy] = useState(false);
  const [zipUrl, setZipUrl] = useState(null);
  
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

  // Load existing data from session
  useEffect(() => {
    if (sessionData.metadata) {
      if (sessionData.metadata.track_title) setTrackTitle(sessionData.metadata.track_title);
      if (sessionData.metadata.artist_name) setArtistName(sessionData.metadata.artist_name);
      if (sessionData.metadata.genre) setGenre(sessionData.metadata.genre);
      if (sessionData.metadata.mood) setMood(sessionData.metadata.mood);
    }
  }, [sessionData]);

  // Fetch release files dynamically
  const fetchReleaseFiles = async () => {
    try {
      const res = await api.listReleaseFiles(sessionId);
      if (res && res.files) {
        setReleaseFiles(res.files);
      } else if (Array.isArray(res)) {
        setReleaseFiles(res);
      }
    } catch (err) {
      console.error('Failed to fetch release files:', err);
    }
  };

  // Load release files on mount
  useEffect(() => {
    if (sessionId) {
      fetchReleaseFiles();
    }
  }, [sessionId]);

  const handleGenerateCover = async () => {
    if (!trackTitle || !artistName) {
      voice.speak('Please enter track title and artist name first');
      return;
    }

    setGeneratingCover(true);
    try {
      voice.speak("Generating cover art...");
      const result = await api.generateReleaseCover(sessionId, trackTitle, artistName, genre, mood, coverStyle);
      
      if (result.data && result.data.images && result.data.images.length > 0) {
        setCoverImages(result.data.images);
        setSelectedCover(result.data.images[0]); // Select first by default
        // Auto-select first cover
        await api.selectReleaseCover(sessionId, result.data.images[0]);
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
      const result = await api.generateReleaseCopy(sessionId, trackTitle, artistName, genre, mood, lyrics);
      
      // Update release copy files state
      if (result.data) {
        setReleaseCopyFiles({
          description_url: result.data.description_url,
          pitch_url: result.data.pitch_url,
          tagline_url: result.data.tagline_url
        });
      }
      
      // Refresh release files list
      await fetchReleaseFiles();
      
      voice.speak("Release copy generated");
    } catch (err) {
      console.error('Copy generation error:', err);
      voice.speak('Failed to generate release copy');
    } finally {
      setGeneratingCopy(false);
    }
  };

  const handleGenerateMetadata = async () => {
    try {
      const result = await api.generateReleaseMetadata(
        sessionId, trackTitle, artistName, mood, genre, explicit, releaseDate
      );
      
      // Refresh release files list
      await fetchReleaseFiles();
      
      voice.speak("Metadata generated");
    } catch (err) {
      console.error('Metadata generation error:', err);
      voice.speak('Failed to generate metadata');
    }
  };

  const handleGenerateLyricsPDF = async () => {
    try {
      const lyrics = sessionData.lyricsData || sessionData.lyrics || '';
      if (!lyrics || !lyrics.trim()) {
        voice.speak('No lyrics found to generate PDF');
        return;
      }
      
      await api.generateLyricsPDF(sessionId, trackTitle, artistName, lyrics);
      
      // Refresh release files list
      await fetchReleaseFiles();
      
      voice.speak("Lyrics PDF generated");
    } catch (err) {
      console.error('Lyrics PDF generation error:', err);
      voice.speak('Failed to generate lyrics PDF');
    }
  };

  const handleSelectCover = async (url) => {
    setSelectedCover(url);
    // Save selected cover to backend
    try {
      await api.selectReleaseCover(sessionId, url);
      // Refresh release files list
      await fetchReleaseFiles();
    } catch (err) {
      console.error('Failed to select cover:', err);
    }
  };

  const handleDownloadAll = async () => {
    try {
      voice.speak("Preparing release pack...");
      const result = await api.downloadAllReleaseFiles(sessionId);
      if (result.zip_url) {
        setZipUrl(result.zip_url);
        // Trigger download
        window.open(result.zip_url, '_blank');
        voice.speak("Release pack ready");
      }
    } catch (err) {
      console.error('ZIP generation error:', err);
      voice.speak('Failed to generate release pack');
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
        <div className="flex flex-col gap-8 p-6 md:p-10 max-w-4xl mx-auto">
          
          {/* Cover Art Preview Section */}
          <div className="space-y-4">
            <h2 className="font-montserrat text-xl text-studio-white font-semibold">Cover Art Preview</h2>
            
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
                    <img src={url} alt={`Cover option ${index + 1}`} className="w-full h-full object-cover" />
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="aspect-square max-w-md mx-auto bg-studio-gray/30 rounded-lg border border-studio-white/10 flex items-center justify-center">
                <p className="text-studio-white/40 font-poppins">No cover art generated yet</p>
              </div>
            )}
          </div>

          {/* Form Inputs */}
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                  placeholder="Enter track title"
                />
              </div>

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
                  placeholder="Enter artist name"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
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
                <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
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
            <label className="block text-sm font-montserrat text-studio-white/60 mb-2">
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
              disabled={!sessionData.lyricsData && !sessionData.lyrics}
              className="w-full py-3 rounded-lg font-montserrat font-semibold bg-studio-gray/50
                       hover:bg-studio-gray/70 text-studio-white transition-all duration-300
                       disabled:opacity-50 disabled:cursor-not-allowed"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              📄 Generate Lyrics PDF
            </motion.button>

            <motion.button
              onClick={handleGenerateMetadata}
              disabled={!trackTitle || !artistName}
              className="w-full py-3 rounded-lg font-montserrat font-semibold bg-studio-gray/50
                       hover:bg-studio-gray/70 text-studio-white transition-all duration-300
                       disabled:opacity-50 disabled:cursor-not-allowed"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              📋 Generate Metadata
            </motion.button>
          </div>

          {/* Release Pack Files Section */}
          <div className="space-y-6 border-t border-studio-white/10 pt-6">
            <h2 className="font-montserrat text-xl text-studio-white font-semibold">Release Pack Files</h2>

            {releaseFiles.length > 0 ? (
              <div className="space-y-2">
                {releaseFiles
                  .filter(f => f.includes("final_cover"))
                  .map((f, idx) => (
                    <a key={idx} href={f} download className="text-sm text-studio-white/70 underline">
                      {f.split("/").pop()}
                    </a>
                  ))}
                {releaseFiles.map((file, idx) => {
                  const fileName = file.split('/').pop();
                  return (
                    <a
                      key={idx}
                      href={file}
                      download
                      className="block px-4 py-2 bg-studio-gray/30 hover:bg-studio-gray/50 rounded-lg
                               text-studio-white font-poppins text-sm transition-all"
                    >
                      • {fileName} (Download)
                    </a>
                  );
                })}
              </div>
            ) : (
              <p className="text-studio-white/40 font-poppins">No release files yet. Generate cover art, metadata, copy, or lyrics to see files here.</p>
            )}

            {/* Release Copy Display (from state) */}
            {releaseCopyFiles && (
              <div>
                <h3 className="font-montserrat text-studio-white/80 mb-2">Release Copy:</h3>
                <div className="space-y-2">
                  {releaseCopyFiles.description_url && (
                    <a
                      href={releaseCopyFiles.description_url}
                      download
                      className="block px-4 py-2 bg-studio-gray/30 hover:bg-studio-gray/50 rounded-lg
                               text-studio-white font-poppins text-sm transition-all"
                    >
                      • release_description.txt (Download)
                    </a>
                  )}
                  {releaseCopyFiles.pitch_url && (
                    <a
                      href={releaseCopyFiles.pitch_url}
                      download
                      className="block px-4 py-2 bg-studio-gray/30 hover:bg-studio-gray/50 rounded-lg
                               text-studio-white font-poppins text-sm transition-all"
                    >
                      • press_pitch.txt (Download)
                    </a>
                  )}
                  {releaseCopyFiles.tagline_url && (
                    <a
                      href={releaseCopyFiles.tagline_url}
                      download
                      className="block px-4 py-2 bg-studio-gray/30 hover:bg-studio-gray/50 rounded-lg
                               text-studio-white font-poppins text-sm transition-all"
                    >
                      • tagline.txt (Download)
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Download All Button (Desktop Only) */}
          <div className="border-t border-studio-white/10 pt-6">
            <motion.button
              onClick={handleDownloadAll}
              className="w-full py-4 rounded-lg font-montserrat font-semibold bg-studio-red
                       hover:bg-studio-red/80 text-studio-white transition-all duration-300"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              📦 Download All (ZIP — Desktop Only)
            </motion.button>
          </div>

        </div>
      </div>
    </StageWrapper>
  );
}
