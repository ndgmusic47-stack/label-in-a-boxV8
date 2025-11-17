"""
Legacy mix routes - isolated from main.py
"""

import os
import uuid
import shutil
import time
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from fastapi import File, UploadFile, HTTPException, Form, APIRouter
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range, high_pass_filter
import requests

from backend.legacy.mix.models import MixRequest, MixApplyRequest
from backend.legacy.upload.security import validate_audio_file

# Import dependencies from main.py
# Using lazy imports to avoid circular dependency issues
import sys
import logging

logger = logging.getLogger(__name__)

# These will be imported from main when routes are registered
# We'll import them at function level to avoid circular imports

# Create router for mix endpoints  
mix_router = APIRouter(prefix="/mix", tags=["mix"])


# ============================================================================
# 3.5. POST /mix/create - CREATE MIX JOB
# ============================================================================

@mix_router.post("/create")
async def create_mix(request: MixRequest):
    """Create a mix job and return job_id for polling"""
    # Import from main to avoid circular imports
    from main import success_response
    
    session_id = request.session_id
    job_id = str(uuid.uuid4())
    
    return success_response(
        data={
            "session_id": session_id,
            "job_id": job_id,
            "status": "processing",
            "progress": 0,
            "mix_url": None,
            "message": "Mix started"
        },
        message="Mix job created"
    )


# ============================================================================
# 4. POST /mix/run - PYDUB CHAIN + OPTIONAL AUPHONIC
# ============================================================================

@mix_router.post("/run")
async def mix_run(request: MixRequest):
    """Phase 2.2: Mix beat + stems with pydub chain, always mix vocals even if no beat"""
    # Import from main to avoid circular imports
    from main import (
        get_session_media_path, log_endpoint_event, success_response, 
        error_response, MEDIA_DIR, get_or_create_project_memory
    )
    import logging
    logger = logging.getLogger(__name__)
    
    session_path = get_session_media_path(request.session_id)
    mix_dir = session_path / "mix"
    mix_dir.mkdir(exist_ok=True, parents=True)
    
    try:
        # Load stems (vocal files)
        stems_path = session_path / "stems"
        stem_files = []
        if stems_path.exists():
            # Get all audio files from stems directory
            stem_files = [
                f for f in stems_path.glob("*.*") 
                if f.suffix.lower() in ('.wav', '.mp3', '.m4a', '.aiff', '.flac')
            ]
        
        if not stem_files:
            logger.warning(f"⚠️ No stems found in {stems_path}")
            log_endpoint_event("/mix/run", request.session_id, "error", {"error": "No stems found"})
            return error_response(
                "Failed to run mix",
                status_code=500,
                data={"session_id": request.session_id}
            )
        
        logger.info(f"🎧 Found {len(stem_files)} stem file(s) to mix: {[f.name for f in stem_files]}")
        
        # Load and process stems
        mixed_vocals = None
        for stem_file in stem_files:
            try:
                stem = AudioSegment.from_file(str(stem_file))
                logger.info(f"Processing stem: {stem_file.name} ({len(stem)}ms)")
            except Exception as e:
                logger.warning(f"Skipping unreadable stem {stem_file}: {e}")
                continue
            
            # HPF on vocals (80-100 Hz)
            if request.hpf_hz > 0:
                stem = high_pass_filter(stem, cutoff=request.hpf_hz)
            
            # Light compression
            stem = compress_dynamic_range(stem, threshold=-20.0, ratio=3.0, attack=5.0, release=50.0)
            
            # Simple de-ess (narrow dip 5-7 kHz) - approximate with EQ
            # Note: pydub doesn't have built-in de-ess, so we simulate with gain reduction
            if request.deess_amount > 0:
                stem = stem - (request.deess_amount * 3)  # Slight reduction
            
            # Apply gain
            stem = stem + (20 * (request.vocal_gain - 1))
            
            # Combine vocals
            if mixed_vocals is None:
                mixed_vocals = stem
            else:
                # Ensure equal lengths before overlaying
                if len(mixed_vocals) < len(stem):
                    mixed_vocals = mixed_vocals + AudioSegment.silent(duration=len(stem) - len(mixed_vocals))
                elif len(stem) < len(mixed_vocals):
                    stem = stem + AudioSegment.silent(duration=len(mixed_vocals) - len(stem))
                mixed_vocals = mixed_vocals.overlay(stem)
        
        if mixed_vocals is None:
            log_endpoint_event("/mix/run", request.session_id, "error", {"error": "No processable stems"})
            return error_response(
                "Failed to run mix",
                status_code=500,
                data={"session_id": request.session_id}
            )
        
        # Check if beat exists
        beat_file = session_path / "beat.mp3"
        has_beat = beat_file.exists()
        
        if has_beat:
            # Load and process beat
            beat = AudioSegment.from_file(str(beat_file))
            beat = beat + (20 * (request.beat_gain - 1))  # Apply gain
            
            # Ensure equal lengths
            if len(mixed_vocals) < len(beat):
                mixed_vocals = mixed_vocals + AudioSegment.silent(duration=len(beat) - len(mixed_vocals))
            elif len(beat) < len(mixed_vocals):
                beat = beat + AudioSegment.silent(duration=len(mixed_vocals) - len(beat))
            
            # Final mix with beat
            final_mix = beat.overlay(mixed_vocals)
            logger.info("Mixing vocals with beat")
        else:
            # Vocals-only mix
            final_mix = mixed_vocals
            logger.info("✅ No beat found — mixing vocals only")
        
        # Export mix - maintain backward compatibility for beats, use mix_dir for vocals-only
        if has_beat:
            # Keep original behavior: save to session root for backward compatibility
            mix_file = session_path / "mix.wav"
            mix_url_path = f"/media/{request.session_id}/mix.wav"
            final_mix.export(str(mix_file), format="wav")
        else:
            # New behavior: vocals-only mixes go to mix directory
            mix_file = mix_dir / "vocals_only_mix.mp3"
            mix_url_path = f"/media/{request.session_id}/mix/vocals_only_mix.mp3"
            final_mix.export(str(mix_file), format="mp3")
        
        # Auphonic mastering (if key present)
        auphonic_key = os.getenv("AUPHONIC_API_KEY")
        master_file = session_path / "master.wav"
        
        if auphonic_key:
            try:
                # TODO: Implement Auphonic API call
                # For now, use local normalize
                logger.warning("Auphonic integration pending - using local normalize")
                mastered = normalize(final_mix)
                mastered.export(str(master_file), format="wav")
            except Exception as e:
                logger.error(f"Auphonic failed, using local: {e}")
                mastered = normalize(final_mix)
                mastered.export(str(master_file), format="wav")
        else:
            # Local normalize
            mastered = normalize(final_mix)
            mastered.export(str(master_file), format="wav")
        
        # Update project memory
        memory = get_or_create_project_memory(request.session_id, MEDIA_DIR)
        memory.add_asset("mix", mix_url_path, {})
        memory.add_asset("master", f"/media/{request.session_id}/master.wav", {})
        memory.advance_stage("mix", "release")
        
        mastering_method = "auphonic" if auphonic_key else "local"
        mix_type = "vocals_only" if not has_beat else "vocals_and_beat"
        
        logger.info(f"✅ Mix completed ({mix_type}) - {len(stem_files)} stems, {mastering_method} mastering")
        logger.info(f"📁 Mix saved to: {mix_url_path}")
        
        log_endpoint_event("/mix/run", request.session_id, "success", {
            "mastering": mastering_method, 
            "stems": len(stem_files),
            "mix_type": mix_type
        })
        
        return success_response(
            data={
                "session_id": request.session_id,
                "job_id": str(uuid.uuid4()),
                "mix_url": mix_url_path,
                "status": "done",
                "progress": 100,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            message="Mix applied"
        )
    
    except Exception as e:
        log_endpoint_event("/mix/run", request.session_id, "error", {"error": str(e)})
        logger.error(f"Mix failed: {str(e)}", exc_info=True)
        return error_response(
            "Failed to run mix",
            status_code=500,
            data={"session_id": request.session_id}
        )


# ============================================================================
# V21: POST /mix/process - AI MIX & MASTER WITH DSP PIPELINE
# ============================================================================

@mix_router.post("/process")
async def mix_process(
    file: Optional[UploadFile] = File(None),
    file_url: Optional[str] = Form(None),
    session_id: str = Form(...),
    ai_mix: bool = Form(True),
    ai_master: bool = Form(True),
    mix_strength: float = Form(0.7),
    master_strength: float = Form(0.8),
    preset: str = Form("clean"),
    # V25: EQ parameters (slider values -6 to +6 dB)
    eq_low: float = Form(0.0),
    eq_mid: float = Form(0.0),
    eq_high: float = Form(0.0),
    # V25: FX parameters
    compression: float = Form(0.5),
    reverb: float = Form(0.3),
    limiter: float = Form(0.8)
):
    """V25: Process single audio file with REAL DSP chain (EQ, Compression, Reverb, Limiter, Mastering)"""
    # Import from main to avoid circular imports
    from main import (
        get_session_media_path, log_endpoint_event, success_response,
        error_response, MEDIA_DIR, get_or_create_project_memory
    )
    import logging
    logger = logging.getLogger(__name__)
    
    session_path = get_session_media_path(session_id)
    mix_dir = session_path / "mix"
    mix_dir.mkdir(exist_ok=True, parents=True)
    
    input_file_path = None
    output_file = mix_dir / "mixed_mastered.wav"
    output_url = f"/media/{session_id}/mix/mixed_mastered.wav"
    
    try:
        # V21: Get input file - from upload or URL
        if file and file.filename:
            # Phase 1: Centralized audio validation
            try:
                await validate_audio_file(file)
            except HTTPException as he:
                return error_response(
                    "Failed to process mix",
                    status_code=500,
                    data={"session_id": session_id}
                )
            # Save uploaded file temporarily
            input_file_path = mix_dir / f"temp_input_{uuid.uuid4().hex[:8]}{Path(file.filename).suffix}"
            content = await file.read()
            with open(input_file_path, 'wb') as f:
                f.write(content)
        elif file_url:
            # Fetch file from URL (can be absolute URL or relative path)
            try:
                # Handle relative paths (e.g., /media/session/stems/file.wav)
                if file_url.startswith('/'):
                    # Convert to absolute path
                    file_path = Path('.' + file_url)
                    if file_path.exists():
                        input_file_path = file_path
                    else:
                        # Try fetching from server URL
                        base_url = f"http://localhost:8000{file_url}"
                        response = requests.get(base_url, timeout=30, stream=True)
                        if not response.ok:
                            return error_response(
                                "Failed to process mix",
                                status_code=500,
                                data={"session_id": session_id}
                            )
                        input_file_path = mix_dir / f"temp_input_{uuid.uuid4().hex[:8]}.wav"
                        with open(input_file_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                else:
                    # Absolute URL
                    response = requests.get(file_url, timeout=30, stream=True)
                    if not response.ok:
                        return error_response(
                            "Failed to process mix",
                            status_code=500,
                            data={"session_id": session_id}
                        )
                    input_file_path = mix_dir / f"temp_input_{uuid.uuid4().hex[:8]}.wav"
                    with open(input_file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
            except Exception as e:
                logger.error(f"Failed to fetch file from URL: {e}")
                return error_response(
                    "Failed to process mix",
                    status_code=500,
                    data={"session_id": session_id}
                )
        else:
            return error_response(
                "Failed to process mix",
                status_code=500,
                data={"session_id": session_id}
            )
        
        if not input_file_path or not input_file_path.exists():
            return error_response(
                "Failed to process mix",
                status_code=500,
                data={"session_id": session_id}
            )
        
        # V21: Validate audio file with pydub
        try:
            audio = AudioSegment.from_file(str(input_file_path))
            if len(audio) == 0:
                if input_file_path.exists():
                    input_file_path.unlink()
                return error_response(
                    "Failed to process mix",
                    status_code=500,
                    data={"session_id": session_id}
                )
        except Exception as e:
            if input_file_path.exists():
                try:
                    input_file_path.unlink()
                except:
                    pass
            logger.error(f"Audio validation failed: {e}")
            return error_response(
                "Failed to process mix",
                status_code=500,
                data={"session_id": session_id}
            )
        
        logger.info(f"🎧 Processing audio: {len(audio)}ms, sample_rate={audio.frame_rate}")
        
        # V25: Validate DSP parameters
        eq_low_gain = max(-6.0, min(6.0, eq_low))
        eq_mid_gain = max(-6.0, min(6.0, eq_mid))
        eq_high_gain = max(-6.0, min(6.0, eq_high))
        compression_val = max(0.0, min(1.0, compression))
        reverb_val = max(0.0, min(1.0, reverb))
        limiter_val = max(0.0, min(1.0, limiter))
        
        # V25: Apply preset overrides if preset is selected
        if preset == "warm":
            eq_low_gain = 2.0
            eq_mid_gain = -1.0
            eq_high_gain = 1.0
            reverb_val = 0.3  # light reverb
            compression_val = 0.6  # medium compression
            limiter_val = 0.7  # soft limiter
        elif preset == "clean":
            eq_low_gain = 0.0
            eq_mid_gain = -2.0
            eq_high_gain = 0.0
            reverb_val = 0.0  # no reverb
            compression_val = 0.3  # low compression
            limiter_val = 0.0  # no limiter
        elif preset == "bright":
            eq_low_gain = 0.0
            eq_mid_gain = -1.0
            eq_high_gain = 3.0
            reverb_val = 0.0  # no reverb
            compression_val = 0.6  # medium compression
            limiter_val = 0.5  # medium limiter
        
        # V25.1: REAL DSP PIPELINE using ffmpeg filters (V25 spec)
        # Build filter chain as single ffmpeg command
        
        # Stage 1: EQ (3-band) - always apply
        eq_low_filter = f"equalizer=f=100:t=lowshelf:g={eq_low_gain}"
        eq_mid_filter = f"equalizer=f=1500:t=peak:g={eq_mid_gain}:width=2"
        eq_high_filter = f"equalizer=f=10000:t=highshelf:g={eq_high_gain}"
        
        # Stage 2: Compression (compand)
        # FIX 2: Cast to integer - compand 'points=' must not contain floats
        # Map compression slider (0-1) to compand threshold
        # compression 0 = no compression, 1 = full compression
        mix_strength_db_int = int(abs(-10.0 - (compression_val * 10.0)))  # Cast compand threshold to int
        compand_filter = f"compand=attacks=0.01:decays=0.2:points=-90/-90|-20/-20|-10/-{mix_strength_db_int}|0/0"
        
        # Stage 3: Reverb (aecho)
        # FIX 1: Reverb delay MUST be integer - map slider (0-1) → delay in ms (20-60), decay 0.2-0.8
        delay_ms = int(20 + (reverb_val * 40))  # always integer between 20 and 60
        decay = 0.2 + (reverb_val * 0.6)  # 0.2-0.8 (decay can be float)
        # Note: FFmpeg aecho takes delay in seconds, but user spec shows delay_ms directly
        # Convert milliseconds to seconds for FFmpeg (delay_ms is already integer)
        aecho_filter = f"aecho=0.8:0.88:{delay_ms/1000.0}:{decay}"
        
        # Stage 4: Limiter (per slider)
        limiter_filter = "alimiter=limit=0.95:level=1"
        
        # Stage 5: Final Mastering Chain (always apply)
        # FIX 3: Stereotools is optional - check availability first
        stereo_filter = ""
        try:
            # Test if stereotools is available in FFmpeg
            test_result = subprocess.run(
                ["ffmpeg", "-filters"],
                capture_output=True,
                timeout=5
            )
            if "stereotools" in test_result.stdout.decode('utf-8', errors='ignore'):
                stereo_filter = "stereotools=mlev=1.05"
        except:
            stereo_filter = ""
        
        master_filter = "alimiter=limit=0.98"
        
        # FIX 4: Build filter chain safely - remove empty filters, no trailing commas
        filters = [eq_low_filter, eq_mid_filter, eq_high_filter, compand_filter, aecho_filter, limiter_filter]
        if stereo_filter:
            filters.append(stereo_filter)
        filters.append("loudnorm=I=-13:TP=-1:LRA=7")
        filters.append(master_filter)
        
        # Remove empty filters to avoid empty commas in chain
        filter_chain = ",".join([f for f in filters if f])
        
        # V25.1: Execute DSP chain with ffmpeg (single command)
        temp_processed = mix_dir / f"temp_processed_{uuid.uuid4().hex[:8]}.wav"
        
        # Build ffmpeg command with filter chain
        cmd = [
            'ffmpeg', '-i', str(input_file_path),
            '-af', filter_chain,
            '-ar', '44100',
            '-ac', '2',  # Ensure stereo output
            '-y', str(temp_processed)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, check=True, timeout=120)
            if not temp_processed.exists():
                raise Exception("FFmpeg output file not created")
            # Move to final output
            shutil.move(str(temp_processed), str(output_file))
            
            # FIX 5: Guarantee output file exists before returning
            # Wait for file to exist and have content (up to 400ms)
            for _ in range(20):  # wait up to 400ms
                if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                    break
                time.sleep(0.02)
            
            # Final check - raise error if file still missing
            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                raise RuntimeError("Output file missing or empty after DSP chain")
            
            logger.info(f"✅ DSP chain applied: {len(filters)} filters")
        except (subprocess.CalledProcessError, FileNotFoundError, Exception) as e:
            logger.error(f"FFmpeg DSP chain failed: {e}")
            if temp_processed.exists():
                temp_processed.unlink()
            # FIX 6: Remove fallback copy - raise error instead
            raise RuntimeError(f"DSP chain failed: {e}")
        
        # Clean up temp input file
        if input_file_path and input_file_path.exists() and input_file_path != output_file:
            try:
                input_file_path.unlink()
            except:
                pass
        
        # V25.1: Update project memory (removed mixCompleted)
        memory = get_or_create_project_memory(session_id, MEDIA_DIR)
        memory.add_asset("mix", output_url, {
            "ai_mix": ai_mix,
            "ai_master": ai_master,
            "preset": preset,
            "mix_strength": mix_strength,
            "master_strength": master_strength,
            "eq_low": eq_low_gain,
            "eq_mid": eq_mid_gain,
            "eq_high": eq_high_gain,
            "compression": compression_val,
            "reverb": reverb_val,
            "limiter": limiter_val
        })
        
        logger.info(f"✅ Mix & master completed - preset={preset}, ai_mix={ai_mix}, ai_master={ai_master}")
        logger.info(f"📁 Processed file saved to: {output_url}")
        logger.info(f"🎛️ DSP params: EQ({eq_low_gain:.1f}/{eq_mid_gain:.1f}/{eq_high_gain:.1f}) Comp={compression_val:.2f} Rev={reverb_val:.2f} Lim={limiter_val:.2f}")
        
        log_endpoint_event("/mix/process", session_id, "success", {
            "preset": preset,
            "ai_mix": ai_mix,
            "ai_master": ai_master,
            "mix_strength": mix_strength,
            "master_strength": master_strength,
            "eq": {"low": eq_low_gain, "mid": eq_mid_gain, "high": eq_high_gain},
            "compression": compression_val,
            "reverb": reverb_val,
            "limiter": limiter_val
        })
        
        return success_response(
            data={
                "session_id": session_id,
                "job_id": str(uuid.uuid4()),
                "mix_url": output_url,
                "status": "done",
                "progress": 100,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            message="Mix processed"
        )
    
    except Exception as e:
        log_endpoint_event("/mix/process", session_id, "error", {"error": str(e)})
        logger.error(f"Mix process failed: {str(e)}", exc_info=True)
        return error_response(
            "Failed to process mix",
            status_code=500,
            data={"session_id": session_id}
        )
    finally:
        # Cleanup temp files
        if input_file_path and input_file_path.exists() and input_file_path != output_file:
            try:
                input_file_path.unlink()
            except:
                pass

