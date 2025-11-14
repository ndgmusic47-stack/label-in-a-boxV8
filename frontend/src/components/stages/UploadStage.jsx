import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { api } from '../../utils/api';
import StageWrapper from './StageWrapper';
import WavesurferPlayer from '../WavesurferPlayer';

export default function UploadStage({ sessionId, sessionData, updateSessionData, voice, onClose }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const handleDrop = useCallback(async (e) => {
    e.preventDefault();
    setDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    const audioFile = files.find(f => f.type.startsWith('audio/') || f.name.endsWith('.wav'));
    
    if (audioFile) {
      await uploadFile(audioFile);
    } else {
      setError('Please drop an audio file (.wav, .mp3, .m4a)');
      voice.speak('Please drop an audio file');
    }
  }, [sessionId]);

  const uploadFile = async (file) => {
    setUploading(true);
    setError(null);
    
    try {
      voice.speak(`Uploading your vocal recording...`);
      
      // Upload recording
      const result = await api.uploadRecording(file, sessionId);
      
      // Sync with backend project state to get vocalFile from project.assets.stems[0].url
      await api.syncProject(sessionId, updateSessionData);
      
      voice.speak('Your vocal is uploaded and ready to mix!');
    } catch (err) {
      setError(err.message);
      voice.speak('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) uploadFile(file);
  };

  return (
    <StageWrapper 
      title="Upload Recording" 
      icon="🎤" 
      onClose={onClose}
      voice={voice}
    >
      <div className="stage-scroll-container">
        <div className="flex flex-col items-center justify-center gap-8 p-6 md:p-10">
        <div className="text-6xl mb-4">
          🎤
        </div>

        <motion.div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={`
            w-full max-w-2xl h-64 border-2 border-dashed rounded-lg
            flex flex-col items-center justify-center gap-4
            transition-all duration-300 cursor-pointer
            ${dragging 
              ? 'border-studio-red bg-studio-red/10' 
              : 'border-studio-white/20 hover:border-studio-white/40'
            }
            ${uploading ? 'opacity-50 pointer-events-none' : ''}
          `}
          whileHover={{ scale: 1.02 }}
        >
          <input
            type="file"
            id="file-input"
            accept="audio/*,.wav,.mp3,.m4a"
            onChange={handleFileSelect}
            className="hidden"
          />
          <label htmlFor="file-input" className="cursor-pointer text-center">
            <p className="text-2xl mb-2">📁</p>
            <p className="text-studio-white font-montserrat">
              {uploading ? 'Uploading...' : 'Drop your vocal recording here'}
            </p>
            <p className="text-sm text-studio-white/40 font-poppins mt-2">
              or click to browse (.wav, .mp3, .m4a)
            </p>
          </label>
        </motion.div>

        {error && (
          <p className="text-red-400 text-sm">{error}</p>
        )}

        {sessionData.vocalFile && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-2xl p-4 bg-studio-gray/30 rounded-lg border border-studio-white/10"
          >
            <p className="text-sm text-studio-white/80 mb-3 font-montserrat">✓ Vocal Uploaded</p>
            <WavesurferPlayer url={sessionData.vocalFile} color="#10B981" height={100} />
          </motion.div>
        )}
        </div>
      </div>
    </StageWrapper>
  );
}
