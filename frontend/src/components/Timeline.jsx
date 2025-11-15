import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect, forwardRef } from 'react';
import '../styles/Timeline.css';

const Timeline = forwardRef(({ currentStage, completedStages = [], onStageClick, showBackButton, onBackToTimeline }, ref) => {
  const [showGoalModal, setShowGoalModal] = useState(false);
  
  const stages = [
    { id: 'beat', icon: '🎵', label: 'Beat', dept: 'Echo' },
    { id: 'lyrics', icon: '✍️', label: 'Lyrics', dept: 'Lyrica' },
    { id: 'upload', icon: '🎙', label: 'Upload', dept: 'Nova' },
    { id: 'mix', icon: '🎚', label: 'Mix', dept: 'Tone' },
    { id: 'release', icon: '💿', label: 'Release', dept: 'Aria' },
    { id: 'content', icon: '📣', label: 'Content', dept: 'Vee' },
    { id: 'analytics', icon: '📊', label: 'Analytics', dept: 'Pulse' }
  ];

  const getStageStatus = (stageId) => {
    if (completedStages.includes(stageId)) return 'completed';
    if (stageId === currentStage) return 'active';
    return 'upcoming';
  };

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

  const progressPercentage = (completedStages.length / stages.length) * 100;
  const isGoalReached = completedStages.length === stages.length;

  useEffect(() => {
    if (isGoalReached && !showGoalModal) {
      // Show modal after short delay
      const timer = setTimeout(() => setShowGoalModal(true), 800);
      return () => clearTimeout(timer);
    }
  }, [isGoalReached]);

  const handleRestartCycle = () => {
    setShowGoalModal(false);
    // Reset workflow (handled by parent)
    if (onBackToTimeline) onBackToTimeline();
  };

  return (
    <>
      <div className="timeline-container">
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

      <div className="timeline-track">
        <motion.div 
          className="timeline-progress-bar"
          initial={{ width: 0 }}
          animate={{ width: `${progressPercentage}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
        
        <div className="timeline-stages">
          {stages.map((stage, index) => {
            const status = getStageStatus(stage.id);
            const isActive = status === 'active';
            const isCompleted = status === 'completed';
            
            return (
              <div key={stage.id} className="timeline-stage-wrapper">
                <motion.div
                  className={`timeline-stage ${status}`}
                  onClick={() => onStageClick(stage.id)}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                  style={{ cursor: 'pointer' }}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
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
                  <div className="stage-label">{stage.label}</div>
                  <div className="stage-dept">{stage.dept}</div>
                  
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
                
                {index < stages.length - 1 && (
                  <motion.div
                    className="timeline-connector"
                    initial={{ scaleX: 0 }}
                    animate={{ 
                      scaleX: 1,
                      backgroundColor: isCompleted ? '#FFB800' : 'rgba(244, 244, 244, 0.2)'
                    }}
                    transition={{ delay: index * 0.1 + 0.2, duration: 0.4 }}
                  />
                )}
              </div>
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
        </div>
      </div>

      <div className="timeline-progress-text">
        {completedStages.length} of {stages.length} stages complete
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
