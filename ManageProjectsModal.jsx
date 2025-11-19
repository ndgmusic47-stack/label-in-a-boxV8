import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../utils/api';
import { useAuth } from '../context/AuthContext';

export default function ManageProjectsModal({ isOpen, onClose, onLoadProject }) {
  const { user } = useAuth();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [renamingId, setRenamingId] = useState(null);
  const [newName, setNewName] = useState('');

  useEffect(() => {
    if (isOpen && user) {
      loadProjects();
    }
  }, [isOpen, user]);

  const loadProjects = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await api.listProjects();
      setProjects(result.projects || []);
    } catch (err) {
      setError(err.message || 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNew = async () => {
    try {
      // Create a new project by saving empty project data
      const emptyProjectData = {
        metadata: { track_title: 'Untitled Project' },
        workflow: { current_stage: 'beat', completed_stages: [] },
        release: {},
        mix: {},
        content: {},
        schedule: {},
        upload: {},
        beat: {},
        assets: {},
        workflow_state: {},
        analytics: {},
        chat_log: [],
        voice_prompts: []
      };
      
      await api.saveProject(user.user_id, null, emptyProjectData);
      await loadProjects();
    } catch (err) {
      setError(err.message || 'Failed to create project');
    }
  };

  const handleLoad = async (projectId) => {
    try {
      const result = await api.loadProject(projectId);
      onLoadProject(result);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to load project');
    }
  };

  const handleRename = async (projectId) => {
    if (!newName.trim()) {
      setRenamingId(null);
      return;
    }

    try {
      // Load project, update name, and save
      const result = await api.loadProject(projectId);
      result.projectData.metadata = result.projectData.metadata || {};
      result.projectData.metadata.track_title = newName.trim();
      
      await api.saveProject(user.user_id, projectId, result.projectData);
      setRenamingId(null);
      setNewName('');
      await loadProjects();
    } catch (err) {
      setError(err.message || 'Failed to rename project');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return dateString;
    }
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
          className="modal-container bg-studio-gray border border-studio-white/20 rounded-lg max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto"
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.8, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg text-studio-gold font-montserrat mb-0">
                📁 Manage Projects
              </h3>
              <button
                onClick={onClose}
                className="text-studio-white/60 hover:text-studio-white text-2xl transition-colors"
              >
                ×
              </button>
            </div>

            {error && (
              <p className="text-sm text-red-400 font-poppins mb-4">
                {error}
              </p>
            )}

            <div className="mb-4">
              <motion.button
                onClick={handleCreateNew}
                disabled={loading}
                className="w-full py-2 bg-studio-red hover:bg-studio-red/80 disabled:bg-studio-gray
                         text-studio-white font-montserrat font-semibold rounded-lg transition-colors"
                whileHover={{ scale: loading ? 1 : 1.02 }}
                whileTap={{ scale: loading ? 1 : 0.98 }}
              >
                ➕ Create New Project
              </motion.button>
            </div>

            <div className="border-t border-studio-white/10 pt-4">
              <h4 className="text-studio-white font-montserrat mb-3">Saved Projects</h4>
              
              {loading ? (
                <div className="text-center py-8 text-studio-white/60">
                  <span className="animate-spin">⏳</span> Loading projects...
                </div>
              ) : projects.length === 0 ? (
                <div className="text-center py-8 text-studio-white/60 font-poppins">
                  No saved projects yet. Create one to get started!
                </div>
              ) : (
                <div className="space-y-2">
                  {projects.map((project) => (
                    <div
                      key={project.projectId}
                      className="bg-studio-dark border border-studio-white/10 rounded-lg p-4 flex items-center justify-between"
                    >
                      <div className="flex-1">
                        {renamingId === project.projectId ? (
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={newName}
                              onChange={(e) => setNewName(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleRename(project.projectId);
                                if (e.key === 'Escape') {
                                  setRenamingId(null);
                                  setNewName('');
                                }
                              }}
                              autoFocus
                              className="flex-1 px-2 py-1 bg-studio-gray border border-studio-white/20 rounded
                                       text-studio-white font-poppins focus:outline-none focus:border-studio-gold"
                            />
                            <button
                              onClick={() => handleRename(project.projectId)}
                              className="px-3 py-1 bg-studio-gold hover:bg-studio-gold/80 text-studio-dark
                                       font-poppins rounded text-sm"
                            >
                              ✓
                            </button>
                            <button
                              onClick={() => {
                                setRenamingId(null);
                                setNewName('');
                              }}
                              className="px-3 py-1 bg-studio-gray hover:bg-studio-gray/80 text-studio-white
                                       font-poppins rounded text-sm"
                            >
                              ✕
                            </button>
                          </div>
                        ) : (
                          <>
                            <div className="text-studio-white font-montserrat font-semibold">
                              {project.name || 'Untitled Project'}
                            </div>
                            <div className="text-studio-white/60 text-sm font-poppins">
                              Updated: {formatDate(project.updatedAt)}
                            </div>
                          </>
                        )}
                      </div>
                      
                      {renamingId !== project.projectId && (
                        <div className="flex gap-2 ml-4">
                          <motion.button
                            onClick={() => {
                              setRenamingId(project.projectId);
                              setNewName(project.name || '');
                            }}
                            className="px-3 py-1 bg-studio-gray hover:bg-studio-gray/80 text-studio-white
                                     font-poppins rounded text-sm transition-colors"
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                          >
                            ✏️
                          </motion.button>
                          <motion.button
                            onClick={() => handleLoad(project.projectId)}
                            className="px-4 py-1 bg-studio-red hover:bg-studio-red/80 text-studio-white
                                     font-poppins rounded text-sm transition-colors"
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                          >
                            Load
                          </motion.button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

