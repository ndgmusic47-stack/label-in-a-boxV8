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
    <div className="flex flex-col w-full h-full bg-studio-black">
      {/* Header with Title and Close Button */}
      <div className="flex-shrink-0 flex items-center justify-between px-8 py-6 border-b border-studio-white/10">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3"
        >
          <span className="text-3xl">{icon}</span>
          <h2 className="text-2xl font-bold font-montserrat text-studio-white">
            {title}
          </h2>
        </motion.div>

        <motion.button
          onClick={onClose}
          className="w-12 h-12 rounded-full
                   bg-studio-gray/50 hover:bg-studio-red
                   border border-studio-white/20 hover:border-studio-red
                   flex items-center justify-center
                   transition-all duration-300"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
        >
          <span className="text-2xl">✕</span>
        </motion.button>
      </div>

      {/* Content - Scrollable */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {children}
      </div>
    </div>
  );
}
