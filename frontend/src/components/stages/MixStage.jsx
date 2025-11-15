import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { api } from '../../utils/api';
import StageWrapper from './StageWrapper';
import WavesurferPlayer from '../WavesurferPlayer';

export default function MixStage({ sessionId, sessionData, updateSessionData, voice, onClose, completeStage }) {
  // V24: AI Mix & Master controls only
  const [aiMixEnabled, setAiMixEnabled] = useState(true);
  const [aiMasterEnabled, setAiMasterEnabled] = useState(true);
  const [mixStrength, setMixStrength] = useState(0.7);
  const [masterStrength, setMasterStrength] = useState(0.8);
  const [selectedPreset, setSelectedPreset] = useState('clean'); // warm, clean, bright
  
  // V25: Enabled EQ/FX states (wired to backend DSP)
  const [eq, setEq] = useState({ low: 0, mid: 0, high: 0 });
  const [comp, setComp] = useState(0.5);
  const [reverb, setReverb] = useState(0.3);
  const [limiter, setLimiter] = useState(0.8);
  
  const [mixing, setMixing] = useState(false);
  const [error, setError] = useState(null);
  
  const fileInputRef = useRef(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);

  // V25: Fixed getAudioFile() - always returns File or URL string, never null
  const getAudioFile = () => {
    if (uploadedFile instanceof File) {
      return uploadedFile;
    }
    if (sessionData.vocalFile && typeof sessionData.vocalFile === 'string') {
      return sessionData.vocalFile;
    }
    return null;
  };

  // V25: Can mix if we have a file
  const canMix = !!getAudioFile();

  // V25: Safety - Ensure audio URL only updates when file exists
  useEffect(() => {
    if (uploadedFile instanceof File) {
      const url = URL.createObjectURL(uploadedFile);
      setAudioUrl(url);
      return () => {
        URL.revokeObjectURL(url);
      };
    } else if (sessionData.vocalFile && typeof sessionData.vocalFile === 'string' && sessionData.vocalFile.length > 0) {
      setAudioUrl(sessionData.vocalFile);
    } else {
      setAudioUrl(null);
    }
  }, [uploadedFile, sessionData.vocalFile]);

  // V24: Handle file upload
  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validate audio file
    const allowedExtensions = ['.wav', '.mp3'];
    const fileName = file.name.toLowerCase();
    const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext));
    
    if (!hasValidExtension) {
      voice.speak('Please upload a WAV or MP3 file.');
      return;
    }
    
    setUploadedFile(file);
    setError(null);
  };

  // V25: Fixed handleMixAndMaster - uses api.processMix with REAL DSP parameters
  const handleMixAndMaster = async () => {
    const file = getAudioFile();
    
    // V25: Safety - validate file exists
    if (!file) {
      voice.speak('Please upload a song file to mix.');
      setError('Please upload an audio file to mix.');
      return;
    }
    
    // V25: Safety - validate file is File object or valid URL
    if (!(file instanceof File) && typeof file !== 'string') {
      voice.speak('Invalid audio file. Please try another file.');
      setError('Invalid audio file format.');
      return;
    }

    setMixing(true);
    setError(null);
    
    try {
      voice.speak('Mixing and mastering your track. One moment.');
      
      // V25: Validate DSP parameters before sending
      const validatedParams = {
        ai_mix: aiMixEnabled,
        ai_master: aiMasterEnabled,
        mix_strength: Math.max(0, Math.min(1, mixStrength)),
        master_strength: Math.max(0, Math.min(1, masterStrength)),
        preset: ['warm', 'clean', 'bright'].includes(selectedPreset) ? selectedPreset : 'clean',
        // V25: Real DSP parameters (clamped to valid ranges)
        eq_low: Math.max(-6, Math.min(6, eq.low)),
        eq_mid: Math.max(-6, Math.min(6, eq.mid)),
        eq_high: Math.max(-6, Math.min(6, eq.high)),
        compression: Math.max(0, Math.min(1, comp)),
        reverb: Math.max(0, Math.min(1, reverb)),
        limiter: Math.max(0, Math.min(1, limiter))
      };
      
      // V25: Call /mix/process endpoint with REAL DSP parameters
      const result = await api.processMix(sessionId, file, validatedParams);
      
      if (result && result.file_url) {
        // V25: Update sessionData with mixedFile
        updateSessionData({ 
          mixedFile: result.file_url,
          mixCompleted: true
        });
        
        // V25: Complete the mix stage
        if (completeStage) {
          await completeStage('mix');
        }
        
        voice.speak('Your track has been mixed and mastered.');
      } else {
        throw new Error('No file URL returned from server');
      }
    } catch (err) {
      console.error('Mix failed:', err);
      const errorMessage = 'Mixing failed. Check your audio file.';
      setError(errorMessage);
      voice.speak('Mix failed. Please try another file.');
    } finally {
      setMixing(false);
    }
  };

  return (
    <StageWrapper 
      title="Mix & Master" 
      icon="🎛️" 
      onClose={onClose}
      voice={voice}
    >
      <div className="stage-scroll-container">
        <div className="flex flex-col items-center justify-center gap-8 p-6 md:p-10">
          {/* V24: Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".wav,.mp3"
            onChange={handleFileSelect}
            className="hidden"
          />
          
          {/* V25: Audio Player Preview (moved above controls) */}
          {sessionData.mixedFile ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full max-w-4xl p-6 bg-studio-gray/30 rounded-lg border border-studio-white/10"
            >
              <p className="text-sm text-studio-white/80 mb-3 font-montserrat">✓ Mix & Master Ready</p>
              <WavesurferPlayer url={sessionData.mixedFile} color="#A855F7" height={120} />
            </motion.div>
          ) : canMix && audioUrl && (
            <div className="w-full max-w-4xl p-4 bg-studio-gray/20 rounded-lg border border-studio-white/5">
              <p className="text-xs text-studio-white/60 mb-2 font-montserrat">Audio Preview</p>
              <WavesurferPlayer 
                url={audioUrl} 
                color="#10B981" 
                height={80} 
              />
            </div>
          )}
          
          {/* V25: Mix Controls (reorganized with labels and grouping) */}
          <div className="w-full max-w-4xl space-y-8">
            {/* Tone Controls (EQ) */}
            <div className="space-y-4">
              <h3 className="text-sm opacity-80 font-montserrat">Tone Controls (EQ)</h3>
              <div className="grid grid-cols-3 gap-6">
                <Slider
                  label="Low"
                  value={eq.low}
                  onChange={(v) => setEq({...eq, low: v})}
                  min={-6}
                  max={6}
                  step={0.5}
                />
                
                <Slider
                  label="Mid"
                  value={eq.mid}
                  onChange={(v) => setEq({...eq, mid: v})}
                  min={-6}
                  max={6}
                  step={0.5}
                />
                
                <Slider
                  label="High"
                  value={eq.high}
                  onChange={(v) => setEq({...eq, high: v})}
                  min={-6}
                  max={6}
                  step={0.5}
                />
              </div>
            </div>

            {/* Dynamics (Compression & Limiter) */}
            <div className="space-y-4">
              <h3 className="text-sm opacity-80 font-montserrat">Dynamics (Compression & Limiter)</h3>
              <div className="grid grid-cols-2 gap-6">
                <Slider
                  label="Compression"
                  value={comp}
                  onChange={setComp}
                  min={0}
                  max={1}
                  step={0.1}
                />
                
                <Slider
                  label="Limiter"
                  value={limiter}
                  onChange={setLimiter}
                  min={0}
                  max={1}
                  step={0.1}
                />
              </div>
            </div>

            {/* Reverb & Presets */}
            <div className="space-y-4">
              <h3 className="text-sm opacity-80 font-montserrat">Reverb & Presets</h3>
              <div className="grid grid-cols-2 gap-6">
                <Slider
                  label="Reverb"
                  value={reverb}
                  onChange={setReverb}
                  min={0}
                  max={1}
                  step={0.1}
                />
                
                <div>
                  <label className="text-sm font-poppins text-studio-white/80 mb-2 block">Preset</label>
                  <div className="grid grid-cols-3 gap-2">
                    {['warm', 'clean', 'bright'].map((preset) => (
                      <button
                        key={preset}
                        onClick={() => setSelectedPreset(preset)}
                        className={`py-2 px-3 rounded text-xs font-montserrat transition-colors ${
                          selectedPreset === preset
                            ? 'bg-studio-red text-white'
                            : 'bg-studio-gray/30 text-studio-white/60 hover:bg-studio-gray/50'
                        }`}
                      >
                        {preset.charAt(0).toUpperCase() + preset.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* AI Processing Controls */}
            <div className="space-y-4">
              <h3 className="text-sm opacity-80 font-montserrat">AI Processing</h3>
              
              {/* AI Mix Toggle */}
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-poppins text-studio-white/80">AI Mix</label>
                <button
                  onClick={() => setAiMixEnabled(!aiMixEnabled)}
                  className={`w-12 h-6 rounded-full transition-colors ${
                    aiMixEnabled ? 'bg-studio-red' : 'bg-studio-gray'
                  }`}
                >
                  <div className={`w-5 h-5 rounded-full bg-white transition-transform ${
                    aiMixEnabled ? 'translate-x-6' : 'translate-x-0.5'
                  }`} />
                </button>
              </div>
              
              {aiMixEnabled && (
                <Slider
                  label="Mix Strength"
                  value={mixStrength}
                  onChange={setMixStrength}
                  min={0}
                  max={1}
                  step={0.1}
                />
              )}
              
              {/* AI Master Toggle */}
              <div className="flex items-center justify-between mb-2 mt-4">
                <label className="text-sm font-poppins text-studio-white/80">AI Master</label>
                <button
                  onClick={() => setAiMasterEnabled(!aiMasterEnabled)}
                  className={`w-12 h-6 rounded-full transition-colors ${
                    aiMasterEnabled ? 'bg-studio-red' : 'bg-studio-gray'
                  }`}
                >
                  <div className={`w-5 h-5 rounded-full bg-white transition-transform ${
                    aiMasterEnabled ? 'translate-x-6' : 'translate-x-0.5'
                  }`} />
                </button>
              </div>
              
              {aiMasterEnabled && (
                <Slider
                  label="Master Strength"
                  value={masterStrength}
                  onChange={setMasterStrength}
                  min={0}
                  max={1}
                  step={0.1}
                />
              )}
            </div>
          </div>

          {/* V25: Mix & Master Button (bottom of same container) */}
          <div className="w-full max-w-4xl space-y-3">
            <motion.button
              onClick={() => fileInputRef.current?.click()}
              disabled={mixing}
              className={`
                w-full py-2 rounded-lg font-montserrat font-semibold text-sm
                transition-all duration-300 border border-studio-white/20
                ${!mixing
                  ? 'bg-studio-gray/30 hover:bg-studio-gray/40 text-studio-white/80'
                  : 'bg-studio-gray text-studio-white/40 cursor-not-allowed'
                }
              `}
            >
              {uploadedFile ? `📁 ${uploadedFile.name}` : '📤 Upload Audio File'}
            </motion.button>

            <motion.button
              onClick={handleMixAndMaster}
              disabled={!canMix || mixing}
              className={`
                w-full py-4 rounded-lg font-montserrat font-semibold
                transition-all duration-300
                ${canMix && !mixing
                  ? 'bg-studio-red hover:bg-studio-red/80 text-studio-white'
                  : 'bg-studio-gray text-studio-white/40 cursor-not-allowed'
                }
              `}
              whileHover={canMix && !mixing ? { scale: 1.02 } : {}}
              whileTap={canMix && !mixing ? { scale: 0.98 } : {}}
            >
              {mixing ? 'Mixing...' : canMix ? 'Mix & Master' : 'Need Audio File'}
            </motion.button>
            
            {/* V24: Error message */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full p-3 bg-red-500/10 border border-red-500/30 rounded-lg"
              >
                <p className="text-sm text-red-400 font-poppins">{error}</p>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </StageWrapper>
  );
}

function Slider({ label, value, onChange, min, max, step }) {
  return (
    <div>
      <div className="flex justify-between mb-2">
        <label className="text-sm font-poppins text-studio-white/80">
          {label}
        </label>
        <span className="text-sm font-mono text-studio-white/60">
          {value > 0 ? '+' : ''}{value.toFixed(1)}
        </span>
      </div>
      <input
        type="range"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        min={min}
        max={max}
        step={step}
        className="w-full h-2 bg-studio-gray rounded-lg appearance-none
                 [&::-webkit-slider-thumb]:appearance-none
                 [&::-webkit-slider-thumb]:w-4
                 [&::-webkit-slider-thumb]:h-4
                 [&::-webkit-slider-thumb]:rounded-full
                 [&::-webkit-slider-thumb]:bg-studio-red
                 cursor-pointer [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:hover:bg-studio-red/80"
      />
    </div>
  );
}
