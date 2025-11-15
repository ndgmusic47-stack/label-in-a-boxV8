# MixStage Investigation Report
**Date:** Investigation Complete  
**Scope:** ALL components involved in MixStage functionality (Frontend + Backend + File Flow)

---

## 1. FILE MAP

### Frontend Files
- `frontend/src/components/stages/MixStage.jsx` - Main mix stage component
- `frontend/src/components/WavesurferPlayer.jsx` - Audio waveform player component
- `frontend/src/components/stages/StageWrapper.jsx` - Stage container wrapper
- `frontend/src/utils/api.js` - API utility functions (processMix, mixAudio, uploadRecording)
- `frontend/src/App.jsx` - Main app component (renders MixStage, manages sessionData)
- `frontend/src/components/stages/UploadStage.jsx` - Upload stage (sets vocalFile)
- `frontend/src/components/stages/ReleaseStage.jsx` - Release stage (uses mixedFile)

### Backend Files
- `main.py` - Main FastAPI application
  - Route: `POST /api/mix/process` (lines 1271-1540)
  - Route: `POST /api/mix/run` (lines 1113-1265) - LEGACY
  - Route: `POST /api/recordings/upload` (lines 1002-1107)
- `mix_engineer.py` - AI mix engineer helper (NOT USED in current implementation)
- `project_memory.py` - Project memory system (stores mix assets)

---

## 2. CODE EVIDENCE

### 2.1 MixStage.jsx

#### Imports
```javascript
import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { api } from '../../utils/api';
import StageWrapper from './StageWrapper';
import WavesurferPlayer from '../WavesurferPlayer';
```

#### State Variables
- `aiMixEnabled` (boolean, default: true)
- `aiMasterEnabled` (boolean, default: true)
- `mixStrength` (number, default: 0.7)
- `masterStrength` (number, default: 0.8)
- `selectedPreset` (string, default: 'clean') - Options: 'warm', 'clean', 'bright'
- `eq` (object: {low, mid, high}, default: {0, 0, 0})
- `comp` (number, default: 0.5)
- `reverb` (number, default: 0.3)
- `limiter` (number, default: 0.8)
- `mixing` (boolean, default: false)
- `error` (string|null, default: null)
- `uploadedFile` (File|null, default: null)
- `audioUrl` (string|null, default: null)

#### Functions
1. **getAudioFile()** (lines 29-37)
   - Returns: File object OR string URL OR null
   - Priority: uploadedFile (File) > sessionData.vocalFile (string) > null

2. **canMix** (line 40)
   - Computed: `!!getAudioFile()`
   - Determines if mix button is enabled

3. **useEffect for audioUrl** (lines 43-55)
   - Watches: `uploadedFile`, `sessionData.vocalFile`
   - Creates object URL for File, or uses string URL directly
   - Cleans up object URLs on unmount

4. **handleFileSelect()** (lines 58-74)
   - Validates: .wav, .mp3 extensions
   - Sets: `uploadedFile`, clears `error`
   - Voice feedback on invalid file

5. **handleMixAndMaster()** (lines 76-143)
   - Validates file exists
   - Builds `validatedParams` object with all DSP parameters
   - Calls: `api.processMix(sessionId, file, validatedParams)`
   - On success: Updates `sessionData.mixedFile` and `sessionData.mixCompleted`
   - Calls `completeStage('mix')` if provided
   - Error handling with voice feedback

#### Components Used
- `<StageWrapper>` - Wraps entire stage
- `<WavesurferPlayer>` - Two instances:
  - Preview: Shows `audioUrl` (uploadedFile or vocalFile) when `canMix && audioUrl`
  - Final: Shows `sessionData.mixedFile` when mix is complete
- `<Slider>` - Internal component (lines 386-414) for EQ/FX controls

#### API Calls
- `api.processMix(sessionId, file, validatedParams)` - Line 117
  - File can be File object or string URL
  - Parameters include: ai_mix, ai_master, mix_strength, master_strength, preset, eq_low, eq_mid, eq_high, compression, reverb, limiter

#### State Updates
- `updateSessionData({ mixedFile: result.file_url, mixCompleted: true })` - Lines 121-124

---

### 2.2 api.js

#### processMix Function (lines 224-259)
```javascript
processMix: async (sessionId, file, params) => {
  const formData = new FormData();
  
  // Handle file - can be File object or URL string
  if (file instanceof File) {
    formData.append('file', file);
  } else if (typeof file === 'string') {
    formData.append('file_url', file);
  } else {
    throw new Error('Invalid file provided');
  }
  
  formData.append('session_id', sessionId);
  formData.append('ai_mix', params.ai_mix || false);
  formData.append('ai_master', params.ai_master || false);
  formData.append('mix_strength', params.mix_strength || 0.7);
  formData.append('master_strength', params.master_strength || 0.8);
  formData.append('preset', params.preset || 'clean');
  formData.append('eq_low', params.eq_low !== undefined ? params.eq_low : 0.0);
  formData.append('eq_mid', params.eq_mid !== undefined ? params.eq_mid : 0.0);
  formData.append('eq_high', params.eq_high !== undefined ? params.eq_high : 0.0);
  formData.append('compression', params.compression !== undefined ? params.compression : 0.5);
  formData.append('reverb', params.reverb !== undefined ? params.reverb : 0.3);
  formData.append('limiter', params.limiter !== undefined ? params.limiter : 0.8);

  const response = await fetch(`${API_BASE}/mix/process`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse(response);
}
```

#### mixAudio Function (LEGACY, lines 208-221)
```javascript
mixAudio: async (sessionId, params) => {
  const response = await fetch(`${API_BASE}/mix/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      vocal_gain: params.vocal_gain || params.vocalGain || 1.0,
      beat_gain: params.beat_gain || params.beatGain || 0.8,
      hpf_hz: params.hpf_hz || params.hpfHz || 80,
      deess_amount: params.deess_amount || params.deessAmount || 0.3,
    }),
  });
  return handleResponse(response);
}
```
**STATUS:** Defined but NOT USED in MixStage.jsx

#### uploadRecording Function (lines 196-206)
```javascript
uploadRecording: async (file, sessionId = null) => {
  const formData = new FormData();
  formData.append('file', file);
  if (sessionId) formData.append('session_id', sessionId);

  const response = await fetch(`${API_BASE}/recordings/upload`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse(response);
}
```

#### syncProject Function (lines 503-560)
- Syncs project assets from backend
- Maps `project.assets.mix.url` → `updates.mixFile`
- Maps `project.assets.stems[0].url` → `updates.vocalFile`

---

### 2.3 WavesurferPlayer.jsx

#### Props
- `url` (string) - Audio file URL
- `height` (number, default: 80) - Waveform height
- `color` (string, default: '#EF4444') - Waveform color
- `onReady` (function, optional) - Callback when ready

#### State
- `isPlaying` (boolean)
- `loading` (boolean)
- `error` (string|null)
- `currentTime` (number)
- `duration` (number)

#### useEffect (lines 13-81)
- Destroys existing WaveSurfer instance before creating new one (line 17-24)
- Creates new WaveSurfer instance when URL changes
- Loads URL: `wavesurfer.load(url)` (line 68)
- Cleanup: Destroys instance on unmount or URL change (lines 71-80)

#### Lifecycle
- **Creation:** When `url` prop changes and `containerRef.current` exists
- **Destruction:** On unmount, URL change, or before creating new instance
- **Error Handling:** Sets error state on WaveSurfer error event

#### Usage in MixStage
1. **Preview Player** (lines 176-180)
   - URL: `audioUrl` (from uploadedFile or sessionData.vocalFile)
   - Color: `#10B981` (green)
   - Height: 80

2. **Final Player** (line 171)
   - URL: `sessionData.mixedFile`
   - Color: `#A855F7` (purple)
   - Height: 120

---

### 2.4 main.py - /api/mix/process Route

#### Route Definition (lines 1271-1289)
```python
@api.post("/mix/process")
async def mix_process(
    file: Optional[UploadFile] = File(None),
    file_url: Optional[str] = Form(None),
    session_id: str = Form(...),
    ai_mix: bool = Form(True),
    ai_master: bool = Form(True),
    mix_strength: float = Form(0.7),
    master_strength: float = Form(0.8),
    preset: str = Form("clean"),
    eq_low: float = Form(0.0),
    eq_mid: float = Form(0.0),
    eq_high: float = Form(0.0),
    compression: float = Form(0.5),
    reverb: float = Form(0.3),
    limiter: float = Form(0.8)
):
```

#### File Input Handling (lines 1300-1350)
1. **From UploadFile:**
   - Saves to: `mix_dir / f"temp_input_{uuid}.{suffix}"`
   - Validates: 50MB limit, .wav/.mp3/.aiff extensions

2. **From file_url:**
   - Handles relative paths: `/media/session/stems/file.wav` → converts to absolute path
   - Handles absolute URLs: Fetches via `requests.get()`
   - Saves to temp file in mix_dir

#### Audio Validation (lines 1355-1369)
- Uses `AudioSegment.from_file()` to validate
- Checks duration > 0
- Cleans up invalid files

#### DSP Pipeline (lines 1373-1480)
1. **Parameter Clamping:**
   - EQ: -6.0 to +6.0 dB
   - Compression/Reverb/Limiter: 0.0 to 1.0

2. **Preset Overrides** (lines 1382-1402):
   - **warm:** eq_low=2.0, eq_mid=-1.0, eq_high=1.0, reverb=0.3, compression=0.6, limiter=0.7
   - **clean:** eq_low=0.0, eq_mid=-2.0, eq_high=0.0, reverb=0.0, compression=0.3, limiter=0.0
   - **bright:** eq_low=0.0, eq_mid=-1.0, eq_high=3.0, reverb=0.0, compression=0.6, limiter=0.5

3. **FFmpeg Filter Chain** (lines 1404-1447):
   - EQ: `equalizer=f=100:t=lowshelf:g={eq_low_gain}` (low)
   - EQ: `equalizer=f=1500:t=peak:g={eq_mid_gain}:width=2` (mid)
   - EQ: `equalizer=f=10000:t=highshelf:g={eq_high_gain}` (high)
   - Compression: `compand=attacks=0.01:decays=0.2:points=-90/-90|-20/-20|-10/-{mix_strength_db}|0/0`
   - Reverb: `aecho=0.8:0.88:{delay_ms/1000.0}:{decay}`
   - Limiter: `alimiter=limit={limit}:level=1`
   - AI Master (if enabled): `loudnorm=I={target_lufs}:TP=-1:LRA=7`, `stereowiden`, `alimiter`

4. **FFmpeg Execution** (lines 1449-1480):
   - Command: `ffmpeg -i {input} -af {filter_chain} -ar 44100 -ac 2 -y {output}`
   - Timeout: 120 seconds
   - Fallback: Copies input to output if FFmpeg fails

#### Output (lines 1296-1297)
- File: `mix_dir / "mixed_mastered.wav"`
- URL: `f"/media/{session_id}/mix/mixed_mastered.wav"`

#### Project Memory Update (lines 1489-1504)
```python
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
memory.update("mixCompleted", True)
```

#### Response (lines 1522-1528)
```python
return success_response(
    data={
        "file_url": output_url,
        "ok": True
    },
    message="Mix and master completed successfully"
)
```

---

### 2.5 main.py - /api/mix/run Route (LEGACY)

#### Route Definition (lines 1113-1114)
```python
@api.post("/mix/run")
async def mix_run(request: MixRequest):
```

#### Request Model (lines 143-148)
```python
class MixRequest(BaseModel):
    session_id: str
    vocal_gain: float = Field(default=1.0, ge=0.0, le=2.0)
    beat_gain: float = Field(default=0.8, ge=0.0, le=2.0)
    hpf_hz: int = Field(default=80, ge=20, le=200)
    deess_amount: float = Field(default=0.3, ge=0.0, le=1.0)
```

#### Functionality
- Loads stems from `session_path / "stems"`
- Loads beat from `session_path / "beat.mp3"` (optional)
- Applies: HPF, compression, de-ess, gain
- Mixes vocals with beat (or vocals-only)
- Outputs: `mix.wav` (with beat) or `mix/vocals_only_mix.mp3` (vocals-only)
- Creates `master.wav` via normalize()

#### Project Memory Update (lines 1234-1237)
```python
memory.add_asset("mix", mix_url_path, {})
memory.add_asset("master", f"/media/{request.session_id}/master.wav", {})
memory.advance_stage("mix", "release")
```

#### Response (lines 1251-1260)
```python
return success_response(
    data={
        "mix_url": mix_url_path,
        "master_url": f"/media/{request.session_id}/master.wav",
        "mastering": mastering_method,
        "stems_mixed": len(stem_files),
        "mix_type": mix_type
    },
    message=f"Mix completed ({mix_type}) with {mastering_method} mastering"
)
```

**STATUS:** LEGACY - Not called by MixStage.jsx, but endpoint still exists

---

### 2.6 main.py - /api/recordings/upload Route

#### Route Definition (lines 1002-1003)
```python
@api.post("/recordings/upload")
async def upload_recording(file: UploadFile = File(...), session_id: Optional[str] = Form(None)):
```

#### Validation (lines 1011-1075)
- Filename required
- Extension: .wav, .mp3, .aiff
- Size: 50MB limit
- Non-zero length
- Audio validation via `AudioSegment.from_file()`

#### File Storage (lines 1049-1051)
- Saves to: `session_path / "stems" / file.filename`
- URL: `f"/media/{session_id}/stems/{file.filename}"`

#### Project Memory Update (lines 1078-1085)
```python
memory.add_asset(
    asset_type="stems",
    file_url=final_url,
    metadata={"filename": file.filename, "size": len(content)}
)
memory.advance_stage("upload", "mix")
```

#### Response (lines 1089-1100)
```python
return success_response(
    data={
        "session_id": session_id,
        "file_url": final_url,
        "uploaded": final_url,
        "vocal_url": final_url,
        "filename": file.filename,
        "path": str(file_path)
    },
    message=f"Uploaded {file.filename} successfully"
)
```

---

### 2.7 App.jsx

#### sessionData State (lines 33-41)
```javascript
const [sessionData, setSessionData] = useState({
  beatFile: null,
  lyricsData: null,
  vocalFile: null,
  masterFile: null,
  genre: 'hip hop',
  mood: 'energetic',
  trackTitle: 'My Track',
});
```
**NOTE:** `mixedFile` is NOT in initial state, added dynamically via `updateSessionData`

#### updateSessionData Function (lines 88-90)
```javascript
const updateSessionData = (data) => {
  setSessionData((prev) => ({ ...prev, ...data }));
};
```

#### MixStage Rendering (lines 135-136)
```javascript
case 'mix':
  return <MixStage {...commonProps} />;
```

#### completeCurrentStage Function (lines 63-86)
- Marks stage complete locally
- Calls `api.syncProject()` to sync with backend
- Advances to next stage

---

### 2.8 project_memory.py

#### Mix Asset Storage (lines 110-124)
```python
def add_asset(self, asset_type: str, file_url: str, metadata: Optional[Dict] = None):
    if asset_type in ["vocals", "stems", "clips"]:
        self.project_data["assets"][asset_type].append({
            "url": file_url,
            "added_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
    else:
        self.project_data["assets"][asset_type] = {
            "url": file_url,
            "added_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
    self.save()
```

#### Mix State (lines 85-90)
```python
"mix": {
    "vocal_level": 0,
    "reverb_amount": 0.3,
    "eq_preset": "neutral",
    "bass_boost": False
}
```
**NOTE:** This mix state is NOT used by /api/mix/process

---

## 3. API MAPPING TABLE

| Endpoint | Method | Called From | Purpose | Status |
|----------|--------|-------------|---------|--------|
| `/api/mix/process` | POST | `api.processMix()` (MixStage.jsx:117) | Single-file AI mix & master with DSP | **ACTIVE** |
| `/api/mix/run` | POST | `api.mixAudio()` (api.js:208) | Legacy beat+vocal mixing | **LEGACY** (not used) |
| `/api/recordings/upload` | POST | `api.uploadRecording()` (UploadStage.jsx:76) | Upload vocal recording | **ACTIVE** |
| `/api/projects/{id}` | GET | `api.getProject()` (App.jsx:52) | Get project data | **ACTIVE** |
| `/api/projects/sync` | N/A | `api.syncProject()` (App.jsx:71) | Sync project assets | **ACTIVE** |

---

## 4. STATE FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│ UPLOAD STAGE                                                │
│ - User uploads file                                        │
│ - api.uploadRecording(file, sessionId)                      │
│ - Backend saves to: /media/{session_id}/stems/{filename}   │
│ - Backend returns: { file_url: "/media/.../stems/..." }    │
│ - updateSessionData({ vocalFile: result.file_url })        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ MIX STAGE - File Selection                                  │
│ - User clicks upload button OR                             │
│ - sessionData.vocalFile already exists                      │
│ - getAudioFile() returns:                                  │
│   • uploadedFile (File) OR                                 │
│   • sessionData.vocalFile (string URL) OR                  │
│   • null                                                    │
│ - audioUrl set via useEffect:                              │
│   • File → URL.createObjectURL(file)                       │
│   • string → sessionData.vocalFile                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ MIX STAGE - Mix & Master                                    │
│ - User clicks "Mix & Master" button                        │
│ - handleMixAndMaster() called                             │
│ - Validates file exists                                    │
│ - Builds validatedParams object                            │
│ - api.processMix(sessionId, file, validatedParams)         │
│   • FormData: file OR file_url                             │
│   • FormData: session_id, ai_mix, ai_master, ...          │
│   • POST /api/mix/process                                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ BACKEND - /api/mix/process                                  │
│ - Receives FormData                                        │
│ - Handles file (upload OR file_url fetch)                  │
│ - Validates audio                                          │
│ - Applies DSP chain (FFmpeg)                               │
│ - Saves to: /media/{session_id}/mix/mixed_mastered.wav    │
│ - Updates project memory:                                  │
│   • memory.add_asset("mix", output_url, metadata)          │
│   • memory.update("mixCompleted", True)                    │
│ - Returns: { file_url: output_url, ok: true }              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ MIX STAGE - Success Handler                                 │
│ - result.file_url received                                 │
│ - updateSessionData({                                       │
│     mixedFile: result.file_url,                            │
│     mixCompleted: true                                      │
│   })                                                        │
│ - completeStage('mix') called                              │
│ - WavesurferPlayer shows sessionData.mixedFile             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ RELEASE STAGE                                               │
│ - Reads sessionData.mixedFile                              │
│ - Uses for release pack creation                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. WAVESURFER EVIDENCE

### Creation Points
1. **Preview Player** (MixStage.jsx:176-180)
   - Created when: `canMix && audioUrl` is true
   - URL: `audioUrl` (from uploadedFile or sessionData.vocalFile)
   - Destroyed when: URL changes or component unmounts

2. **Final Player** (MixStage.jsx:171)
   - Created when: `sessionData.mixedFile` exists
   - URL: `sessionData.mixedFile`
   - Destroyed when: URL changes or component unmounts

### Destruction Points
1. **Before New Instance** (WavesurferPlayer.jsx:17-24)
   - Destroys existing instance before creating new one
   - Prevents memory leaks

2. **On URL Change** (WavesurferPlayer.jsx:71-80)
   - Cleanup function in useEffect
   - Destroys instance when URL prop changes

3. **On Unmount** (WavesurferPlayer.jsx:71-80)
   - Same cleanup function handles unmount

### URL Flow
1. **Upload Stage → Mix Stage:**
   - `sessionData.vocalFile` set → `audioUrl` set → Preview player shows

2. **Mix Complete:**
   - `sessionData.mixedFile` set → Final player shows

3. **File Upload in Mix Stage:**
   - `uploadedFile` set → `audioUrl` created via `URL.createObjectURL()` → Preview player shows

### Potential Crash Points
1. **Invalid URL:**
   - If `sessionData.mixedFile` is set but file doesn't exist → WaveSurfer error event → Error state shown

2. **URL Change Race Condition:**
   - If URL changes rapidly, multiple instances might be created before cleanup

3. **Object URL Not Revoked:**
   - If `uploadedFile` changes, old object URL should be revoked (handled in useEffect cleanup)

---

## 6. CONTRADICTION DETECTION

### 6.1 Parameter Naming Inconsistencies

| Frontend | Backend | Status |
|----------|---------|--------|
| `eq.low` | `eq_low` | ✅ Consistent (FormData) |
| `eq.mid` | `eq_mid` | ✅ Consistent (FormData) |
| `eq.high` | `eq_high` | ✅ Consistent (FormData) |
| `comp` | `compression` | ✅ Consistent (FormData) |
| `reverb` | `reverb` | ✅ Consistent (FormData) |
| `limiter` | `limiter` | ✅ Consistent (FormData) |
| `aiMixEnabled` | `ai_mix` | ✅ Consistent (FormData) |
| `aiMasterEnabled` | `ai_master` | ✅ Consistent (FormData) |
| `mixStrength` | `mix_strength` | ✅ Consistent (FormData) |
| `masterStrength` | `master_strength` | ✅ Consistent (FormData) |
| `selectedPreset` | `preset` | ✅ Consistent (FormData) |

### 6.2 FormData Field Names

**Frontend (api.js:224-259):**
- `file` (if File object)
- `file_url` (if string)
- `session_id`
- `ai_mix`
- `ai_master`
- `mix_strength`
- `master_strength`
- `preset`
- `eq_low`
- `eq_mid`
- `eq_high`
- `compression`
- `reverb`
- `limiter`

**Backend (main.py:1271-1289):**
- `file` (Optional[UploadFile])
- `file_url` (Optional[str])
- `session_id` (str)
- `ai_mix` (bool)
- `ai_master` (bool)
- `mix_strength` (float)
- `master_strength` (float)
- `preset` (str)
- `eq_low` (float)
- `eq_mid` (float)
- `eq_high` (float)
- `compression` (float)
- `reverb` (float)
- `limiter` (float)

**STATUS:** ✅ All field names match

### 6.3 Unused Variables

1. **mix_engineer.py**
   - Entire file is NOT imported or used in main.py
   - Contains `AIMixEngineer` class with `analyze_track()`, `suggest_mix_parameters()`
   - **STATUS:** Unused helper file

2. **api.js:208-221 - mixAudio()**
   - Function defined but NOT called by MixStage.jsx
   - Only used by legacy code (if any)
   - **STATUS:** Legacy function, unused

3. **main.py:/api/mix/run**
   - Route exists but NOT called by MixStage.jsx
   - **STATUS:** Legacy endpoint, unused

4. **project_memory.py:85-90 - mix state**
   - `project_data["mix"]` object with `vocal_level`, `reverb_amount`, `eq_preset`, `bass_boost`
   - NOT used by `/api/mix/process`
   - **STATUS:** Unused state structure

### 6.4 Legacy Code References

1. **MixStage.jsx Comments:**
   - Line 8: "V24: AI Mix & Master controls only"
   - Line 76: "V25: Fixed handleMixAndMaster - uses api.processMix with REAL DSP parameters"
   - Line 116: "V25: Call /mix/process endpoint with REAL DSP parameters"
   - Line 120: "V25: Update sessionData with mixedFile"
   - **STATUS:** Comments reference version numbers, no legacy code

2. **api.js Comments:**
   - Line 223: "V25: Process mix and master with REAL DSP chain"
   - **STATUS:** Version comments only

3. **main.py Comments:**
   - Line 1110: "# 4. POST /mix/run - PYDUB CHAIN + OPTIONAL AUPHONIC"
   - Line 1268: "# V21: POST /mix/process - AI MIX & MASTER WITH DSP PIPELINE"
   - **STATUS:** Comments indicate legacy vs new

### 6.5 File Path Inconsistencies

1. **Upload Stage Output:**
   - Backend saves to: `/media/{session_id}/stems/{filename}`
   - Frontend receives: `file_url` from response
   - **STATUS:** ✅ Consistent

2. **Mix Stage Output:**
   - Backend saves to: `/media/{session_id}/mix/mixed_mastered.wav`
   - Frontend receives: `file_url` from response
   - **STATUS:** ✅ Consistent

3. **Legacy Mix Output:**
   - `/api/mix/run` saves to: `/media/{session_id}/mix.wav` OR `/media/{session_id}/mix/vocals_only_mix.mp3`
   - **STATUS:** Different path structure, but not used

### 6.6 SessionData Field Names

| Field | Set By | Used By | Status |
|-------|--------|---------|--------|
| `vocalFile` | UploadStage.jsx:83 | MixStage.jsx:33,50 | ✅ Consistent |
| `mixedFile` | MixStage.jsx:122 | MixStage.jsx:164,171, ReleaseStage.jsx:28,93,153 | ✅ Consistent |
| `mixCompleted` | MixStage.jsx:123 | Not checked anywhere | ⚠️ Set but unused |
| `masterFile` | Not set by MixStage | ReleaseStage.jsx:28,93 | ⚠️ Legacy field |

---

## 7. FINAL EVIDENCE SUMMARY

### Frontend Evidence
- ✅ MixStage.jsx uses `api.processMix()` (not legacy `mixAudio()`)
- ✅ FormData construction handles File objects and string URLs
- ✅ All DSP parameters passed correctly (eq_low/mid/high, compression, reverb, limiter)
- ✅ Preset selection (warm/clean/bright) wired to backend
- ✅ `sessionData.mixedFile` set on successful mix
- ✅ WavesurferPlayer used for preview and final playback
- ✅ Two WavesurferPlayer instances: preview (green) and final (purple)
- ✅ File validation: .wav, .mp3 extensions only
- ✅ Error handling with voice feedback
- ⚠️ Legacy `mixAudio()` function exists but unused
- ⚠️ `mixCompleted` flag set but never checked

### Backend Evidence
- ✅ `/api/mix/process` route exists and functional
- ✅ Handles both File upload and `file_url` string
- ✅ Validates audio files (50MB limit, extensions, pydub validation)
- ✅ DSP pipeline: EQ, Compression, Reverb, Limiter via FFmpeg
- ✅ Preset overrides: warm/clean/bright
- ✅ AI Master chain: loudnorm, stereowiden, limiter
- ✅ Output: `/media/{session_id}/mix/mixed_mastered.wav`
- ✅ Project memory updated with mix asset and metadata
- ✅ `mixCompleted` flag set in project memory
- ⚠️ Legacy `/api/mix/run` route exists but unused
- ⚠️ `mix_engineer.py` file exists but not imported/used

### File Flow Evidence
- ✅ Upload: File → FormData('file') → `/api/recordings/upload` → `/media/{session_id}/stems/{filename}`
- ✅ Mix: File/URL → FormData('file' or 'file_url') → `/api/mix/process` → `/media/{session_id}/mix/mixed_mastered.wav`
- ✅ Response: `{ file_url: "/media/...", ok: true }`
- ✅ Frontend: `updateSessionData({ mixedFile: result.file_url })`
- ✅ Wavesurfer: Receives `sessionData.mixedFile` URL

### State Flow Evidence
- ✅ `uploadedFile` (File) → `audioUrl` (object URL) → Preview player
- ✅ `sessionData.vocalFile` (string URL) → `audioUrl` → Preview player
- ✅ `sessionData.mixedFile` (string URL) → Final player
- ✅ `canMix` computed from `getAudioFile()` result
- ✅ `mixCompleted` set but not used in conditional logic

### Wavesurfer Evidence
- ✅ Created in useEffect when URL prop changes
- ✅ Destroyed before creating new instance
- ✅ Cleanup on unmount/URL change
- ✅ Error handling via error event listener
- ✅ Two instances: preview (canMix && audioUrl) and final (sessionData.mixedFile)

### Contradiction Evidence
- ✅ No parameter naming inconsistencies
- ✅ FormData field names match backend expectations
- ⚠️ Unused: `mix_engineer.py`, `api.mixAudio()`, `/api/mix/run` route
- ⚠️ Unused: `project_memory["mix"]` state object
- ⚠️ Unused: `sessionData.mixCompleted` flag (set but never checked)
- ✅ No legacy code in MixStage.jsx (only comments)
- ✅ File paths consistent between frontend and backend

---

**END OF REPORT**

