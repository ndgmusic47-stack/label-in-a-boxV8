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
import AuthModal from './components/AuthModal';
import ManageProjectsModal from './components/ManageProjectsModal';
import UpgradeModal from './components/UpgradeModal';
import BillingSuccess from './components/BillingSuccess';
import BillingCancel from './components/BillingCancel';
import { useVoice } from './hooks/useVoice';
import { useAuth } from './context/AuthContext';
import { api } from './utils/api';
import { handlePaywall } from './utils/paywall';
import './styles/ErrorBoundary.css';

function App() {
  const { user, loading: authLoading, logout } = useAuth();
  const [activeStage, setActiveStage] = useState(null);
  const [isStageOpen, setIsStageOpen] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showAccountMenu, setShowAccountMenu] = useState(false);
  const [showManageProjects, setShowManageProjects] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeFeature, setUpgradeFeature] = useState(null);
  const [currentProjectId, setCurrentProjectId] = useState(null);
  const [saveToast, setSaveToast] = useState(null);
  const [currentStage, setCurrentStage] = useState('beat');
  const [completedStages, setCompletedStages] = useState({});
  const timelineRef = useRef(null);
  const accountMenuRef = useRef(null);
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

  const handleLogout = () => {
    logout();
    setShowAccountMenu(false);
  };

  const openUpgradeModal = (feature) => {
    setUpgradeFeature(feature);
    setShowUpgradeModal(true);
  };

  const handleUpgradeToPro = async () => {
    if (!user) {
      setShowAuthModal(true);
      return;
    }

    try {
      setShowAccountMenu(false);
      const result = await api.createCheckoutSession(user.user_id);
      if (result && result.url) {
        window.location.href = result.url;
      } else {
        console.error('No checkout URL returned');
      }
    } catch (err) {
      console.error('Failed to create checkout session:', err);
      // Show error or fallback to modal
      openUpgradeModal(null);
    }
  };

  const handleSaveProject = async () => {
    if (!user) return;
    
    try {
      // Get current project data
      const project = await api.getProject(sessionId);
      if (!project) {
        throw new Error('No project data to save');
      }

      // Save project
      const result = await api.saveProject(user.user_id, currentProjectId, project);
      
      // PHASE 8.4: Check for paywall
      if (!handlePaywall(result, openUpgradeModal)) {
        return;
      }
      
      setCurrentProjectId(result.projectId);
      
      // Show success toast
      setSaveToast('Project saved!');
      setTimeout(() => setSaveToast(null), 3000);
      
      setShowAccountMenu(false);
    } catch (err) {
      console.error('Failed to save project:', err);
      
      // PHASE 8.4: Check if error is paywall response
      if (err.isPaywall && err.errorData) {
        if (!handlePaywall(err.errorData, openUpgradeModal)) {
          return;
        }
      }
      
      setSaveToast('Failed to save project');
      setTimeout(() => setSaveToast(null), 3000);
    }
  };

  const handleLoadProject = async (projectData) => {
    try {
      // Import project data into current session
      // The backend will handle importing the data when we save it to the current session
      // For now, update UI state from loaded project
      if (projectData.projectData) {
        const data = projectData.projectData;
        
        // Update workflow state
        if (data.workflow) {
          setCurrentStage(data.workflow.current_stage || 'beat');
          const completedArray = data.workflow.completed_stages || [];
          const completedObj = {};
          completedArray.forEach(stage => {
            completedObj[stage] = true;
          });
          setCompletedStages(completedObj);
        }
        
        // Update session data
        if (data.metadata) {
          updateSessionData({
            genre: data.metadata.genre || 'hip hop',
            mood: data.metadata.mood || 'energetic',
            trackTitle: data.metadata.track_title || 'My Track',
          });
        }
        
        // Set project ID so future saves update this project
        setCurrentProjectId(projectData.projectId);
        
        // Save the loaded data to current session (this imports it into projectMemory)
        // The backend will merge this with the current session
        if (user) {
          await api.saveProject(user.user_id, projectData.projectId, data);
        }
      }
      
      // Close any open stages and return to timeline
      setActiveStage(null);
      setIsStageOpen(false);
      
      // Reload project data to sync with backend
      await loadProjectData();
    } catch (err) {
      console.error('Failed to load project:', err);
    }
  };

  // Close account menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (accountMenuRef.current && !accountMenuRef.current.contains(event.target)) {
        setShowAccountMenu(false);
      }
    };

    if (showAccountMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showAccountMenu]);

  const renderStage = () => {
    const commonProps = {
      sessionId,
      sessionData,
      updateSessionData,
      voice,
      onClose: handleClose,
      onNext: goToNextStage,
      completeStage: completeCurrentStage,
      openUpgradeModal,
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

  // Global loading state while restoring session
  if (authLoading) {
    return (
      <div className="fixed inset-0 bg-studio-dark flex items-center justify-center z-50">
        <div className="text-center">
          <div className="text-studio-white text-lg font-montserrat mb-2">Loading your account…</div>
          <div className="animate-spin text-studio-gold text-2xl">⏳</div>
        </div>
      </div>
    );
  }

  // Handle billing routes
  const currentPath = window.location.pathname;
  if (currentPath === '/billing/success') {
    return <BillingSuccess />;
  }
  if (currentPath === '/billing/cancel') {
    return <BillingCancel />;
  }

  return (
    <div className="app-root">
      {/* Auth Header */}
      <div className="fixed top-4 right-4 z-50">
        {!user ? (
          <motion.button
            onClick={() => setShowAuthModal(true)}
            className="px-4 py-2 bg-studio-red hover:bg-studio-red/80 text-studio-white 
                     font-montserrat font-semibold rounded-lg transition-colors"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            Sign In
          </motion.button>
        ) : (
          <div className="relative" ref={accountMenuRef}>
            <motion.div
              onClick={() => setShowAccountMenu(!showAccountMenu)}
              className="w-10 h-10 rounded-full bg-studio-gold flex items-center justify-center 
                       text-studio-dark font-montserrat font-bold cursor-pointer
                       hover:bg-studio-gold/80 transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {user.email?.[0]?.toUpperCase() || 'A'}
            </motion.div>
            
            {showAccountMenu && (
              <motion.div
                className="absolute top-12 right-0 bg-studio-gray border border-studio-white/20 
                         rounded-lg min-w-[180px] shadow-lg"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <div className="py-2">
                  <div className="px-4 py-2 text-studio-white/60 text-sm font-poppins border-b border-studio-white/10">
                    {user.email}
                  </div>
                  <button
                    onClick={() => {
                      setShowAccountMenu(false);
                      // TODO: Navigate to account page in Phase 8.4
                    }}
                    className="w-full text-left px-4 py-2 text-studio-white font-poppins hover:bg-studio-dark/50 transition-colors"
                  >
                    Account
                  </button>
                  <button
                    onClick={() => {
                      setShowAccountMenu(false);
                      setShowManageProjects(true);
                    }}
                    className="w-full text-left px-4 py-2 text-studio-white font-poppins hover:bg-studio-dark/50 transition-colors"
                  >
                    Manage Projects
                  </button>
                  <button
                    onClick={handleSaveProject}
                    className="w-full text-left px-4 py-2 text-studio-white font-poppins hover:bg-studio-dark/50 transition-colors"
                  >
                    Save Project
                  </button>
                  <button
                    onClick={handleUpgradeToPro}
                    className="w-full text-left px-4 py-2 text-studio-gold font-poppins hover:bg-studio-dark/50 transition-colors"
                  >
                    Upgrade to Pro
                  </button>
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2 text-red-400 font-poppins hover:bg-studio-dark/50 transition-colors"
                  >
                    Logout
                  </button>
                </div>
              </motion.div>
            )}
          </div>
        )}
      </div>

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

      {/* Auth Modal */}
      <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} />

      {/* Manage Projects Modal */}
      <ManageProjectsModal 
        isOpen={showManageProjects} 
        onClose={() => setShowManageProjects(false)}
        onLoadProject={handleLoadProject}
      />

      {/* Upgrade Modal */}
      <UpgradeModal 
        isOpen={showUpgradeModal} 
        onClose={() => {
          setShowUpgradeModal(false);
          setUpgradeFeature(null);
        }}
        feature={upgradeFeature}
      />

      {/* Save Toast */}
      {saveToast && (
        <motion.div
          className="fixed bottom-4 right-4 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg z-50 font-poppins"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
        >
          {saveToast}
        </motion.div>
      )}

    </div>
  );
}

export default App;