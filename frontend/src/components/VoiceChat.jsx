import { motion, AnimatePresence } from 'framer-motion';

export default function VoiceChat({ voice, activeStage, sessionData }) {
  const { isListening, transcript, interimTranscript, startListening, stopListening } = voice;

  const handleToggleListen = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  return (
    <div className="fixed bottom-8 left-8 z-30 flex flex-col gap-4 max-w-md
                    pb-20 md:pb-8
                    pointer-events-auto">
      {/* Voice Button */}
      <motion.button
        onClick={handleToggleListen}
        className={`
          w-16 h-16 rounded-full flex items-center justify-center
          transition-all duration-300
          ${isListening 
            ? 'bg-studio-red animate-pulse-glow' 
            : 'bg-studio-gray border-2 border-studio-white/20 hover:border-studio-red'
          }
        `}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
      >
        <span className="text-2xl">{isListening ? '🎙️' : '🎤'}</span>
      </motion.button>

      {/* Transcript Bubble */}
      <AnimatePresence>
        {(transcript || interimTranscript) && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.8 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.8 }}
            className="p-4 rounded-lg bg-studio-gray/90 backdrop-blur-sm border border-studio-white/10"
          >
            <p className="text-sm font-poppins text-studio-white">
              {transcript}
              {interimTranscript && (
                <span className="text-studio-white/50"> {interimTranscript}</span>
              )}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Voice Status */}
      {isListening && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-2 text-xs text-studio-red font-montserrat"
        >
          <span className="w-2 h-2 bg-studio-red rounded-full animate-pulse" />
          Listening...
        </motion.div>
      )}
    </div>
  );
}
