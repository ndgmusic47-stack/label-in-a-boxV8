import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Timeline from './components/Timeline';
import MistLayer from './components/MistLayer';
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
  const [isStageOpen, setIsStageOpen] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [currentStage, setCurrentStage] = useState('beat');
  const [completedStages, setCompletedStages] = useState({});
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

  // NP22: Global stage order for full workflow
  const stageOrder = [
    "beat",      // Beat creation module  
    "lyrics",    // Lyrics module
    "upload",    // Beat upload module
    "mix",       // Mix Stage
    "release",   // Release Pack module
    "content"    // Content/Viral module
  ];

  // Load project data on mount (workflow status is tracked in project memory)
  useEffect(() => {
    loadProjectData();
  }, [sessionId]);

  const loadProjectData = async () => {
    try {
      const project = await api.getProject(sessionId);
      if (project && project.workflow) {
        setCurrentStage(project.workflow.current_stage || 'beat');
        // Convert array to object format for tick system
        const completedArray = project.workflow.completed_stages || [];
        const completedObj = {};
        completedArray.forEach(stage => {
          completedObj[stage] = true;
        });
        setCompletedStages(completedObj);
      }
    } catch (err) {
      // New session - use defaults
    }
  };

  const completeCurrentStage = async (stage) => {
    // Phase 1: Mark stage as complete using object format for tick system
    setCompletedStages(prev => ({ ...prev, [stage]: true }));
    
    // Sync with backend to get updated project state after stage completion
    try {
      await api.syncProject(sessionId, updateSessionData);
    } catch (err) {
      console.error('Failed to sync project after stage completion:', err);
    }
    
    // Suggest next stage using NP22 stage order
    const currentIndex = stageOrder.indexOf(stage);
    if (currentIndex < stageOrder.length - 1) {
      const nextStage = stageOrder[currentIndex + 1];
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
    setIsStageOpen(true);
    window.scrollTo({ top: 0, behavior: 'instant' });
    voice.stopSpeaking();
  };

  const handleClose = () => {
    setActiveStage(null);
    setIsStageOpen(false);
  };

  const handleBackToTimeline = () => {
    setActiveStage(null);
    setIsStageOpen(false);
  };

  const openStage = (stageId) => {
    setActiveStage(stageId);
    setIsStageOpen(true);
    window.scrollTo({ top: 0, behavior: 'instant' });
    voice.stopSpeaking();
  };

  const goToNextStage = () => {
    const index = stageOrder.indexOf(activeStage);
    if (index !== -1 && index < stageOrder.length - 1) {
      const nextStage = stageOrder[index + 1];
      openStage(nextStage);
    }
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
      onNext: goToNextStage,
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
    <div className="app-root">
      <MistLayer activeStage={activeStage || currentStage} />

      {!showAnalytics && !isStageOpen && (
        <div className="timeline-centered">
          <Timeline
            ref={timelineRef}
            currentStage={currentStage}
            activeStage={activeStage}
            completedStages={completedStages}
            onStageClick={handleStageClick}
            showBackButton={!!activeStage}
            onBackToTimeline={handleBackToTimeline}
          />
        </div>
      )}

      <main className={`stage-screen ${isStageOpen ? 'fullscreen' : ''}`}>
        <ErrorBoundary onReset={() => setActiveStage(null)}>
          {renderStage()}
        </ErrorBoundary>
      </main>

      <VoiceControl />

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

    </div>
  );
}

export default App;