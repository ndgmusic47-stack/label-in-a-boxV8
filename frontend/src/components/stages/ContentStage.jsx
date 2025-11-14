import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../../utils/api';
import StageWrapper from './StageWrapper';

export default function ContentStage({ sessionId, sessionData, updateSessionData, voice, onClose }) {
  const [activeTab, setActiveTab] = useState('social');
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const [videoFiles, setVideoFiles] = useState([]);
  const [audioFile, setAudioFile] = useState(null);
  const [beatData, setBeatData] = useState(null);
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoResult, setVideoResult] = useState(null);
  
  const [platforms, setPlatforms] = useState({});
  const [scheduledPosts, setScheduledPosts] = useState([]);
  const [selectedPlatform, setSelectedPlatform] = useState('instagram');
  const [scheduleLoading, setScheduleLoading] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    
    try {
      voice.speak('Generating social media content for your track...');
      
      // Phase 2.2: handleResponse extracts data automatically
      const result = await api.generateContent(
        sessionData.trackTitle || 'My Track',
        sessionData.artist || 'Artist',
        sessionId
      );
      
      // Backend returns {captions: [{hook, text, hashtags}]}
      setContent({
        hooks: result.captions?.map(c => c.hook) || [],
        captions: result.captions?.map(c => c.text) || [],
        hashtags: result.captions?.[0]?.hashtags || []
      });
      voice.speak('Your content ideas are ready!');
    } catch (err) {
      voice.speak('Failed to generate content. Try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!content && activeTab === 'social') {
      handleGenerate();
      loadPlatforms();
      loadScheduledPosts();
    }
  }, [activeTab]);

  const loadPlatforms = async () => {
    try {
      // Phase 2.2: handleResponse extracts data automatically
      const result = await api.getSocialPlatforms();
      setPlatforms(result.platforms || {});
    } catch (err) {
      console.error('Failed to load platforms:', err);
    }
  };

  const loadScheduledPosts = async () => {
    try {
      const result = await api.getScheduledPosts(sessionId);
      if (result.status === 'ready') {
        setScheduledPosts(result.posts);
      }
    } catch (err) {
      console.error('Failed to load scheduled posts:', err);
    }
  };

  const handleSchedulePost = async (content, scheduledTime, hashtags) => {
    setScheduleLoading(true);
    try {
      voice.speak(`Scheduling post for ${selectedPlatform}...`);
      
      const result = await api.schedulePost(
        sessionId,
        selectedPlatform,
        content,
        scheduledTime
      );
      
      if (result.status === 'scheduled') {
        voice.speak(result.message);
        loadScheduledPosts();
      }
    } catch (err) {
      voice.speak('Scheduling failed. Try again.');
    } finally {
      setScheduleLoading(false);
    }
  };

  const handleCancelPost = async (postId) => {
    try {
      voice.speak('Cancelling post...');
      const result = await api.cancelPost(sessionId, postId);
      if (result.status === 'cancelled') {
        voice.speak('Post cancelled');
        loadScheduledPosts();
      }
    } catch (err) {
      voice.speak('Cancel failed');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    voice.speak('Copied to clipboard');
  };

  const handleVideoFileChange = (e) => {
    const files = Array.from(e.target.files);
    setVideoFiles(files);
    voice.speak(`${files.length} video clip${files.length > 1 ? 's' : ''} selected`);
  };

  const handleAudioFileChange = (e) => {
    const file = e.target.files[0];
    setAudioFile(file);
    voice.speak('Audio track selected');
  };

  const handleAnalyzeBeats = async () => {
    if (!audioFile) {
      voice.speak('Please upload an audio track first');
      return;
    }

    setVideoLoading(true);
    try {
      voice.speak('Analyzing beats in your track...');
      
      const formData = new FormData();
      formData.append('session_id', sessionData.sessionId);
      formData.append('audio_file', audioFile);
      
      videoFiles.forEach(file => {
        formData.append('video_files', file);
      });

      const result = await api.analyzeVideoBeats(formData);
      
      if (result.status === 'analyzed') {
        setBeatData(result);
        voice.speak(`Found ${result.beat_count} beats at ${result.beat_data.tempo.toFixed(0)} BPM. ${result.suggestions.tips[0]}`);
      }
    } catch (err) {
      voice.speak('Beat analysis failed. Try again.');
    } finally {
      setVideoLoading(false);
    }
  };

  const handleCreateBeatSync = async () => {
    if (!beatData) {
      voice.speak('Analyze beats first');
      return;
    }

    setVideoLoading(true);
    try {
      voice.speak('Creating beat-synced video...');
      
      const result = await api.createBeatSyncVideo(sessionData.sessionId, 'energetic');
      
      if (result.status === 'created') {
        setVideoResult(result);
        voice.speak(`Beat-synced video created with ${result.clip_count} clips!`);
      }
    } catch (err) {
      voice.speak('Video creation failed. Try again.');
    } finally {
      setVideoLoading(false);
    }
  };

  const handleExportVideo = async (quality = 'high') => {
    if (!videoResult) {
      voice.speak('Create a video first');
      return;
    }

    setVideoLoading(true);
    try {
      voice.speak(`Exporting video in ${quality} quality...`);
      
      const result = await api.exportVideo(sessionData.sessionId, 'mp4', quality);
      
      if (result.status === 'exported') {
        voice.speak(`Video exported! ${result.file_size_mb} megabytes.`);
      }
    } catch (err) {
      voice.speak('Export failed. Try again.');
    } finally {
      setVideoLoading(false);
    }
  };

  return (
    <StageWrapper 
      title="Content & Video" 
      icon="🎬" 
      onClose={onClose}
      voice={voice}
    >
      <div className="flex flex-col h-full">
        {/* Tabs */}
        <div className="flex gap-2 p-4 border-b border-studio-white/10">
          <TabButton
            active={activeTab === 'social'}
            onClick={() => setActiveTab('social')}
            icon="📱"
            label="Social Content"
          />
          {/* Video Editor tab hidden until backend is ready */}
        </div>

        {/* Content */}
        <div className="stage-scroll-container">
          <AnimatePresence mode="wait">
            {activeTab === 'social' && (
              <SocialContentTab
                loading={loading}
                content={content}
                onGenerate={handleGenerate}
                onCopy={copyToClipboard}
                voice={voice}
                platforms={platforms}
                selectedPlatform={selectedPlatform}
                onPlatformChange={setSelectedPlatform}
                onSchedulePost={handleSchedulePost}
                scheduledPosts={scheduledPosts}
                onCancelPost={handleCancelPost}
                scheduleLoading={scheduleLoading}
              />
            )}
          </AnimatePresence>
        </div>
      </div>
    </StageWrapper>
  );
}

function TabButton({ active, onClick, icon, label }) {
  return (
    <motion.button
      onClick={onClick}
      className={`
        px-6 py-2 rounded-lg font-montserrat transition-all
        ${active 
          ? 'bg-studio-red text-studio-white' 
          : 'bg-studio-gray/30 text-studio-white/60 hover:bg-studio-gray/50'
        }
      `}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <span className="mr-2">{icon}</span>
      {label}
    </motion.button>
  );
}

function SocialContentTab({ 
  loading, 
  content, 
  onGenerate, 
  onCopy, 
  voice,
  platforms,
  selectedPlatform,
  onPlatformChange,
  onSchedulePost,
  scheduledPosts,
  onCancelPost,
  scheduleLoading
}) {
  const [selectedContent, setSelectedContent] = useState('');
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleTime, setScheduleTime] = useState('12:00');

  const handleSchedule = () => {
    if (!selectedContent || !scheduleDate) {
      voice.speak('Please select content and a date first');
      return;
    }

    const scheduledTime = `${scheduleDate}T${scheduleTime}:00Z`;
    const hashtags = content?.hashtags || [];
    onSchedulePost(selectedContent, scheduledTime, hashtags);
  };

  return (
    <motion.div
      key="social"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="flex flex-col gap-6 p-6 md:p-10"
    >
      <div className="text-6xl mb-4 text-center">
        📱
      </div>

      <div className="w-full max-w-4xl mx-auto space-y-8">
        {loading ? (
          <p className="text-studio-white/60 font-poppins text-center">Generating content...</p>
        ) : content ? (
          <>
            {/* Content Generation */}
            <div className="space-y-6">
              <Section title="Hooks" items={content.hooks} onCopy={onCopy} onSelect={setSelectedContent} />
              <Section title="Captions" items={content.captions} onCopy={onCopy} onSelect={setSelectedContent} />
              
              <div>
                <h3 className="text-studio-red font-montserrat font-semibold text-lg mb-3">
                  Hashtags
                </h3>
                <div className="flex flex-wrap gap-2">
                  {content.hashtags?.map((tag, i) => (
                    <motion.button
                      key={i}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.25, ease: "easeOut", delay: i * 0.05 }}
                      onClick={() => onCopy(tag)}
                      className="px-3 py-1 bg-studio-gray/50 hover:bg-studio-gray
                               text-sm text-studio-white/80 rounded-full
                               border border-studio-white/10 hover:border-studio-red/50
                               transition-all duration-200"
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      {tag}
                    </motion.button>
                  ))}
                </div>
              </div>

              <motion.button
                onClick={onGenerate}
                className="w-full py-3 bg-studio-gray hover:bg-studio-gray/80
                         text-studio-white font-montserrat rounded-lg"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                Generate New Content
              </motion.button>
            </div>

            {/* Scheduling Section */}
            <div className="border-t border-studio-white/10 pt-8 space-y-4">
              <h3 className="text-studio-red font-montserrat font-semibold text-xl mb-4">
                📅 Schedule Post
              </h3>

              {/* Platform Selector */}
              <div>
                <label className="text-studio-white/80 font-montserrat text-sm mb-2 block">
                  Platform
                </label>
                <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
                  {Object.keys(platforms).map(platform => (
                    <motion.button
                      key={platform}
                      onClick={() => onPlatformChange(platform)}
                      className={`
                        py-2 px-3 rounded-lg font-montserrat capitalize text-sm
                        ${selectedPlatform === platform
                          ? 'bg-studio-red text-studio-white'
                          : 'bg-studio-gray/30 text-studio-white/60 hover:bg-studio-gray/50'
                        }
                      `}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      {platform}
                    </motion.button>
                  ))}
                </div>
              </div>

              {/* Date & Time */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-studio-white/80 font-montserrat text-sm mb-2 block">
                    Date
                  </label>
                  <input
                    type="date"
                    value={scheduleDate}
                    onChange={(e) => setScheduleDate(e.target.value)}
                    className="w-full p-3 bg-studio-gray/30 border border-studio-white/10
                             text-studio-white rounded-lg focus:border-studio-red/50
                             focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-studio-white/80 font-montserrat text-sm mb-2 block">
                    Time
                  </label>
                  <input
                    type="time"
                    value={scheduleTime}
                    onChange={(e) => setScheduleTime(e.target.value)}
                    className="w-full p-3 bg-studio-gray/30 border border-studio-white/10
                             text-studio-white rounded-lg focus:border-studio-red/50
                             focus:outline-none"
                  />
                </div>
              </div>

              {/* Schedule Button - Disabled with tooltip */}
              <div className="relative group">
                <motion.button
                  disabled={true}
                  className="w-full py-3 rounded-lg font-montserrat
                           bg-studio-gray/30 text-studio-white/30 cursor-not-allowed"
                  title="Scheduling requires TikTok / Instagram API integration."
                >
                  Schedule Post
                </motion.button>
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-studio-gray text-studio-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                  Scheduling requires TikTok / Instagram API integration.
                </div>
              </div>

              {selectedContent && (
                <div className="p-4 bg-studio-gray/20 rounded-lg border border-studio-white/10">
                  <p className="text-studio-white/60 text-sm mb-1">Selected Content:</p>
                  <p className="text-studio-white/90 text-sm">{selectedContent.substring(0, 100)}...</p>
                </div>
              )}
            </div>

            {/* Scheduled Posts */}
            {scheduledPosts.length > 0 && (
              <div className="border-t border-studio-white/10 pt-8">
                <h3 className="text-studio-red font-montserrat font-semibold text-xl mb-4">
                  📌 Scheduled Posts ({scheduledPosts.length})
                </h3>
                <div className="space-y-3">
                  {scheduledPosts.map((post, i) => (
                    <motion.div
                      key={post.post_id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.1 }}
                      className="p-4 bg-studio-gray/30 rounded-lg border border-studio-white/10
                               flex justify-between items-start"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="px-2 py-1 bg-studio-red/20 text-studio-red
                                         text-xs rounded-full capitalize">
                            {post.platform}
                          </span>
                          <span className="text-studio-white/60 text-xs">
                            {new Date(post.scheduled_time).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-studio-white/80 text-sm">
                          {post.content.substring(0, 80)}...
                        </p>
                      </div>
                      <motion.button
                        onClick={() => onCancelPost(post.post_id)}
                        className="ml-4 px-3 py-1 bg-studio-gray/50 hover:bg-studio-red/20
                                 text-studio-white/60 hover:text-studio-red text-sm rounded"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        Cancel
                      </motion.button>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : null}
      </div>
    </motion.div>
  );
}

function VideoEditorTab({
  videoFiles,
  audioFile,
  beatData,
  videoResult,
  loading,
  onVideoFileChange,
  onAudioFileChange,
  onAnalyzeBeats,
  onCreateBeatSync,
  onExportVideo,
  voice
}) {
  return (
    <motion.div
      key="video"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="flex flex-col gap-6 p-6 md:p-10"
    >
      <div className="text-6xl mb-4 text-center">
        🎬
      </div>

      <div className="w-full max-w-4xl mx-auto space-y-6">
        {/* Upload Section */}
        <div className="space-y-4">
          <h3 className="text-studio-red font-montserrat font-semibold text-lg">
            1. Upload Files
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FileUploadBox
              label="Video Clips"
              accept="video/*"
              multiple
              onChange={onVideoFileChange}
              fileCount={videoFiles.length}
              icon="🎥"
            />
            
            <FileUploadBox
              label="Audio Track"
              accept="audio/*"
              onChange={onAudioFileChange}
              fileCount={audioFile ? 1 : 0}
              icon="🎵"
            />
          </div>
        </div>

        {/* Beat Analysis Section */}
        <div className="space-y-4">
          <h3 className="text-studio-red font-montserrat font-semibold text-lg">
            2. Analyze Beats
          </h3>
          
          <motion.button
            onClick={onAnalyzeBeats}
            disabled={!audioFile || loading}
            className={`
              w-full py-3 rounded-lg font-montserrat transition-all
              ${!audioFile || loading
                ? 'bg-studio-gray/30 text-studio-white/30 cursor-not-allowed'
                : 'bg-studio-gray hover:bg-studio-red text-studio-white'
              }
            `}
            whileHover={!audioFile || loading ? {} : { scale: 1.02 }}
            whileTap={!audioFile || loading ? {} : { scale: 0.98 }}
          >
            {loading ? 'Analyzing...' : 'Detect Beats'}
          </motion.button>

          {beatData && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 bg-studio-gray/30 rounded-lg border border-studio-white/10"
            >
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-studio-white/60 text-sm">Tempo</p>
                  <p className="text-studio-white font-montserrat text-xl">
                    {beatData.beat_data.tempo.toFixed(0)} BPM
                  </p>
                </div>
                <div>
                  <p className="text-studio-white/60 text-sm">Beats Found</p>
                  <p className="text-studio-white font-montserrat text-xl">
                    {beatData.beat_count}
                  </p>
                </div>
              </div>
              
              <div className="space-y-2">
                <p className="text-studio-white/80 text-sm font-montserrat font-semibold">
                  AI Suggestions:
                </p>
                {beatData.suggestions.tips.slice(0, 3).map((tip, i) => (
                  <p key={i} className="text-studio-white/60 text-sm">
                    • {tip}
                  </p>
                ))}
              </div>
            </motion.div>
          )}
        </div>

        {/* Create Beat-Sync Video */}
        <div className="space-y-4">
          <h3 className="text-studio-red font-montserrat font-semibold text-lg">
            3. Create Beat-Synced Video
          </h3>
          
          <motion.button
            onClick={onCreateBeatSync}
            disabled={!beatData || loading}
            className={`
              w-full py-3 rounded-lg font-montserrat transition-all
              ${!beatData || loading
                ? 'bg-studio-gray/30 text-studio-white/30 cursor-not-allowed'
                : 'bg-studio-gray hover:bg-studio-red text-studio-white'
              }
            `}
            whileHover={!beatData || loading ? {} : { scale: 1.02 }}
            whileTap={!beatData || loading ? {} : { scale: 0.98 }}
          >
            {loading ? 'Creating...' : 'Auto-Edit to Beats'}
          </motion.button>

          {videoResult && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-4 bg-studio-gray/30 rounded-lg border border-studio-green/30"
            >
              <p className="text-studio-green text-sm mb-2">✓ Video Created</p>
              <p className="text-studio-white/80">
                {videoResult.message}
              </p>
            </motion.div>
          )}
        </div>

        {/* Export Section */}
        <div className="space-y-4">
          <h3 className="text-studio-red font-montserrat font-semibold text-lg">
            4. Export
          </h3>
          
          <div className="grid grid-cols-3 gap-3">
            {['high', 'medium', 'low'].map(quality => (
              <motion.button
                key={quality}
                onClick={() => onExportVideo(quality)}
                disabled={!videoResult || loading}
                className={`
                  py-3 rounded-lg font-montserrat transition-all capitalize
                  ${!videoResult || loading
                    ? 'bg-studio-gray/30 text-studio-white/30 cursor-not-allowed'
                    : 'bg-studio-gray hover:bg-studio-red text-studio-white'
                  }
                `}
                whileHover={!videoResult || loading ? {} : { scale: 1.02 }}
                whileTap={!videoResult || loading ? {} : { scale: 0.98 }}
              >
                {quality}
              </motion.button>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function FileUploadBox({ label, accept, multiple, onChange, fileCount, icon }) {
  return (
    <div className="relative">
      <label className="block w-full p-6 bg-studio-gray/30 border-2 border-dashed 
                       border-studio-white/20 hover:border-studio-red/50 
                       rounded-lg cursor-pointer transition-all group">
        <div className="text-center">
          <div className="text-4xl mb-2">{icon}</div>
          <p className="text-studio-white/80 font-montserrat font-semibold mb-1">
            {label}
          </p>
          <p className="text-studio-white/50 text-sm">
            {fileCount > 0 
              ? `${fileCount} file${fileCount > 1 ? 's' : ''} selected`
              : 'Click to upload'
            }
          </p>
        </div>
        <input
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={onChange}
          className="hidden"
        />
      </label>
    </div>
  );
}

function Section({ title, items, onCopy, onSelect }) {
  return (
    <div>
      <h3 className="text-studio-red font-montserrat font-semibold text-lg mb-3">
        {title}
      </h3>
      <div className="space-y-2">
        {items?.map((item, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            className="p-4 bg-studio-gray/50 hover:bg-studio-gray
                     rounded-lg border border-studio-white/10
                     hover:border-studio-red/50 transition-all group"
          >
            <p className="text-studio-white/90 font-poppins mb-2">{item}</p>
            <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={() => onCopy(item)}
                className="px-3 py-1 bg-studio-gray hover:bg-studio-red/20
                         text-studio-white/80 text-xs rounded"
              >
                Copy
              </button>
              {onSelect && (
                <button
                  onClick={() => onSelect(item)}
                  className="px-3 py-1 bg-studio-red hover:bg-studio-red/80
                           text-studio-white text-xs rounded"
                >
                  Select for Schedule
                </button>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
