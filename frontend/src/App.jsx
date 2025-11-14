import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Timeline from './components/Timeline';
import MistLayer from './components/MistLayer';
import VoiceChat from './components/VoiceChat';
import VoiceControl from './components/VoiceControl';
import ErrorBoundary from './components/ErrorBoundary';
import BeatStage from './components/stages/BeatStage';
import LyricsStage from './components/stages/LyricsStage';
import UploadStage from './components/stages/UploadStage';
import MixStage from './components/stages/MixStage';
import ReleaseStage from './components/stages/ReleaseStage';
import ContentStage from './components/stages/ContentStage';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import { useVoice } from './hooks/useVoice';
import { api } from './utils/api';
import './styles/ErrorBoundary.css';

function App() {
  const [activeStage, setActiveStage] = useState(null);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [currentStage, setCurrentStage] = useState('beat');
  const [completedStages, setCompletedStages] = useState([]);
  const [stagePositions, setStagePositions] = useState({});
  const timelineRef = useRef(null);
  const [sessionId, setSessionId] = useState(() => {
    const stored = localStorage.getItem('liab_session_id');
    if (stored) return stored;
    const newId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('liab_session_id', newId);
    return newId;
  });
  const [sessionData, setSessionData] = useState({
    beatFile: null,
    lyricsData: null,
    vocalFile: null,
    masterFile: null,
    genre: 'hip hop',
    mood: 'energetic',
    trackTitle: 'My Track',
  });

  const voice = useVoice(sessionId);

  // Load project data on mount (workflow status is tracked in project memory)
  useEffect(() => {
    loadProjectData();
  }, [sessionId]);

  const loadProjectData = async () => {
    try {
      const project = await api.getProject(sessionId);
      if (project && project.workflow) {
        setCurrentStage(project.workflow.current_stage || 'beat');
        setCompletedStages(project.workflow.completed_stages || []);
      }
    } catch (err) {
      // New session - use defaults
      console.log('New project session started');
    }
  };

  const completeCurrentStage = async (stage) => {
    // Mark stage as complete locally (backend tracks via project memory)
    if (!completedStages.includes(stage)) {
      setCompletedStages([...completedStages, stage]);
    }
    
    // Sync with backend to get updated project state after stage completion
    try {
      await api.syncProject(sessionId, updateSessionData);
    } catch (err) {
      console.error('Failed to sync project after stage completion:', err);
    }
    
    // Suggest next stage
    const stages = ['beat', 'lyrics', 'upload', 'mix', 'release', 'content', 'analytics'];
    const currentIndex = stages.indexOf(stage);
    if (currentIndex < stages.length - 1) {
      const nextStage = stages[currentIndex + 1];
      setCurrentStage(nextStage);
      voice.speak(`${stage} stage complete! ${nextStage} is next`);
    } else {
      voice.speak(`${stage} complete! All stages finished!`);
    }
  };

  const updateSessionData = (data) => {
    setSessionData((prev) => ({ ...prev, ...data }));
  };

  const handleStageClick = (stageId) => {
    setActiveStage(stageId);
    voice.stopSpeaking();
  };

  const handleClose = () => {
    setActiveStage(null);
  };

  const handleBackToTimeline = () => {
    setActiveStage(null);
  };

  const handleAnalyticsClose = () => {
    setShowAnalytics(false);
  };

  const handleAnalyticsClick = () => {
    setShowAnalytics(true);
    voice.stopSpeaking();
  };

  const renderStage = () => {
    const commonProps = {
      sessionId,
      sessionData,
      updateSessionData,
      voice,
      onClose: handleClose,
      completeStage: completeCurrentStage,
    };

    switch (activeStage) {
      case 'beat':
        return <BeatStage {...commonProps} />;
      case 'lyrics':
        return <LyricsStage {...commonProps} />;
      case 'upload':
        return <UploadStage {...commonProps} />;
      case 'mix':
        return <MixStage {...commonProps} />;
      case 'release':
        return <ReleaseStage {...commonProps} />;
      case 'content':
        return <ContentStage {...commonProps} />;
      case 'analytics':
        return <AnalyticsDashboard {...commonProps} />;
      default:
        return null;
    }
  };

  return (
    <div className="relative w-full h-full overflow-hidden bg-studio-black">
      {/* Red Pulsating Mist Layer - Phase 3 */}
      {currentStage && !showAnalytics && (
        <MistLayer activeStage={currentStage} stagePositions={stagePositions} />
      )}

      {/* Main Title */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="absolute top-8 left-1/2 transform -translate-x-1/2 z-10"
      >
        <h1 className="text-4xl font-bold font-montserrat tracking-wider text-studio-white">
          LABEL IN A BOX
        </h1>
      </motion.div>

      {/* Analytics Button */}
      {!activeStage && !showAnalytics && (
        <motion.button
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          onClick={handleAnalyticsClick}
          className="absolute top-8 right-8 z-10 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600
                   hover:from-blue-500 hover:to-purple-500 rounded-lg font-montserrat font-semibold
                   text-studio-white transition-all duration-300 flex items-center gap-2
                   shadow-lg hover:shadow-xl transform hover:scale-105"
        >
          <span>📊</span> Analytics
        </motion.button>
      )}

      {/* Timeline - Always Visible */}
      {!showAnalytics && (
        <Timeline
          ref={timelineRef}
          currentStage={currentStage}
          completedStages={completedStages}
          onStageClick={handleStageClick}
          showBackButton={!!activeStage}
          onBackToTimeline={handleBackToTimeline}
          onStagePositionsUpdate={setStagePositions}
        />
      )}

      {/* Stage Panels */}
      <AnimatePresence mode="wait">
        {activeStage && (
          <motion.div
            key={activeStage}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="relative z-20"
            style={{ marginTop: '200px', height: 'calc(100vh - 200px)' }}
          >
            <ErrorBoundary onReset={() => setActiveStage(null)}>
              {renderStage()}
            </ErrorBoundary>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Analytics Dashboard */}
      <AnimatePresence>
        {showAnalytics && (
          <ErrorBoundary onReset={() => setShowAnalytics(false)}>
            <AnalyticsDashboard
              sessionId={sessionId}
              voice={voice}
              onClose={handleAnalyticsClose}
            />
          </ErrorBoundary>
        )}
      </AnimatePresence>

      {/* Voice Chat Interface */}
      {voice.isSupported && (
        <VoiceChat
          voice={voice}
          activeStage={activeStage}
          sessionData={sessionData}
        />
      )}

      {/* V4 Voice Control System */}
      <VoiceControl />
    </div>
  );
}

export default App;