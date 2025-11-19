import { motion } from 'framer-motion';

export default function BillingSuccess() {
  // Use window.location for navigation since we don't have react-router
  const navigateToDashboard = () => {
    window.location.href = '/';
  };

  return (
    <div className="min-h-screen bg-studio-dark flex items-center justify-center p-4">
      <motion.div
        className="bg-studio-gray border border-studio-white/20 rounded-lg p-8 max-w-md w-full text-center"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      >
        <h2 className="text-3xl font-montserrat text-studio-gold mb-4">
          You're Pro Now 🎉
        </h2>
        <p className="text-studio-white/80 font-poppins mb-6">
          Your account has been upgraded successfully.
        </p>
        <motion.button
          onClick={navigateToDashboard}
          className="px-6 py-3 bg-studio-red hover:bg-studio-red/80
                   text-studio-white font-montserrat font-semibold rounded-lg transition-colors"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          Continue
        </motion.button>
      </motion.div>
    </div>
  );
}

