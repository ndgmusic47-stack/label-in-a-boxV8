import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect, forwardRef } from 'react';
import '../styles/Timeline.css';

const Timeline = forwardRef(({ currentStage, activeStage, completedStages = [], onStageClick, showBackButton, onBackToTimeline, setProject, setCurrentStage: setCurrentStageProp, project, sessionData }, ref) => {
  const [showGoalModal, setShowGoalModal] = useState(false);
  const [wasAllComplete, setWasAllComplete] = useState(false);
  
  const stages = [
    { id: 'beat', icon: '🎵', label: 'Beat', dept: 'Echo' },
    { id: 'lyrics', icon: '✍️', label: 'Lyrics', dept: 'Lyrica' },
    { id: 'upload', icon: '🎙', label: 'Upload', dept: 'Nova' },
    { id: 'mix', icon: '🎚', label: 'Mix', dept: 'Tone' },
    { id: 'release', icon: '💿', label: 'Release', dept: 'Aria' },
    { id: 'content', icon: '📣', label: 'Content', dept: 'Vee' },
    { id: 'analytics', icon: '📊', label: 'Analytics', dept: 'Pulse' }
  ];

  const updateProjectStage = (stage, data) => {
    if (setProject) {
      setProject(prev => ({
        ...prev,
        stages: {
          ...prev.stages,
          [stage]: {
            ...(prev.stages?.[stage] || {}),
            ...data
          }
        }
      }));
    }
  };

  const moveToNextStage = () => {
    if (setCurrentStageProp) {
      setCurrentStageProp(prev => {
        const currentIndex = stages.findIndex(s => s.id === prev);
        if (currentIndex < stages.length - 1) {
          return stages[currentIndex + 1].id;
        }
        return prev;
      });
    }
  };

  const getStageStatus = (stageId) => {
    // Phase 1: Check object format for tick system
    if (completedStages[stageId]) return 'completed';
    
    // PATCH 2.6: For mix stage, also check project.stages.mix.completed or sessionData.masterFile
    if (stageId === 'mix') {
      const mixCompleted = project?.stages?.mix?.completed || sessionData?.masterFile;
      if (mixCompleted) return 'completed';
    }
    
    return 'upcoming';
  };

  // Mix stage completion is handled via completeStage prop passed from App.jsx
  // When MixStage calls completeStage("mix"), App.jsx updates completedStages
  // and Timeline automatically reflects the completion status

  const getStagePrompt = () => {
    const stage = stages.find(s => s.id === currentStage);
    const prompts = {
      'beat': 'Create your instrumental foundation',
      'lyrics': 'Write your story and message',
      'upload': 'Record and upload your vocals',
      'mix': 'Balance and polish your sound',
      'release': 'Prepare your music for the world',
      'content': 'Create marketing content and videos',
      'analytics': 'Track your success and growth'
    };
    return stage ? prompts[currentStage] || 'Continue your creative journey' : '';
  };

  // Phase 1: Calculate progress from object format
  const completedCount = Object.keys(completedStages).filter(key => completedStages[key]).length;
  const progressPercentage = (completedCount / stages.length) * 100;
  const isGoalReached = completedCount === stages.length;

  // Fix Goal Reached animation trigger - only fire once when transitioning from not-all-complete to all-complete
  useEffect(() => {
    if (isGoalReached && !wasAllComplete && !showGoalModal) {
      // Show modal after short delay
      const timer = setTimeout(() => {
        setShowGoalModal(true);
        setWasAllComplete(true);
      }, 800);
      return () => clearTimeout(timer);
    } else if (!isGoalReached) {
      // Reset when not all complete
      setWasAllComplete(false);
    }
  }, [isGoalReached, wasAllComplete, showGoalModal]);

  const handleRestartCycle = () => {
    setShowGoalModal(false);
    // Reset workflow (handled by parent)
    if (onBackToTimeline) onBackToTimeline();
  };

  return (
    <>
      <div className="timeline timeline-container">
        {showBackButton && (
          <motion.button
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            onClick={onBackToTimeline}
            className="back-to-timeline-btn"
          >
            ← Back to Timeline
          </motion.button>
        )}
        
        <div className="timeline-header">
          <h2 className="timeline-title">Your Label in a Box</h2>
          <p className="timeline-subtitle">
            Current Stage: <span className="current-stage-name">{stages.find(s => s.id === currentStage)?.label || 'Beat'}</span>
          </p>
          <p className="stage-prompt">{getStagePrompt()}</p>
        </div>

        
        
        {stages.map((stage, index) => {
          const status = getStageStatus(stage.id);
          // Fix glow behavior - only clicked module should glow (not based on completion or currentStage)
          const isActive = activeStage === stage.id;
          const isCompleted = status === 'completed';
          
          return (
            <motion.div
              key={stage.id}
              className={`stage ${status}`}
              onClick={() => onStageClick(stage.id)}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              style={{ cursor: 'pointer' }}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <div className={`timeline-icon ${isActive ? 'active' : ''} ${status}`}>
                {isActive && (
                  <motion.div
                    className="pulse-ring"
                    animate={{
                      scale: [1, 1.8],
                      opacity: [0.5, 0]
                    }}
                    transition={{
                      duration: 2.5,
                      repeat: Infinity,
                      ease: 'easeOut',
                      repeatDelay: 0.3
                    }}
                  />
                )}
                <div className="stage-icon">{stage.icon}</div>
              </div>
              <div className="stage-label">{stage.label}</div>
              
              {isCompleted && (
                <motion.div
                  className="completion-check"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 300 }}
                >
                  ✓
                </motion.div>
              )}
            </motion.div>
          );
        })}
        
        <motion.div
          className="timeline-goal"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: stages.length * 0.1 }}
        >
          <div className={`goal-icon ${isGoalReached ? 'completed' : ''}`}>🎯</div>
          <div className={`goal-label ${isGoalReached ? 'completed' : ''}`}>Goal Reached</div>
        </motion.div>

        <div className="timeline-progress-text">
          {completedCount} of {stages.length} stages complete
          {progressPercentage === 100 && (
            <span className="celebration"> — Release Ready! 🎉</span>
          )}
        </div>
      </div>

      {/* Goal Reached Modal */}
      <AnimatePresence>
        {showGoalModal && (
          <motion.div
            className="goal-modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowGoalModal(false)}
          >
            <motion.div
              className="goal-modal"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 25 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="goal-modal-icon">🎯</div>
              <h2 className="goal-modal-title">Cycle Complete!</h2>
              <p className="goal-modal-message">
                Your release pack is ready—tracks are mixed, content is created, and analytics are live. 
                Ready to start your next masterpiece?
              </p>
              <button 
                className="goal-modal-button"
                onClick={handleRestartCycle}
              >
                Restart Cycle
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
});

Timeline.displayName = 'Timeline';

export default Timeline;
