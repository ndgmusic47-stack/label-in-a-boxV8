// Use backend proxy via Vite dev server
const API_BASE = '/api';

// Phase 2.2: Helper to handle standardized JSON responses {ok, data, message} or {ok, error}
// Phase 8.4: Preserve error data for paywall checks
const handleResponse = async (response) => {
 const result = await response.json();

 // Phase 8.4: Check for paywall errors even if response.ok is true (in case backend returns 403 but ok: false)
 if (!result.ok) {
   // Phase 8.4: For upgrade_required errors, attach full error data to error object
   const error = new Error(result.error || result.message || 'API request failed');
   if (result.error === "upgrade_required") {
     error.errorData = result;
     error.isPaywall = true;
   }
   throw error;
 }

 // Return data directly for easier consumption
 return result.data || result;
};

export const api = {
 // ========== AUTHENTICATION ==========

 authMe: async (token) => {
   const response = await fetch(`${API_BASE}/auth/me`, {
     headers: { "Authorization": `Bearer ${token}` }
   });
   return handleResponse(response);
 },

 login: async (email, password) => {
   const response = await fetch(`${API_BASE}/auth/login`, {
     method: "POST",
     headers: {"Content-Type": "application/json"},
     body: JSON.stringify({ email, password })
   });
   return handleResponse(response);
 },

 signup: async (email, password) => {
   const response = await fetch(`${API_BASE}/auth/signup`, {
     method: "POST",
     headers: {"Content-Type": "application/json"},
     body: JSON.stringify({ email, password })
   });
   return handleResponse(response);
 },

 // ========== V4 PROJECT MEMORY ==========

 listProjects: async () => {
   const response = await fetch(`${API_BASE}/projects`);
   return response.json();
 },

 getProject: async (sessionId) => {
   const response = await fetch(`${API_BASE}/projects/${sessionId}`);
   const result = await response.json();
   if (!result.ok) {
     throw new Error(result.error || 'Failed to get project');
   }
   return result.project || result;
 },

 // ========== V4 VOICE SYSTEM ==========

 getVoices: async () => {
   const response = await fetch(`${API_BASE}/voices`);
   return response.json();
 },

 // Phase 2.2: Voice endpoint uses /voices/say with persona
 voiceSpeak: async (persona, text, sessionId = null) => {
   const response = await fetch(`${API_BASE}/voices/say`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       persona,
       text,
       session_id: sessionId,
     }),
   });
   return handleResponse(response);
 },

 voiceStop: async (sessionId = null) => {
   const response = await fetch(`${API_BASE}/voices/stop`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       session_id: sessionId,
     }),
   });
   return handleResponse(response);
 },

 voicePause: async (sessionId = null) => {
   const response = await fetch(`${API_BASE}/voices/pause`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       session_id: sessionId,
     }),
   });
   return handleResponse(response);
 },

 voiceMute: async (sessionId = null) => {
   const response = await fetch(`${API_BASE}/voices/mute`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       session_id: sessionId,
     }),
   });
   return handleResponse(response);
 },

 voiceRespond: async (voiceId, message, sessionId = null) => {
   const formData = new FormData();
   formData.append('message', message);
   if (sessionId) formData.append('session_id', sessionId);

   const response = await fetch(`${API_BASE}/voices/${voiceId}/respond`, {
     method: 'POST',
     body: formData,
   });
   return response.json();
 },

 // ========== V4 REFERENCE ENGINE ==========

 analyzeReference: async (sessionId, file = null, spotifyUrl = null) => {
   const formData = new FormData();
   formData.append('session_id', sessionId);
   if (file) formData.append('file', file);
   if (spotifyUrl) formData.append('spotify_url', spotifyUrl);

   const response = await fetch(`${API_BASE}/reference/analyze`, {
     method: 'POST',
     body: formData,
   });
   return response.json();
 },

 // ========== EXISTING ENDPOINTS ==========

 createBeat: async (promptText, mood, genre = 'hip hop', sessionId = null) => {
   const body = {
     prompt: promptText,
     mood,
     genre,
     session_id: sessionId,
   };
   const response = await fetch(`${API_BASE}/beats/create`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify(body),
   });
   return handleResponse(response);
 },

 getBeatCredits: async () => {
   const response = await fetch(`${API_BASE}/beats/credits`);
   return handleResponse(response);
 },

 generateLyrics: async (genre, mood, theme = '', sessionId = null) => {
   const response = await fetch(`${API_BASE}/songs/write`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       genre,
       mood,
       theme,
       session_id: sessionId,
     }),
   });
   return handleResponse(response);
 },

 // V17: Generate lyrics from beat
 // V18.2: Accepts either File object or FormData object
 generateLyricsFromBeat: async (fileOrFormData, sessionId = null) => {
   let body = fileOrFormData instanceof FormData 
     ? fileOrFormData 
     : (() => { const fd = new FormData(); fd.append("file", fileOrFormData); return fd; })();
   
   if (sessionId) {
     body.append('session_id', sessionId);
   }
   
   const response = await fetch(`${API_BASE}/lyrics/from_beat`, {
     method: 'POST',
     body,
   });
   return handleResponse(response);
 },

 // V17: Generate free lyrics from theme
 generateFreeLyrics: async (theme) => {
   const response = await fetch(`${API_BASE}/lyrics/free`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ theme }),
   });
   return handleResponse(response);
 },

 // V18.1: Refine lyrics based on user instruction with history and metadata
 refineLyrics: async (lyricsText, instruction, bpm = null, history = [], structuredLyrics = null, rhythmMap = null) => {
   const response = await fetch(`${API_BASE}/lyrics/refine`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ 
       lyrics: lyricsText, 
       instruction, 
       bpm,
       history,
       structured_lyrics: structuredLyrics,
       rhythm_map: rhythmMap
     }),
   });
   return handleResponse(response);
 },

 uploadRecording: async (file, sessionId = null) => {
   const formData = new FormData();
   formData.append('file', file);
   if (sessionId) formData.append('session_id', sessionId);

  const response = await fetch(`${API_BASE}/upload-audio`, {
    method: 'POST',
    body: formData,
  });
   return handleResponse(response);
 },

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
  },

  // V25: Process mix and master with REAL DSP chain
  processMix: async (sessionId, file, params) => {
    const formData = new FormData();
    
    // Handle file - can be File object or URL string
    if (file instanceof File) {
      formData.append('file', file);
    } else if (typeof file === 'string') {
      // If it's a URL string, backend will fetch it
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
    
    // V25: EQ parameters
    formData.append('eq_low', params.eq_low !== undefined ? params.eq_low : 0.0);
    formData.append('eq_mid', params.eq_mid !== undefined ? params.eq_mid : 0.0);
    formData.append('eq_high', params.eq_high !== undefined ? params.eq_high : 0.0);
    
    // V25: FX parameters
    formData.append('compression', params.compression !== undefined ? params.compression : 0.5);
    formData.append('reverb', params.reverb !== undefined ? params.reverb : 0.3);
    formData.append('limiter', params.limiter !== undefined ? params.limiter : 0.8);

    const response = await fetch(`${API_BASE}/mix/process`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(response);
  },



  // NEW RELEASE MODULE ENDPOINTS
  generateReleaseCover: async (sessionId, trackTitle, artistName, genre, mood, style = 'realistic') => {
    const response = await fetch(`${API_BASE}/release/cover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        track_title: trackTitle,
        artist_name: artistName,
        genre,
        mood,
        style,
      }),
    });
    return handleResponse(response);
  },

  selectReleaseCover: async (sessionId, coverUrl) => {
    const response = await fetch(`${API_BASE}/release/select-cover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        cover_url: coverUrl,
      }),
    });
    return handleResponse(response);
  },

  listReleaseFiles: async (sessionId) => {
    const response = await fetch(`${API_BASE}/release/files?session_id=${sessionId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    const result = await handleResponse(response);
    return result.data || result;
  },

  getReleasePack: async (sessionId) => {
    const response = await fetch(`${API_BASE}/release/pack?session_id=${sessionId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(response);
  },

  generateReleaseCopy: async (sessionId, trackTitle, artistName, genre, mood, lyrics = '') => {
    const response = await fetch(`${API_BASE}/release/copy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        track_title: trackTitle,
        artist_name: artistName,
        genre,
        mood,
        lyrics,
      }),
    });
    return handleResponse(response);
  },

  generateLyricsPDF: async (sessionId, title, artist, lyrics) => {
    const response = await fetch(`${API_BASE}/release/lyrics`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        title,
        artist,
        lyrics,
      }),
    });
    return handleResponse(response);
  },

  generateReleaseMetadata: async (sessionId, trackTitle, artistName, mood, genre, explicit, releaseDate) => {
    const token = localStorage.getItem('auth_token');
    const response = await fetch(`${API_BASE}/release/metadata`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        session_id: sessionId,
        track_title: trackTitle,
        artist_name: artistName,
        mood,
        genre,
        explicit,
        release_date: releaseDate,
      }),
    });
    return handleResponse(response);
  },

  downloadAllReleaseFiles: async (sessionId) => {
    const response = await fetch(`${API_BASE}/release/download-all`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
      }),
    });
    return handleResponse(response);
  },



  // V23.1: LEGACY - Old caption generator removed
  // generateContent: async (title, artist, sessionId = null) => {
  //   const response = await fetch(`${API_BASE}/content/ideas`, {
  //     method: 'POST',
  //     headers: { 'Content-Type': 'application/json' },
  //     body: JSON.stringify({
  //       session_id: sessionId,
  //       title,
  //       artist,
  //     }),
  //   });
  //   return handleResponse(response);
  // },

  // V23: ContentStage MVP endpoints
  generateVideoIdea: async (sessionId, title, lyrics, mood, genre) => {
    const response = await fetch(`${API_BASE}/content/idea`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        title,
        lyrics,
        mood,
        genre,
      }),
    });
    return handleResponse(response);
  },

  uploadVideo: async (file, sessionId) => {
    const formData = new FormData();
    formData.append('file', file);
    if (sessionId) formData.append('session_id', sessionId);

    const response = await fetch(`${API_BASE}/content/upload-video`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(response);
  },

  analyzeVideo: async (transcript, title, lyrics, mood, genre) => {
    const response = await fetch(`${API_BASE}/content/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        transcript,
        title,
        lyrics,
        mood,
        genre,
      }),
    });
    return handleResponse(response);
  },

  generateContentText: async (sessionId, title, transcript, lyrics, mood, genre) => {
    const response = await fetch(`${API_BASE}/content/generate-text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        title,
        transcript,
        lyrics,
        mood,
        genre,
      }),
    });
    return handleResponse(response);
  },

  scheduleVideo: async (sessionId, videoUrl, caption, hashtags, platform, scheduleTime) => {
    const response = await fetch(`${API_BASE}/content/schedule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        video_url: videoUrl,
        caption,
        hashtags: hashtags || [],
        platform: platform || 'tiktok',
        schedule_time: scheduleTime,
      }),
    });
    return handleResponse(response);
  },

  saveScheduled: async (data) => {
    const response = await fetch(`${API_BASE}/content/save-scheduled`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  getScheduled: async (sessionId) => {
    const response = await fetch(`${API_BASE}/content/get-scheduled?session_id=${sessionId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse(response);
  },


 // ========== ANALYTICS ==========

 getProjectAnalytics: async (sessionId) => {
   const response = await fetch(`${API_BASE}/analytics/session/${sessionId}`);
   return handleResponse(response);
 },

 getDashboardAnalytics: async () => {
   const response = await fetch(`${API_BASE}/analytics/dashboard/all`);
   return handleResponse(response);
 },

 updateAnalytics: async (sessionId, streams = null, revenue = null, saves = null, shares = null) => {
   const formData = new FormData();
   formData.append('session_id', sessionId);
   if (streams !== null) formData.append('streams', streams);
   if (revenue !== null) formData.append('revenue', revenue);
   if (saves !== null) formData.append('saves', saves);
   if (shares !== null) formData.append('shares', shares);

   const response = await fetch(`${API_BASE}/analytics/update`, {
     method: 'POST',
     body: formData,
   });
   return response.json();
 },

 analyzeVideoBeats: async (formData) => {
   const response = await fetch(`${API_BASE}/video/analyze`, {
     method: 'POST',
     body: formData,
   });
   return response.json();
 },

 createBeatSyncVideo: async (sessionId, style = 'energetic', outputName = 'beat_sync_video.mp4') => {
   const formData = new FormData();
   formData.append('session_id', sessionId);
   formData.append('style', style);
   formData.append('output_name', outputName);

   const response = await fetch(`${API_BASE}/video/beat-sync`, {
     method: 'POST',
     body: formData,
   });
   return response.json();
 },

 exportVideo: async (sessionId, format = 'mp4', quality = 'high', resolution = null) => {
   const formData = new FormData();
   formData.append('session_id', sessionId);
   formData.append('format', format);
   formData.append('quality', quality);
   if (resolution) formData.append('resolution', resolution);

   const response = await fetch(`${API_BASE}/video/export`, {
     method: 'POST',
     body: formData,
   });
   return response.json();
 },

 getSocialPlatforms: async () => {
   const response = await fetch(`${API_BASE}/social/platforms`);
   return handleResponse(response);
 },

  schedulePost: async (sessionId, platform, caption, whenIso) => {
    const response = await fetch(`${API_BASE}/social/posts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        platform,
        caption,
        when_iso: whenIso,
      }),
    });
    return handleResponse(response);
  },


 getScheduledPosts: async (sessionId, platform = null) => {
   const url = platform
     ? `${API_BASE}/social/posts/${sessionId}?platform=${platform}`
     : `${API_BASE}/social/posts/${sessionId}`;
   const response = await fetch(url);
   return response.json();
 },

 cancelPost: async (sessionId, postId) => {
   const formData = new FormData();
   formData.append('session_id', sessionId);
   formData.append('post_id', postId);

   const response = await fetch(`${API_BASE}/social/cancel`, {
     method: 'POST',
     body: formData,
   });
   return response.json();
 },

 getOptimalTimes: async (platform, timezone = 'EST') => {
   const response = await fetch(`${API_BASE}/social/optimal-times/${platform}?timezone=${timezone}`);
   return response.json();
 },

 processIntent: async (sessionId, command) => {
   const formData = new FormData();
   formData.append('session_id', sessionId);
   formData.append('command', command);

   const response = await fetch(`${API_BASE}/intent`, {
     method: 'POST',
     body: formData,
   });
   return response.json();
 },

 // ========== SYNC PROJECT HELPER ==========
 
 syncProject: async (sessionId, updateSessionData) => {
   try {
     const project = await api.getProject(sessionId);
     if (!project) return;
     
     const updates = {};
     
     // Sync assets according to spec
     if (project.assets) {
       // Beat file from project.assets.beat.url
       if (project.assets.beat?.url) {
         updates.beatFile = project.assets.beat.url;
       }
       
       // Vocal file from project.assets.stems[0]?.url
       if (project.assets.stems && project.assets.stems.length > 0 && project.assets.stems[0]?.url) {
         updates.vocalFile = project.assets.stems[0].url;
       }
       
       // Mix file from project.assets.mix?.url
       if (project.assets.mix?.url) {
         updates.mixFile = project.assets.mix.url;
       }
       
       // Master file from project.assets.master?.url
       if (project.assets.master?.url) {
         updates.masterFile = project.assets.master.url;
       }
       
      // Cover art (optional)
      if (project.assets.cover_art?.url) {
        updates.coverArt = project.assets.cover_art.url;
      }
      
      // Release pack (optional)
      if (project.assets.release_pack) {
        updates.releasePack = project.assets.release_pack;
      }
    }
     
     // Sync metadata
     if (project.metadata) {
       if (project.metadata.mood) updates.mood = project.metadata.mood;
       if (project.metadata.genre) updates.genre = project.metadata.genre;
       if (project.metadata.track_title) updates.trackTitle = project.metadata.track_title;
       if (project.metadata.artist_name) updates.artistName = project.metadata.artist_name;
     }
     
     if (Object.keys(updates).length > 0 && updateSessionData) {
       updateSessionData(updates);
     }
     
     return updates;
   } catch (err) {
     console.error('Failed to sync project:', err);
     throw err;
   }
 },

 // ========== ADVANCE STAGE ==========
 
 advanceStage: async (sessionId) => {
   const response = await fetch(`${API_BASE}/projects/${sessionId}/advance`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
   });
   return handleResponse(response);
 },

 // ========== PROJECT SAVE/LOAD (PHASE 8.3) ==========

 saveProject: async (userId, projectId, projectData) => {
   const token = localStorage.getItem('auth_token');
   const response = await fetch(`${API_BASE}/projects/save`, {
     method: 'POST',
     headers: { 
       'Content-Type': 'application/json',
       'Authorization': `Bearer ${token}`
     },
     body: JSON.stringify({
       userId,
       projectId: projectId || null,
       projectData
     })
   });
   return handleResponse(response);
 },

 listProjects: async () => {
   const token = localStorage.getItem('auth_token');
   const response = await fetch(`${API_BASE}/projects/list`, {
     headers: { 
       'Authorization': `Bearer ${token}`
     }
   });
   return handleResponse(response);
 },

 loadProject: async (projectId) => {
   const token = localStorage.getItem('auth_token');
   const response = await fetch(`${API_BASE}/projects/load`, {
     method: 'POST',
     headers: { 
       'Content-Type': 'application/json',
       'Authorization': `Bearer ${token}`
     },
     body: JSON.stringify({ projectId })
   });
   return handleResponse(response);
 },

 // ========== BILLING (PHASE 9) ==========

 createCheckoutSession: async (userId, priceId = null) => {
   const token = localStorage.getItem('auth_token');
   const response = await fetch(`${API_BASE}/billing/create-checkout-session`, {
     method: 'POST',
     headers: { 
       'Content-Type': 'application/json',
       'Authorization': `Bearer ${token}`
     },
     body: JSON.stringify({ userId, priceId })
   });
   return handleResponse(response);
 },

 createPortalSession: async () => {
   const token = localStorage.getItem('auth_token');
   const response = await fetch(`${API_BASE}/billing/portal`, {
     method: 'POST',
     headers: { 
       'Content-Type': 'application/json',
       'Authorization': `Bearer ${token}`
     }
   });
   return handleResponse(response);
 },
};