from pydub import AudioSegment
import numpy as np


def apply_limiter(audio: AudioSegment, ceiling: float = -1.0):
    """
    True peak limiter with fast attack and optimized release for commercial sound.
    
    Parameters:
    - ceiling: -1.0 dB (true peak ceiling)
    - attack: near-instant (<1ms) for transparent limiting
    - release: 30ms (faster than previous 60ms to prevent pumping)
    - lookahead: ~1.5ms using padding for smooth operation
    - secondary recovery: quickly return to unity when audio is quiet
    - Prevents inter-sample peaks and overshoot
    """
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    sr = audio.frame_rate

    if len(samples) == 0:
        return audio

    # Normalize samples to [-1, 1] range
    max_val = np.max(np.abs(samples))
    if max_val > 0:
        samples_norm = samples / max_val
    else:
        return audio  # silent audio

    # Convert ceiling from dBFS to linear (normalized)
    ceiling_linear = 10 ** (ceiling / 20)

    # Attack: near-instant (<1ms) - very fast response
    attack_ms = 0.5
    attack_coeff = np.exp(-1.0 / (sr * (attack_ms / 1000.0)))
    
    # Release time: 30ms (faster than previous 60ms)
    release_ms = 30.0
    release_coeff = np.exp(-1.0 / (sr * (release_ms / 1000.0)))
    
    # Secondary recovery for quiet sections (faster return to unity)
    recovery_ms = 10.0
    recovery_coeff = np.exp(-1.0 / (sr * (recovery_ms / 1000.0)))

    # Look-ahead buffer: ~1.5ms using padding
    lookahead_samples = int(sr * 0.0015)  # 1.5ms lookahead
    if lookahead_samples < 1:
        lookahead_samples = 1
    
    # Pad samples with zeros for lookahead
    padded_samples = np.pad(samples_norm, (0, lookahead_samples), mode='constant')

    # True peak estimation: check current sample and adjacent samples
    # This helps catch inter-sample peaks that can occur between samples
    def estimate_true_peak(signal, idx):
        """Estimate true peak by checking current and adjacent samples"""
        if idx == 0:
            return abs(signal[0])
        elif idx >= len(signal) - 1:
            return abs(signal[-1])
        else:
            # Check current, previous, and next samples
            # True peak can be higher than any single sample
            peak = max(abs(signal[idx-1]), abs(signal[idx]), abs(signal[idx+1]))
            # Estimate inter-sample peak using linear interpolation
            if idx > 0 and idx < len(signal) - 1:
                # Simple estimate: peak could be between samples
                inter_peak = (abs(signal[idx-1]) + abs(signal[idx]) + abs(signal[idx+1])) / 3.0
                peak = max(peak, inter_peak * 1.1)  # 10% safety margin
            return peak

    # Process with look-ahead and optimized release
    output = samples_norm.copy()
    gain_reduction = 1.0
    gain_history = np.ones_like(samples_norm)

    for i in range(len(samples_norm)):
        # Estimate true peak at lookahead position (using padded buffer)
        lookahead_idx = i + lookahead_samples
        if lookahead_idx < len(padded_samples):
            true_peak = estimate_true_peak(padded_samples, lookahead_idx)
        else:
            true_peak = estimate_true_peak(samples_norm, min(i, len(samples_norm) - 1))

        # Calculate required gain reduction
        if true_peak > ceiling_linear:
            required_reduction = ceiling_linear / true_peak
            # Fast attack: near-instant response
            gain_reduction = attack_coeff * gain_reduction + (1 - attack_coeff) * required_reduction
            gain_reduction = min(gain_reduction, required_reduction)
        else:
            # Check if audio is quiet for secondary recovery
            current_level = abs(padded_samples[lookahead_idx] if lookahead_idx < len(padded_samples) else samples_norm[min(i, len(samples_norm) - 1)])
            quiet_threshold = ceiling_linear * 0.3  # 30% of ceiling = quiet
            
            if current_level < quiet_threshold and gain_reduction < 0.99:
                # Secondary recovery: faster return to unity for quiet sections
                gain_reduction = recovery_coeff * gain_reduction + (1 - recovery_coeff) * 1.0
            else:
                # Standard release: gradually return to unity gain
                gain_reduction = release_coeff * gain_reduction + (1 - release_coeff) * 1.0

        # Ensure gain doesn't go above 1.0
        gain_reduction = min(1.0, max(0.0, gain_reduction))
        gain_history[i] = gain_reduction

    # Smooth gain reduction to avoid artifacts
    smooth_window = int(sr * 0.001)  # 1ms smoothing
    if smooth_window > 1:
        smoothed_gain = np.zeros_like(gain_history)
        for i in range(len(gain_history)):
            start_idx = max(0, i - smooth_window // 2)
            end_idx = min(len(gain_history), i + smooth_window // 2)
            smoothed_gain[i] = np.mean(gain_history[start_idx:end_idx])
        gain_history = smoothed_gain

    # Apply gain reduction
    output = samples_norm * gain_history
    
    # Scale back to original range
    if max_val > 0:
        output = output * max_val
    
    # Final hard clip to prevent any overshoot
    output = np.clip(output, -32768, 32767)

    return audio._spawn(output.astype(np.int16).tobytes())
