import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import { api } from '../utils/api';

export default function UpgradeModal({ isOpen, onClose, feature }) {
  const { user } = useAuth();
  if (!isOpen) return null;

  const getFeatureMessage = () => {
    switch (feature) {
      case 'multi_project':
        return 'Upgrade to Pro to create multiple projects';
      case 'daily_release_limit':
        return 'Upgrade to Pro for unlimited releases';
      default:
        return 'Upgrade to Pro to unlock this feature';
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className="modal-container bg-studio-gray border border-studio-white/20 rounded-lg max-w-md w-full mx-4"
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.8, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          onClick={(e) => e.stopPropagation()}
        >
          <h3 className="text-lg text-studio-gold font-montserrat mb-4">
            Upgrade to NP22 Pro
          </h3>
          
          <p className="text-studio-white/80 font-poppins mb-6">
            {getFeatureMessage()}
          </p>

          <div className="mb-6">
            <p className="text-studio-white font-poppins mb-3">Unlock:</p>
            <ul className="space-y-2">
              <li className="flex items-center text-studio-white/90 font-poppins">
                <span className="text-studio-gold mr-2">✓</span>
                Unlimited Projects
              </li>
              <li className="flex items-center text-studio-white/90 font-poppins">
                <span className="text-studio-gold mr-2">✓</span>
                Unlimited Releases
              </li>
              <li className="flex items-center text-studio-white/90 font-poppins">
                <span className="text-studio-gold mr-2">✓</span>
                Faster Mix Engine (future)
              </li>
              <li className="flex items-center text-studio-white/90 font-poppins">
                <span className="text-studio-gold mr-2">✓</span>
                Priority Support
              </li>
            </ul>
          </div>

          <div className="flex gap-3">
            <motion.button
              onClick={async () => {
                if (!user) {
                  onClose();
                  return;
                }
                try {
                  const result = await api.createCheckoutSession(user.user_id);
                  if (result && result.url) {
                    window.location.href = result.url;
                  } else {
                    console.error('No checkout URL returned');
                    onClose();
                  }
                } catch (err) {
                  console.error('Failed to create checkout session:', err);
                  onClose();
                }
              }}
              className="flex-1 py-2 bg-studio-red hover:bg-studio-red/80
                       text-studio-white font-montserrat font-semibold rounded-lg transition-colors"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              Upgrade
            </motion.button>
            
            <motion.button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 bg-studio-gray/50 hover:bg-studio-gray/70
                       text-studio-white font-montserrat font-semibold rounded-lg transition-colors"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              Cancel
            </motion.button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

