# 🔍 LABEL-IN-A-BOX: FULL TECHNICAL ARCHITECTURE REVIEW
## Current State After V17 → V23.1 Implementation

**Review Date:** Current State  
**Purpose:** Complete technical documentation reflecting all module updates  
**Status:** Production System with Documented Issues

---

## SECTION 1 — CURRENT TECH STACK (FE + BE)

### Frontend Technologies

**Core Framework:**
- React 18.2.0
- Vite 5.0.8 (dev server on port 5000, production build to `/dist`)
- JavaScript (ES6+ modules)

**UI Libraries:**
- Framer Motion 11.0.0 (animations)
- Tailwind CSS 3.4.0 (styling)
- PostCSS + Autoprefixer (CSS processing)
- Wavesurfer.js 7.7.3 (audio waveform visualization)

**State Management:**
- React Hooks (useState, useEffect, useRef)
- Local state in `App.jsx` (`sessionData`, `currentStage`, `completedStages`)
- localStorage for session persistence (`liab_session_id`)

**Build System:**
- Vite dev server with proxy (`/api` → backend port 8000)
- Production: static files served from `frontend/dist/`

---

### Backend Technologies

**Core Framework:**
- FastAPI (Python)
- Uvicorn (ASGI server, port 8000)
- Pydantic (request/response validation)

**API Structure:**
- RESTful API with `/api` prefix (via `APIRouter`)
- Standardized responses: `{ok: true/false, data: {...}, message: "..."}` or `{ok: false, error: "..."}`
- CORS enabled for all origins

**File Storage:**
- Local filesystem: `./media/{session_id}/` directory structure
- Static file serving: `/media` mount point
- Project memory: `project.json` per session

**Logging:**
- Python logging to `./logs/app.log`
- Endpoint event logging via `log_endpoint_event()`

---

### File Storage Architecture

```
media/
  {session_id}/
    project.json              # Project state, workflow, assets, metadata
    beat.mp3                  # Generated beat
    lyrics.txt                # Generated lyrics
    stems/                    # Uploaded vocal recordings
      {filename}.wav
    mix.wav                   # Mixed audio (with beat)
    mix/                      # V21: Vocals-only mixes
      vocals_only_mix.mp3
      mixed_mastered.wav      # V21: AI-processed mix
    master.wav                # Mastered audio
    cover.jpg                 # Generated cover art
    release/                   # V22: Release pack directory
      release_pack.zip
      mixed.wav
      mixed.mp3
      cover.jpg
      metadata.json
      lyrics.txt
    voices/                   # gTTS voice MP3s (SHA256 cache)
      {sha256_hash}.mp3
    videos/                   # V23: Uploaded videos
      {filename}.mp4
      {filename}_transcript.txt
    schedule.json             # Social media schedule (local JSON)
```

---

### Audio Processing Stack

**Libraries:**
- pydub (audio manipulation: normalize, compress, HPF)
- aubio (BPM detection)
- librosa (audio analysis - available but not actively used)
- soundfile (audio I/O - available but not actively used)

**Processing Pipeline:**
1. **Beat Generation:** Beatoven API → download → save to `beat.mp3`
2. **Vocal Upload:** Validate → save to `stems/{filename}`
3. **Mixing (V21):**
   - Single-file processing via `/api/mix/process`
   - AI Mix: HPF @ 30Hz, compression (ratio 2.0-5.0), EQ mid cut, presets (warm/bright/clean)
   - AI Master: Hard limiter (-1.0 dB), loudness normalization (-12 to -10 LUFS), stereo widening
4. **Legacy Mixing (`/api/mix/run`):**
   - Vocals: HPF (80-100 Hz), compression, de-ess, gain
   - Beat: Gain adjustment
   - Overlay: Vocals + beat (or vocals-only)
   - Normalize: Local (Auphonic not implemented)

**FFmpeg Integration:**
- Used for advanced DSP (EQ shelves, loudnorm, stereo widening)
- Fallback to pydub if FFmpeg unavailable

---

### Video Processing Stack

**Libraries:**
- moviepy (available but not actively used)
- FFmpeg (via subprocess for audio extraction, duration detection)

**V23 Content Module:**
- Video upload: `.mp4`, `.mov`, `.avi`, `.mkv` (100MB limit)
- Audio extraction: FFmpeg extracts audio track to `.wav`
- Transcript extraction: OpenAI Whisper API (if key available)
- Duration detection: FFmpeg metadata parsing

**Not Implemented:**
- Video editing/beat sync
- Video export
- Video analysis (visual)

---

### AI Usage Points

**OpenAI Integration:**
- **GPT-4o-mini** for:
  - Lyrics generation (`/api/songs/write`)
  - NP22-style lyrics (`generate_np22_lyrics()`)
  - Lyrics refinement (`/api/lyrics/refine`)
  - Video idea generation (`/api/content/idea`)
  - Video analysis (`/api/content/analyze`)
  - Content text generation (`/api/content/generate-text`)
- **Whisper-1** for:
  - Video transcript extraction (`/api/content/upload-video`)

**Third-Party APIs:**
- **Beatoven API:** Beat generation (with fallback to demo beat)
- **gTTS (Google Text-to-Speech):** Voice synthesis (10s debounce, SHA256 cache)
- **GetLate.dev API:** Social media scheduling (with local JSON fallback)

**Not Implemented:**
- Auphonic API (mastering - TODO in code)
- Spotify API (reference engine exists but not wired)

---

### Scheduling Integrations

**GetLate.dev API:**
- Platform: TikTok, Shorts, Reels
- Endpoint: `/api/social/posts` and `/api/content/schedule`
- Fallback: Local JSON storage (`schedule.json`)

**Local JSON Storage:**
- File: `media/{session_id}/schedule.json`
- Format: Array of post objects with `post_id`, `platform`, `caption`, `scheduled_time`, `status`

---

### Third-Party Libraries & Dependencies

**Backend (`requirements.txt`):**
- fastapi, uvicorn[standard]
- pydantic
- pydub
- moviepy
- Pillow (image generation)
- python-multipart
- requests
- openai
- librosa, soundfile
- spotipy (not actively used)
- numpy, scipy
- gtts
- python-dotenv
- aubio

**Frontend (`package.json`):**
- react, react-dom
- framer-motion
- wavesurfer.js
- @vitejs/plugin-react
- autoprefixer, postcss, tailwindcss
- vite

---

## SECTION 2 — UPDATED PRODUCT ARCHITECTURE (END-TO-END)

### BeatStage (V17)

**Component:** `frontend/src/components/stages/BeatStage.jsx`  
**Backend:** `POST /api/beats/create`, `GET /api/beats/credits`

**Flow:**
1. User inputs prompt text + mood
2. Frontend: `api.createBeat(promptText, mood, genre, sessionId)`
3. Backend: Beatoven API (or fallback demo beat)
4. Save: `media/{session_id}/beat.mp3`
5. ProjectMemory: `add_asset("beat", url, metadata)`, `advance_stage("beat", "lyrics")`
6. Frontend: `api.syncProject()` → `sessionData.beatFile` updated
7. Display: WavesurferPlayer with beat waveform
8. Completion: Manual "Use Beat" button → `api.advanceStage()` + `onClose()`

**SessionData:**
- `beatFile`: URL to beat (`/media/{session_id}/beat.mp3`)
- `beatMetadata`: `{bpm, key, duration}`
- `mood`: User-selected mood
- `genre`: User-selected genre

**ProjectMemory:**
- `assets.beat`: `{url, added_at, metadata: {bpm, mood, source, metadata}}`
- `metadata.tempo`: BPM
- `metadata.mood`: Mood
- `metadata.genre`: Genre
- `workflow.current_stage`: "lyrics"
- `workflow.completed_stages`: ["beat"]

---

### LyricsStage (V18.2)

**Component:** `frontend/src/components/stages/LyricsStage.jsx`  
**Backend:** 
- `POST /api/songs/write` (standard)
- `POST /api/lyrics/from_beat` (V17: from uploaded beat)
- `POST /api/lyrics/free` (V17: from theme)
- `POST /api/lyrics/refine` (V18: interactive refinement)

**Flow:**
1. **Mode 1 (From Beat):** Upload beat → `api.generateLyricsFromBeat(file, sessionId)` → BPM/mood detection → NP22 lyrics
2. **Mode 2 (Free):** Enter theme → `api.generateFreeLyrics(theme)` → NP22 lyrics
3. **Mode 3 (From Session Beat):** V18.2 - Auto-detect `sessionData.beatFile` → Fetch blob → `api.generateLyricsFromBeat(formData, sessionId)`
4. **Standard Mode:** Enter theme → `api.generateLyrics(genre, mood, theme, sessionId)` → OpenAI → Structured parsing → Voice preview
5. **Refinement (V18):** Instruction → `api.refineLyrics(lyricsText, instruction, bpm, history, structuredLyrics, rhythmMap)` → Refined lyrics

**SessionData:**
- `lyricsData`: Lyrics text (string) or structured object
- `bpm`: BPM from beat (if available)

**ProjectMemory:**
- `assets.lyrics`: `{url: "/media/{session_id}/lyrics.txt", added_at, metadata}`
- `workflow.current_stage`: "upload"
- `workflow.completed_stages`: ["beat", "lyrics"]

**V18.1 Features:**
- Structured parsing: `parse_lyrics_to_structured()` (detects [Hook], [Verse], [Chorus], [Bridge])
- Rhythm approximation: `estimateBarRhythm()` (bar counts per line)
- Conversation history: Last 3 interactions tracked

---

### UploadStage (V20)

**Component:** `frontend/src/components/stages/UploadStage.jsx`  
**Backend:** `POST /api/recordings/upload`

**Flow:**
1. User drags/drops or selects audio file (`.wav`, `.mp3`, `.aiff`)
2. Frontend validation: File size (50MB), extension check
3. Frontend: `api.uploadRecording(file, sessionId)`
4. Backend validation: File type, size, audio integrity (pydub)
5. Save: `media/{session_id}/stems/{filename}`
6. ProjectMemory: `add_asset("stems", url, metadata)`, `advance_stage("upload", "mix")`
7. Frontend: `api.syncProject()` → `sessionData.vocalFile` from `project.assets.stems[0].url`
8. Display: WavesurferPlayer with vocal waveform
9. Completion: V20 - Auto `completeStage("upload")` after success

**SessionData:**
- `vocalFile`: URL to vocal (`/media/{session_id}/stems/{filename}`)
- `vocalUploaded`: Boolean flag

**ProjectMemory:**
- `assets.stems`: Array of `{url, added_at, metadata: {filename, size}}`
- `workflow.current_stage`: "mix"
- `workflow.completed_stages`: ["beat", "lyrics", "upload"]

---

### MixStage (V21.1)

**Component:** `frontend/src/components/stages/MixStage.jsx`  
**Backend:** 
- `POST /api/mix/run` (legacy: beat + vocals mixing)
- `POST /api/mix/process` (V21: single-file AI mix & master)

**Flow (V21 - AI Mix & Master):**
1. User uploads file OR uses `sessionData.vocalFile`
2. Frontend: `api.processMix(sessionId, file, {ai_mix, ai_master, mix_strength, master_strength, preset})`
3. Backend: Single-file processing
   - AI Mix: HPF @ 30Hz, compression (ratio 2.0-5.0), EQ mid cut, presets (warm/bright/clean)
   - AI Master: Hard limiter (-1.0 dB), loudness normalization (-12 to -10 LUFS), stereo widening
4. Save: `media/{session_id}/mix/mixed_mastered.wav`
5. ProjectMemory: `add_asset("mix", url, metadata)`, `update("mixCompleted", True)`
6. Frontend: `sessionData.mixedFile` updated
7. Display: Audio player + WavesurferPlayer

**Flow (Legacy `/api/mix/run`):**
1. User adjusts sliders (vocal_gain, beat_gain, hpf_hz, deess_amount)
2. Frontend: `api.mixAudio(sessionId, params)`
3. Backend: Load stems + beat → HPF, compression, de-ess, gain → Overlay → Normalize
4. Save: `mix.wav` (with beat) or `mix/vocals_only_mix.mp3` (vocals-only)
5. Save: `master.wav` (normalized)
6. ProjectMemory: `add_asset("mix", url)`, `add_asset("master", url)`, `advance_stage("mix", "release")`

**SessionData:**
- `mixedFile`: URL to processed mix (`/media/{session_id}/mix/mixed_mastered.wav`)
- `mixFile`: Legacy URL to `mix.wav`
- `masterFile`: Legacy URL to `master.wav`
- `mixCompleted`: Boolean flag

**ProjectMemory:**
- `assets.mix`: `{url, added_at, metadata: {ai_mix, ai_master, preset, mix_strength, master_strength}}`
- `assets.master`: `{url, added_at, metadata}`
- `mix.mixCompleted`: `true`
- `workflow.current_stage`: "release"
- `workflow.completed_stages`: ["beat", "lyrics", "upload", "mix"]

**UI Controls:**
- Volume: Beat, Vocal (functional)
- EQ: Low, Mid, High (DISABLED - "Coming Soon")
- Effects: Compression, Reverb, Limiter (DISABLED - "Coming Soon")
- AI Processing: AI Mix toggle, Mix Strength, AI Master toggle, Master Strength, Preset (warm/clean/bright)

---

### ReleaseStage (V22)

**Component:** `frontend/src/components/stages/ReleaseStage.jsx`  
**Backend:** 
- `POST /api/release/generate-cover`
- `POST /api/release/pack`

**Flow:**
1. User inputs title, artist, genre, mood, release date, ISRC, lyrics
2. Cover Art: `api.generateCoverArt(title, artist, sessionId)` → Pillow gradient → Save `cover.jpg`
3. Release Pack: `api.createReleasePack(sessionId, mixedFile, coverFile, metadata, lyrics)`
4. Backend: Download mixed file → Export MP3 → Generate metadata.json → Create ZIP
5. Save: `media/{session_id}/release/release_pack.zip` (contains: mixed.wav, mixed.mp3, cover.jpg, metadata.json, lyrics.txt)
6. ProjectMemory: `add_asset("release_pack", url)`, `add_asset("cover_art", url)`, `advance_stage("release", "content")`
7. Frontend: `api.syncProject()` → `sessionData.releasePackUrl`, `sessionData.coverArt` updated
8. Completion: Auto `completeStage("release")` after pack creation

**SessionData:**
- `releasePackUrl`: URL to ZIP (`/media/{session_id}/release/release_pack.zip`)
- `coverArt`: URL to cover (`/media/{session_id}/cover.jpg`)
- `trackTitle`: User input
- `artistName`: User input
- `genre`: User input
- `mood`: User input
- `release_date`: User input
- `isrc`: Auto-generated or user input
- `lyricsData`: Lyrics text

**ProjectMemory:**
- `assets.release_pack`: `{url, added_at, metadata: {title, artist, isrc, release_date}}`
- `assets.cover_art`: `{url, added_at, metadata: {title, artist}}`
- `metadata.track_title`: Title
- `metadata.artist_name`: Artist
- `metadata.genre`: Genre
- `metadata.mood`: Mood
- `workflow.current_stage`: "content"
- `workflow.completed_stages`: ["beat", "lyrics", "upload", "mix", "release"]

---

### ContentStage (V23.1)

**Component:** `frontend/src/components/stages/ContentStage.jsx`  
**Backend:** `content.py` router
- `POST /api/content/idea` (Step 1: Generate video idea)
- `POST /api/content/upload-video` (Step 2: Upload video + extract transcript)
- `POST /api/content/analyze` (Step 3: Analyze video for viral score)
- `POST /api/content/generate-text` (Step 4: Generate captions & hashtags)
- `POST /api/content/schedule` (Step 5: Schedule video via GetLate)

**Flow:**
1. **Step 1:** `api.generateVideoIdea(sessionId, title, lyrics, mood, genre)` → OpenAI → `{idea, hook, script, visual}`
2. **Step 2:** Upload video → `api.uploadVideo(file, sessionId)` → FFmpeg audio extraction → Whisper transcript → Save video + transcript
3. **Step 3:** `api.analyzeVideo(transcript, title, lyrics, mood, genre)` → OpenAI → `{score, summary, improvements, suggested_hook, thumbnail_suggestion}`
4. **Step 4:** `api.generateContentText(sessionId, title, transcript, lyrics, mood, genre)` → OpenAI → `{captions, hashtags, hooks, posting_strategy, ideas}`
5. **Step 5:** `api.scheduleVideo(sessionId, videoUrl, caption, hashtags, platform, scheduleTime)` → GetLate API (or local JSON) → Schedule post
6. Completion: Auto `completeStage("content")` after scheduling

**SessionData:**
- `contentIdea`: `{idea, hook, script, visual}`
- `uploadedVideo`: URL to video (`/media/{session_id}/videos/{filename}`)
- `videoTranscript`: Transcript text
- `viralAnalysis`: `{score, summary, improvements, suggested_hook, thumbnail_suggestion}`
- `contentTextPack`: `{captions, hashtags, hooks, posting_strategy, ideas}`
- `contentScheduled`: Boolean flag

**ProjectMemory:**
- `assets.uploaded_video`: `{url, added_at, metadata: {filename, duration, fps, transcript}}`
- `contentScheduled`: `true`
- `workflow.current_stage`: "analytics"
- `workflow.completed_stages`: ["beat", "lyrics", "upload", "mix", "release", "content"]

---

### Timeline

**Component:** `frontend/src/components/Timeline.jsx`

**Structure:**
- 7 stages: Beat, Lyrics, Upload, Mix, Release, Content, Analytics
- Centered overlay: `top: 50%`, `left: 50%`, `transform: translate(-50%, -50%)`
- Z-index: 20 (above MistLayer, below stage screens)
- Visibility: `!showAnalytics && !isStageOpen`

**State:**
- `currentStage`: React state in `App.jsx` (suggested next stage)
- `completedStages`: Array in `App.jsx` (completed stage IDs)
- `activeStage`: React state in `App.jsx` (which UI is open)

**Progress:**
- Progress bar: `completedStages.length / 7`
- Stage status: `completed`, `active`, `upcoming`
- Pulse ring animation on active stage
- Goal reached modal when all 7 stages complete

---

### MistLayer

**Component:** `frontend/src/components/MistLayer.jsx`

**Visual:**
- Purple/gold gradient background (`mist.css`)
- Position animates based on `activeStage || currentStage`
- CSS variables: `--x`, `--y` control gradient center

**Position Map:**
- beat: `{x: '10%', y: '40%'}`
- lyrics: `{x: '28%', y: '40%'}`
- upload: `{x: '46%', y: '40%'}`
- mix: `{x: '64%', y: '40%'}`
- release: `{x: '82%', y: '40%'}`
- content: `{x: '90%', y: '40%'}`
- analytics: `{x: '95%', y: '40%'}`

---

### SessionData Structure

**Location:** `App.jsx` React state

```javascript
{
  beatFile: null,              // URL to beat.mp3
  lyricsData: null,             // Lyrics text or structured object
  vocalFile: null,              // URL to vocal stem
  masterFile: null,             // URL to master.wav (legacy)
  mixFile: null,                // URL to mix.wav (legacy)
  mixedFile: null,              // URL to mixed_mastered.wav (V21)
  genre: 'hip hop',
  mood: 'energetic',
  trackTitle: 'My Track',
  artistName: null,
  coverArt: null,               // URL to cover.jpg
  releasePackUrl: null,         // URL to release_pack.zip
  beatMetadata: null,           // {bpm, key, duration}
  bpm: null,                    // BPM from beat
  isrc: null,                   // ISRC code
  release_date: null,           // Release date
  // V23 ContentStage
  contentIdea: null,
  uploadedVideo: null,
  videoTranscript: null,
  viralAnalysis: null,
  contentTextPack: null,
  contentScheduled: false
}
```

---

### ProjectMemory Structure

**Location:** `media/{session_id}/project.json`

```json
{
  "session_id": "...",
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime",
  "metadata": {
    "tempo": 120,
    "key": "C",
    "mood": "energetic",
    "genre": "hip hop",
    "artist_name": "NP22",
    "track_title": "My Track"
  },
  "assets": {
    "beat": { "url": "...", "added_at": "...", "metadata": {...} },
    "lyrics": { "url": "...", "added_at": "...", "metadata": {...} },
    "vocals": [],
    "stems": [{ "url": "...", "added_at": "...", "metadata": {...} }],
    "mix": { "url": "...", "added_at": "...", "metadata": {...} },
    "master": { "url": "...", "added_at": "...", "metadata": {...} },
    "release_pack": { "url": "...", "added_at": "...", "metadata": {...} },
    "cover_art": { "url": "...", "added_at": "...", "metadata": {...} },
    "clips": [],
    "reference_track": null,
    "uploaded_video": { "url": "...", "added_at": "...", "metadata": {...} }
  },
  "workflow": {
    "current_stage": "beat",
    "completed_stages": [],
    "unlocked_stages": ["beat"]
  },
  "workflow_state": {
    "beat_done": false,
    "lyrics_done": false,
    "vocals_done": false,
    "mix_done": false,
    "release_done": false,
    "content_done": false
  },
  "mix": {
    "vocal_level": 0,
    "reverb_amount": 0.3,
    "eq_preset": "neutral",
    "bass_boost": false
  },
  "beat": {
    "tempo": 120
  },
  "mixCompleted": true,
  "contentScheduled": false
}
```

---

### Backend Routes + Endpoints

**API Router:** `/api` prefix

**Beat Module:**
- `POST /api/beats/create` - Generate beat (Beatoven or fallback)
- `GET /api/beats/credits` - Get Beatoven credits

**Lyrics Module:**
- `POST /api/songs/write` - Standard lyrics generation
- `POST /api/lyrics/from_beat` - Generate from uploaded beat (V17)
- `POST /api/lyrics/free` - Generate from theme (V17)
- `POST /api/lyrics/refine` - Refine lyrics with instruction (V18)

**Upload Module:**
- `POST /api/recordings/upload` - Upload vocal recording (V20)

**Mix Module:**
- `POST /api/mix/run` - Legacy mixing (beat + vocals)
- `POST /api/mix/process` - V21: Single-file AI mix & master

**Release Module:**
- `POST /api/release/generate-cover` - Generate cover art
- `POST /api/release/pack` - Create release pack ZIP (V22)

**Content Module (V23):**
- `POST /api/content/idea` - Generate video idea
- `POST /api/content/upload-video` - Upload video + extract transcript
- `POST /api/content/analyze` - Analyze video for viral score
- `POST /api/content/generate-text` - Generate captions & hashtags
- `POST /api/content/schedule` - Schedule video via GetLate

**Social Module:**
- `GET /api/social/platforms` - Get supported platforms
- `POST /api/social/posts` - Schedule social post

**Analytics Module:**
- `GET /api/analytics/session/{id}` - Get session analytics
- `GET /api/analytics/dashboard/all` - Get dashboard analytics

**Voice Module:**
- `POST /api/voices/say` - Generate speech (gTTS)
- `POST /api/voices/stop` - Stop voices
- `POST /api/voices/pause` - Pause voices
- `POST /api/voices/mute` - Mute voices

**Project Module:**
- `GET /api/projects` - List all projects
- `GET /api/projects/{session_id}` - Get project
- `POST /api/projects/{session_id}/advance` - Advance stage

**Utility:**
- `GET /api/health` - Health check

---

### File Flow (Beat → Vocal → Mix → Release → Content)

1. **Beat Generation:**
   - Input: User prompt + mood
   - Output: `media/{session_id}/beat.mp3`
   - ProjectMemory: `assets.beat` updated

2. **Lyrics Generation:**
   - Input: Theme OR beat file OR session beat
   - Output: `media/{session_id}/lyrics.txt`
   - ProjectMemory: `assets.lyrics` updated

3. **Vocal Upload:**
   - Input: Audio file (.wav, .mp3, .aiff)
   - Output: `media/{session_id}/stems/{filename}`
   - ProjectMemory: `assets.stems[]` updated

4. **Mixing:**
   - Input: Vocal file + beat (optional) OR single file (V21)
   - Output: `media/{session_id}/mix.wav` OR `media/{session_id}/mix/mixed_mastered.wav`
   - Output: `media/{session_id}/master.wav` (legacy)
   - ProjectMemory: `assets.mix`, `assets.master` updated

5. **Release:**
   - Input: Mixed file + cover + metadata + lyrics
   - Output: `media/{session_id}/release/release_pack.zip`
   - ProjectMemory: `assets.release_pack`, `assets.cover_art` updated

6. **Content:**
   - Input: Video file + transcript + analysis
   - Output: `media/{session_id}/videos/{filename}`, `schedule.json`
   - ProjectMemory: `assets.uploaded_video`, `contentScheduled` updated

---

## SECTION 3 — CURRENT KNOWN ISSUES (PER MODULE)

### BeatStage

**Strengths:**
- ✅ Beat generation works (Beatoven API or fallback)
- ✅ Metadata extraction (bpm, key, duration)
- ✅ Credit system functional
- ✅ WavesurferPlayer displays beat
- ✅ Never returns 422 (always succeeds)

**Weaknesses:**
- ❌ Stage completion requires manual "Use Beat" click (not automatic)
- ❌ No error handling UI (silent failures possible)
- ❌ Credit modal shows but doesn't prevent generation if credits = 0

**Contradictions:**
- Backend advances stage automatically (`memory.advance_stage("beat", "lyrics")`)
- Frontend `completedStages` never updated until manual click
- MistLayer position stuck until manual stage click

---

### LyricsStage

**Strengths:**
- ✅ Three generation modes functional (from beat, free, from session beat)
- ✅ Structured parsing works (verse/chorus/bridge)
- ✅ V18.1 features functional (history, rhythm approximation)
- ✅ V18 refinement functional
- ✅ Scrollable display works

**Bugs Still to Fix:**
- ❌ Stage completion not automatically triggered
- ❌ No error handling UI for refinement failures
- ❌ History tracking may grow unbounded (should cap at 3)

**Missing Features:**
- ❌ No export lyrics button
- ❌ No copy-to-clipboard functionality
- ❌ No lyrics preview with beat sync

**Contradictions:**
- Backend saves lyrics and advances stage
- Frontend `completedStages` never updated
- MistLayer position stuck

---

### UploadStage

**Strengths:**
- ✅ Drag-and-drop works
- ✅ File validation works (frontend + backend)
- ✅ Backend saves correctly
- ✅ Project memory updated
- ✅ WavesurferPlayer displays vocal
- ✅ V20: Auto `completeStage("upload")` after success

**Contradictions:**
- V20 added completion trigger, but MistLayer may not update immediately
- Error state exists but not always displayed

**Limitations:**
- ❌ No progress indicator for large files
- ❌ No cancellation option
- ❌ No multiple file upload support
- ❌ No file preview before upload

---

### MixStage (MOST IMPORTANT SECTION)

**API Misalignment:**
- ❌ Frontend calls `/api/mix/process` (V21) but also has legacy `/api/mix/run` code
- ❌ `api.processMix()` expects file OR file_url, but frontend may pass wrong format
- ❌ Backend `/api/mix/process` expects FormData with `file_url` OR `file`, but frontend may send File object incorrectly

**UI Misalignment:**
- ❌ EQ sliders (Low/Mid/High) DISABLED but still visible ("Coming Soon")
- ❌ Compression/Reverb/Limiter sliders DISABLED but still visible
- ❌ AI Mix/Master toggles exist but may not reflect actual processing state
- ❌ Preset buttons (warm/clean/bright) exist but may not apply correctly

**DSP Inconsistencies:**
- ❌ EQ sliders don't affect audio (backend not implemented)
- ❌ Compression slider doesn't affect audio (backend not implemented)
- ❌ Reverb slider doesn't affect audio (backend not implemented)
- ❌ Limiter slider doesn't affect audio (backend not implemented)
- ❌ AI Mix/Master processing may not match UI controls (strength sliders)

**Audio Player Positioning Issues:**
- ❌ WavesurferPlayer may crash when toggles change
- ❌ Audio player may not reload when `sessionData.mixedFile` updates
- ❌ Preview players (beat/vocal) may not sync with main player

**Toggle → Crash Issue:**
- ❌ Toggling AI Mix/Master may cause audio player to crash
- ❌ Root cause: Audio player not re-initializing on state change
- ❌ WavesurferPlayer may not handle URL changes correctly

**Broken Fallback:**
- ❌ If `/api/mix/process` fails, no fallback to `/api/mix/run`
- ❌ Error handling may not surface to user

**File Load Error:**
- ❌ "Failed to load audio" bug when `sessionData.vocalFile` is URL string
- ❌ Frontend tries to fetch URL but may fail if URL is relative
- ❌ Backend expects file OR file_url, but frontend may send wrong format

**"Failed to Load Audio" Bug:**
- ❌ WavesurferPlayer fails when URL is relative path
- ❌ Need to ensure URLs are absolute or properly prefixed
- ❌ Backend file serving may not be accessible from frontend

**Why EQ/Effects Are Not Working:**
- ❌ Backend `/api/mix/process` doesn't accept EQ parameters
- ❌ Backend `/api/mix/run` doesn't apply EQ (only HPF, compression, de-ess, gain)
- ❌ Frontend sliders are disabled but still visible (misleading UX)

**Why Toggles Crash Audio Player:**
- ❌ WavesurferPlayer not re-initializing on URL change
- ❌ State updates may cause component re-render without proper cleanup
- ❌ Audio context may be destroyed/recreated incorrectly

**Missing Error Handling:**
- ❌ No error display for mix failures
- ❌ No retry mechanism
- ❌ No validation of file before processing

**Missing Correct Endpoint Call:**
- ❌ Frontend may call wrong endpoint (legacy vs V21)
- ❌ File format may not match backend expectations
- ❌ Parameters may not match backend schema

**Leftover Legacy Logic:**
- ❌ `handleMix()` still exists but calls `handleMixAndMaster()`
- ❌ Legacy `mixFile`/`masterFile` checks still in code
- ❌ Old volume sliders (beatVolume, vocalVolume) not used in V21 flow

**Incorrect State Flows:**
- ❌ `canMix` logic checks `uploadedFile || sessionData.vocalFile` but may not handle URL strings correctly
- ❌ `getAudioFile()` may return URL string but backend expects File object
- ❌ State updates may not trigger re-render correctly

**Missing Backend Logic:**
- ❌ EQ processing not implemented in backend
- ❌ Reverb processing not implemented
- ❌ Limiter processing not implemented (only hard limiter in AI Master)
- ❌ Preset filters may not apply correctly (warm/bright/clean)

**UI Layout Contradictions:**
- ❌ Disabled sliders still visible (confusing UX)
- ❌ "Coming Soon" labels but functionality partially implemented
- ❌ AI controls mixed with legacy controls

---

### ReleaseStage

**Stability:**
- ✅ Cover art generation works
- ✅ Release pack ZIP creation works
- ✅ Metadata.json included
- ✅ V22: Auto `completeStage("release")` after pack creation

**Missing Polish:**
- ❌ No preview of ZIP contents before download
- ❌ No validation of metadata fields
- ❌ No ISRC format validation
- ❌ No error handling for ZIP creation failures

**Future Improvements:**
- ❌ Add preview of release pack contents
- ❌ Add metadata validation
- ❌ Add ISRC format validation
- ❌ Add error handling UI

---

### ContentStage

**What Is Now Correct:**
- ✅ V23.1: All 5 steps functional (idea, upload, analyze, generate-text, schedule)
- ✅ Video upload works (FFmpeg audio extraction, Whisper transcript)
- ✅ Video analysis works (OpenAI viral score)
- ✅ Content text generation works (captions, hashtags, hooks)
- ✅ Scheduling works (GetLate API or local JSON)
- ✅ Auto `completeStage("content")` after scheduling

**What Still Needs Cleanup:**
- ❌ Error handling for video upload failures
- ❌ Error handling for transcript extraction failures
- ❌ Error handling for analysis failures
- ❌ No video preview before scheduling
- ❌ No video player component

**What Is Upcoming:**
- ❌ Video editor tab (hidden, backend not implemented)
- ❌ Video beat sync (backend exists but not wired)
- ❌ Video export (backend exists but not wired)

---

## SECTION 4 — REQUIRED FIXES BEFORE V24

### Critical (Must Fix Now)

1. **MixStage: Toggle → Crash Issue**
   - **Issue:** Toggling AI Mix/Master crashes audio player
   - **Fix:** Re-initialize WavesurferPlayer on state change, add proper cleanup
   - **Location:** `MixStage.jsx` - `handleMixAndMaster()`, WavesurferPlayer component

2. **MixStage: "Failed to Load Audio" Bug**
   - **Issue:** WavesurferPlayer fails when URL is relative path
   - **Fix:** Ensure URLs are absolute or properly prefixed, validate URL format
   - **Location:** `MixStage.jsx` - WavesurferPlayer URL handling

3. **MixStage: File Load Error**
   - **Issue:** Backend expects file OR file_url, but frontend may send wrong format
   - **Fix:** Validate file format before API call, handle URL strings correctly
   - **Location:** `MixStage.jsx` - `getAudioFile()`, `handleMixAndMaster()`

4. **MixStage: Missing Error Handling**
   - **Issue:** No error display for mix failures
   - **Fix:** Add error state display, show error message to user
   - **Location:** `MixStage.jsx` - Error state handling

---

### High Priority

5. **MixStage: API Misalignment**
   - **Issue:** Frontend may call wrong endpoint or send wrong parameters
   - **Fix:** Ensure `api.processMix()` called with correct parameters, validate backend response
   - **Location:** `MixStage.jsx` - `handleMixAndMaster()`, `api.js` - `processMix()`

6. **MixStage: UI Misalignment**
   - **Issue:** Disabled sliders still visible, misleading UX
   - **Fix:** Hide disabled controls or add clear "Not Implemented" messaging
   - **Location:** `MixStage.jsx` - Slider components

7. **MixStage: DSP Inconsistencies**
   - **Issue:** EQ/Effects sliders don't affect audio
   - **Fix:** Either implement backend processing OR remove UI controls
   - **Location:** `MixStage.jsx` - Slider components, `main.py` - `/api/mix/process`

8. **MixStage: Leftover Legacy Logic**
   - **Issue:** Legacy code still present, may cause conflicts
   - **Fix:** Remove legacy `handleMix()`, clean up old state variables
   - **Location:** `MixStage.jsx` - Legacy functions, state variables

---

### Medium Priority

9. **All Stages: Stage Completion Not Triggered**
   - **Issue:** Some stages don't auto-trigger completion
   - **Fix:** Ensure `completeStage()` called after successful operations
   - **Location:** All stage components

10. **All Stages: Missing Error Handling**
    - **Issue:** Errors not always displayed to user
    - **Fix:** Add error state display to all components
    - **Location:** All stage components

11. **MixStage: Audio Player Positioning Issues**
    - **Issue:** WavesurferPlayer may not reload on state change
    - **Fix:** Add proper re-initialization logic
    - **Location:** `MixStage.jsx` - WavesurferPlayer component

12. **MixStage: Broken Fallback**
    - **Issue:** No fallback if `/api/mix/process` fails
    - **Fix:** Add fallback to `/api/mix/run` or show error
    - **Location:** `MixStage.jsx` - `handleMixAndMaster()`

---

### Low Priority

13. **MixStage: Preset Filters Not Working**
    - **Issue:** Warm/bright/clean presets may not apply correctly
    - **Fix:** Verify backend preset processing, test each preset
    - **Location:** `main.py` - `/api/mix/process` preset logic

14. **MixStage: State Flow Issues**
    - **Issue:** State updates may not trigger re-render correctly
    - **Fix:** Review state management, ensure proper React updates
    - **Location:** `MixStage.jsx` - State management

15. **ContentStage: Error Handling**
    - **Issue:** No error handling for video processing failures
    - **Fix:** Add error states for each step
    - **Location:** `ContentStage.jsx` - Error handling

---

## SECTION 5 — DEPENDENCY MAP

### Module Dependencies

**BeatStage:**
- Depends on: None (entry point)
- Safe: ✅ Yes (stable, well-tested)
- Fragile: ❌ No
- Must Refactor: ❌ No

**LyricsStage:**
- Depends on: BeatStage (optional - can use session beat)
- Safe: ✅ Yes (stable, V18.2 features working)
- Fragile: ⚠️ Partially (history tracking may grow unbounded)
- Must Refactor: ❌ No

**UploadStage:**
- Depends on: None (can work standalone)
- Safe: ✅ Yes (V20 stable)
- Fragile: ❌ No
- Must Refactor: ❌ No

**MixStage:**
- Depends on: UploadStage (needs vocal file) OR BeatStage (optional - needs beat)
- Safe: ❌ No (multiple critical issues)
- Fragile: ✅ Yes (toggle crashes, file load errors, API misalignment)
- Must Refactor: ✅ Yes (V24 - critical fixes required)

**ReleaseStage:**
- Depends on: MixStage (needs mixed file)
- Safe: ✅ Yes (V22 stable)
- Fragile: ❌ No
- Must Refactor: ❌ No

**ContentStage:**
- Depends on: ReleaseStage (optional - can work standalone)
- Safe: ✅ Yes (V23.1 stable)
- Fragile: ⚠️ Partially (error handling missing)
- Must Refactor: ❌ No

**Timeline:**
- Depends on: All stages (tracks completion)
- Safe: ✅ Yes (stable)
- Fragile: ❌ No
- Must Refactor: ❌ No

**MistLayer:**
- Depends on: App.jsx state (activeStage, currentStage)
- Safe: ✅ Yes (stable)
- Fragile: ❌ No
- Must Refactor: ❌ No

---

### Safe Modules (No Changes Needed)

- BeatStage
- UploadStage
- ReleaseStage
- Timeline
- MistLayer

---

### Fragile Modules (Handle with Care)

- MixStage: **CRITICAL** - Multiple issues, must fix in V24
- LyricsStage: History tracking may grow unbounded
- ContentStage: Error handling missing

---

### Modules That Must Be Refactored

- **MixStage (V24):**
  - Fix toggle → crash issue
  - Fix file load errors
  - Fix API misalignment
  - Remove legacy code
  - Add error handling
  - Fix UI misalignment

---

## SECTION 6 — UPDATED MASTER SHEET

### BeatStage (V17)

**Description:** Generate AI beats using Beatoven API or fallback demo beat.

**Real Functionality:**
- User inputs prompt text and mood
- Calls `/api/beats/create` with prompt, mood, genre, sessionId
- Backend tries Beatoven API (polls up to 3 minutes), falls back to demo beat
- Saves to `media/{session_id}/beat.mp3`
- Extracts metadata (bpm, key, duration) from Beatoven response
- Updates ProjectMemory with beat asset and metadata
- Advances stage to "lyrics"

**Real Backend Routes:**
- `POST /api/beats/create` - Generate beat
- `GET /api/beats/credits` - Get credits

**Real SessionData:**
- `beatFile`: URL to beat
- `beatMetadata`: `{bpm, key, duration}`
- `mood`: User-selected mood
- `genre`: User-selected genre

**Missing Features:**
- Auto-trigger stage completion (requires manual "Use Beat" click)
- Error handling UI

**Contradictions:**
- Backend advances stage automatically, but frontend doesn't update `completedStages` until manual click

**Next-Step Suggestions:**
- Add auto `completeStage("beat")` after successful generation
- Add error handling UI

---

### LyricsStage (V18.2)

**Description:** Generate NP22-style lyrics from beat, theme, or session beat, with interactive refinement.

**Real Functionality:**
- Mode 1: Upload beat → BPM/mood detection → NP22 lyrics
- Mode 2: Enter theme → NP22 lyrics
- Mode 3: Use session beat → Auto-fetch → NP22 lyrics
- Standard: Enter theme → OpenAI GPT-4o-mini → Structured parsing → Voice preview
- Refinement: Instruction → OpenAI refinement with history, structured lyrics, rhythm map

**Real Backend Routes:**
- `POST /api/songs/write` - Standard lyrics
- `POST /api/lyrics/from_beat` - From beat (V17)
- `POST /api/lyrics/free` - From theme (V17)
- `POST /api/lyrics/refine` - Refinement (V18)

**Real SessionData:**
- `lyricsData`: Lyrics text or structured object
- `bpm`: BPM from beat (if available)

**Missing Features:**
- Auto-trigger stage completion
- Export lyrics button
- Copy-to-clipboard
- Lyrics preview with beat sync

**Contradictions:**
- Backend saves and advances stage, but frontend doesn't update `completedStages`

**Next-Step Suggestions:**
- Add auto `completeStage("lyrics")` after successful generation
- Add export/copy functionality

---

### UploadStage (V20)

**Description:** Upload vocal recordings with validation and auto-completion.

**Real Functionality:**
- Drag-and-drop or file select
- Frontend validation (file size, extension)
- Backend validation (audio integrity)
- Saves to `media/{session_id}/stems/{filename}`
- Updates ProjectMemory with stem asset
- Advances stage to "mix"
- Auto `completeStage("upload")` after success

**Real Backend Routes:**
- `POST /api/recordings/upload` - Upload vocal

**Real SessionData:**
- `vocalFile`: URL to vocal stem
- `vocalUploaded`: Boolean flag

**Missing Features:**
- Progress indicator for large files
- Cancellation option
- Multiple file upload
- File preview before upload

**Contradictions:**
- None (V20 fixes applied)

**Next-Step Suggestions:**
- Add progress indicator
- Add multiple file support

---

### MixStage (V21.1) - **CRITICAL**

**Description:** AI-powered mix & master with single-file processing, plus legacy beat+vocals mixing.

**Real Functionality:**
- V21: Upload file OR use `sessionData.vocalFile` → AI Mix (HPF, compression, EQ, presets) → AI Master (limiter, loudness, stereo widening) → Save `mixed_mastered.wav`
- Legacy: Adjust sliders → Mix beat + vocals → Save `mix.wav` and `master.wav`
- Updates ProjectMemory with mix/master assets
- Advances stage to "release"

**Real Backend Routes:**
- `POST /api/mix/run` - Legacy mixing
- `POST /api/mix/process` - V21: AI mix & master

**Real SessionData:**
- `mixedFile`: URL to `mixed_mastered.wav` (V21)
- `mixFile`: URL to `mix.wav` (legacy)
- `masterFile`: URL to `master.wav` (legacy)
- `mixCompleted`: Boolean flag

**Missing Features:**
- EQ processing (sliders disabled)
- Reverb processing (slider disabled)
- Limiter processing (slider disabled)
- Error handling UI
- Proper file format handling

**Contradictions:**
- **CRITICAL:** Toggle → crash issue
- **CRITICAL:** "Failed to load audio" bug
- **CRITICAL:** File load error
- **CRITICAL:** API misalignment
- **CRITICAL:** UI misalignment (disabled sliders visible)
- **CRITICAL:** DSP inconsistencies (EQ/effects not working)
- Legacy code still present
- State flow issues

**Next-Step Suggestions:**
- **V24: Fix all critical issues**
- Remove legacy code
- Implement EQ/effects OR remove UI controls
- Add error handling
- Fix audio player re-initialization

---

### ReleaseStage (V22)

**Description:** Generate cover art and create release pack ZIP with metadata.

**Real Functionality:**
- User inputs title, artist, genre, mood, release date, ISRC, lyrics
- Generate cover art → Pillow gradient → Save `cover.jpg`
- Create release pack → Download mixed file → Export MP3 → Generate metadata.json → Create ZIP
- Save to `media/{session_id}/release/release_pack.zip`
- Updates ProjectMemory with release_pack and cover_art assets
- Advances stage to "content"
- Auto `completeStage("release")` after pack creation

**Real Backend Routes:**
- `POST /api/release/generate-cover` - Generate cover
- `POST /api/release/pack` - Create release pack

**Real SessionData:**
- `releasePackUrl`: URL to ZIP
- `coverArt`: URL to cover
- `trackTitle`, `artistName`, `genre`, `mood`, `release_date`, `isrc`, `lyricsData`

**Missing Features:**
- Preview of ZIP contents
- Metadata validation
- ISRC format validation
- Error handling UI

**Contradictions:**
- None (V22 fixes applied)

**Next-Step Suggestions:**
- Add ZIP preview
- Add metadata validation

---

### ContentStage (V23.1)

**Description:** Generate video ideas, upload videos, analyze for viral potential, generate captions/hashtags, and schedule posts.

**Real Functionality:**
- Step 1: Generate video idea → OpenAI → `{idea, hook, script, visual}`
- Step 2: Upload video → FFmpeg audio extraction → Whisper transcript → Save video + transcript
- Step 3: Analyze video → OpenAI → `{score, summary, improvements, suggested_hook, thumbnail_suggestion}`
- Step 4: Generate content text → OpenAI → `{captions, hashtags, hooks, posting_strategy, ideas}`
- Step 5: Schedule video → GetLate API (or local JSON) → Schedule post
- Auto `completeStage("content")` after scheduling

**Real Backend Routes:**
- `POST /api/content/idea` - Generate idea
- `POST /api/content/upload-video` - Upload video
- `POST /api/content/analyze` - Analyze video
- `POST /api/content/generate-text` - Generate text
- `POST /api/content/schedule` - Schedule video

**Real SessionData:**
- `contentIdea`: `{idea, hook, script, visual}`
- `uploadedVideo`: URL to video
- `videoTranscript`: Transcript text
- `viralAnalysis`: `{score, summary, improvements, suggested_hook, thumbnail_suggestion}`
- `contentTextPack`: `{captions, hashtags, hooks, posting_strategy, ideas}`
- `contentScheduled`: Boolean flag

**Missing Features:**
- Error handling for each step
- Video preview before scheduling
- Video player component

**Contradictions:**
- None (V23.1 stable)

**Next-Step Suggestions:**
- Add error handling
- Add video preview
- Add video player

---

## END OF TECHNICAL ARCHITECTURE REVIEW

**This document serves as the complete technical reference for:**
- Current tech stack and dependencies
- End-to-end product architecture
- All module functionality and issues
- Required fixes prioritized by severity
- Dependency relationships
- Updated master sheet with real functionality

**Use this document for:**
- Understanding system architecture
- Planning V24 fixes (especially MixStage)
- Debugging issues
- Onboarding new developers
- Technical decision-making

**Last Updated:** Current State (V17 → V23.1)  
**Next Version:** V24 (MixStage Critical Fixes)

