import { useState } from 'react';
import { motion } from 'framer-motion';
import { api } from '../../utils/api';
import StageWrapper from './StageWrapper';
import WavesurferPlayer from '../WavesurferPlayer';

export default function MixStage({ sessionId, sessionData, updateSessionData, voice, onClose }) {
  const [beatVolume, setBeatVolume] = useState(0.8);
  const [vocalVolume, setVocalVolume] = useState(1.0);
  const [eq, setEq] = useState({ low: 0, mid: 0, high: 0 });
  const [comp, setComp] = useState(0.5);
  const [reverb, setReverb] = useState(0.3);
  const [limiter, setLimiter] = useState(0.8);
  const [mixing, setMixing] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState(null);

  // Allow mixing with just vocals (no beat required)
  const canMix = sessionData.vocalFile || (sessionData.uploaded && sessionData.uploaded.length > 0);

  const handleAutoMix = async () => {
    if (!canMix) return;
    
    setAnalyzing(true);
    
    try {
      voice.speak('Setting optimal mix levels for you...');
      
      // Phase 2.2: Auto-mix uses smart defaults
      setBeatVolume(0.7);
      setVocalVolume(1.0);
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

  const handleMix = async () => {
    if (!canMix) {
      voice.speak('You need to upload vocals first');
      return;
    }

    setMixing(true);
    
    try {
      if (sessionData.beatFile) {
        voice.speak('Mixing your track with beat now...');
      } else {
        voice.speak('Mixing your vocals now...');
      }
      
      // Call backend mix endpoint with proper parameters
      const result = await api.mixAudio(sessionId, {
        vocal_gain: vocalVolume,
        beat_gain: beatVolume,
        hpf_hz: 80,
        deess_amount: 0.3
      });
      
      // After successful mix, sync with backend to get updated project state
      await api.syncProject(sessionId, updateSessionData);
      
      if (result.mix_type === 'vocals_only') {
        voice.speak('Your vocals-only mix is ready!');
      } else {
        voice.speak('Your master is ready! Sounds fire!');
      }
    } catch (err) {
      voice.speak('Mix failed. Check your files and try again.');
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
        {/* Source Preview */}
        {canMix && (
          <div className="w-full max-w-4xl grid grid-cols-2 gap-6 mb-4">
            <div className="p-4 bg-studio-gray/20 rounded-lg border border-studio-white/5">
              <p className="text-xs text-studio-white/60 mb-2 font-montserrat">Beat Preview</p>
              <WavesurferPlayer url={sessionData.beatFile} color="#3B82F6" height={60} />
            </div>
            <div className="p-4 bg-studio-gray/20 rounded-lg border border-studio-white/5">
              <p className="text-xs text-studio-white/60 mb-2 font-montserrat">Vocal Preview</p>
              <WavesurferPlayer url={sessionData.vocalFile} color="#10B981" height={60} />
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
              onClick={handleMix}
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

        {sessionData.mixFile && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-4xl p-6 bg-studio-gray/30 rounded-lg border border-studio-white/10"
          >
            <p className="text-sm text-studio-white/80 mb-3 font-montserrat">✓ Mix Ready</p>
            <WavesurferPlayer url={sessionData.mixFile} color="#A855F7" height={120} />
          </motion.div>
        )}
        
        {sessionData.masterFile && (
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
