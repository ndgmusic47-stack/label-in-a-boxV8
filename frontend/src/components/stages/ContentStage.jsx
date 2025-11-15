import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../../utils/api';
import StageWrapper from './StageWrapper';

export default function ContentStage({ sessionId, sessionData, updateSessionData, voice, onClose, completeStage }) {
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
      setVideoTranscript(result.transcript);
      updateSessionData({
        uploadedVideo: result.file_url,
        videoTranscript: result.transcript
      });
      voice.speak('Video uploaded and processed!');
    } catch (err) {
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
      voice.speak('Captions and hashtags generated!');
    } catch (err) {
      voice.speak('Failed to generate content text. Try again.');
    } finally {
      setTextPackLoading(false);
    }
  };

  // V23: Step 5 - Schedule Video (using GETLATE API via /content/schedule)
  const handleScheduleVideo = async (selectedCaption, selectedHashtags, scheduleTime) => {
    if (!uploadedVideo || !selectedCaption || !scheduleTime) {
      voice.speak('Please complete all steps first');
      return;
    }

    setScheduleLoading(true);
    try {
      voice.speak('Scheduling video...');
      
      const result = await api.scheduleVideo(
        sessionId,
        uploadedVideo,
        selectedCaption,
        selectedHashtags,
        selectedPlatform,
        scheduleTime
      );
      
      if (result.status === 'scheduled') {
        updateSessionData({ contentScheduled: true });
        voice.speak('Your video has been scheduled.');
        if (completeStage) {
          await completeStage('content');
        }
      }
    } catch (err) {
      voice.speak('Scheduling failed. Try again.');
    } finally {
      setScheduleLoading(false);
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
        {/* V23: Step 1 - Generate Video Idea */}
        <div className="space-y-4 border-b border-studio-white/10 pb-6">
          <h3 className="text-studio-red font-montserrat font-semibold text-lg">
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
              <div>
                <p className="text-studio-white/60 text-sm mb-1">Idea:</p>
                <p className="text-studio-white/90">{contentIdea.idea}</p>
              </div>
              <div>
                <p className="text-studio-white/60 text-sm mb-1">Hook:</p>
                <p className="text-studio-white/90">{contentIdea.hook}</p>
              </div>
              <div>
                <p className="text-studio-white/60 text-sm mb-1">Script:</p>
                <p className="text-studio-white/90">{contentIdea.script}</p>
              </div>
              <div>
                <p className="text-studio-white/60 text-sm mb-1">Visual:</p>
                <p className="text-studio-white/90">{contentIdea.visual}</p>
              </div>
            </div>
          )}
        </div>

        {/* V23: Step 2 - Upload Video */}
        <div className="space-y-4 border-b border-studio-white/10 pb-6">
          <h3 className="text-studio-red font-montserrat font-semibold text-lg">
            Step 2: Upload Finished Video
          </h3>
          <label className="block w-full p-6 bg-studio-gray/30 border-2 border-dashed border-studio-white/20 hover:border-studio-red/50 rounded-lg cursor-pointer transition-all">
            <div className="text-center">
              <div className="text-4xl mb-2">🎥</div>
              <p className="text-studio-white/80 font-montserrat font-semibold mb-1">
                {uploadedVideo ? 'Video Uploaded' : 'Click to upload MP4 or MOV'}
              </p>
              <p className="text-studio-white/50 text-sm">
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
              <p className="text-studio-white/60 text-sm mb-1">Video URL:</p>
              <p className="text-studio-white/90 text-sm break-all">{uploadedVideo}</p>
              {videoTranscript && (
                <div className="mt-3">
                  <p className="text-studio-white/60 text-sm mb-1">Transcript:</p>
                  <p className="text-studio-white/90 text-sm">{videoTranscript.substring(0, 200)}...</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* V23: Step 3 - Analyze Video */}
        <div className="space-y-4 border-b border-studio-white/10 pb-6">
          <h3 className="text-studio-red font-montserrat font-semibold text-lg">
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
                  <p className="text-studio-red font-montserrat text-2xl font-bold">{viralAnalysis.score}/100</p>
                </div>
                <div className="flex-1">
                  <p className="text-studio-white/60 text-sm mb-1">Summary:</p>
                  <p className="text-studio-white/90">{viralAnalysis.summary}</p>
                </div>
              </div>
              {viralAnalysis.improvements && viralAnalysis.improvements.length > 0 && (
                <div>
                  <p className="text-studio-white/60 text-sm mb-2">Improvements:</p>
                  <ul className="space-y-1">
                    {viralAnalysis.improvements.map((imp, i) => (
                      <li key={i} className="text-studio-white/90 text-sm">• {imp}</li>
                    ))}
                  </ul>
                </div>
              )}
              {viralAnalysis.suggested_hook && (
                <div>
                  <p className="text-studio-white/60 text-sm mb-1">Suggested Hook:</p>
                  <p className="text-studio-white/90">{viralAnalysis.suggested_hook}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* V23: Step 4 - Generate Captions & Hashtags */}
        <div className="space-y-4 border-b border-studio-white/10 pb-6">
          <h3 className="text-studio-red font-montserrat font-semibold text-lg">
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
                  <p className="text-studio-white/60 text-sm mb-2">Captions:</p>
                  <div className="space-y-2">
                    {contentTextPack.captions.map((caption, i) => (
                      <motion.button
                        key={i}
                        onClick={() => setSelectedCaption(caption)}
                        className={`w-full p-3 text-left rounded-lg border transition-all ${
                          selectedCaption === caption
                            ? 'bg-studio-red/20 border-studio-red text-studio-white'
                            : 'bg-studio-gray/50 border-studio-white/10 text-studio-white/90 hover:border-studio-red/50'
                        }`}
                        whileHover={{ scale: 1.01 }}
                        whileTap={{ scale: 0.99 }}
                      >
                        {caption}
                      </motion.button>
                    ))}
                  </div>
                </div>
              )}
              {contentTextPack.hashtags && contentTextPack.hashtags.length > 0 && (
                <div>
                  <p className="text-studio-white/60 text-sm mb-2">Hashtags:</p>
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
              {contentTextPack.posting_strategy && (
                <div>
                  <p className="text-studio-white/60 text-sm mb-1">Posting Strategy:</p>
                  <p className="text-studio-white/90">{contentTextPack.posting_strategy}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* V23: Step 5 - Schedule Video */}
        <div className="space-y-4 border-t border-studio-white/10 pt-8">
          <h3 className="text-studio-red font-montserrat font-semibold text-lg">
            Step 5: Schedule Video
          </h3>

          {/* Platform Selector */}
          <div>
            <label className="text-studio-white/80 font-montserrat text-sm mb-2 block">
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

          {/* Schedule Button */}
          <motion.button
            onClick={() => {
              if (!selectedCaption || !scheduleDate) {
                voice.speak('Please select a caption and schedule date first');
                return;
              }
              const scheduledTime = `${scheduleDate}T${scheduleTime}:00Z`;
              onScheduleVideo(selectedCaption, selectedHashtags, scheduledTime);
            }}
            disabled={!uploadedVideo || !selectedCaption || !scheduleDate || scheduleLoading}
            className="w-full py-3 rounded-lg font-montserrat
                     bg-studio-gray hover:bg-studio-red text-studio-white
                     disabled:opacity-50 disabled:cursor-not-allowed"
            whileHover={(!uploadedVideo || !selectedCaption || !scheduleDate || scheduleLoading) ? {} : { scale: 1.02 }}
            whileTap={(!uploadedVideo || !selectedCaption || !scheduleDate || scheduleLoading) ? {} : { scale: 0.98 }}
          >
            {scheduleLoading ? 'Scheduling...' : 'Schedule Video'}
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
}

