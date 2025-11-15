# MASTER TECHNICAL BRIEFING
## Label-in-a-Box v4 - Complete Codebase Analysis

**Date:** Generated Analysis  
**Purpose:** CTO-Level Technical Breakdown - Diagnostic Only (No Fixes)

---

## 1. ARCHITECTURE OVERVIEW

### Full Stack Structure
- **Backend:** FastAPI (Python) on port 8000
- **Frontend:** React 18.2.0 + Vite on port 5000
- **Communication:** RESTful API via `/api` prefix, proxied through Vite dev server
- **State Management:** React useState hooks + localStorage for session persistence
- **File Storage:** Local filesystem (`./media/{session_id}/`)

### Frontend Structure
```
frontend/
├── src/
│   ├── App.jsx                    # Root component, stage routing
│   ├── main.jsx                   # React entry point
│   ├── components/
│   │   ├── Timeline.jsx          # Stage navigation UI
│   │   ├── MistLayer.jsx          # Background gradient effect
│   │   ├── VoiceChat.jsx          # Voice input UI
│   │   ├── VoiceControl.jsx      # Voice playback controls
│   │   ├── WavesurferPlayer.jsx   # Audio waveform player
│   │   ├── AnalyticsDashboard.jsx # Analytics overlay
│   │   ├── ErrorBoundary.jsx      # Error handling
│   │   └── stages/
│   │       ├── StageWrapper.jsx   # Common stage container
│   │       ├── BeatStage.jsx       # Beat generation
│   │       ├── LyricsStage.jsx    # Lyrics generation
│   │       ├── UploadStage.jsx    # Vocal upload
│   │       ├── MixStage.jsx       # Mixing interface
│   │       ├── ReleaseStage.jsx   # Release pack creation
│   │       └── ContentStage.jsx   # Social content
│   ├── hooks/
│   │   └── useVoice.js            # Voice recognition & TTS
│   ├── utils/
│   │   └── api.js                 # API client wrapper
│   └── styles/
│       ├── index.css              # Global styles
│       ├── Timeline.css           # Timeline styling
│       └── mist.css               # MistLayer gradient
```

### Backend Structure
```
backend/
├── main.py                        # FastAPI app, all endpoints
├── project_memory.py              # Persistent project state
├── cover_art_generator.py         # Local cover art generation
├── analytics_engine.py            # Analytics calculations
├── social_scheduler.py            # Social media scheduling
├── requirements.txt               # Python dependencies
└── media/                         # Session-based file storage
    └── {session_id}/
        ├── project.json           # Project state
        ├── beat.mp3
        ├── lyrics.txt
        ├── stems/                 # Uploaded vocals
        ├── mix.wav
        ├── master.wav
        ├── cover.jpg
        └── release_pack.zip
```

### API Routes (All under `/api` prefix)
1. **Beat Generation:** `POST /beats/create`
2. **Lyrics:** `POST /songs/write`
3. **Upload:** `POST /recordings/upload`
4. **Mix:** `POST /mix/run`
5. **Release:** `POST /release/generate-cover`, `POST /release/pack`
6. **Content:** `POST /content/ideas`
7. **Social:** `GET /social/platforms`, `POST /social/posts`
8. **Analytics:** `GET /analytics/session/{id}`, `GET /analytics/dashboard/all`
9. **Voice:** `POST /voices/say`, `POST /voices/stop`, `POST /voices/mute`, `POST /voices/pause`
10. **Projects:** `GET /projects`, `GET /projects/{id}`
11. **Health:** `GET /health`

### Data Flow
1. **User Action** → Frontend component
2. **API Call** → `api.js` utility → FastAPI endpoint
3. **Backend Processing** → ProjectMemory updates → File I/O
4. **Response** → Standardized `{ok, data, message}` format
5. **Frontend Update** → `syncProject()` → `updateSessionData()` → React re-render

### State Flow
- **Session ID:** Generated on mount, stored in localStorage
- **Current Stage:** Managed in `App.jsx` (`currentStage` state) + `ProjectMemory.workflow.current_stage`
- **Completed Stages:** Array in `App.jsx` + `ProjectMemory.workflow.completed_stages`
- **Active Stage:** `activeStage` in `App.jsx` (which stage UI is open)
- **Session Data:** `sessionData` object in `App.jsx` (beatFile, lyricsData, vocalFile, etc.)

### Component Hierarchy
```
App (root)
├── MistLayer (background)
├── Timeline (centered, z-index 20)
├── stage-screen (main content area, z-index 5)
│   └── ErrorBoundary
│       └── [Active Stage Component]
│           └── StageWrapper
│               └── stage-scroll-container
├── VoiceControl (fixed bottom-right, z-index 50)
├── AnalyticsDashboard (AnimatePresence overlay, z-index 50)
└── VoiceChat (fixed bottom-left, z-index 9999)
```

### Module Communication Patterns
- **Props Drilling:** All stage components receive `sessionId`, `sessionData`, `updateSessionData`, `voice`, `onClose`, `completeStage`
- **API Abstraction:** All backend calls go through `api.js` utility
- **State Sync:** `api.syncProject()` reads backend `project.json` and updates frontend state
- **Voice System:** Global `window.currentVoiceAudio` for audio playback coordination

---

## 2. EVERY MODULE IN THE PRODUCT

### Beat Module
- **Component:** `BeatStage.jsx`
- **Backend:** `POST /api/beats/create`
- **Flow:** User inputs mood → API call → Beatoven API (or fallback) → `beat.mp3` saved → ProjectMemory updated → Frontend syncs
- **State:** `sessionData.beatFile` (URL string)
- **Persona:** Echo (dept label only, no actual AI)

### Lyrics Module
- **Component:** `LyricsStage.jsx`
- **Backend:** `POST /api/songs/write`
- **Flow:** User inputs theme → OpenAI GPT-4o-mini (or fallback) → `lyrics.txt` saved → Structured parsing (verse/chorus/bridge) → Voice preview via gTTS → ProjectMemory updated
- **State:** `sessionData.lyricsData` (object with verse/chorus/bridge)
- **Persona:** Lyrica (dept label only)

### Upload/Record Module
- **Component:** `UploadStage.jsx`
- **Backend:** `POST /api/recordings/upload`
- **Flow:** Drag-and-drop or file input → Multipart upload → Saved to `stems/` directory → ProjectMemory updated → Frontend syncs
- **State:** `sessionData.vocalFile` (URL string from `project.assets.stems[0].url`)
- **Persona:** Nova (dept label only)

### Mix Module
- **Component:** `MixStage.jsx`
- **Backend:** `POST /api/mix/run`
- **Flow:** User adjusts sliders (vocal_gain, beat_gain, hpf_hz, deess_amount) → pydub processing → Mix beat + stems → Normalize → Save `mix.wav` and `master.wav` → ProjectMemory updated
- **State:** `sessionData.mixFile`, `sessionData.masterFile`
- **Persona:** Tone (dept label only)
- **Note:** EQ, Compression, Reverb, Limiter sliders are **DISABLED** (coming soon)

### Release Module
- **Component:** `ReleaseStage.jsx`
- **Backend:** `POST /api/release/generate-cover`, `POST /api/release/pack`
- **Flow:** User inputs title/artist → Cover art generation (Pillow, local) → `cover.jpg` saved → Release pack ZIP creation (master.wav + cover.jpg + metadata.json) → ProjectMemory updated
- **State:** `sessionData.coverArt`, `sessionData.releasePack`
- **Persona:** Aria (dept label only)

### Content Module
- **Component:** `ContentStage.jsx`
- **Backend:** `POST /api/content/ideas`, `POST /api/social/posts`
- **Flow:** Auto-generates demo captions (hooks, text, hashtags) → User can schedule posts → GetLate.dev API (or local JSON fallback) → `schedule.json` saved
- **State:** `content` object, `scheduledPosts` array
- **Persona:** Vee (dept label only)
- **Note:** Video editor tab is **HIDDEN** (backend not ready)

### Analytics Module
- **Component:** `AnalyticsDashboard.jsx`
- **Backend:** `GET /api/analytics/session/{id}`, `GET /api/analytics/dashboard/all`
- **Flow:** Reads `project.json` analytics section → Calculates metrics → Displays stats (streams, revenue, saves, shares, platform breakdown)
- **State:** `projectAnalytics`, `dashboardData`
- **Persona:** Pulse (dept label only)
- **Note:** All metrics are **DEMO DATA** (no real tracking)

### Voice Control Module
- **Component:** `VoiceControl.jsx`
- **Backend:** `POST /api/voices/say` (gTTS), `POST /api/voices/stop`, `POST /api/voices/mute`, `POST /api/voices/pause`
- **Flow:** `useVoice.speak()` → Backend generates MP3 via gTTS → Returns URL → Frontend plays via `window.currentVoiceAudio` → Subtitle display
- **State:** `currentSubtitle`, `currentVoice`, `audioQueue`
- **Personas:** echo, lyrica, nova, tone, aria, vee, pulse (gTTS TLD accents only)

### MistLayer System
- **Component:** `MistLayer.jsx`
- **Purpose:** Purple/gold gradient background that animates position based on active stage
- **Implementation:** CSS `radial-gradient` with CSS variables `--x` and `--y` updated via props
- **Position Map:** Hardcoded percentages for each stage (beat: 10%, lyrics: 28%, etc.)

### Timeline System
- **Component:** `Timeline.jsx`
- **Purpose:** Horizontal stage navigation with progress tracking
- **Features:** 
  - Stage icons with status (active/completed/upcoming)
  - Progress bar animation
  - Pulse ring on active stage
  - Goal reached modal
- **State:** Receives `currentStage` and `completedStages` from App.jsx

### StageScreen System
- **Location:** `App.jsx` → `<main className="stage-screen">`
- **CSS:** `frontend/src/styles/index.css` lines 133-142
- **Layout:** 
  - Position: `absolute`, `top: calc(50% + 110px)`
  - Height: `calc(100vh - (50% + 110px))`
  - Overflow: `overflow-y: auto`
  - Z-index: 5
- **Issue:** Stage content renders in a scrollable box below the timeline, NOT full-screen

---

## 3. TECHNICAL COMPONENTS

### React Components
- **App.jsx:** Root orchestrator
- **Timeline.jsx:** Stage navigation
- **MistLayer.jsx:** Background gradient
- **VoiceChat.jsx:** Voice input UI
- **VoiceControl.jsx:** Voice playback controls
- **WavesurferPlayer.jsx:** Audio waveform visualization
- **AnalyticsDashboard.jsx:** Analytics overlay
- **ErrorBoundary.jsx:** Error handling
- **LoadingSpinner.jsx:** Loading indicator
- **StageWrapper.jsx:** Common stage container
- **BeatStage.jsx, LyricsStage.jsx, UploadStage.jsx, MixStage.jsx, ReleaseStage.jsx, ContentStage.jsx:** Individual stage UIs

### Hooks
- **useVoice.js:** 
  - Web Speech API for recognition
  - Backend TTS via `/api/voices/say`
  - Global audio playback management

### CSS Files
- **index.css:** Global styles, stage-screen layout, voice controls
- **Timeline.css:** Timeline styling, progress bar, goal modal
- **mist.css:** MistLayer gradient animation
- **ErrorBoundary.css:** Error UI styling

### Backend Endpoints
All endpoints return standardized format:
- Success: `{ok: true, data: {...}, message: "..."}`
- Error: `{ok: false, error: "..."}`

### Utility Functions
- **api.js:** 
  - `handleResponse()`: Parses standardized responses
  - `syncProject()`: Syncs backend project.json to frontend state
  - All API method wrappers

### Audio Processing Logic
- **Backend:** pydub library
  - `AudioSegment.from_file()`: Load audio
  - `high_pass_filter()`: HPF on vocals
  - `compress_dynamic_range()`: Compression
  - `normalize()`: Mastering
  - `overlay()`: Mixing
- **Frontend:** wavesurfer.js for waveform visualization

### Global State/Context
- **No Context API:** All state managed via props drilling
- **localStorage:** Session ID persistence
- **window.currentVoiceAudio:** Global audio element reference
- **window.playVoice / window.stopVoice:** Global voice control functions

### File Storage
- **Backend:** `./media/{session_id}/` directory structure
- **Static Serving:** FastAPI `StaticFiles` mounted at `/media`
- **Project Memory:** `project.json` in each session directory

### Third-Party Integrations
- **Beatoven.ai:** Beat generation (with fallback to demo beat)
- **OpenAI:** Lyrics generation (GPT-4o-mini, with fallback)
- **gTTS:** Voice synthesis (10s debounce, SHA256 cache)
- **GetLate.dev:** Social media scheduling (with local JSON fallback)
- **Auphonic:** Mentioned but **NOT IMPLEMENTED** (TODO comment in code)

### Animation/UI Frameworks
- **framer-motion:** All animations (AnimatePresence, motion.div, etc.)
- **Tailwind CSS:** Utility classes (via PostCSS)
- **wavesurfer.js:** Audio waveform rendering

---

## 4. HOW EACH MODULE WORKS TODAY

### Beat Module
1. **Trigger:** User clicks "Generate Beat" button
2. **Files Used:** `BeatStage.jsx`, `api.js`, `main.py` (lines 232-446)
3. **Backend Endpoint:** `POST /api/beats/create`
4. **Backend Logic:**
   - Validates request (mood, genre, bpm, duration)
   - Tries Beatoven API if key available
   - Polls for completion (up to 3 minutes)
   - Falls back to demo beat if API fails
   - Saves to `media/{session_id}/beat.mp3`
   - Updates ProjectMemory
5. **Returns:** `{session_id, url: "/media/{id}/beat.mp3", status: "ready"}`
6. **Renders:** WavesurferPlayer component with beat URL
7. **Timeline Interaction:** None (stage completion not automatically triggered)
8. **StageScreen Interaction:** Renders inside `stage-screen` scroll container

### Lyrics Module
1. **Trigger:** User clicks "Generate Lyrics" button
2. **Files Used:** `LyricsStage.jsx`, `api.js`, `main.py` (lines 452-579)
3. **Backend Endpoint:** `POST /api/songs/write`
4. **Backend Logic:**
   - Tries OpenAI GPT-4o-mini if key available
   - Falls back to static template
   - Parses lyrics into verse/chorus/bridge sections
   - Generates voice preview via gTTS (first 200 chars)
   - Saves to `media/{session_id}/lyrics.txt`
   - Updates ProjectMemory
5. **Returns:** `{lyrics: {verse, chorus, bridge}, lyrics_text, path, voice_url, provider}`
6. **Renders:** Structured lyrics display with sections
7. **Timeline Interaction:** None
8. **StageScreen Interaction:** Renders inside `stage-screen` scroll container

### Upload Module
1. **Trigger:** User drags file or clicks file input
2. **Files Used:** `UploadStage.jsx`, `api.js`, `main.py` (lines 585-631)
3. **Backend Endpoint:** `POST /api/recordings/upload`
4. **Backend Logic:**
   - Validates file type (.wav, .mp3, .m4a, .aiff, .flac)
   - Saves to `media/{session_id}/stems/{filename}`
   - Updates ProjectMemory (adds to `assets.stems` array)
5. **Returns:** `{session_id, uploaded, vocal_url, filename, path}`
6. **Renders:** WavesurferPlayer with vocal URL
7. **Timeline Interaction:** None
8. **StageScreen Interaction:** Renders inside `stage-screen` scroll container

### Mix Module
1. **Trigger:** User clicks "Mix & Master" button
2. **Files Used:** `MixStage.jsx`, `api.js`, `main.py` (lines 637-789)
3. **Backend Endpoint:** `POST /api/mix/run`
4. **Backend Logic:**
   - Loads stems from `stems/` directory
   - Applies HPF, compression, de-ess (approximate), gain
   - Loads beat if exists, applies gain
   - Overlays vocals on beat (or vocals-only if no beat)
   - Normalizes (local, Auphonic not implemented)
   - Saves `mix.wav` and `master.wav`
   - Updates ProjectMemory
5. **Returns:** `{mix_url, master_url, mastering: "local", stems_mixed, mix_type}`
6. **Renders:** WavesurferPlayer for mix and master
7. **Timeline Interaction:** None
8. **StageScreen Interaction:** Renders inside `stage-screen` scroll container
9. **Note:** EQ, Compression, Reverb, Limiter sliders are **DISABLED** (UI only)

### Release Module
1. **Trigger:** User clicks "Generate AI Cover Art" or "Generate Release Pack"
2. **Files Used:** `ReleaseStage.jsx`, `api.js`, `main.py` (lines 795-881), `cover_art_generator.py`
3. **Backend Endpoints:** 
   - `POST /api/release/generate-cover`
   - `POST /api/release/pack`
4. **Backend Logic:**
   - Cover: Uses Pillow to generate gradient or load from `assets/covers/`, adds text overlay
   - Pack: Creates ZIP with master.wav, cover.jpg, metadata.json
   - Updates ProjectMemory
5. **Returns:** `{url: "/media/{id}/cover.jpg"}` or `{url: "/media/{id}/release_pack.zip"}`
6. **Renders:** Cover preview image, download link for ZIP
7. **Timeline Interaction:** None
8. **StageScreen Interaction:** Renders inside `stage-screen` scroll container

### Content Module
1. **Trigger:** Auto-generates on tab open, or user clicks "Generate New Content"
2. **Files Used:** `ContentStage.jsx`, `api.js`, `main.py` (lines 887-918)
3. **Backend Endpoint:** `POST /api/content/ideas`
4. **Backend Logic:**
   - Returns **DEMO CAPTIONS** (hardcoded array)
   - No AI generation (despite UI suggesting it)
5. **Returns:** `{captions: [{hook, text, hashtags}]}`
6. **Renders:** Hooks, captions, hashtags with copy buttons, scheduling UI (disabled)
7. **Timeline Interaction:** None
8. **StageScreen Interaction:** Renders inside `stage-screen` scroll container
9. **Note:** Scheduling button is **DISABLED** (tooltip says "requires TikTok/Instagram API integration")

### Analytics Module
1. **Trigger:** User clicks Analytics stage icon
2. **Files Used:** `AnalyticsDashboard.jsx`, `api.js`, `main.py` (lines 1034-1122), `analytics_engine.py`
3. **Backend Endpoints:** 
   - `GET /api/analytics/session/{id}`
   - `GET /api/analytics/dashboard/all`
4. **Backend Logic:**
   - Reads `project.json` analytics section
   - Generates **DEMO METRICS** (estimated_reach = scheduled_posts * 1000)
   - Calculates platform breakdown from project data
5. **Returns:** `{analytics: {stages_completed, files_created, scheduled_posts, estimated_reach}}`
6. **Renders:** Stats cards, platform breakdown, insights (all demo data)
7. **Timeline Interaction:** Opens as overlay (z-index 50), hides timeline
8. **StageScreen Interaction:** Full-screen overlay, NOT in stage-screen container

### Voice Control Module
1. **Trigger:** `useVoice.speak()` called from any component
2. **Files Used:** `useVoice.js`, `VoiceControl.jsx`, `api.js`, `main.py` (lines 1128-1154)
3. **Backend Endpoint:** `POST /api/voices/say`
4. **Backend Logic:**
   - 10-second debounce with SHA256 cache key
   - Generates MP3 via gTTS with persona-specific TLD
   - Saves to `media/{session_id}/voices/{cache_key}.mp3`
   - Returns URL even if debounced (plays cached file)
5. **Returns:** `{url: "/media/{id}/voices/{hash}.mp3", persona, cached, session_id}`
6. **Renders:** Subtitle display in VoiceControl component (bottom-right)
7. **Timeline Interaction:** None
8. **StageScreen Interaction:** Fixed position overlay (z-index 50)

---

## 5. INCOMPLETE, BROKEN, STUBBED, OR PLACEHOLDER

### Half-Built Features

#### 1. **Mix Stage EQ/Effects Controls**
- **Location:** `MixStage.jsx` lines 131-200
- **Issue:** All sliders (EQ Low/Mid/High, Compression, Reverb, Limiter) are **DISABLED**
- **Status:** UI exists but non-functional, labeled "Coming Soon"
- **Impact:** Users can only adjust vocal/beat gain, no actual EQ or effects processing

#### 2. **Content Stage Video Editor**
- **Location:** `ContentStage.jsx` lines 223-224
- **Issue:** Video editor tab is **HIDDEN** (commented out)
- **Status:** Backend endpoints exist (`/api/video/analyze`, `/api/video/beat-sync`, `/api/video/export`) but not implemented
- **Impact:** Video editing feature completely unavailable

#### 3. **Social Media Scheduling**
- **Location:** `ContentStage.jsx` lines 422-435
- **Issue:** Schedule button is **DISABLED** with tooltip "requires TikTok/Instagram API integration"
- **Status:** Backend supports GetLate.dev API and local JSON fallback, but frontend button disabled
- **Impact:** Users cannot schedule posts despite backend capability

#### 4. **Auphonic Mastering Integration**
- **Location:** `main.py` line 743
- **Issue:** `# TODO: Implement Auphonic API call`
- **Status:** Always uses local `normalize()` function
- **Impact:** No professional mastering, only basic normalization

### Missing Backend Logic

#### 1. **Video Processing Endpoints**
- **Expected:** `POST /api/video/analyze`, `POST /api/video/beat-sync`, `POST /api/video/export`
- **Status:** Referenced in `api.js` but **NOT IMPLEMENTED** in `main.py`
- **Files:** `video_editor.py` exists but not imported/used

#### 2. **Intent Router Integration**
- **Expected:** `POST /api/intent` for voice commands
- **Status:** `intent_router.py` exists but **NOT WIRED** to main.py
- **Impact:** Voice commands cannot route to backend actions

#### 3. **Reference Engine**
- **Expected:** `POST /api/reference/analyze` for reference track analysis
- **Status:** `reference_engine.py` exists but **NOT WIRED** to main.py
- **Impact:** Reference track feature unavailable

### Non-Functioning UI Elements

#### 1. **Stage Completion Not Triggered Automatically**
- **Location:** All stage components
- **Issue:** `completeStage()` prop exists but **NEVER CALLED** in stage components
- **Impact:** Stages never marked complete, progress bar never advances

#### 2. **MistLayer Glow Does Not Move**
- **Location:** `MistLayer.jsx`, `App.jsx` line 146
- **Issue:** MistLayer receives `activeStage || currentStage`, but `activeStage` is only set on click, not on stage completion
- **Impact:** Glow position only updates on manual stage click, not on workflow progression

#### 3. **Timeline Active Stage Not Synced**
- **Location:** `App.jsx` lines 22-23, 52-54
- **Issue:** `currentStage` loaded from backend but **NOT UPDATED** when stages complete
- **Impact:** Timeline shows wrong active stage after completion

### Broken AI Calls

#### 1. **Content Generation**
- **Location:** `main.py` lines 887-918
- **Issue:** Returns **HARDCODED DEMO CAPTIONS**, no AI generation
- **Impact:** Users see same generic content every time

#### 2. **Analytics Insights**
- **Location:** `analytics_engine.py` lines 282-320
- **Issue:** Generates **STATIC INSIGHTS** based on demo metrics, not real AI analysis
- **Impact:** Insights are generic templates, not personalized

### Modules That Partially Load or Return Empty Data

#### 1. **Analytics Dashboard**
- **Location:** `AnalyticsDashboard.jsx` lines 20-50
- **Issue:** Returns demo metrics (estimated_reach = scheduled_posts * 1000)
- **Impact:** All analytics are fake data, no real tracking

#### 2. **Social Platforms**
- **Location:** `ContentStage.jsx` lines 57-65
- **Issue:** `api.getSocialPlatforms()` returns `{platforms: ["tiktok", "shorts", "reels"]}` but frontend expects object keys
- **Impact:** Platform selector may not render correctly

### Incorrect CSS or Layout Issues

#### 1. **Stage Content in Scroll Box, Not Full-Screen**
- **Location:** `frontend/src/styles/index.css` lines 133-142
- **Issue:** `.stage-screen` has `position: absolute`, `top: calc(50% + 110px)`, `height: calc(100vh - (50% + 110px))`
- **Impact:** Stages render in a small scrollable box below timeline, NOT full-screen as intended

#### 2. **Timeline Centered Overlay**
- **Location:** `frontend/src/styles/Timeline.css` lines 1-8
- **Issue:** `.timeline-centered` is `position: absolute`, `top: 50%`, `left: 50%`, `transform: translate(-50%, -50%)`
- **Impact:** Timeline always visible, blocking stage content

#### 3. **Z-Index Conflicts**
- **Location:** Multiple files
- **Issue:** 
  - Timeline: z-index 20
  - Stage-screen: z-index 5
  - VoiceControl: z-index 50
  - AnalyticsDashboard: z-index 50
  - VoiceChat: z-index 9999
- **Impact:** Timeline may block stage content, VoiceChat may block everything

### Render Errors

#### 1. **WavesurferPlayer URL Errors**
- **Location:** `WavesurferPlayer.jsx` lines 13-54
- **Issue:** If `url` is null or invalid, component still tries to load
- **Impact:** Console errors when beat/vocal files not available

#### 2. **Missing Error Handling in Stage Components**
- **Location:** All stage components
- **Issue:** API errors caught but not always displayed to user
- **Impact:** Silent failures, user confusion

### Performance or Memory Limits

#### 1. **Voice Debounce Cache**
- **Location:** `main.py` lines 166-178
- **Issue:** In-memory dict `_voice_debounce_cache` never cleared
- **Impact:** Memory leak over time

#### 2. **Project Memory Loading**
- **Location:** `App.jsx` lines 45-60
- **Issue:** `loadProjectData()` only runs on mount, not on session change
- **Impact:** Stale data if session changes

---

## 6. STATE MANAGEMENT ISSUES

### Where Stage Changes Occur

1. **On Mount:** `App.jsx` `loadProjectData()` reads `project.workflow.current_stage` from backend
2. **On Stage Click:** `handleStageClick()` sets `activeStage` (UI only, doesn't update `currentStage`)
3. **On Stage Completion:** `completeCurrentStage()` updates `currentStage` locally and calls `syncProject()`, but **STAGES NEVER CALL `completeStage()`**
4. **Backend:** `ProjectMemory.advance_stage()` updates `workflow.current_stage` in `project.json`

### Where Active/Completed States Are Stored

- **Frontend:** 
  - `currentStage`: React state in `App.jsx`
  - `completedStages`: React state array in `App.jsx`
  - `activeStage`: React state in `App.jsx` (which UI is open)
- **Backend:**
  - `project.json` → `workflow.current_stage`
  - `project.json` → `workflow.completed_stages` (array)

### Why Glow Does Not Move Between Modules

**Root Cause:** `MistLayer` receives `activeStage || currentStage` from `App.jsx` line 146.

- `activeStage` is only set when user **clicks** a stage icon (`handleStageClick()`)
- `currentStage` is only updated in `completeCurrentStage()`, which is **NEVER CALLED**
- When a stage completes (e.g., beat generated), `activeStage` remains null, so MistLayer uses `currentStage`
- But `currentStage` is not updated until `completeCurrentStage()` runs, which never happens
- **Result:** Glow position only changes on manual stage click, not on workflow progression

### Why Modules Load in Small Scroll Box Instead of Full-Screen

**Root Cause:** CSS layout in `frontend/src/styles/index.css` lines 133-142.

```css
.stage-screen {
    position: absolute;
    top: calc(50% + 110px);  /* Starts below timeline */
    left: 0;
    width: 100%;
    height: calc(100vh - (50% + 110px));  /* Only half screen height */
    overflow-y: auto;  /* Scrollable */
    padding: 2rem;
    z-index: 5;  /* Below timeline (z-index 20) */
}
```

- Timeline is centered at `top: 50%` with `z-index: 20`
- Stage-screen starts at `top: calc(50% + 110px)` with `z-index: 5`
- **Result:** Stages render in a scrollable box below the timeline, NOT full-screen

**Intended Behavior:** Stages should render full-screen when `activeStage` is set, hiding the timeline.

---

## 7. UX ISSUES

### Missing Progress Bar
- **Location:** Timeline shows progress bar, but it's **STATIC** (based on `completedStages.length`)
- **Issue:** Progress never advances because stages never call `completeStage()`
- **Impact:** Users see 0% progress even after completing stages

### Missing Transitions
- **Location:** Stage switching
- **Issue:** No smooth transition when switching stages, just instant render
- **Impact:** Jarring user experience

### Missing Full-Screen Module Views
- **Location:** All stage components
- **Issue:** Stages render in scroll box, not full-screen
- **Impact:** Cluttered UI, timeline always visible

### Wrong Z-Index Overlays
- **Location:** Multiple components
- **Issue:** 
  - Timeline (z-index 20) blocks stage-screen (z-index 5)
  - VoiceChat (z-index 9999) may block everything
- **Impact:** UI elements overlap incorrectly

### Layout Inconsistencies

#### 1. **Timeline Always Visible**
- **Issue:** Timeline never hides when stage is active
- **Expected:** Timeline should hide or minimize when `activeStage` is set

#### 2. **Stage Header Not Sticky**
- **Location:** `StageWrapper.jsx`
- **Issue:** Stage header scrolls with content
- **Expected:** Header should be sticky/fixed at top

#### 3. **Voice Controls Overlap Content**
- **Location:** `VoiceControl.jsx` (fixed bottom-right)
- **Issue:** May overlap stage content on mobile
- **Expected:** Should adjust position or hide when not needed

#### 4. **Mobile Responsiveness**
- **Location:** `frontend/src/styles/index.css` lines 206-228
- **Issue:** Limited mobile breakpoints, voice controls may not scale correctly
- **Expected:** Better mobile layout adjustments

---

## 8. DEPENDENCY BREAKDOWN

### Frontend Dependencies (`frontend/package.json`)

#### Production
- **react:** `^18.2.0` - UI framework
- **react-dom:** `^18.2.0` - React DOM rendering
- **framer-motion:** `^11.0.0` - Animation library
- **wavesurfer.js:** `^7.7.3` - Audio waveform visualization

#### Development
- **@vitejs/plugin-react:** `^4.2.0` - Vite React plugin
- **autoprefixer:** `^10.4.16` - CSS autoprefixer
- **postcss:** `^8.4.32` - CSS post-processor
- **tailwindcss:** `^3.4.0` - Utility-first CSS framework
- **vite:** `^5.0.8` - Build tool and dev server

### Backend Dependencies (`requirements.txt`)

- **fastapi** - Web framework
- **uvicorn[standard]** - ASGI server
- **pydantic** - Data validation
- **pydub** - Audio processing
- **moviepy** - Video processing (NOT USED)
- **Pillow** - Image processing
- **python-multipart** - File upload support
- **requests** - HTTP client
- **openai** - OpenAI API client
- **librosa** - Audio analysis (NOT USED)
- **soundfile** - Audio file I/O (NOT USED)
- **spotipy** - Spotify API (NOT USED)
- **numpy** - Numerical computing (NOT USED)
- **scipy** - Scientific computing (NOT USED)
- **gtts** - Google Text-to-Speech
- **python-dotenv** - Environment variable management

### What Each Is Used For

- **framer-motion:** All UI animations (AnimatePresence, motion.div, etc.)
- **wavesurfer.js:** Audio waveform visualization in WavesurferPlayer
- **pydub:** Audio mixing, normalization, HPF, compression
- **Pillow:** Cover art generation
- **gtts:** Voice synthesis for AI personas
- **openai:** Lyrics generation (GPT-4o-mini)
- **fastapi/uvicorn:** Backend server
- **tailwindcss:** Utility classes (via PostCSS)

### Conflicts

- **moviepy, librosa, soundfile, spotipy, numpy, scipy:** Listed in requirements but **NOT USED** in code
- **Potential conflict:** Multiple audio libraries (pydub, librosa, soundfile) but only pydub is used

---

## 9. MAJOR TECHNICAL BOTTLENECKS

### 1. **No Automatic Stage Completion**
- **Impact:** Progress never tracks, workflow state never advances
- **Bottleneck:** Every stage component has `completeStage` prop but **NEVER CALLS IT**
- **Fix Complexity:** Low (add `completeStage(stageId)` call after successful API response)

### 2. **State Synchronization Issues**
- **Impact:** Frontend and backend state can drift
- **Bottleneck:** `syncProject()` only called manually, not on every state change
- **Fix Complexity:** Medium (implement automatic sync on API responses)

### 3. **Layout Architecture (Scroll Box vs Full-Screen)**
- **Impact:** Poor UX, stages feel cramped
- **Bottleneck:** CSS layout forces scroll box, not full-screen
- **Fix Complexity:** Medium (refactor CSS, add conditional rendering)

### 4. **Missing Error Handling**
- **Impact:** Silent failures, user confusion
- **Bottleneck:** API errors caught but not always displayed
- **Fix Complexity:** Low (add error state to all components)

### 5. **Voice System Debounce Cache Memory Leak**
- **Impact:** Memory usage grows over time
- **Bottleneck:** `_voice_debounce_cache` never cleared
- **Fix Complexity:** Low (add TTL or size limit)

### 6. **Demo Data Everywhere**
- **Impact:** No real functionality (analytics, content generation)
- **Bottleneck:** Hardcoded responses instead of real processing
- **Fix Complexity:** High (implement real AI/analytics)

### 7. **Disabled Features (EQ, Effects, Video Editor)**
- **Impact:** Limited functionality, user frustration
- **Bottleneck:** UI exists but backend not implemented
- **Fix Complexity:** High (implement audio processing, video editing)

### 8. **No Intent Router Integration**
- **Impact:** Voice commands cannot route to backend
- **Bottleneck:** `intent_router.py` exists but not wired
- **Fix Complexity:** Medium (wire up endpoint, test routing)

### 9. **Timeline Always Visible**
- **Impact:** Cluttered UI, stages feel secondary
- **Bottleneck:** Timeline never hides when stage active
- **Fix Complexity:** Low (add conditional rendering)

### 10. **MistLayer Glow Not Moving**
- **Impact:** Visual feedback broken
- **Bottleneck:** `activeStage` not updated on completion
- **Fix Complexity:** Low (fix state flow)

---

## 10. STRUCTURED DOCUMENT SUMMARY

### Architecture Overview
- **Stack:** FastAPI + React + Vite
- **State:** React hooks + localStorage + ProjectMemory (JSON files)
- **Communication:** RESTful API with standardized responses
- **Storage:** Local filesystem (`./media/{session_id}/`)

### Frontend (React) Breakdown
- **Root:** `App.jsx` orchestrates all components
- **Stages:** 6 stage components (Beat, Lyrics, Upload, Mix, Release, Content) + Analytics overlay
- **Navigation:** Timeline component with progress tracking
- **Voice:** useVoice hook + VoiceControl + VoiceChat components
- **State:** Props drilling (no Context API)

### Backend (FastAPI) Breakdown
- **Entry:** `main.py` contains all endpoints
- **Memory:** `ProjectMemory` class manages `project.json` files
- **Services:** CoverArtGenerator, AnalyticsEngine, SocialScheduler (all local, no external APIs except Beatoven/OpenAI)
- **Audio:** pydub for mixing, gTTS for voice synthesis

### Module-by-Module Analysis
- **Beat:** Beatoven API with fallback → `beat.mp3`
- **Lyrics:** OpenAI GPT-4o-mini with fallback → `lyrics.txt` + voice preview
- **Upload:** Multipart file upload → `stems/` directory
- **Mix:** pydub processing → `mix.wav` + `master.wav`
- **Release:** Pillow cover art + ZIP creation → `cover.jpg` + `release_pack.zip`
- **Content:** Demo captions (hardcoded) → scheduling UI (disabled)
- **Analytics:** Demo metrics (hardcoded) → stats display

### State Flow & Stage Management
- **Current Stage:** Stored in `App.jsx` state + `project.json`
- **Completed Stages:** Array in `App.jsx` + `project.json`
- **Active Stage:** Which UI is open (set on click)
- **Issue:** Stages never call `completeStage()`, so progress never advances

### UI/UX Behavior Analysis
- **Layout:** Stages render in scroll box below timeline (NOT full-screen)
- **Timeline:** Always visible, centered overlay (z-index 20)
- **Glow:** MistLayer position only updates on manual click, not on completion
- **Progress:** Static (0% because stages never complete)

### AI/Audio Processing Logic
- **Beat:** Beatoven API (async polling) or demo fallback
- **Lyrics:** OpenAI GPT-4o-mini or static fallback
- **Voice:** gTTS with 10s debounce + SHA256 cache
- **Mix:** pydub (HPF, compression, normalize, overlay)
- **Content:** **HARDCODED DEMO** (no AI)
- **Analytics:** **DEMO METRICS** (no real tracking)

### Missing Features
1. Stage completion automation
2. Full-screen stage views
3. EQ/Effects processing (UI disabled)
4. Video editor (tab hidden)
5. Social scheduling (button disabled)
6. Auphonic mastering (TODO)
7. Intent router integration
8. Reference engine integration
9. Real content generation (demo only)
10. Real analytics tracking (demo only)

### Known Bugs & Weaknesses
1. **Stages never complete** → Progress bar stuck at 0%
2. **Glow doesn't move** → Visual feedback broken
3. **Stages in scroll box** → Poor UX
4. **Timeline always visible** → Cluttered UI
5. **Voice debounce memory leak** → Memory grows over time
6. **Missing error handling** → Silent failures
7. **State sync issues** → Frontend/backend drift
8. **Z-index conflicts** → UI overlap issues

### Performance Issues
1. **Voice cache never cleared** → Memory leak
2. **Project data only loads on mount** → Stale data
3. **No API response caching** → Redundant calls
4. **Large audio files in memory** → Potential memory issues

### Technical Debt
1. **Unused dependencies** (moviepy, librosa, soundfile, spotipy, numpy, scipy)
2. **Hardcoded demo data** (content, analytics)
3. **Disabled UI features** (EQ, effects, video editor)
4. **Missing backend integrations** (Auphonic, intent router, reference engine)
5. **No Context API** → Props drilling everywhere
6. **No error boundaries** in stage components (only root)
7. **No loading states** in some components
8. **No TypeScript** → Type safety missing

### Dependencies
- **Frontend:** React 18.2.0, framer-motion 11.0.0, wavesurfer.js 7.7.3, Tailwind CSS 3.4.0
- **Backend:** FastAPI, pydub, Pillow, gtts, openai, requests
- **Unused:** moviepy, librosa, soundfile, spotipy, numpy, scipy

### Everything That Needs Fixing

#### Critical (Blocks Core Functionality)
1. **Stage completion not triggered** → Add `completeStage()` calls
2. **Progress bar stuck** → Fix completion tracking
3. **Glow doesn't move** → Fix state flow on completion
4. **Stages in scroll box** → Refactor CSS to full-screen

#### High Priority (Major UX Issues)
5. **Timeline always visible** → Hide when stage active
6. **Missing error handling** → Add error states everywhere
7. **State sync issues** → Auto-sync on API responses
8. **Z-index conflicts** → Fix layering

#### Medium Priority (Feature Completeness)
9. **Demo data everywhere** → Implement real AI/analytics
10. **Disabled features** → Implement EQ/effects/video
11. **Social scheduling disabled** → Wire up backend
12. **Intent router not wired** → Integrate endpoint

#### Low Priority (Polish)
13. **Voice cache memory leak** → Add TTL
14. **Missing transitions** → Add animations
15. **Mobile responsiveness** → Improve breakpoints
16. **Unused dependencies** → Remove from requirements.txt

---

## END OF BRIEFING

**Note:** This is a diagnostic document only. No fixes have been applied. All issues identified are based on code analysis and require verification through testing.

