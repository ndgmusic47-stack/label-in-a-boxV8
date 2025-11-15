import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../../utils/api';
import StageWrapper from './StageWrapper';

// Copy to clipboard helper
const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text);
};

// Compute virality score based on transparent formula
function computeViralityScore(caption, title, hook) {
  let score = 50;

  if (caption && caption.length > 60) score += 10;
  if (caption && caption.includes("#")) score += 5;
  if (hook && hook.length > 20) score += 10;
  if (title && title.toLowerCase().includes("you")) score += 5;

  return Math.min(score, 95);
}

export default function ContentStage({ sessionId, sessionData, updateSessionData, voice, onClose, onNext, completeStage }) {
  const [activeTab, setActiveTab] = useState('social');
  const [selectedPlatform, setSelectedPlatform] = useState('tiktok');
  const [scheduleLoading, setScheduleLoading] = useState(false);

  // V23: ContentStage MVP state
  const [contentIdea, setContentIdea] = useState(sessionData.contentIdea || null);
  const [uploadedVideo, setUploadedVideo] = useState(sessionData.uploadedVideo || null);
  const [videoTranscript, setVideoTranscript] = useState(sessionData.videoTranscript || null);
  const [viralAnalysis, setViralAnalysis] = useState(sessionData.viralAnalysis || null);
  const [contentTextPack, setContentTextPack] = useState(sessionData.contentTextPack || null);
  const [ideaLoading, setIdeaLoading] = useState(false);
  const [videoUploadLoading, setVideoUploadLoading] = useState(false);
  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [textPackLoading, setTextPackLoading] = useState(false);

  // V23: Step 1 - Generate Video Idea
  const handleGenerateVideoIdea = async () => {
    setIdeaLoading(true);
    try {
      voice.speak('Generating video idea...');
      
      const result = await api.generateVideoIdea(
        sessionId,
        sessionData.trackTitle || sessionData.title || 'My Track',
        sessionData.lyricsData || sessionData.lyrics || '',
        sessionData.mood || 'energetic',
        sessionData.genre || 'hip hop'
      );
      
      setContentIdea(result);
      updateSessionData({ contentIdea: result });
      voice.speak('Video idea generated!');
    } catch (err) {
      voice.speak('Failed to generate video idea. Try again.');
    } finally {
      setIdeaLoading(false);
    }
  };

  // V23: Step 2 - Upload Video
  const handleVideoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.mp4') && !file.name.toLowerCase().endsWith('.mov')) {
      voice.speak('Please upload an MP4 or MOV file');
      return;
    }

    setVideoUploadLoading(true);
    try {
      voice.speak('Uploading video...');
      
      const result = await api.uploadVideo(file, sessionId);
      
      setUploadedVideo(result.file_url);
      // Handle transcript with proper error handling
      let transcriptText = result.transcript || '';
      if (!transcriptText || transcriptText.includes('[Transcript') || transcriptText.includes('failed')) {
        transcriptText = 'Transcript unavailable. Try again later.';
      }
      setVideoTranscript(transcriptText);
      updateSessionData({
        uploadedVideo: result.file_url,
        videoTranscript: transcriptText
      });
      voice.speak('Video uploaded and processed!');
    } catch (err) {
      setVideoTranscript('Transcript unavailable. Try again later.');
      voice.speak('Video upload failed. Try again.');
    } finally {
      setVideoUploadLoading(false);
    }
  };

  // V23: Step 3 - Analyze Video
  const handleAnalyzeVideo = async () => {
    if (!videoTranscript) {
      voice.speak('Please upload a video first');
      return;
    }

    setAnalyzeLoading(true);
    try {
      voice.speak('Analyzing video for viral potential...');
      
      const result = await api.analyzeVideo(
        videoTranscript,
        sessionData.trackTitle || sessionData.title || 'My Track',
        sessionData.lyricsData || sessionData.lyrics || '',
        sessionData.mood || 'energetic',
        sessionData.genre || 'hip hop'
      );
      
      setViralAnalysis(result);
      updateSessionData({ viralAnalysis: result });
      voice.speak(`Analysis complete! Viral score: ${result.score}`);
    } catch (err) {
      voice.speak('Video analysis failed. Try again.');
    } finally {
      setAnalyzeLoading(false);
    }
  };

  // V23: Step 4 - Generate Captions & Hashtags
  const handleGenerateTextPack = async () => {
    setTextPackLoading(true);
    try {
      voice.speak('Generating captions and hashtags...');
      
      const result = await api.generateContentText(
        sessionId,
        sessionData.trackTitle || sessionData.title || 'My Track',
        videoTranscript || '',
        sessionData.lyricsData || sessionData.lyrics || '',
        sessionData.mood || 'energetic',
        sessionData.genre || 'hip hop'
      );
      
      setContentTextPack(result);
      updateSessionData({ contentTextPack: result });
      // Mark content stage as complete when content is generated
      if (completeStage) {
        completeStage('content');
      }
      voice.speak('Captions and hashtags generated!');
    } catch (err) {
      voice.speak('Failed to generate content text. Try again.');
    } finally {
      setTextPackLoading(false);
    }
  };

  // V23: Step 5 - Schedule Video (using GETLATE API via /content/schedule)
  const handleScheduleVideo = async (selectedCaption, selectedHashtags, scheduleTime, platform) => {
    if (!uploadedVideo || !selectedCaption || !scheduleTime) {
      voice.speak('Please complete all steps first');
      return;
    }

    setScheduleLoading(true);
    setError('');
    setSuccess('');
    try {
      voice.speak('Scheduling video...');
      
      const result = await api.scheduleVideo(
        sessionId,
        uploadedVideo,
        selectedCaption,
        selectedHashtags,
        platform || selectedPlatform,
        scheduleTime
      );
      
      if (result.status === 'scheduled' || result.status === 'saved') {
        // Save scheduled post to session memory
        await api.saveScheduled({
          sessionId,
          platform: platform || selectedPlatform,
          dateTime: scheduleTime,
          caption: selectedCaption,
        });
        
        updateSessionData({ contentScheduled: true });
        voice.speak('Your video has been scheduled.');
        setSuccess('Your post is scheduled!');
        
        // Auto-clear success message after 3 seconds
        setTimeout(() => setSuccess(''), 3000);
        
        // Mark schedule stage as complete (only triggers once per session)
        // Check if schedule stage is already complete to avoid retriggering
        if (completeStage && !sessionData.scheduleComplete) {
          completeStage('schedule');
          updateSessionData({ scheduleComplete: true });
        }
      }
    } catch (err) {
      const errorMsg = err.message || 'Scheduling failed. Try again.';
      setError(errorMsg);
      voice.speak(errorMsg);
      // Auto-clear error after 3 seconds
      setTimeout(() => setError(''), 3000);
    } finally {
      setScheduleLoading(false);
    }
  };

  return (
    <StageWrapper 
      title="Content & Video" 
      icon="🎬" 
      onClose={onClose}
      onNext={onNext}
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
                voice={voice}
                selectedPlatform={selectedPlatform}
                onPlatformChange={setSelectedPlatform}
                scheduleLoading={scheduleLoading}
                // V23: ContentStage MVP props
                contentIdea={contentIdea}
                uploadedVideo={uploadedVideo}
                videoTranscript={videoTranscript}
                viralAnalysis={viralAnalysis}
                contentTextPack={contentTextPack}
                onGenerateVideoIdea={handleGenerateVideoIdea}
                onVideoUpload={handleVideoUpload}
                onAnalyzeVideo={handleAnalyzeVideo}
                onGenerateTextPack={handleGenerateTextPack}
                onScheduleVideo={handleScheduleVideo}
                ideaLoading={ideaLoading}
                videoUploadLoading={videoUploadLoading}
                analyzeLoading={analyzeLoading}
                textPackLoading={textPackLoading}
                sessionId={sessionId}
                sessionData={sessionData}
                completeStage={completeStage}
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
  voice,
  selectedPlatform,
  onPlatformChange,
  scheduleLoading,
  // V23: ContentStage MVP props
  contentIdea,
  uploadedVideo,
  videoTranscript,
  viralAnalysis,
  contentTextPack,
  onGenerateVideoIdea,
  onVideoUpload,
  onAnalyzeVideo,
  onGenerateTextPack,
  onScheduleVideo,
  ideaLoading,
  videoUploadLoading,
  analyzeLoading,
  textPackLoading,
  sessionId,
  sessionData,
  completeStage
}) {
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleTime, setScheduleTime] = useState('12:00');
  const [selectedCaption, setSelectedCaption] = useState('');
  const [selectedHashtags, setSelectedHashtags] = useState([]);
  const [scheduledPosts, setScheduledPosts] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Load scheduled posts on mount and after scheduling
  useEffect(() => {
    const loadScheduled = async () => {
      try {
        const result = await api.getScheduled(sessionId);
        // Handle both array response and data wrapper
        const posts = Array.isArray(result) ? result : (result?.data || []);
        setScheduledPosts(posts || []);
      } catch (err) {
        // Silently fail - no scheduled posts yet
        setScheduledPosts([]);
      }
    };
    if (sessionId) {
      loadScheduled();
    }
  }, [sessionId]);

  return (
    <motion.div
      key="social"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="flex flex-col gap-6 p-6 md:p-10"
    >
      <div className="icon-wrapper text-6xl mb-4 text-center">
        📱
      </div>

      <div className="w-full max-w-4xl mx-auto space-y-8">
        {/* Viral Helper Message */}
        <p className="text-sm text-studio-white/70 font-poppins mb-2">
          🔥 This module helps you create viral content — follow the steps below.
        </p>

        {/* V23: Step 1 - Generate Video Idea */}
        <div className="space-y-4 border-b border-studio-white/10 pb-6">
          <h3 className="text-lg text-studio-gold font-montserrat font-semibold">
            Step 1: Generate Video Idea
          </h3>
          <motion.button
            onClick={onGenerateVideoIdea}
            disabled={ideaLoading}
            className="w-full py-3 bg-studio-gray hover:bg-studio-red text-studio-white font-montserrat rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            whileHover={ideaLoading ? {} : { scale: 1.02 }}
            whileTap={ideaLoading ? {} : { scale: 0.98 }}
          >
            {ideaLoading ? 'Generating...' : 'Generate Video Idea'}
          </motion.button>
          {contentIdea && (
            <div className="p-4 bg-studio-gray/30 rounded-lg border border-studio-white/10 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <p className="text-xs text-studio-white/60 font-poppins mb-1">Idea:</p>
                  <p className="text-sm text-studio-white/90 font-poppins">{contentIdea.idea}</p>
                </div>
                <motion.button
                  onClick={() => copyToClipboard(contentIdea.idea)}
                  className="px-2 py-1 text-xs bg-studio-gray/50 hover:bg-studio-gray/70 text-studio-white rounded transition-all"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  Copy
                </motion.button>
              </div>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <p className="text-xs text-studio-white/60 font-poppins mb-1">Hook:</p>
                  <p className="text-sm text-studio-white/90 font-poppins">{contentIdea.hook}</p>
                </div>
                <motion.button
                  onClick={() => copyToClipboard(contentIdea.hook)}
                  className="px-2 py-1 text-xs bg-studio-gray/50 hover:bg-studio-gray/70 text-studio-white rounded transition-all"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  Copy
                </motion.button>
              </div>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <p className="text-xs text-studio-white/60 font-poppins mb-1">Script:</p>
                  <p className="text-sm text-studio-white/90 font-poppins">{contentIdea.script}</p>
                </div>
                <motion.button
                  onClick={() => copyToClipboard(contentIdea.script)}
                  className="px-2 py-1 text-xs bg-studio-gray/50 hover:bg-studio-gray/70 text-studio-white rounded transition-all"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  Copy
                </motion.button>
              </div>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1">
                  <p className="text-xs text-studio-white/60 font-poppins mb-1">Visual:</p>
                  <p className="text-sm text-studio-white/90 font-poppins">{contentIdea.visual}</p>
                </div>
                <motion.button
                  onClick={() => copyToClipboard(contentIdea.visual)}
                  className="px-2 py-1 text-xs bg-studio-gray/50 hover:bg-studio-gray/70 text-studio-white rounded transition-all"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  Copy
                </motion.button>
              </div>
            </div>
          )}
        </div>

        {/* V23: Step 2 - Upload Video */}
        <div className="space-y-4 border-b border-studio-white/10 pb-6">
          <h3 className="text-lg text-studio-gold font-montserrat font-semibold">
            Step 2: Upload Finished Video
          </h3>
          <label className="block w-full p-6 bg-studio-gray/30 border-2 border-dashed border-studio-white/20 hover:border-studio-red/50 rounded-lg cursor-pointer transition-all">
            <div className="text-center">
              <div className="text-4xl mb-2">🎥</div>
              <p className="text-sm text-studio-white/90 font-montserrat font-semibold mb-1">
                {uploadedVideo ? 'Video Uploaded' : 'Click to upload MP4 or MOV'}
              </p>
              <p className="text-xs text-studio-white/60 font-poppins">
                {videoUploadLoading ? 'Uploading...' : (uploadedVideo ? 'Change video' : 'Select video file')}
              </p>
            </div>
            <input
              type="file"
              accept=".mp4,.mov"
              onChange={onVideoUpload}
              disabled={videoUploadLoading}
              className="hidden"
            />
          </label>
          {uploadedVideo && (
            <div className="p-4 bg-studio-gray/30 rounded-lg border border-studio-white/10">
              <p className="text-xs text-studio-white/60 font-poppins mb-1">Video URL:</p>
              <p className="text-sm text-studio-white/90 font-poppins text-sm break-all">{uploadedVideo}</p>
              {videoTranscript && (
                <div className="mt-3">
                  <p className="text-xs text-studio-white/60 font-poppins mb-1">Transcript:</p>
                  <p className="text-sm text-studio-white/90 font-poppins">
                    {videoTranscript.length > 200 && !videoTranscript.includes('unavailable')
                      ? `${videoTranscript.substring(0, 200)}...`
                      : videoTranscript}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* V23: Step 3 - Analyze Video */}
        <div className="space-y-4 border-b border-studio-white/10 pb-6">
          <h3 className="text-lg text-studio-gold font-montserrat font-semibold">
            Step 3: Analyze Video
          </h3>
          <motion.button
            onClick={onAnalyzeVideo}
            disabled={!videoTranscript || analyzeLoading}
            className="w-full py-3 bg-studio-gray hover:bg-studio-red text-studio-white font-montserrat rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            whileHover={(!videoTranscript || analyzeLoading) ? {} : { scale: 1.02 }}
            whileTap={(!videoTranscript || analyzeLoading) ? {} : { scale: 0.98 }}
          >
            {analyzeLoading ? 'Analyzing...' : 'Analyze Video'}
          </motion.button>
          {viralAnalysis && (
            <div className="p-4 bg-studio-gray/30 rounded-lg border border-studio-white/10 space-y-3">
              <div className="flex items-center gap-4">
                <div>
                  <p className="text-studio-white/60 text-sm mb-1">Viral Score:</p>
                  <p className="text-lg text-studio-gold font-montserrat font-bold">
                    {computeViralityScore(
                      selectedCaption || contentTextPack?.captions?.[0] || '',
                      sessionData.trackTitle || sessionData.title || '',
                      contentIdea?.hook || viralAnalysis.suggested_hook || ''
                    )}/100
                  </p>
                  <p className="text-xs text-studio-white/60 font-poppins mt-1">
                    (Experimental — based on text structure)
                  </p>
                </div>
                <div className="flex-1">
                  <p className="text-xs text-studio-white/60 font-poppins mb-1">Summary:</p>
                  <p className="text-sm text-studio-white/90 font-poppins">{viralAnalysis.summary}</p>
                </div>
              </div>
              {viralAnalysis.improvements && viralAnalysis.improvements.length > 0 && (
                <div>
                  <p className="text-xs text-studio-white/60 font-poppins mb-2">Improvements:</p>
                  <ul className="space-y-1">
                    {viralAnalysis.improvements.map((imp, i) => (
                      <li key={i} className="text-sm text-studio-white/90 font-poppins">• {imp}</li>
                    ))}
                  </ul>
                </div>
              )}
              {viralAnalysis.suggested_hook && (
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <p className="text-xs text-studio-white/60 font-poppins mb-1">Suggested Hook:</p>
                    <p className="text-sm text-studio-white/90 font-poppins">{viralAnalysis.suggested_hook}</p>
                  </div>
                  <motion.button
                    onClick={() => copyToClipboard(viralAnalysis.suggested_hook)}
                    className="px-2 py-1 text-xs bg-studio-gray/50 hover:bg-studio-gray/70 text-studio-white rounded transition-all"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    Copy
                  </motion.button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* V23: Step 4 - Generate Captions & Hashtags */}
        <div className="space-y-4 border-b border-studio-white/10 pb-6">
          <h3 className="text-lg text-studio-gold font-montserrat font-semibold">
            Step 4: Generate Captions & Hashtags
          </h3>
          <motion.button
            onClick={onGenerateTextPack}
            disabled={textPackLoading}
            className="w-full py-3 bg-studio-gray hover:bg-studio-red text-studio-white font-montserrat rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            whileHover={textPackLoading ? {} : { scale: 1.02 }}
            whileTap={textPackLoading ? {} : { scale: 0.98 }}
          >
            {textPackLoading ? 'Generating...' : 'Generate Captions & Hashtags'}
          </motion.button>
          {contentTextPack && (
            <div className="p-4 bg-studio-gray/30 rounded-lg border border-studio-white/10 space-y-4">
              {contentTextPack.captions && contentTextPack.captions.length > 0 && (
                <div>
                  <p className="text-xs text-studio-white/60 font-poppins mb-2">Captions:</p>
                  <div className="space-y-2">
                    {contentTextPack.captions.map((caption, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <motion.button
                          onClick={() => setSelectedCaption(caption)}
                          className={`flex-1 p-3 text-left rounded-lg border transition-all ${
                            selectedCaption === caption
                              ? 'bg-studio-red/20 border-studio-red text-studio-white'
                              : 'bg-studio-gray/50 border-studio-white/10 text-studio-white/90 hover:border-studio-red/50'
                          }`}
                          whileHover={{ scale: 1.01 }}
                          whileTap={{ scale: 0.99 }}
                        >
                          {caption}
                        </motion.button>
                        <motion.button
                          onClick={() => copyToClipboard(caption)}
                          className="px-2 py-1 text-xs bg-studio-gray/50 hover:bg-studio-gray/70 text-studio-white rounded transition-all self-center"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          Copy
                        </motion.button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {contentTextPack.hashtags && contentTextPack.hashtags.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-studio-white/60 font-poppins">Hashtags:</p>
                    <motion.button
                      onClick={() => copyToClipboard(contentTextPack.hashtags.join(' '))}
                      className="px-2 py-1 text-xs bg-studio-gray/50 hover:bg-studio-gray/70 text-studio-white rounded transition-all"
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      Copy All
                    </motion.button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {contentTextPack.hashtags.map((tag, i) => (
                      <motion.button
                        key={i}
                        onClick={() => {
                          if (selectedHashtags.includes(tag)) {
                            setSelectedHashtags(selectedHashtags.filter(t => t !== tag));
                          } else {
                            setSelectedHashtags([...selectedHashtags, tag]);
                          }
                        }}
                        className={`px-3 py-1 text-sm rounded-full border transition-all ${
                          selectedHashtags.includes(tag)
                            ? 'bg-studio-red/20 border-studio-red text-studio-white'
                            : 'bg-studio-gray/50 border-studio-white/10 text-studio-white/80 hover:border-studio-red/50'
                        }`}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        {tag}
                      </motion.button>
                    ))}
                  </div>
                </div>
              )}
              {contentTextPack.hooks && contentTextPack.hooks.length > 0 && (
                <div>
                  <p className="text-xs text-studio-white/60 font-poppins mb-2">Hooks:</p>
                  <div className="space-y-2">
                    {contentTextPack.hooks.map((hook, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <div className="flex-1 p-3 bg-studio-gray/50 rounded-lg border border-studio-white/10">
                          <p className="text-sm text-studio-white/90 font-poppins">{hook}</p>
                        </div>
                        <motion.button
                          onClick={() => copyToClipboard(hook)}
                          className="px-2 py-1 text-xs bg-studio-gray/50 hover:bg-studio-gray/70 text-studio-white rounded transition-all self-center"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          Copy
                        </motion.button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {contentTextPack.posting_strategy && (
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <p className="text-xs text-studio-white/60 font-poppins mb-1">Posting Strategy:</p>
                    <p className="text-sm text-studio-white/90 font-poppins">{contentTextPack.posting_strategy}</p>
                  </div>
                  <motion.button
                    onClick={() => copyToClipboard(contentTextPack.posting_strategy)}
                    className="px-2 py-1 text-xs bg-studio-gray/50 hover:bg-studio-gray/70 text-studio-white rounded transition-all"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    Copy
                  </motion.button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* V23: Step 5 - Schedule Video */}
        <div className="space-y-4 border-t border-studio-white/10 pt-8">
          <h3 className="text-lg text-studio-gold font-montserrat font-semibold">
            Step 5: Schedule Video
          </h3>

          {/* Platform Selector */}
          <div>
            <label className="text-xs text-studio-white/60 font-montserrat mb-2 block">
              Platform
            </label>
            <div className="grid grid-cols-3 gap-2">
              {['tiktok', 'shorts', 'reels'].map(platform => (
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
              <label className="text-xs text-studio-white/60 font-montserrat mb-2 block">
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
              <label className="text-xs text-studio-white/60 font-montserrat mb-2 block">
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

          {/* Error/Success Messages */}
          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm">
              {error}
            </div>
          )}
          {success && (
            <div className="p-3 bg-green-500/20 border border-green-500/50 rounded-lg text-green-300 text-sm">
              {success}
            </div>
          )}

          {/* Schedule Button */}
          <motion.button
            onClick={async () => {
              // Validate inputs
              if (!selectedPlatform) {
                setError('Please select a platform before scheduling.');
                voice.speak('Please select a platform');
                setTimeout(() => setError(''), 3000);
                return;
              }
              if (!scheduleDate) {
                setError('Please select a date before scheduling.');
                voice.speak('Please select a date');
                setTimeout(() => setError(''), 3000);
                return;
              }
              if (!scheduleTime) {
                setError('Please select a time before scheduling.');
                voice.speak('Please select a time');
                setTimeout(() => setError(''), 3000);
                return;
              }
              if (!selectedCaption) {
                setError('Please select a caption before scheduling.');
                voice.speak('Please select a caption');
                setTimeout(() => setError(''), 3000);
                return;
              }
              
              const scheduledTime = `${scheduleDate}T${scheduleTime}:00Z`;
              await onScheduleVideo(selectedCaption, selectedHashtags, scheduledTime, selectedPlatform);
              
              // Reload scheduled posts after scheduling
              try {
                const result = await api.getScheduled(sessionId);
                const posts = Array.isArray(result) ? result : (result?.data || []);
                setScheduledPosts(posts || []);
              } catch (err) {
                // Silently fail
              }
            }}
            disabled={!uploadedVideo || !selectedCaption || !scheduleDate || !scheduleTime || !selectedPlatform || scheduleLoading}
            className="w-full py-3 rounded-lg font-montserrat
                     bg-studio-gray hover:bg-studio-red text-studio-white
                     disabled:opacity-50 disabled:cursor-not-allowed"
            whileHover={(!uploadedVideo || !selectedCaption || !scheduleDate || !scheduleTime || !selectedPlatform || scheduleLoading) ? {} : { scale: 1.02 }}
            whileTap={(!uploadedVideo || !selectedCaption || !scheduleDate || !scheduleTime || !selectedPlatform || scheduleLoading) ? {} : { scale: 0.98 }}
          >
            {scheduleLoading ? 'Scheduling...' : 'Schedule Video'}
          </motion.button>

          {/* Scheduled Posts List */}
          <div className="text-studio-white/80 mt-4">
            <h4 className="text-sm text-studio-white/90 mb-2 font-montserrat font-semibold">Scheduled Posts:</h4>
            {scheduledPosts.length > 0 ? (
              <div className="space-y-1">
                {scheduledPosts.map((post, i) => {
                  const formatDate = (dateStr) => {
                    if (!dateStr) return 'Unknown date';
                    try {
                      const date = new Date(dateStr);
                      return date.toLocaleDateString('en-US', { 
                        month: 'short', 
                        day: 'numeric', 
                        year: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit',
                        hour12: true
                      });
                    } catch (e) {
                      return dateStr;
                    }
                  };
                  
                  const dateTime = post.dateTime || post.time || post.scheduled_time;
                  return (
                    <div key={i} className="text-xs mb-1 text-studio-white/70">
                      • {post.platform ? post.platform.charAt(0).toUpperCase() + post.platform.slice(1) : 'Unknown'} — {formatDate(dateTime)}
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-studio-white/60 font-poppins">No scheduled posts yet.</p>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

