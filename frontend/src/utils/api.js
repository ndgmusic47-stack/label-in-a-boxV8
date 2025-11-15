// Use backend proxy via Vite dev server
const API_BASE = '/api';

// Phase 2.2: Helper to handle standardized JSON responses {ok, data, message} or {ok, error}
const handleResponse = async (response) => {
 const result = await response.json();

 if (!result.ok) {
   // Surface backend error message or fallback to generic
   throw new Error(result.error || result.message || 'API request failed');
 }

 // Return data directly for easier consumption
 return result.data || result;
};

export const api = {
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

 uploadRecording: async (file, sessionId = null) => {
   const formData = new FormData();
   formData.append('file', file);
   if (sessionId) formData.append('session_id', sessionId);

   const response = await fetch(`${API_BASE}/recordings/upload`, {
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



  generateCoverArt: async (title, artist, sessionId) => {
    const response = await fetch(`${API_BASE}/release/generate-cover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        title,
        artist,
      }),
    });
    return handleResponse(response);
  },


 createReleasePack: async (sessionId) => {
   const response = await fetch(`${API_BASE}/release/pack`, {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       session_id: sessionId,
     }),
   });
   return handleResponse(response);
 },

  generateContent: async (title, artist, sessionId = null) => {
    const response = await fetch(`${API_BASE}/content/ideas`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        title,
        artist,
      }),
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
};