import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { api } from '../../utils/api';
import StageWrapper from './StageWrapper';
import WavesurferPlayer from '../WavesurferPlayer';

export default function MixStage({ sessionId, sessionData, updateSessionData, voice, onClose, completeStage }) {
  const [beatVolume, setBeatVolume] = useState(0.8);
  const [vocalVolume, setVocalVolume] = useState(1.0);
  const [eq, setEq] = useState({ low: 0, mid: 0, high: 0 });
  const [comp, setComp] = useState(0.5);
  const [reverb, setReverb] = useState(0.3);
  const [limiter, setLimiter] = useState(0.8);
  const [mixing, setMixing] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState(null);
  
  // V21: AI Mix & Master toggles and controls
  const [aiMixEnabled, setAiMixEnabled] = useState(true);
  const [aiMasterEnabled, setAiMasterEnabled] = useState(true);
  const [mixStrength, setMixStrength] = useState(0.7);
  const [masterStrength, setMasterStrength] = useState(0.8);
  const [selectedPreset, setSelectedPreset] = useState('clean'); // warm, clean, bright
  
  const fileInputRef = useRef(null);
  const [uploadedFile, setUploadedFile] = useState(null);

  // V21: File selection logic - use uploaded file OR sessionData.vocalFile
  const getAudioFile = () => {
    if (uploadedFile) return uploadedFile;
    if (sessionData.vocalFile) {
      // Convert URL to file if possible, or return URL for backend to fetch
      return sessionData.vocalFile;
    }
    return null;
  };

  // V21: Allow mixing with uploaded file OR sessionData.vocalFile
  const canMix =
    uploadedFile ||
    sessionData.vocalFile ||
    (sessionData.uploaded && sessionData.uploaded.length > 0); // legacy fallback

  const handleAutoMix = async () => {
    if (!canMix) return;
    
    setAnalyzing(true);
    
    try {
      voice.speak('Setting optimal mix levels for you...');
      
      // Phase 2.2: Auto-mix uses smart defaults (single-file mixing context)
      setEq({ low: 2, mid: 0, high: 1 });
      setComp(0.6);
      setReverb(0.4);
      setLimiter(0.9);
      
      voice.speak('Mix levels optimized! Press Mix & Master when ready.');
    } catch (err) {
      voice.speak('Failed to analyze the mix. Try adjusting manually.');
    } finally {
      setAnalyzing(false);
    }
  };

  // V21: Handle file upload
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
  };

  // V21: New handleMixAndMaster function
  const handleMixAndMaster = async () => {
    const audioFile = getAudioFile();
    
    if (!audioFile && !canMix) {
      voice.speak('Please upload a song file to mix.');
      return;
    }

    setMixing(true);
    
    try {
      voice.speak('Mixing and mastering your track. One moment.');
      
      // V21: Prepare file for upload
      let fileToUpload = null;
      if (uploadedFile) {
        fileToUpload = uploadedFile;
      } else if (sessionData.vocalFile && typeof sessionData.vocalFile === 'string') {
        // Fetch file from URL if it's a string URL
        try {
          const response = await fetch(sessionData.vocalFile);
          const blob = await response.blob();
          fileToUpload = new File([blob], 'audio.wav', { type: blob.type });
        } catch (fetchErr) {
          // If fetch fails, pass the URL to backend
          fileToUpload = sessionData.vocalFile;
        }
      }
      
      if (!fileToUpload) {
        voice.speak('I could not find the audio file. Please try again.');
        setMixing(false);
        return;
      }
      
      // V21: Call new /mix/process endpoint
      const result = await api.processMix(sessionId, fileToUpload, {
        ai_mix: aiMixEnabled,
        ai_master: aiMasterEnabled,
        mix_strength: mixStrength,
        master_strength: masterStrength,
        preset: selectedPreset
      });
      
      if (result && result.file_url) {
        // V21: Update sessionData with mixedFile
        updateSessionData({ 
          mixedFile: result.file_url,
          mixCompleted: true
        });
        
        // V21: Complete the mix stage
        if (completeStage) {
          await completeStage('mix');
        }
        
        voice.speak('Your track has been mixed and mastered.');
      } else {
        throw new Error('No file URL returned');
      }
    } catch (err) {
      console.error('Mix failed:', err);
      voice.speak('I could not mix this file. Please try again.');
    } finally {
      setMixing(false);
    }
  };

  // Keep old handleMix for backward compatibility (can be removed later)
  const handleMix = handleMixAndMaster;

  return (
    <StageWrapper 
      title="Mix & Master" 
      icon="🎛️" 
      onClose={onClose}
      voice={voice}
    >
      <div className="stage-scroll-container">
        <div className="flex flex-col items-center justify-center gap-8 p-6 md:p-10">
        {/* V21: File Upload Input (hidden) */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".wav,.mp3"
          onChange={handleFileSelect}
          className="hidden"
        />
        
        {/* V21: Source Preview - only show if no processed file exists */}
        {!sessionData.mixedFile && canMix && (
          <div className="w-full max-w-4xl grid grid-cols-2 gap-6 mb-4">
            {sessionData.beatFile && (
              <div className="p-4 bg-studio-gray/20 rounded-lg border border-studio-white/5">
                <p className="text-xs text-studio-white/60 mb-2 font-montserrat">Beat Preview</p>
                <WavesurferPlayer url={sessionData.beatFile} color="#3B82F6" height={60} />
              </div>
            )}
            <div className="p-4 bg-studio-gray/20 rounded-lg border border-studio-white/5">
              <p className="text-xs text-studio-white/60 mb-2 font-montserrat">Vocal Preview</p>
              <WavesurferPlayer url={sessionData.vocalFile || (uploadedFile && URL.createObjectURL(uploadedFile))} color="#10B981" height={60} />
            </div>
          </div>
        )}
        
        <div className="w-full max-w-4xl grid grid-cols-2 gap-8">
          {/* Left: Volume Controls */}
          <div className="space-y-6">
            <h3 className="text-studio-red font-montserrat font-semibold text-lg mb-4">
              Volume
            </h3>
            
            <Slider
              label="Beat"
              value={beatVolume}
              onChange={setBeatVolume}
              min={0}
              max={2}
              step={0.1}
            />
            
            <Slider
              label="Vocal"
              value={vocalVolume}
              onChange={setVocalVolume}
              min={0}
              max={2}
              step={0.1}
            />

            <h3 className="text-studio-red font-montserrat font-semibold text-lg mt-8 mb-4">
              EQ <span className="text-xs text-studio-white/40 font-normal">(Coming Soon)</span>
            </h3>
            
            <Slider
              label="Low"
              value={eq.low}
              onChange={(v) => setEq({...eq, low: v})}
              min={-12}
              max={12}
              step={1}
              disabled={true}
            />
            
            <Slider
              label="Mid"
              value={eq.mid}
              onChange={(v) => setEq({...eq, mid: v})}
              min={-12}
              max={12}
              step={1}
              disabled={true}
            />
            
            <Slider
              label="High"
              value={eq.high}
              onChange={(v) => setEq({...eq, high: v})}
              min={-12}
              max={12}
              step={1}
              disabled={true}
            />
          </div>

          {/* Right: Effects */}
          <div className="space-y-6">
            <h3 className="text-studio-red font-montserrat font-semibold text-lg mb-4">
              Effects <span className="text-xs text-studio-white/40 font-normal">(Coming Soon)</span>
            </h3>
            
            <Slider
              label="Compression"
              value={comp}
              onChange={setComp}
              min={0}
              max={1}
              step={0.1}
              disabled={true}
            />
            
            <Slider
              label="Reverb"
              value={reverb}
              onChange={setReverb}
              min={0}
              max={1}
              step={0.1}
              disabled={true}
            />
            
            <Slider
              label="Limiter"
              value={limiter}
              onChange={setLimiter}
              min={0}
              max={1}
              step={0.1}
              disabled={true}
            />

            {/* V21: AI Mix & Master Controls */}
            <h3 className="text-studio-red font-montserrat font-semibold text-lg mt-8 mb-4">
              AI Processing
            </h3>
            
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
            
            {/* V21: Preset Selection */}
            <div className="mt-4">
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

            <motion.button
              onClick={handleAutoMix}
              disabled={!canMix || analyzing}
              className={`
                w-full mt-6 py-3 rounded-lg font-montserrat font-semibold
                transition-all duration-300 border-2
                ${canMix && !analyzing
                  ? 'border-purple-500 bg-purple-500/10 hover:bg-purple-500/20 text-purple-400'
                  : 'border-studio-gray bg-studio-gray/10 text-studio-white/40 cursor-not-allowed'
                }
              `}
              whileHover={canMix ? { scale: 1.02 } : {}}
              whileTap={canMix ? { scale: 0.98 } : {}}
            >
              {analyzing ? '🤖 Analyzing...' : '✨ AI Auto-Mix'}
            </motion.button>

            <motion.button
              onClick={() => fileInputRef.current?.click()}
              disabled={mixing}
              className={`
                w-full mt-3 py-2 rounded-lg font-montserrat font-semibold text-sm
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
                w-full mt-3 py-4 rounded-lg font-montserrat font-semibold
                transition-all duration-300
                ${canMix && !mixing
                  ? 'bg-studio-red hover:bg-studio-red/80 text-studio-white'
                  : 'bg-studio-gray text-studio-white/40 cursor-not-allowed'
                }
              `}
              whileHover={canMix ? { scale: 1.02 } : {}}
              whileTap={canMix ? { scale: 0.98 } : {}}
            >
              {mixing ? 'Mixing...' : canMix ? 'Mix & Master' : 'Need Vocals'}
            </motion.button>
          </div>
        </div>

        {aiSuggestions && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-4xl p-4 bg-purple-500/10 rounded-lg border border-purple-500/30"
          >
            <p className="text-xs text-purple-400 font-montserrat font-semibold mb-1">
              🤖 AI Mix Engineer (Tone)
            </p>
            <p className="text-sm text-studio-white/80 font-poppins">
              {aiSuggestions.reasoning}
            </p>
          </motion.div>
        )}

        {/* V21: Show only processed preview (mixed_mastered.wav) */}
        {sessionData.mixedFile && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-4xl p-6 bg-studio-gray/30 rounded-lg border border-studio-white/10"
          >
            <p className="text-sm text-studio-white/80 mb-3 font-montserrat">✓ Mix & Master Ready</p>
            <audio controls src={sessionData.mixedFile} className="w-full mb-3" />
            <WavesurferPlayer url={sessionData.mixedFile} color="#A855F7" height={120} />
          </motion.div>
        )}
        
        {/* Keep legacy mixFile/masterFile for backward compatibility, but prioritize mixedFile */}
        {!sessionData.mixedFile && sessionData.mixFile && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-4xl p-6 bg-studio-gray/30 rounded-lg border border-studio-white/10"
          >
            <p className="text-sm text-studio-white/80 mb-3 font-montserrat">✓ Mix Ready</p>
            <WavesurferPlayer url={sessionData.mixFile} color="#A855F7" height={120} />
          </motion.div>
        )}
        
        {!sessionData.mixedFile && sessionData.masterFile && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-4xl p-6 bg-studio-gray/30 rounded-lg border border-studio-white/10"
          >
            <p className="text-sm text-studio-white/80 mb-3 font-montserrat">✓ Master Ready</p>
            <WavesurferPlayer url={sessionData.masterFile} color="#A855F7" height={120} />
          </motion.div>
        )}
        </div>
      </div>
    </StageWrapper>
  );
}

function Slider({ label, value, onChange, min, max, step, disabled = false }) {
  return (
    <div className={disabled ? 'opacity-50' : ''}>
      <div className="flex justify-between mb-2">
        <label className={`text-sm font-poppins ${disabled ? 'text-studio-white/40' : 'text-studio-white/80'}`}>
          {label}
        </label>
        <span className={`text-sm font-mono ${disabled ? 'text-studio-white/30' : 'text-studio-white/60'}`}>
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
        disabled={disabled}
        className={`w-full h-2 bg-studio-gray rounded-lg appearance-none
                 [&::-webkit-slider-thumb]:appearance-none
                 [&::-webkit-slider-thumb]:w-4
                 [&::-webkit-slider-thumb]:h-4
                 [&::-webkit-slider-thumb]:rounded-full
                 [&::-webkit-slider-thumb]:bg-studio-red
                 ${disabled 
                   ? 'cursor-not-allowed opacity-50 [&::-webkit-slider-thumb]:bg-studio-gray [&::-webkit-slider-thumb]:cursor-not-allowed' 
                   : 'cursor-pointer [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:hover:bg-studio-red/80'
                 }`}
      />
    </div>
  );
}
