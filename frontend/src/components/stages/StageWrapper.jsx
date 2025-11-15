import { useEffect } from 'react';
import { motion } from 'framer-motion';

export default function StageWrapper({ title, icon, children, onClose, voice, onVoiceCommand }) {
  useEffect(() => {
    if (voice && onVoiceCommand) {
      const checkTranscript = setInterval(() => {
        if (voice.transcript) {
          onVoiceCommand(voice.transcript);
        }
      }, 1000);

      return () => clearInterval(checkTranscript);
    }
  }, [voice, onVoiceCommand]);

  return (
    <div className="stage-wrapper">
      {/* Header with Title and Close Button */}
      <div className="stage-header">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="stage-header-title"
        >
          <span className="text-3xl">{icon}</span>
          <h2 className="text-2xl font-bold font-montserrat text-studio-white">
            {title}
          </h2>
        </motion.div>

        <motion.button
          onClick={onClose}
          className="stage-close-button"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
        >
          <span className="text-2xl">✕</span>
        </motion.button>
      </div>

      {/* Content */}
      <div className="stage-content">
        {children}
      </div>
    </div>
  );
}
