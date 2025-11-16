# Label-in-a-Box v4 - Master Technical Specification

**Version:** Post V37 (Billing Integration)  
**Last Updated:** 2024  
**Status:** Production Ready

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Module-by-Module Breakdown](#2-module-by-module-breakdown)
3. [Global UI Architecture](#3-global-ui-architecture)
4. [Auth System (Phase 8)](#4-auth-system-phase-8)
5. [Project System (Phase 8.3)](#5-project-system-phase-83)
6. [Paywall System (Phase 8.4)](#6-paywall-system-phase-84)
7. [Stripe Billing (Phase 9)](#7-stripe-billing-phase-9)
8. [File Structure Documentation](#8-file-structure-documentation)
9. [API Route Map](#9-api-route-map)
10. [Known Legacy Code](#10-known-legacy-code)
11. [Dependencies](#11-dependencies)
12. [Risks + Future Improvements](#12-risks--future-improvements)

---

## 1. System Overview

### 1.1 High-Level Architecture

Label-in-a-Box is a full-stack music production platform that guides users through a complete workflow from beat creation to release. The system consists of:

- **Frontend:** React 18 + Vite, TailwindCSS, Framer Motion
- **Backend:** FastAPI (Python 3.x), async/await architecture
- **Storage:** File-based JSON (users, projects), media files on disk
- **Authentication:** JWT-based with bcrypt password hashing
- **Billing:** Stripe integration for subscription management
- **AI Services:** OpenAI (GPT-4o-mini, TTS, DALL-E), Beatoven.ai, Whisper

### 1.2 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React/Vite)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   App    │  │ Timeline │  │  Stages  │  │  Voice   │   │
│  │  (Main)  │  │          │  │          │  │ Control  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │              │              │         │
│       └─────────────┴──────────────┴──────────────┘         │
│                          │                                  │
│                    API Client (api.js)                      │
└──────────────────────────┼──────────────────────────────────┘
                           │ HTTP/REST
┌──────────────────────────┼──────────────────────────────────┐
│                    Backend (FastAPI)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   Auth   │  │ Billing  │  │ Content  │  │   Main   │   │
│  │  Router  │  │  Router  │  │  Router  │  │  Router  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │              │              │         │
│       └─────────────┴──────────────┴──────────────┘         │
│                          │                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Project Memory (project_memory.py)            │  │
│  │         - Session-based state management              │  │
│  │         - User-scoped project isolation               │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Database Layer (database.py)                   │  │
│  │         - JSON file storage (data/users.json)         │  │
│  │         - User accounts, plans, Stripe IDs            │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                    Storage Layer                            │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  /media/{user_id}│  │  /data/projects/  │               │
│  │  /{session_id}/  │  │  {user_id}/      │               │
│  │  - beat.mp3      │  │  - {project}.json │               │
│  │  - lyrics.txt    │  └──────────────────┘               │
│  │  - mix/          │  ┌──────────────────┐               │
│  │  - release/      │  │  /data/users.json │               │
│  └──────────────────┘  └──────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Frontend System (React / Vite)

**Technology Stack:**
- React 18.2.0 with Hooks
- Vite 5.0.8 (build tool)
- TailwindCSS 3.4.0 (styling)
- Framer Motion 11.0.0 (animations)
- Wavesurfer.js 7.7.3 (audio visualization)

**Key Components:**
- `App.jsx` - Main application orchestrator
- `Timeline.jsx` - Stage navigation UI
- `MistLayer.jsx` - Animated background
- `VoiceControl.jsx` - Global voice system UI
- Stage components in `components/stages/`
- `AuthContext.jsx` - Authentication state management

**State Management:**
- React Context API for auth state
- Local component state for stage data
- `localStorage` for session persistence
- Project memory synced via API

**Build Configuration:**
- Dev server: `vite --host 0.0.0.0 --port 5000`
- Production build: `vite build` → `frontend/dist/`
- Proxy API calls to backend during development

### 1.4 Backend System (FastAPI / Python)

**Technology Stack:**
- FastAPI (async web framework)
- Uvicorn (ASGI server)
- Pydantic (data validation)
- PyJWT (token management)
- Passlib[bcrypt] (password hashing)
- Stripe SDK (billing)

**Architecture:**
- Router-based organization (`auth_router`, `billing_router`, `content_router`, main `api` router)
- Dependency injection for authentication (`get_current_user`)
- Standardized JSON responses (`success_response`, `error_response`)
- Comprehensive logging to `logs/app.log`

**Key Modules:**
- `main.py` - Core API routes and orchestration
- `auth.py` - Authentication endpoints
- `billing.py` - Stripe integration
- `content.py` - Content generation and scheduling
- `project_memory.py` - Session state management
- `database.py` - User data persistence
- `mix_engineer.py` - AI mix analysis
- `voice_system.py` - Voice agent definitions

### 1.5 Storage Architecture

**Media Storage:**
- Path: `./media/{user_id}/{session_id}/`
- Structure:
  ```
  media/
    {user_id}/
      {session_id}/
        beat.mp3
        lyrics.txt
        stems/
          {uploaded_file}.wav
        mix/
          mixed_mastered.wav
        release/
          cover/
            cover_1.jpg, cover_1_1500.jpg, cover_1_vertical.jpg
            final_cover_3000.jpg, final_cover_1500.jpg, final_cover_vertical.jpg
          copy/
            release_description.txt, press_pitch.txt, tagline.txt
          lyrics/
            lyrics.pdf
          metadata/
            metadata.json
          audio/
            mixed_mastered.wav, mixed_mastered.mp3
          release_pack.zip
        videos/
          {uploaded_video}.mp4
          {video}_transcript.txt
        voices/
          {sha256_hash}.mp3
        project.json
        schedule.json
  ```

**User Database:**
- Path: `./data/users.json`
- Structure:
  ```json
  {
    "{user_id}": {
      "email": "user@example.com",
      "password_hash": "$2b$12$...",
      "created_at": "2024-01-01T00:00:00",
      "plan": "free" | "pro",
      "stripe_customer_id": "cus_...",
      "last_release_timestamp": "2024-01-01T00:00:00"
    }
  }
  ```

**Project Storage:**
- Path: `./data/projects/{user_id}/{project_id}.json`
- Structure:
  ```json
  {
    "projectId": "uuid",
    "userId": "user_id",
    "name": "Project Name",
    "projectData": { /* full project memory structure */ },
    "createdAt": "2024-01-01T00:00:00",
    "updatedAt": "2024-01-01T00:00:00"
  }
  ```

### 1.6 Auth + User Session Lifecycle

**Authentication Flow:**
1. User signs up → `POST /api/auth/signup`
   - Email validation, password hashing (bcrypt)
   - Stripe customer creation
   - JWT token generation (7-day expiry)
   - Token stored in `localStorage` as `auth_token`

2. User logs in → `POST /api/auth/login`
   - Email/password verification
   - JWT token generation
   - Token stored in `localStorage`

3. Session restoration → `GET /api/auth/me`
   - Frontend checks `localStorage` on mount
   - Validates token with backend
   - Restores user state in `AuthContext`

4. Protected routes → `Depends(get_current_user)`
   - Extracts `Authorization: Bearer {token}` header
   - Validates JWT, loads user from database
   - Returns user dict to route handler

**Session Management:**
- Frontend: `sessionId` stored in `localStorage` as `liab_session_id`
- Backend: Session ID used for media path isolation
- User-scoped: Media paths include `user_id` for isolation

### 1.7 System Interactions

**Request Flow:**
1. User action in React component
2. Component calls `api.{method}()` from `utils/api.js`
3. Request sent to `/api/{endpoint}` with auth headers
4. FastAPI route handler processes request
5. `ProjectMemory` instance loaded/created for session
6. Business logic executed (AI calls, file processing, etc.)
7. `ProjectMemory.save()` updates `project.json`
8. Standardized JSON response returned
9. Frontend updates UI state

**State Synchronization:**
- `api.syncProject()` - Syncs backend project state to frontend
- `updateSessionData()` - Updates React component state
- `completeStage()` - Marks stage complete, advances workflow

---

## 2. Module-by-Module Breakdown

### 2.1 Beat Stage (Upload)

**Components:**
- `frontend/src/components/stages/BeatStage.jsx`

**Backend Routes:**
- `POST /api/beats/create` - Generate beat via Beatoven API
- `GET /api/beats/credits` - Get remaining Beatoven credits

**State Stored:**
- `sessionData.beatFile` - URL to generated beat
- `sessionData.beatMetadata` - BPM, key, duration
- `sessionData.mood` - Beat mood
- `project.json`:
  ```json
  {
    "assets": {
      "beat": {
        "url": "/media/{session_id}/beat.mp3",
        "metadata": { "bpm": 120, "key": "C", "duration": 60 }
      }
    },
    "metadata": {
      "tempo": 120,
      "mood": "energetic",
      "genre": "hip hop"
    }
  }
  ```

**Tick System Interaction:**
- On beat generation success → `completeStage('beat')`
- Updates `completedStages` object: `{ beat: true }`
- Timeline shows checkmark on beat icon

**Media Storage:**
- Beat file: `media/{user_id}/{session_id}/beat.mp3`
- Fallback: `media/demo_beats/default_beat.mp3` if Beatoven unavailable

**Processing Flow:**
1. User enters prompt, mood, genre
2. Frontend calls `api.createBeat(promptText, mood, genre, sessionId)`
3. Backend builds Beatoven API request
4. Polls for completion (up to 3 minutes, 3-second intervals)
5. Downloads generated audio to session directory
6. Updates `ProjectMemory` with beat asset
7. Returns `{ url, metadata, session_id }`
8. Frontend updates `sessionData` and shows Wavesurfer player

### 2.2 Lyrics Stage

**Components:**
- `frontend/src/components/stages/LyricsStage.jsx`

**Backend Routes:**
- `POST /api/songs/write` - Generate lyrics from genre/mood/theme
- `POST /api/lyrics/from_beat` - Generate lyrics from uploaded beat file
- `POST /api/lyrics/free` - Generate free lyrics from theme
- `POST /api/lyrics/refine` - Refine/rewrite lyrics based on instruction

**State Stored:**
- `sessionData.lyricsData` - Full lyrics text
- `sessionData.lyrics` - Structured lyrics (verse/chorus/bridge)
- `project.json`:
  ```json
  {
    "assets": {
      "lyrics": {
        "url": "/media/{session_id}/lyrics.txt",
        "metadata": { "genre": "hip hop", "mood": "energetic" }
      }
    }
  }
  ```

**Tick System Interaction:**
- On lyrics generation → `completeStage('lyrics')`
- Updates `completedStages` object: `{ lyrics: true }`

**Media Storage:**
- Lyrics file: `media/{user_id}/{session_id}/lyrics.txt`

**Processing Flow:**
1. User selects generation mode (from beat, free, or refine)
2. Frontend calls appropriate API endpoint
3. Backend uses OpenAI GPT-4o-mini to generate NP22-style lyrics
4. Parses lyrics into structured sections (verse/chorus/bridge)
5. Saves to `lyrics.txt` in session directory
6. Updates `ProjectMemory`
7. Returns structured lyrics object
8. Frontend displays lyrics with copy-to-clipboard buttons

### 2.3 Upload Stage

**Components:**
- `frontend/src/components/stages/UploadStage.jsx`

**Backend Routes:**
- `POST /api/recordings/upload` - Upload vocal recording

**State Stored:**
- `sessionData.vocalFile` - URL to uploaded vocal file
- `project.json`:
  ```json
  {
    "assets": {
      "stems": [
        {
          "url": "/media/{session_id}/stems/{filename}.wav",
          "added_at": "2024-01-01T00:00:00",
          "metadata": { "filename": "...", "size": 1234567 }
        }
      ]
    }
  }
  ```

**Tick System Interaction:**
- On successful upload → `completeStage('upload')`
- Updates `completedStages` object: `{ upload: true }`

**Media Storage:**
- Vocal files: `media/{user_id}/{session_id}/stems/{filename}.wav`

**Processing Flow:**
1. User selects audio file (.wav, .mp3, .aiff)
2. Frontend validates file type and size (50MB limit)
3. Uploads via FormData to `/api/recordings/upload`
4. Backend validates file with pydub
5. Saves to `stems/` directory
6. Updates `ProjectMemory` with stem asset
7. Returns file URL
8. Frontend displays uploaded file with Wavesurfer player

### 2.4 MixStage — DSP Backend

**Components:**
- `frontend/src/components/stages/MixStage.jsx`

**Backend Routes:**
- `POST /api/mix/run` - Legacy pydub-based mixing (beat + vocals)
- `POST /api/mix/process` - V25 DSP pipeline (single file processing)

**State Stored:**
- `sessionData.mixedFile` - URL to mixed/mastered file
- `sessionData.mixParams` - DSP parameters used
- `project.json`:
  ```json
  {
    "assets": {
      "mix": {
        "url": "/media/{session_id}/mix/mixed_mastered.wav",
        "metadata": {
          "ai_mix": true,
          "ai_master": true,
          "preset": "clean",
          "eq_low": 0.0,
          "eq_mid": -2.0,
          "eq_high": 0.0,
          "compression": 0.3,
          "reverb": 0.0,
          "limiter": 0.0
        }
      }
    }
  }
  ```

**Tick System Interaction:**
- On mix completion → `completeStage('mix')`
- Updates `completedStages` object: `{ mix: true }`

**FFmpeg Filters (V25 DSP Pipeline):**

1. **EQ (3-band):**
   - Low shelf: `equalizer=f=100:t=lowshelf:g={eq_low}` (-6 to +6 dB)
   - Mid peak: `equalizer=f=1500:t=peak:g={eq_mid}:width=2` (-6 to +6 dB)
   - High shelf: `equalizer=f=10000:t=highshelf:g={eq_high}` (-6 to +6 dB)

2. **Compression:**
   - `compand=attacks=0.01:decays=0.2:points=-90/-90|-20/-20|-10/-{threshold}|0/0`
   - Threshold calculated from compression slider (0-1) → (-10 to -20 dB)

3. **Reverb:**
   - `aecho=0.8:0.88:{delay_ms/1000.0}:{decay}`
   - Delay: 20-60ms (integer), Decay: 0.2-0.8

4. **Limiter:**
   - `alimiter=limit=0.95:level=1`

5. **Mastering Chain:**
   - `loudnorm=I=-13:TP=-1:LRA=7` (loudness normalization)
   - `alimiter=limit=0.98` (final limiter)
   - Optional: `stereotools=mlev=1.05` (if available)

**Parameters:**
- `ai_mix` (bool) - Enable AI mix processing
- `ai_master` (bool) - Enable AI mastering
- `mix_strength` (0-1) - AI mix intensity
- `master_strength` (0-1) - AI master intensity
- `preset` ("warm" | "clean" | "bright") - Preset overrides manual sliders
- `eq_low`, `eq_mid`, `eq_high` (-6 to +6 dB) - EQ gains
- `compression` (0-1) - Compression amount
- `reverb` (0-1) - Reverb amount
- `limiter` (0-1) - Limiter threshold

**Processing Flow:**
1. User uploads audio file or selects existing file
2. Frontend calls `api.processMix(sessionId, file, dspParams)`
3. Backend validates file (pydub check)
4. Builds FFmpeg filter chain from parameters
5. Executes single FFmpeg command with all filters
6. Saves output to `mix/mixed_mastered.wav`
7. Updates `ProjectMemory` with mix asset
8. Returns file URL
9. Frontend displays Wavesurfer player with processed audio

**Temp File Paths:**
- Input: `mix/temp_input_{uuid}.wav`
- Processing: `mix/temp_processed_{uuid}.wav`
- Output: `mix/mixed_mastered.wav`

**Output File Paths:**
- Final mix: `/media/{session_id}/mix/mixed_mastered.wav`

### 2.5 ReleaseStage

**Components:**
- `frontend/src/components/stages/ReleaseStage.jsx`

**Backend Routes:**
- `POST /api/release/cover` - Generate cover art (3 images via DALL-E)
- `POST /api/release/select-cover` - Select final cover art
- `POST /api/release/copy` - Generate release copy (description, pitch, tagline)
- `POST /api/release/lyrics` - Generate lyrics PDF
- `POST /api/release/metadata` - Generate metadata.json
- `GET /api/release/files` - List all release files
- `GET /api/release/pack` - Get complete release pack data
- `POST /api/release/download-all` - Generate ZIP of all files

**State Stored:**
- `sessionData.trackTitle`, `sessionData.artistName`
- `sessionData.genre`, `sessionData.mood`
- `sessionData.releaseDate`, `sessionData.explicit`
- `project.json`:
  ```json
  {
    "release": {
      "title": "Track Title",
      "artist": "Artist Name",
      "genre": "hip hop",
      "mood": "energetic",
      "explicit": false,
      "release_date": "2024-01-01",
      "cover_art": "/media/{session_id}/release/cover/final_cover_3000.jpg",
      "metadata_path": "/media/{session_id}/release/metadata/metadata.json",
      "files": [ /* array of file URLs */ ]
    },
    "assets": {
      "cover_art": { "url": "..." },
      "release_pack": { "url": "/media/{session_id}/release/release_pack.zip" }
    }
  }
  ```

**Tick System Interaction:**
- On ZIP download → `completeStage('release')`
- Updates `completedStages` object: `{ release: true }`

**Cover Art System:**
- Generates 3 images via DALL-E 2 (1024x1024)
- Upscales to 3000x3000, creates 1500x1500 and 1080x1920 variants
- User selects one → copies to `final_cover_*.jpg` files
- All variants saved in `release/cover/` directory

**Metadata:**
- `metadata.json` includes: title, artist, genre, mood, explicit, release_date, duration_seconds, bpm, key
- Extracted from project memory and audio analysis

**File Generation:**
- Cover art: 3000x3000, 1500x1500, 1080x1920 (vertical)
- Release copy: `release_description.txt`, `press_pitch.txt`, `tagline.txt`
- Lyrics PDF: Generated with ReportLab
- Metadata: JSON file
- Audio: WAV and MP3 (320kbps) in `release/audio/`

**Release Pack Structure:**
```
release_pack.zip
├── audio/
│   ├── mixed_mastered.wav
│   └── mixed_mastered.mp3
├── cover/
│   ├── cover_3000.jpg
│   ├── cover_1500.jpg
│   └── cover_vertical.jpg
├── lyrics/
│   └── lyrics.pdf
├── metadata/
│   └── metadata.json
└── copy/
    ├── release_description.txt
    ├── press_pitch.txt
    └── tagline.txt
```

### 2.6 Content Stage

**Components:**
- `frontend/src/components/stages/ContentStage.jsx`

**Backend Routes:**
- `POST /api/content/idea` - Generate video idea
- `POST /api/content/upload-video` - Upload video + extract transcript
- `POST /api/content/analyze` - Analyze video for viral score
- `POST /api/content/generate-text` - Generate captions, hashtags, hooks
- `POST /api/content/schedule` - Schedule video via GetLate API
- `POST /api/content/save-scheduled` - Save scheduled post locally
- `GET /api/content/get-scheduled` - Get all scheduled posts

**State Stored:**
- `sessionData.contentIdea` - Video idea object
- `sessionData.uploadedVideo` - Video file URL
- `sessionData.videoTranscript` - Extracted transcript
- `sessionData.viralAnalysis` - Analysis results
- `sessionData.contentTextPack` - Captions, hashtags, hooks
- `project.json`:
  ```json
  {
    "assets": {
      "uploaded_video": {
        "url": "/media/{session_id}/videos/{filename}.mp4",
        "metadata": { "duration": 60, "fps": 30, "transcript": "..." }
      }
    },
    "contentScheduled": true
  }
  ```

**Tick System Interaction:**
- On content text generation → `completeStage('content')`
- Updates `completedStages` object: `{ content: true }`

**Viral Scoring:**
- Formula: `50 + (caption_length > 60 ? 10 : 0) + (has_hashtags ? 5 : 0) + (hook_length > 20 ? 10 : 0) + (title_has_you ? 5 : 0)`
- Max score: 95
- Displayed in UI with improvements suggestions

**Transcript Logic:**
- Video uploaded → FFmpeg extracts audio → OpenAI Whisper transcribes
- Fallback: `"[Transcript not available - OpenAI API key required]"`
- Saved to `videos/{filename}_transcript.txt`

**Content Generation:**
- Uses OpenAI GPT-4o-mini to generate:
  - 3 caption options
  - 5-10 hashtags
  - 3 hook options
  - Posting strategy (one sentence)
  - 3 additional content ideas

**Copy-to-Clipboard Integration:**
- All generated text has "Copy" buttons
- Uses `navigator.clipboard.writeText()`
- Visual feedback on copy action

**Schedule Stage:**
- User selects platform (TikTok, Shorts, Reels)
- Sets date and time
- Selects caption and hashtags
- Calls `/api/content/schedule` with ISO datetime
- GetLate API integration (if key configured) or local JSON fallback
- Scheduled posts saved to `schedule.json` in session directory

**UI Flow:**
1. Generate video idea → displays idea, hook, script, visual
2. Upload video → extracts transcript, shows video URL
3. Analyze video → shows viral score, improvements, suggested hook
4. Generate text pack → shows captions, hashtags, hooks, posting strategy
5. Schedule video → platform/date/time selection, saves to schedule

**How Ticks Integrate:**
- Content stage completion tracked in `completedStages`
- Schedule completion tracked separately (`scheduleComplete` flag)

### 2.7 Voices + Audio Control

**Components:**
- `frontend/src/components/VoiceControl.jsx` - Global voice UI
- `frontend/src/hooks/useVoice.js` - Voice hook

**Backend Routes:**
- `POST /api/voices/say` - Generate speech (gTTS with debounce)
- `POST /api/voices/stop` - Stop playback (no-op)
- `POST /api/voices/pause` - Pause playback (no-op)
- `POST /api/voices/mute` - Mute playback (no-op)

**Voice Engine Pipeline:**
1. Frontend calls `voice.speak(text, persona)`
2. Hook calls `api.voiceSpeak(persona, text, sessionId)`
3. Backend `gtts_speak()` function:
   - Generates SHA256 cache key: `hashlib.sha256(f"{persona}:{text}")`
   - Checks 10-second debounce window
   - If not cached, generates gTTS audio with persona-specific TLD
   - Saves to `voices/{cache_key}.mp3`
   - Returns URL: `/media/{session_id}/voices/{cache_key}.mp3`
4. Frontend receives URL
5. `window.playVoiceGlobal()` plays audio via HTML5 Audio
6. Global audio element managed by `VoiceControl` component

**Endpoints:**
- `/api/voices/say` - Main speech generation
- `/api/voices/stop` - Stops current playback (frontend-only)
- `/api/voices/pause` - Pauses playback (frontend-only)
- `/api/voices/mute` - Mutes audio (frontend-only)

**How Playback Works:**
- Global `<audio>` element in `VoiceControl.jsx`
- `window.playVoiceGlobal(url, volume, text, persona)` function
- Volume slider controls global audio volume
- Persona selector changes `window.selectedVoicePersona`
- Playback state tracked in component state

**Expected Behavior Per Module:**
- **Beat Stage:** "Creating a {mood} beat for you..." on generation start
- **Lyrics Stage:** "Here are your lyrics" after generation
- **Upload Stage:** "Upload complete" after file upload
- **Mix Stage:** "Mixing and mastering your track. One moment."
- **Release Stage:** "Generating cover art..." on cover generation
- **Content Stage:** "Generating video idea..." on idea generation

**Remove Legacy Parts:**
- Old OpenAI TTS system (replaced by gTTS)
- Multiple voice engine implementations (consolidated to gTTS)
- Unused voice endpoints (kept minimal set)

---

## 3. Global UI Architecture

### 3.1 StageScreen

**Component:** `App.jsx` → `main.stage-screen`

**Layout:**
- Fullscreen when stage is open (`isStageOpen === true`)
- Centered timeline when no stage open
- Fixed header with auth controls (top-right)

**Stage Rendering:**
- `renderStage()` function switches based on `activeStage`
- Common props passed to all stages:
  - `sessionId`, `sessionData`, `updateSessionData`
  - `voice`, `onClose`, `onNext`, `completeStage`, `openUpgradeModal`

**Stage Order:**
```javascript
const stageOrder = [
  "beat",      // Beat creation
  "lyrics",    // Lyrics module
  "upload",    // Beat upload module
  "mix",       // Mix Stage
  "release",   // Release Pack module
  "content"    // Content/Viral module
];
```

### 3.2 MistLayer (Background Visuals)

**Component:** `frontend/src/components/MistLayer.jsx`

**Implementation:**
- CSS-based animated gradient mist
- Position mapped to `activeStage`:
  ```javascript
  const mistPositions = {
    beat: { x: '10%', y: '40%' },
    lyrics: { x: '28%', y: '40%' },
    upload: { x: '46%', y: '40%' },
    mix: { x: '64%', y: '40%' },
    release: { x: '82%', y: '40%' },
    content: { x: '90%', y: '40%' },
    analytics: { x: '95%', y: '40%' }
  };
  ```
- CSS variables `--x` and `--y` control mist position
- Smooth transitions via CSS animations

**Styling:**
- Purple/gold gradient (NP22 brand colors)
- Animated blur effect
- Fixed position, z-index behind content

### 3.3 Timeline Layout

**Component:** `frontend/src/components/Timeline.jsx`

**Structure:**
- Horizontal baseline with stage icons
- Stage icons positioned above/below baseline
- Goal icon at end (🎯)
- Progress text below

**Stages:**
```javascript
const stages = [
  { id: 'beat', icon: '🎵', label: 'Beat', dept: 'Echo' },
  { id: 'lyrics', icon: '✍️', label: 'Lyrics', dept: 'Lyrica' },
  { id: 'upload', icon: '🎙', label: 'Upload', dept: 'Nova' },
  { id: 'mix', icon: '🎚', label: 'Mix', dept: 'Tone' },
  { id: 'release', icon: '💿', label: 'Release', dept: 'Aria' },
  { id: 'content', icon: '📣', label: 'Content', dept: 'Vee' },
  { id: 'analytics', icon: '📊', label: 'Analytics', dept: 'Pulse' }
];
```

**Icon System:**
- Emoji icons for each stage
- Department name (voice persona) shown on hover
- Icons are clickable → opens stage

**Glow Behavior:**
- Only clicked/active stage glows
- `isActive = activeStage === stage.id`
- Pulse ring animation on active stage
- No glow based on completion or `currentStage`

**Tick System:**
- Completion tracked in `completedStages` object: `{ beat: true, lyrics: true, ... }`
- Checkmark (✓) appears on completed stages
- Progress calculated: `(completedCount / stages.length) * 100`

**Goal Reached Animation:**
- Modal appears when all stages complete
- Triggered once (prevents re-triggering)
- "Cycle Complete!" message
- "Restart Cycle" button resets workflow

---

## 4. Auth System (Phase 8)

### 4.1 User Model

**Structure:**
```python
{
  "user_id": "uuid",
  "email": "user@example.com",
  "password_hash": "$2b$12$...",  # bcrypt hash
  "created_at": datetime,
  "plan": "free" | "pro",
  "stripe_customer_id": "cus_...",
  "last_release_timestamp": "2024-01-01T00:00:00"  # For free tier limits
}
```

**Storage:**
- File: `data/users.json`
- Loaded/saved via `database.load_users()` / `database.save_users()`

### 4.2 Signup/Login

**Signup Flow:**
1. `POST /api/auth/signup` with `{ email, password }`
2. Email validation (regex)
3. Password length check (min 6 characters)
4. Email uniqueness check
5. Password hashing (bcrypt)
6. Stripe customer creation (if available)
7. User saved to `data/users.json`
8. JWT token generated
9. Returns `{ ok: true, token, user_id }`

**Login Flow:**
1. `POST /api/auth/login` with `{ email, password }`
2. Find user by email
3. Verify password (bcrypt)
4. JWT token generated
5. Returns `{ ok: true, token, user_id }`

**Frontend Integration:**
- `AuthModal.jsx` - Signup/login form
- `AuthContext.jsx` - State management
- Token stored in `localStorage` as `auth_token`
- User state in React Context

### 4.3 JWT Handling

**Token Creation:**
```python
def create_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

**Token Validation:**
- `get_current_user` dependency extracts `Authorization: Bearer {token}` header
- Decodes JWT, verifies signature and expiry
- Loads user from database
- Returns user dict to route handler

**Secret Key:**
- Currently hardcoded: `"np22_super_secret_key"`
- **TODO:** Move to environment variable in production

### 4.4 Token Restore

**Frontend Flow:**
1. `App.jsx` mounts → `AuthContext` checks `localStorage.getItem("auth_token")`
2. If token exists → calls `api.authMe(token)`
3. Backend validates token → returns user data
4. User state restored in `AuthContext`
5. Loading state: `authLoading` prevents UI flash

**Backend Endpoint:**
- `GET /api/auth/me` - Returns current user info from JWT

### 4.5 Account Dropdown

**Component:** `App.jsx` → Account menu (top-right)

**Features:**
- User avatar (first letter of email)
- Dropdown menu:
  - Email display
  - Account (placeholder)
  - Manage Projects
  - Save Project
  - Upgrade to Pro
  - Logout

**State:**
- `showAccountMenu` - Controls dropdown visibility
- Click outside closes menu (useEffect hook)

### 4.6 Auth Guards

**Protected Routes:**
- All `/api/projects/*` routes require `Depends(get_current_user)`
- `/api/billing/*` routes require authentication
- `/api/release/metadata` requires authentication (for free tier limits)

**Frontend Guards:**
- Project save/load requires user
- Upgrade modal shows auth modal if not logged in
- Manage Projects modal requires authentication

**What Requires Login:**
- Saving projects
- Loading projects
- Listing projects
- Creating checkout sessions
- Accessing billing portal
- Generating release metadata (free tier limit enforcement)

---

## 5. Project System (Phase 8.3)

### 5.1 Project Save

**Endpoint:** `POST /api/projects/save`

**Request:**
```json
{
  "userId": "user_id",
  "projectId": "uuid" | null,  // null for new project
  "projectData": { /* full project memory structure */ }
}
```

**Process:**
1. Validates user authentication
2. Checks free tier limits (max 1 project for free users)
3. Generates `projectId` if not provided
4. Saves to `data/projects/{user_id}/{project_id}.json`
5. Returns `{ ok: true, projectId, name }`

**Free Tier Limit:**
- Free users: Max 1 project
- Pro users: Unlimited projects
- Enforced in `save_project()` route handler

**File Structure:**
```json
{
  "projectId": "uuid",
  "userId": "user_id",
  "name": "Project Name",
  "projectData": { /* project memory */ },
  "createdAt": "2024-01-01T00:00:00",
  "updatedAt": "2024-01-01T00:00:00"
}
```

### 5.2 Project Load

**Endpoint:** `POST /api/projects/load`

**Request:**
```json
{
  "projectId": "uuid"
}
```

**Process:**
1. Validates user authentication
2. Loads project file from `data/projects/{user_id}/{project_id}.json`
3. Returns `{ ok: true, projectData, projectId, name }`

**Frontend Integration:**
- `ManageProjectsModal.jsx` lists all projects
- `handleLoadProject()` in `App.jsx`:
  1. Updates UI state from loaded project
  2. Sets `currentProjectId` for future saves
  3. Saves loaded data to current session (imports into projectMemory)
  4. Reloads project data to sync with backend

### 5.3 How projectMemory Maps to projectData

**Project Memory Structure:**
```json
{
  "session_id": "session_123",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "metadata": { "tempo": 120, "key": "C", "mood": "energetic", ... },
  "assets": { "beat": {...}, "lyrics": {...}, "mix": {...}, ... },
  "workflow": { "current_stage": "beat", "completed_stages": [...] },
  "workflow_state": { "beat_done": true, "lyrics_done": false, ... },
  "mix": { "vocal_level": 0, "reverb_amount": 0.3, ... },
  "beat": { "tempo": 120 },
  "release": { "title": "...", "artist": "...", ... },
  "chat_log": [],
  "voice_prompts": [],
  "analytics": { "streams": 0, "saves": 0, ... }
}
```

**Export Function:**
- `export_project(memory)` - Exports current project data
- Returns all relevant sections for saving

**Import Function:**
- `import_project(data, memory)` - Imports project data into memory
- Updates all sections in `project_data` dict
- Calls `memory.save()` to persist

**Mapping:**
- `projectData` in saved project = full `project_memory.project_data`
- When loading: `import_project(projectData, current_memory)`
- When saving: `export_project(current_memory)` → `projectData`

### 5.4 User-Specific Paths

**Media Storage:**
- Old: `media/{session_id}/` (no user isolation)
- New: `media/{user_id}/{session_id}/` (user-scoped)
- Backward compatibility: Falls back to `media/{session_id}/` if no `user_id`

**Project Storage:**
- `data/projects/{user_id}/{project_id}.json`
- User isolation enforced by authentication

**Session Isolation:**
- Each user's sessions are isolated
- `get_session_media_path(session_id, user_id)` handles path generation

### 5.5 Media Isolation

**Implementation:**
- `ProjectMemory.__init__()` accepts `user_id` parameter
- Media paths include `user_id`: `media/{user_id}/{session_id}/`
- Backend routes use `current_user["user_id"]` from auth dependency

**Benefits:**
- Users cannot access other users' media
- Clean separation for multi-tenant deployment
- Easier backup/restore per user

### 5.6 Switching Behavior

**When Loading Project:**
1. User selects project from `ManageProjectsModal`
2. `handleLoadProject()` called
3. Project data loaded from `data/projects/{user_id}/{project_id}.json`
4. UI state updated (workflow, metadata, etc.)
5. Project data imported into current session's `ProjectMemory`
6. `currentProjectId` set for future saves
7. Stages closed, returns to timeline
8. Project data synced with backend

**When Saving Project:**
1. User clicks "Save Project" in account menu
2. Current project data exported via `api.getProject(sessionId)`
3. Saved to `data/projects/{user_id}/{project_id}.json`
4. If new project, `projectId` generated and returned
5. Success toast shown

### 5.7 Session Regeneration

**Session ID Generation:**
- Frontend: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
- Stored in `localStorage` as `liab_session_id`
- Backend: Uses provided `session_id` or generates UUID

**New Session:**
- User can start new project → new `sessionId` generated
- Old session data remains in `media/{user_id}/{old_session_id}/`
- New session creates fresh `ProjectMemory` instance

---

## 6. Paywall System (Phase 8.4)

### 6.1 Free Tier vs Pro Tier

**Free Tier Limits:**
- Max 1 saved project
- 1 release per 24 hours (enforced in `/api/release/metadata`)

**Pro Tier:**
- Unlimited projects
- Unlimited releases
- All features unlocked

**Plan Storage:**
- User model: `"plan": "free" | "pro"`
- Default: `"free"` on signup
- Updated to `"pro"` via Stripe webhook

### 6.2 Gated Features

**Project Limits:**
- `POST /api/projects/save` - Checks project count for free users
- Returns `403` with `{ ok: false, error: "upgrade_required", feature: "multi_project" }`

**Release Limits:**
- `POST /api/release/metadata` - Checks `last_release_timestamp`
- If < 24 hours since last release → returns `403` with `{ ok: false, error: "upgrade_required", feature: "daily_release_limit" }`

### 6.3 Backend Limit Enforcement

**Implementation:**
- Route handlers check `current_user.get("plan", "free")`
- Free tier limits enforced before processing
- Returns standardized error response:
  ```json
  {
    "ok": false,
    "error": "upgrade_required",
    "feature": "multi_project" | "daily_release_limit"
  }
  ```

**Error Response:**
- Status code: `403 Forbidden`
- Frontend detects `error === "upgrade_required"`
- Triggers upgrade modal

### 6.4 handlePaywall() Handler

**Location:** `frontend/src/utils/paywall.js`

**Function:**
```javascript
export function handlePaywall(response, openUpgradeModal) {
  if (response && response.error === "upgrade_required") {
    openUpgradeModal(response.feature);
    return false;  // Block action
  }
  return true;  // Allow action
}
```

**Usage:**
- Called after API responses
- Checks for `upgrade_required` error
- Opens upgrade modal with feature name
- Returns `false` to block action, `true` to allow

**Integration:**
- `App.jsx`: `handleSaveProject()`, `handleLoadProject()`
- `ReleaseStage.jsx`: `handleGenerateMetadata()`
- All paywall-protected actions

### 6.5 Upgrade Modal Behavior

**Component:** `frontend/src/components/UpgradeModal.jsx`

**Features:**
- Shows feature-specific upgrade message
- "Upgrade to Pro" button → redirects to Stripe checkout
- "Cancel" button → closes modal

**Trigger:**
- `openUpgradeModal(feature)` called from paywall handler
- Modal state: `showUpgradeModal`, `upgradeFeature`

**Flow:**
1. User hits limit → API returns `upgrade_required`
2. `handlePaywall()` detects error
3. `openUpgradeModal(feature)` called
4. Modal displays upgrade message
5. User clicks "Upgrade to Pro" → `handleUpgradeToPro()`
6. Creates Stripe checkout session → redirects to Stripe

---

## 7. Stripe Billing (Phase 9)

### 7.1 Full Stripe Flow Mapping

**Environment Variables:**
- `STRIPE_SECRET` - Stripe secret key (sk_test_... or sk_live_...)
- `STRIPE_WEBHOOK_SECRET` - Webhook signing secret
- `PRICE_PRO_MONTHLY` - Stripe Price ID for Pro subscription
- `FRONTEND_URL` - Frontend URL for redirects (default: `http://localhost:5173`)

### 7.2 Checkout Session

**Endpoint:** `POST /api/billing/create-checkout-session`

**Request:**
```json
{
  "userId": "user_id",
  "priceId": "price_..." | null  // Optional, uses env default if null
}
```

**Process:**
1. Validates user authentication
2. Loads user from database
3. Gets `stripe_customer_id` (created on signup)
4. Creates Stripe Checkout Session:
   ```python
   stripe.checkout.Session.create(
       customer=customer_id,
       mode="subscription",
       line_items=[{"price": price_id, "quantity": 1}],
       success_url=FRONTEND_URL + "/billing/success",
       cancel_url=FRONTEND_URL + "/billing/cancel"
   )
   ```
5. Returns `{ ok: true, url: session.url }`

**Frontend Flow:**
1. User clicks "Upgrade to Pro"
2. `handleUpgradeToPro()` in `App.jsx`
3. Calls `api.createCheckoutSession(user.user_id)`
4. Redirects to `result.url` (Stripe checkout page)
5. User completes payment on Stripe
6. Stripe redirects to `/billing/success` or `/billing/cancel`

### 7.3 Webhook Event Handling

**Endpoint:** `POST /api/billing/webhook`

**Process:**
1. Receives raw request body
2. Extracts `stripe-signature` header
3. Verifies webhook signature:
   ```python
   event = stripe.Webhook.construct_event(
       payload, sig_header, STRIPE_WEBHOOK_SECRET
   )
   ```
4. Handles events:
   - `customer.subscription.created` - New subscription
   - `checkout.session.completed` - Checkout completed
5. Finds user by `stripe_customer_id`
6. Updates user plan to `"pro"`:
   ```python
   users[user_id]["plan"] = "pro"
   save_users(users)
   ```

**Webhook Configuration:**
- Stripe Dashboard → Webhooks → Add endpoint
- URL: `https://your-domain.com/api/billing/webhook`
- Events: `customer.subscription.created`, `checkout.session.completed`
- Copy signing secret to `STRIPE_WEBHOOK_SECRET`

### 7.4 Billing Portal

**Endpoint:** `POST /api/billing/portal`

**Process:**
1. Validates user authentication
2. Gets user's `stripe_customer_id`
3. Creates Billing Portal session:
   ```python
   stripe.billing_portal.Session.create(
       customer=customer_id,
       return_url=FRONTEND_URL + "/dashboard"
   )
   ```
4. Returns `{ ok: true, url: session.url }`

**Frontend Integration:**
- "Manage Subscription" button (future feature)
- Redirects to Stripe Billing Portal
- User can cancel, update payment method, view invoices

### 7.5 How user.plan = "pro" is Updated

**Update Paths:**
1. **Webhook (Primary):**
   - Stripe sends webhook event
   - Backend processes event
   - Updates `users[user_id]["plan"] = "pro"`
   - Saves to `data/users.json`

2. **Manual Update (Admin):**
   - Direct database edit (not recommended)
   - Update `data/users.json` manually

**Verification:**
- User logs in → `GET /api/auth/me` returns updated plan
- Frontend `AuthContext` updates user state
- UI reflects pro status

### 7.6 Safe Error Handling

**Checkout Session Errors:**
- Missing Stripe customer → `400 Bad Request`
- Invalid price ID → `500 Internal Server Error`
- Stripe API errors → Logged, returned as error response

**Webhook Errors:**
- Invalid signature → `400 Bad Request`
- Missing signature → `400 Bad Request`
- User not found → Logged as warning, returns success (idempotent)

**Frontend Error Handling:**
- Checkout creation failure → Shows error, falls back to upgrade modal
- Webhook processing errors → Logged server-side, user plan updated on next login

### 7.7 Environment Variables

**Required:**
```bash
STRIPE_SECRET=sk_test_...  # or sk_live_... for production
STRIPE_WEBHOOK_SECRET=whsec_...
PRICE_PRO_MONTHLY=price_...
FRONTEND_URL=https://your-domain.com  # or http://localhost:5173 for dev
```

**Optional:**
- `STRIPE_SECRET` - Falls back to placeholder if not set (checkout will fail)
- `PRICE_PRO_MONTHLY` - Must be set for checkout to work
- `FRONTEND_URL` - Defaults to `http://localhost:5173`

---

## 8. File Structure Documentation

### 8.1 Root Directory

```
BeatService/
├── main.py                    # Main FastAPI app, core routes
├── auth.py                    # Authentication routes
├── auth_utils.py             # JWT and password utilities
├── billing.py                # Stripe billing routes
├── content.py                # Content generation routes
├── database.py               # User database (JSON file)
├── project_memory.py         # Project state management
├── mix_engineer.py           # AI mix analysis
├── voice_system.py           # Voice agent definitions
├── cover_art_generator.py   # Local cover art generation
├── requirements.txt          # Python dependencies
├── render.yaml              # Render.com deployment config
│
├── data/                     # User and project data
│   ├── users.json           # User accounts database
│   └── projects/            # Saved projects
│       └── {user_id}/
│           └── {project_id}.json
│
├── media/                    # Media files (user-scoped)
│   └── {user_id}/
│       └── {session_id}/
│           ├── beat.mp3
│           ├── lyrics.txt
│           ├── stems/
│           ├── mix/
│           ├── release/
│           ├── videos/
│           ├── voices/
│           └── project.json
│
├── assets/                   # Static assets
│   ├── covers/              # Cover art templates
│   ├── demo/                # Demo files
│   └── sfx/                 # Sound effects
│
├── logs/                     # Application logs
│   └── app.log              # All endpoint events
│
└── frontend/                 # React frontend
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── index.html
    └── src/
        ├── main.jsx         # React entry point
        ├── App.jsx          # Main app component
        ├── components/      # React components
        ├── context/         # React Context providers
        ├── hooks/           # Custom React hooks
        ├── utils/           # Utility functions
        └── styles/          # CSS files
```

### 8.2 Backend Files

**Core:**
- `main.py` - FastAPI app, all main routes, 2700+ lines
- `auth.py` - Signup, login, token validation
- `billing.py` - Stripe checkout, webhooks, portal
- `content.py` - Video ideas, analysis, scheduling
- `database.py` - JSON file I/O for users
- `project_memory.py` - Session state, project persistence

**Services:**
- `mix_engineer.py` - AI mix parameter suggestions
- `voice_system.py` - Voice agent definitions (7 personas)
- `cover_art_generator.py` - Local cover art (Pillow)
- `analytics_engine.py` - Analytics calculations
- `social_scheduler.py` - GetLate API integration

### 8.3 Frontend Files

**Entry Points:**
- `main.jsx` - React app initialization, AuthProvider wrapper
- `App.jsx` - Main orchestrator, stage routing, auth UI

**Components:**
- `components/Timeline.jsx` - Stage navigation
- `components/MistLayer.jsx` - Animated background
- `components/VoiceControl.jsx` - Global voice UI
- `components/stages/*.jsx` - Stage components
- `components/AuthModal.jsx` - Signup/login
- `components/ManageProjectsModal.jsx` - Project list
- `components/UpgradeModal.jsx` - Paywall modal

**Hooks:**
- `hooks/useVoice.js` - Voice recognition and playback

**Utils:**
- `utils/api.js` - API client functions
- `utils/auth.js` - Auth helpers
- `utils/paywall.js` - Paywall handler

**Context:**
- `context/AuthContext.jsx` - Authentication state

### 8.4 Where Media is Stored

**Session Media:**
- `media/{user_id}/{session_id}/` - All session files
- Beat: `beat.mp3`
- Lyrics: `lyrics.txt`
- Vocals: `stems/{filename}.wav`
- Mix: `mix/mixed_mastered.wav`
- Release: `release/` (cover, copy, lyrics, metadata, audio)
- Videos: `videos/{filename}.mp4`
- Voices: `voices/{sha256_hash}.mp3`

**Static Assets:**
- `assets/covers/` - Cover art templates
- `assets/demo/` - Demo beats
- `assets/sfx/` - Sound effects

### 8.5 Where Project Data is Stored

**Active Sessions:**
- `media/{user_id}/{session_id}/project.json` - Current session state

**Saved Projects:**
- `data/projects/{user_id}/{project_id}.json` - Saved project snapshots

**User Data:**
- `data/users.json` - All user accounts

---

## 9. API Route Map

### 9.1 Authentication Routes

| Method | Route | Parameters | Purpose | File | Response |
|--------|-------|------------|---------|------|----------|
| POST | `/api/auth/signup` | `{ email, password }` | Create user account | `auth.py:50` | `{ ok, token, user_id }` |
| POST | `/api/auth/login` | `{ email, password }` | Login and get token | `auth.py:112` | `{ ok, token, user_id }` |
| GET | `/api/auth/me` | `Authorization: Bearer {token}` | Get current user | `auth.py:150` | `{ ok, user_id, email, plan }` |
| POST | `/api/auth/logout` | None | Logout (client-side) | `auth.py:196` | `{ ok, message }` |

### 9.2 Beat Routes

| Method | Route | Parameters | Purpose | File | Response |
|--------|-------|------------|---------|------|----------|
| POST | `/api/beats/create` | `{ prompt?, mood?, genre?, bpm?, duration_sec?, session_id? }` | Generate beat | `main.py:247` | `{ ok, data: { url, metadata } }` |
| GET | `/api/beats/credits` | None | Get Beatoven credits | `main.py:505` | `{ ok, data: { credits } }` |

### 9.3 Lyrics Routes

| Method | Route | Parameters | Purpose | File | Response |
|--------|-------|------------|---------|------|----------|
| POST | `/api/songs/write` | `{ genre, mood, theme?, session_id?, beat_context? }` | Generate lyrics | `main.py:564` | `{ ok, data: { lyrics, lyrics_text, path } }` |
| POST | `/api/lyrics/from_beat` | `file: UploadFile, session_id?: Form` | Generate from beat | `main.py:784` | `{ ok, data: { lyrics, bpm, mood } }` |
| POST | `/api/lyrics/free` | `{ theme }` | Generate free lyrics | `main.py:887` | `{ ok, data: { lyrics } }` |
| POST | `/api/lyrics/refine` | `{ lyrics, instruction, bpm?, history?, structured_lyrics?, rhythm_map? }` | Refine lyrics | `main.py:909` | `{ ok, data: { lyrics } }` |

### 9.4 Upload Routes

| Method | Route | Parameters | Purpose | File | Response |
|--------|-------|------------|---------|------|----------|
| POST | `/api/recordings/upload` | `file: UploadFile, session_id?: Form` | Upload vocal | `main.py:1009` | `{ ok, data: { file_url, filename } }` |

### 9.5 Mix Routes

| Method | Route | Parameters | Purpose | File | Response |
|--------|-------|------------|---------|------|----------|
| POST | `/api/mix/run` | `{ session_id, vocal_gain, beat_gain, hpf_hz, deess_amount }` | Legacy mix | `main.py:1120` | `{ ok, data: { mix_url, master_url } }` |
| POST | `/api/mix/process` | `file?: UploadFile, file_url?: Form, session_id, ai_mix, ai_master, mix_strength, master_strength, preset, eq_low, eq_mid, eq_high, compression, reverb, limiter` | DSP mix | `main.py:1278` | `{ ok, data: { file_url } }` |

### 9.6 Release Routes

| Method | Route | Parameters | Purpose | File | Response |
|--------|-------|------------|---------|------|----------|
| POST | `/api/release/cover` | `{ session_id, track_title, artist_name, genre, mood, style? }` | Generate cover | `main.py:1590` | `{ ok, data: { images: [...] } }` |
| POST | `/api/release/select-cover` | `{ session_id, cover_url }` | Select cover | `main.py:1664` | `{ ok, data: { final_cover } }` |
| POST | `/api/release/copy` | `{ session_id, track_title, artist_name, genre, mood, lyrics? }` | Generate copy | `main.py:1698` | `{ ok, data: { description_url, pitch_url, tagline_url } }` |
| POST | `/api/release/lyrics` | `{ session_id, title, artist, lyrics }` | Generate PDF | `main.py:1808` | `{ ok, data: { pdf_url } }` |
| POST | `/api/release/metadata` | `{ session_id, track_title, artist_name, mood, genre, explicit, release_date }` | Generate metadata | `main.py:1905` | `{ ok, data: { metadata_url } }` |
| GET | `/api/release/files` | `session_id: Query` | List files | `main.py:2014` | `{ ok, data: { files: [...] } }` |
| GET | `/api/release/pack` | `session_id: Query` | Get pack data | `main.py:2067` | `{ ok, data: { coverArt, metadataFile, ... } }` |
| POST | `/api/release/download-all` | `{ session_id }` | Generate ZIP | `main.py:2142` | `{ ok, data: { zip_url } }` |

### 9.7 Content Routes

| Method | Route | Parameters | Purpose | File | Response |
|--------|-------|------------|---------|------|----------|
| POST | `/api/content/idea` | `{ session_id?, title?, lyrics?, mood?, genre? }` | Generate idea | `content.py:59` | `{ ok, data: { idea, hook, script, visual } }` |
| POST | `/api/content/upload-video` | `file: UploadFile, session_id?: Form` | Upload video | `content.py:139` | `{ ok, data: { file_url, transcript, duration } }` |
| POST | `/api/content/analyze` | `{ transcript, title?, lyrics?, mood?, genre? }` | Analyze video | `content.py:266` | `{ ok, data: { score, summary, improvements, suggested_hook } }` |
| POST | `/api/content/generate-text` | `{ session_id?, title?, transcript?, lyrics?, mood?, genre? }` | Generate text | `content.py:363` | `{ ok, data: { captions, hashtags, hooks, posting_strategy, ideas } }` |
| POST | `/api/content/schedule` | `{ session_id, video_url, caption, hashtags?, platform, schedule_time }` | Schedule video | `content.py:453` | `{ ok, data: { post_id, platform, scheduled_time, status } }` |
| POST | `/api/content/save-scheduled` | `{ sessionId, platform, dateTime?, time?, caption? }` | Save scheduled | `content.py:560` | `{ ok, data: { post_id, status } }` |
| GET | `/api/content/get-scheduled` | `session_id: Query` | Get scheduled | `content.py:613` | `{ ok, data: [...] }` |

### 9.8 Voice Routes

| Method | Route | Parameters | Purpose | File | Response |
|--------|-------|------------|---------|------|----------|
| POST | `/api/voices/say` | `{ persona, text, session_id? }` | Generate speech | `main.py:2487` | `{ ok, data: { url, persona, cached } }` |
| POST | `/api/voices/stop` | `{ session_id? }` | Stop playback | `main.py:2509` | `{ ok, data: { action } }` |
| POST | `/api/voices/pause` | `{ session_id? }` | Pause playback | `main.py:2503` | `{ ok, data: { action } }` |
| POST | `/api/voices/mute` | `{ session_id? }` | Mute playback | `main.py:2497` | `{ ok, data: { action } }` |

### 9.9 Project Routes

| Method | Route | Parameters | Purpose | File | Response |
|--------|-------|------------|---------|------|----------|
| GET | `/api/projects` | `Authorization: Bearer {token}` | List projects | `main.py:2529` | `{ ok, projects: [...] }` |
| GET | `/api/projects/{session_id}` | `session_id: Path, Authorization: Bearer {token}` | Get project | `main.py:2541` | `{ ok, project: {...} }` |
| POST | `/api/projects/{session_id}/advance` | `session_id: Path, Authorization: Bearer {token}` | Advance stage | `main.py:2551` | `{ ok, data: { current_stage } }` |
| POST | `/api/projects/save` | `{ userId, projectId?, projectData }, Authorization: Bearer {token}` | Save project | `main.py:2580` | `{ ok, data: { projectId, name } }` |
| GET | `/api/projects/list` | `Authorization: Bearer {token}` | List user projects | `main.py:2639` | `{ ok, data: { projects: [...] } }` |
| POST | `/api/projects/load` | `{ projectId }, Authorization: Bearer {token}` | Load project | `main.py:2670` | `{ ok, data: { projectData, projectId, name } }` |

### 9.10 Billing Routes

| Method | Route | Parameters | Purpose | File | Response |
|--------|-------|------------|---------|------|----------|
| POST | `/api/billing/create-checkout-session` | `{ userId, priceId? }, Authorization: Bearer {token}` | Create checkout | `billing.py:34` | `{ ok, url }` |
| POST | `/api/billing/webhook` | Raw body, `stripe-signature: Header` | Stripe webhook | `billing.py:84` | `{ ok, received }` |
| POST | `/api/billing/portal` | `Authorization: Bearer {token}` | Billing portal | `billing.py:140` | `{ ok, url }` |

### 9.11 Utility Routes

| Method | Route | Parameters | Purpose | File | Response |
|--------|-------|------------|---------|------|----------|
| GET | `/api/health` | None | Health check | `main.py:2519` | `{ status, beatoven_configured, ... }` |

### 9.12 Related Frontend Call Sites

**Authentication:**
- `api.signup()` → `POST /api/auth/signup` - `utils/api.js:43`
- `api.login()` → `POST /api/auth/login` - `utils/api.js:34`
- `api.authMe()` → `GET /api/auth/me` - `utils/api.js:27`

**Beats:**
- `api.createBeat()` → `POST /api/beats/create` - `utils/api.js:151`
- `api.getBeatCredits()` → `GET /api/beats/credits` - `utils/api.js:166`

**Lyrics:**
- `api.generateLyrics()` → `POST /api/songs/write` - `utils/api.js:171`
- `api.generateLyricsFromBeat()` → `POST /api/lyrics/from_beat` - `utils/api.js:187`
- `api.generateFreeLyrics()` → `POST /api/lyrics/free` - `utils/api.js:204`
- `api.refineLyrics()` → `POST /api/lyrics/refine` - `utils/api.js:214`

**Upload:**
- `api.uploadRecording()` → `POST /api/recordings/upload` - `utils/api.js:230`

**Mix:**
- `api.mixAudio()` → `POST /api/mix/run` - `utils/api.js:242`
- `api.processMix()` → `POST /api/mix/process` - `utils/api.js:258`

**Release:**
- `api.generateReleaseCover()` → `POST /api/release/cover` - `utils/api.js:298`
- `api.selectReleaseCover()` → `POST /api/release/select-cover` - `utils/api.js:314`
- `api.generateReleaseCopy()` → `POST /api/release/copy` - `utils/api.js:343`
- `api.generateLyricsPDF()` → `POST /api/release/lyrics` - `utils/api.js:359`
- `api.generateReleaseMetadata()` → `POST /api/release/metadata` - `utils/api.js:373`
- `api.listReleaseFiles()` → `GET /api/release/files` - `utils/api.js:326`
- `api.getReleasePack()` → `GET /api/release/pack` - `utils/api.js:335`
- `api.downloadAllReleaseFiles()` → `POST /api/release/download-all` - `utils/api.js:394`

**Content:**
- `api.generateVideoIdea()` → `POST /api/content/idea` - `utils/api.js:422`
- `api.uploadVideo()` → `POST /api/content/upload-video` - `utils/api.js:437`
- `api.analyzeVideo()` → `POST /api/content/analyze` - `utils/api.js:449`
- `api.generateContentText()` → `POST /api/content/generate-text` - `utils/api.js:464`
- `api.scheduleVideo()` → `POST /api/content/schedule` - `utils/api.js:480`
- `api.saveScheduled()` → `POST /api/content/save-scheduled` - `utils/api.js:496`
- `api.getScheduled()` → `GET /api/content/get-scheduled` - `utils/api.js:505`

**Voice:**
- `api.voiceSpeak()` → `POST /api/voices/say` - `utils/api.js:76`
- `api.voiceStop()` → `POST /api/voices/stop` - `utils/api.js:89`
- `api.voicePause()` → `POST /api/voices/pause` - `utils/api.js:100`
- `api.voiceMute()` → `POST /api/voices/mute` - `utils/api.js:111`

**Projects:**
- `api.getProject()` → `GET /api/projects/{session_id}` - `utils/api.js:59`
- `api.syncProject()` → Helper function - `utils/api.js:635`
- `api.advanceStage()` → `POST /api/projects/{session_id}/advance` - `utils/api.js:696`
- `api.saveProject()` → `POST /api/projects/save` - `utils/api.js:706`
- `api.listProjects()` → `GET /api/projects/list` - `utils/api.js:723`
- `api.loadProject()` → `POST /api/projects/load` - `utils/api.js:733`

**Billing:**
- `api.createCheckoutSession()` → `POST /api/billing/create-checkout-session` - `utils/api.js:748`
- `api.createPortalSession()` → `POST /api/billing/portal` - `utils/api.js:761`

---

## 10. Known Legacy Code (To Remove)

### 10.1 Legacy Voice Engines

**Removed:**
- OpenAI TTS system (replaced by gTTS)
- Multiple voice engine implementations
- Unused voice endpoints

**Current:**
- gTTS-only system with SHA256 caching
- 10-second debounce window
- Persona-specific TLD mapping

### 10.2 Old Timeline Code

**Status:** Clean - Timeline.jsx is current implementation

**Removed:**
- Old stage locking system (stages are not locked in v4)
- Legacy progress tracking

### 10.3 Unused Scripts

**Status:** No unused scripts identified

### 10.4 Dead CSS

**Status:** CSS files are actively used:
- `styles/index.css` - Global styles
- `styles/Timeline.css` - Timeline component
- `styles/mist.css` - MistLayer background
- `styles/ErrorBoundary.css` - Error boundary

### 10.5 Unused Components

**Removed:**
- `TestConnection.jsx` - Deleted (git status shows deletion)

**Active Components:**
- All stage components in use
- All modal components in use
- All utility components in use

### 10.6 Old Version Remnants

**Status:** Codebase is clean post-V37

**Migration Notes:**
- User-scoped media paths (`media/{user_id}/{session_id}/`) implemented
- Backward compatibility maintained for sessions without `user_id`
- Project save/load system fully implemented

---

## 11. Dependencies

### 11.1 Backend Dependencies (requirements.txt)

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | Latest | Web framework |
| uvicorn[standard] | Latest | ASGI server |
| pydantic | Latest | Data validation |
| pydub | Latest | Audio processing |
| moviepy | Latest | Video processing |
| Pillow | Latest | Image processing |
| python-multipart | Latest | File uploads |
| requests | Latest | HTTP client |
| openai | Latest | OpenAI API (GPT, TTS, Whisper, DALL-E) |
| librosa | Latest | Audio analysis |
| soundfile | Latest | Audio I/O |
| spotipy | Latest | Spotify integration (reference engine) |
| numpy | Latest | Numerical operations |
| scipy | Latest | Scientific computing |
| gtts | Latest | Google Text-to-Speech |
| python-dotenv | Latest | Environment variables |
| aubio | Latest | BPM detection |
| reportlab | Latest | PDF generation |
| PyJWT | Latest | JWT token management |
| passlib[bcrypt] | Latest | Password hashing |
| stripe | Latest | Stripe billing SDK |

### 11.2 Frontend Dependencies (package.json)

| Package | Version | Purpose |
|---------|---------|---------|
| react | ^18.2.0 | UI framework |
| react-dom | ^18.2.0 | React DOM renderer |
| framer-motion | ^11.0.0 | Animations |
| wavesurfer.js | ^7.7.3 | Audio visualization |

**Dev Dependencies:**
- @vitejs/plugin-react ^4.2.0 - Vite React plugin
- autoprefixer ^10.4.16 - CSS autoprefixer
- postcss ^8.4.32 - CSS processor
- tailwindcss ^3.4.0 - Utility CSS framework
- vite ^5.0.8 - Build tool

### 11.3 External Services

| Service | Purpose | API Key Required |
|---------|---------|------------------|
| Beatoven.ai | Beat generation | `BEATOVEN_API_KEY` |
| OpenAI | GPT, TTS, Whisper, DALL-E | `OPENAI_API_KEY` |
| Stripe | Billing and payments | `STRIPE_SECRET`, `STRIPE_WEBHOOK_SECRET` |
| GetLate.dev | Social media scheduling | `GETLATE_API_KEY` (optional) |
| Auphonic | Audio mastering | `AUPHONIC_API_KEY` (optional, not implemented) |

---

## 12. Risks + Future Improvements

### 12.1 Where the System is Brittle

**1. File-Based Storage:**
- **Risk:** JSON files not suitable for production scale
- **Impact:** Concurrent writes could corrupt data
- **Mitigation:** Use database (PostgreSQL/MongoDB) for production

**2. JWT Secret Key:**
- **Risk:** Hardcoded in `auth_utils.py`
- **Impact:** Security vulnerability if code leaked
- **Mitigation:** Move to environment variable, use strong random key

**3. Media Storage:**
- **Risk:** Local disk storage not scalable
- **Impact:** Disk space limits, no redundancy
- **Mitigation:** Use cloud storage (S3, Cloudflare R2)

**4. Session ID Generation:**
- **Risk:** Frontend-generated, could collide
- **Impact:** Session conflicts
- **Mitigation:** Backend-generated UUIDs

**5. Error Handling:**
- **Risk:** Some routes don't handle all edge cases
- **Impact:** Unhandled exceptions could crash server
- **Mitigation:** Comprehensive try-catch, error logging

**6. Rate Limiting:**
- **Risk:** No rate limiting on API routes
- **Impact:** Abuse, API cost overruns
- **Mitigation:** Implement rate limiting middleware

### 12.2 Recommended Refactors

**1. Database Migration:**
- Replace JSON files with PostgreSQL
- Use SQLAlchemy ORM
- Migrate existing data

**2. Authentication:**
- Move JWT secret to environment variable
- Implement token refresh mechanism
- Add password reset flow

**3. Media Storage:**
- Migrate to cloud storage (S3-compatible)
- Implement CDN for media delivery
- Add media cleanup job for old sessions

**4. API Structure:**
- Split `main.py` into smaller modules
- Implement service layer pattern
- Add comprehensive API documentation (OpenAPI/Swagger)

**5. Error Handling:**
- Standardize error responses
- Implement error tracking (Sentry)
- Add request ID tracking

**6. Testing:**
- Add unit tests for core functions
- Add integration tests for API routes
- Add E2E tests for critical flows

### 12.3 Planned Improvements

**1. Real-Time Features:**
- WebSocket support for live updates
- Real-time collaboration
- Live audio streaming

**2. Advanced Mixing:**
- AI-powered mix suggestions
- Reference track matching
- Stem separation

**3. Distribution:**
- Direct distribution to streaming platforms
- ISRC code generation
- Release scheduling

**4. Analytics:**
- Real streaming analytics
- Social media metrics
- Revenue tracking

**5. Mobile App:**
- React Native mobile app
- Offline mode
- Mobile-optimized UI

### 12.4 Stability Priorities

**High Priority:**
1. Move JWT secret to environment variable
2. Add database for user/project storage
3. Implement rate limiting
4. Add comprehensive error handling
5. Migrate media to cloud storage

**Medium Priority:**
1. Split `main.py` into modules
2. Add API documentation
3. Implement testing suite
4. Add monitoring/alerting
5. Optimize audio processing performance

**Low Priority:**
1. Real-time features
2. Advanced AI features
3. Mobile app
4. Distribution integration

---

## Appendix A: Environment Variables

### Required for Production

```bash
# Stripe
STRIPE_SECRET=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
PRICE_PRO_MONTHLY=price_...

# Frontend
FRONTEND_URL=https://your-domain.com

# JWT (should be strong random string)
JWT_SECRET=your-strong-random-secret-key-here
```

### Optional (Features work with fallbacks)

```bash
# AI Services
OPENAI_API_KEY=sk-...
BEATOVEN_API_KEY=...
GETLATE_API_KEY=...
AUPHONIC_API_KEY=...
```

---

## Appendix B: Deployment

### Render.com Configuration

**File:** `render.yaml`

**Services:**
- Web service (FastAPI backend)
- Static site (Frontend build)

**Environment:**
- Python 3.11+
- Node.js 18+ (for frontend build)

**Build Commands:**
- Backend: `pip install -r requirements.txt`
- Frontend: `cd frontend && npm install && npm run build`

**Start Command:**
- `uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## Document Version History

- **v1.0** - Initial master tech specs (Post V37)
- Created: 2024
- Author: System Analysis
- Status: Production Ready

---

**End of Master Technical Specification**

