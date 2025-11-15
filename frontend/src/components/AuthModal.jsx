import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';

export default function AuthModal({ isOpen, onClose }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, signup } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await signup(email, password);
      }
      onClose();
      setEmail('');
      setPassword('');
    } catch (err) {
      setError(err.message || 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setIsLogin(!isLogin);
    setError('');
    setEmail('');
    setPassword('');
  };

  if (!isOpen) return null;

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
          <h3 className="text-lg text-studio-gold font-montserrat mb-0">
            {isLogin ? '🔐 Sign In' : '✨ Sign Up'}
          </h3>
          
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
                className="w-full px-4 py-2 bg-studio-dark border border-studio-white/20 rounded-lg
                         text-studio-white font-poppins placeholder-studio-white/40
                         focus:outline-none focus:border-studio-gold disabled:opacity-50"
              />
            </div>
            
            <div>
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                className="w-full px-4 py-2 bg-studio-dark border border-studio-white/20 rounded-lg
                         text-studio-white font-poppins placeholder-studio-white/40
                         focus:outline-none focus:border-studio-gold disabled:opacity-50"
              />
            </div>

            {error && (
              <p className="text-sm text-red-400 font-poppins mb-0">
                {error}
              </p>
            )}

            <div className="flex gap-3">
              <motion.button
                type="submit"
                disabled={loading}
                className="flex-1 py-2 bg-studio-red hover:bg-studio-red/80 disabled:bg-studio-gray
                         text-studio-white font-montserrat font-semibold rounded-lg transition-colors"
                whileHover={{ scale: loading ? 1 : 1.02 }}
                whileTap={{ scale: loading ? 1 : 0.98 }}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="animate-spin">⏳</span>
                    {isLogin ? 'Signing in...' : 'Signing up...'}
                  </span>
                ) : (
                  isLogin ? 'Sign In' : 'Sign Up'
                )}
              </motion.button>
              
              <motion.button
                type="button"
                onClick={onClose}
                disabled={loading}
                className="flex-1 py-2 bg-studio-gray/50 hover:bg-studio-gray/70 disabled:bg-studio-gray
                         text-studio-white font-montserrat font-semibold rounded-lg transition-colors"
                whileHover={{ scale: loading ? 1 : 1.02 }}
                whileTap={{ scale: loading ? 1 : 0.98 }}
              >
                Cancel
              </motion.button>
            </div>
          </form>

          <div className="text-center mt-2">
            <button
              type="button"
              onClick={switchMode}
              disabled={loading}
              className="text-sm text-studio-white/60 hover:text-studio-white font-poppins transition-colors disabled:opacity-50"
            >
              {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

