# Files to Upload for Deployment

## Changed Files (Upload These 4 Files)

### Backend
1. **`main.py`**
   - Fixed `/api/beats/create` endpoint (422 error handling, fallback to demo beats)
   - Fixed `/api/mix/run` endpoint (vocals-only mixing support)

### Frontend
2. **`frontend/src/components/stages/MixStage.jsx`**
   - Updated to allow mixing with vocals only (no beat required)

3. **`frontend/src/components/stages/LyricsStage.jsx`**
   - Added scrollable container for lyrics display

4. **`frontend/src/styles/index.css`**
   - Added `.lyrics-scroll` styles with Royal Indigo + Warm Gold scrollbar

---

## Deployment Methods

### Option 1: Render (Git-based) - RECOMMENDED

1. **Commit and push to Git:**
   ```bash
   git add main.py
   git add frontend/src/components/stages/MixStage.jsx
   git add frontend/src/components/stages/LyricsStage.jsx
   git add frontend/src/styles/index.css
   git commit -m "Fix: Beat generation 422 handling, vocals-only mixing, lyric scrolling"
   git push
   ```

2. **Render will automatically:**
   - Detect the changes
   - Run build command: `cd frontend && npm install && npm run build && cd .. && pip install -r requirements.txt`
   - Deploy the updated application

### Option 2: Manual Upload (if not using Git)

**Upload these 4 files to your server:**
- `main.py` → root directory
- `frontend/src/components/stages/MixStage.jsx` → `frontend/src/components/stages/`
- `frontend/src/components/stages/LyricsStage.jsx` → `frontend/src/components/stages/`
- `frontend/src/styles/index.css` → `frontend/src/styles/`

**Then rebuild frontend:**
```bash
cd frontend
npm install
npm run build
```

**Restart backend:**
```bash
# If using systemd
sudo systemctl restart your-service-name

# If using PM2
pm2 restart your-app-name

# If running directly
# Stop current process and restart:
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Quick Checklist

- [ ] Upload `main.py` (backend fixes)
- [ ] Upload `frontend/src/components/stages/MixStage.jsx` (vocals-only mixing)
- [ ] Upload `frontend/src/components/stages/LyricsStage.jsx` (scrollable lyrics)
- [ ] Upload `frontend/src/styles/index.css` (scrollbar styling)
- [ ] Rebuild frontend (if manual deployment)
- [ ] Restart backend server
- [ ] Test `/api/beats/create` endpoint
- [ ] Test `/api/mix/run` with vocals only
- [ ] Verify lyrics scroll in UI

---

## No Other Files Changed

These are the ONLY 4 files that were modified. No other files need to be uploaded.

