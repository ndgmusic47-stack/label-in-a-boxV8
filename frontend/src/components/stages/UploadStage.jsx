import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { api } from '../../utils/api';
import StageWrapper from './StageWrapper';
import WavesurferPlayer from '../WavesurferPlayer';

export default function UploadStage({ sessionId, sessionData, updateSessionData, voice, onClose, onNext, completeStage }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  // V20: Frontend audio validation
  const validateAudioFile = (file) => {
    // Check file size (50MB limit)
    const maxSize = 50 * 1024 * 1024; // 50MB in bytes
    if (file.size > maxSize) {
      return { valid: false, error: 'File size exceeds 50MB limit' };
    }

    // Check file extension (supported formats: .wav, .mp3, .aiff)
    const allowedExtensions = ['.wav', '.mp3', '.aiff'];
    const fileName = file.name.toLowerCase();
    const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext));
    
    if (!hasValidExtension) {
      return { valid: false, error: 'Unsupported format. Please use .wav, .mp3, or .aiff' };
    }

    return { valid: true };
  };

  const handleDrop = useCallback(async (e) => {
    e.preventDefault();
    setDragging(false);
    
    try {
      const files = Array.from(e.dataTransfer.files);
      const audioFile = files.find(f => f.type.startsWith('audio/') || f.name.match(/\.(wav|mp3|aiff)$/i));
      
      if (audioFile) {
        // V20: Validate before upload
        const validation = validateAudioFile(audioFile);
        if (!validation.valid) {
          setError(validation.error);
          voice.speak('There was a problem uploading your vocal file.');
          return;
        }
        await uploadFile(audioFile);
      } else {
        setError('Please drop an audio file (.wav, .mp3, .aiff)');
        voice.speak('Please drop an audio file');
      }
    } catch (err) {
      setError(err.message || 'An error occurred');
      voice.speak('There was a problem uploading your vocal file.');
    }
  }, [sessionId, voice]);

  const uploadFile = async (file) => {
    setUploading(true);
    setError(null);
    
    try {
      // V20: Frontend validation before upload
      const validation = validateAudioFile(file);
      if (!validation.valid) {
        setError(validation.error);
        voice.speak('There was a problem uploading your vocal file.');
        setUploading(false);
        return;
      }

      voice.speak(`Uploading your vocal recording...`);
      
      // Upload recording
      const result = await api.uploadRecording(file, sessionId);
      
      // V20: Extract file URL from result
      const fileUrl = result.file_url || result.vocal_url || result.uploaded;
      
      // V20: Update sessionData with vocal file
      updateSessionData({
        vocalFile: fileUrl,
        vocalUploaded: true
      });
      
      // Sync with backend project state to get vocalFile from project.assets.stems[0].url
      await api.syncProject(sessionId, updateSessionData);
      
      // V20: Auto-complete upload stage
      if (completeStage) {
        completeStage('upload');
      }
      
      // V20: Voice feedback on success
      voice.speak('Vocal uploaded successfully. You can proceed to the mix stage.');
    } catch (err) {
      setError(err.message || 'Upload failed. Please try again.');
      // V20: Voice feedback on error
      voice.speak('There was a problem uploading your vocal file.');
    } finally {
      setUploading(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      // V20: Validate before upload
      const validation = validateAudioFile(file);
      if (!validation.valid) {
        setError(validation.error);
        voice.speak('There was a problem uploading your vocal file.');
        return;
      }
      uploadFile(file);
    }
  };

  return (
    <StageWrapper 
      title="Upload Recording" 
      icon="🎤" 
      onClose={onClose}
      onNext={onNext}
      voice={voice}
    >
      <div className="stage-scroll-container">
        <div className="flex flex-col items-center justify-center gap-8 p-6 md:p-10">
        <div className="icon-wrapper text-6xl mb-4">
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
            accept="audio/*,.wav,.mp3,.aiff"
            onChange={handleFileSelect}
            className="hidden"
          />
          <label htmlFor="file-input" className="cursor-pointer text-center">
            <p className="text-2xl mb-2">📁</p>
            <p className="text-sm text-studio-white/90 font-montserrat">
              {uploading ? 'Uploading...' : 'Drop your vocal recording here'}
            </p>
            <p className="text-xs text-studio-white/60 font-poppins mt-2">
              or click to browse (.wav, .mp3, .aiff)
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
            <p className="text-sm text-studio-white/90 mb-3 font-montserrat">✓ Vocal Uploaded</p>
            <WavesurferPlayer url={sessionData.vocalFile} color="#10B981" height={100} />
          </motion.div>
        )}

        {/* V20: Show context from previous stages (beat + lyrics) */}
        {sessionData.beatFile && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-2xl p-4 bg-studio-gray/30 rounded-lg border border-studio-white/10"
          >
            <p className="text-sm text-studio-white/90 mb-3 font-montserrat">Beat Preview</p>
            <audio controls src={sessionData.beatFile} className="w-full" />
          </motion.div>
        )}

        {sessionData.lyricsData && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-2xl p-4 bg-studio-gray/30 rounded-lg border border-studio-white/10"
          >
            <p className="text-sm text-studio-white/90 mb-3 font-montserrat">Lyrics</p>
            <pre className="text-sm text-studio-white/70 font-poppins whitespace-pre-wrap overflow-auto max-h-48">
              {typeof sessionData.lyricsData === 'string' 
                ? sessionData.lyricsData 
                : (sessionData.lyricsData.lyrics_text || JSON.stringify(sessionData.lyricsData, null, 2))}
            </pre>
          </motion.div>
        )}
        </div>
      </div>
    </StageWrapper>
  );
}
