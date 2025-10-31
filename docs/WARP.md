# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common Commands

### Build Docker Image
```bash
make build
# or
./scripts/build.sh
```
**Note:** Takes 30-60 minutes and requires ~15-20 GB disk space. Downloads all AI models. Only needs to be done once.

### Run Container
```bash
make run
# or
./scripts/run.sh
```
Starts the application at **http://localhost:7860** with `--network none` (completely offline).

### Stop Container
```bash
make stop
# or
./scripts/stop.sh
# or
Ctrl+C
```

### Clean Image
```bash
make clean
```
Removes the Docker image.

### Verify Health
```bash
curl http://localhost:7860/health
```

### View Logs
```bash
docker logs silent-scribe
```

### Verify Network Isolation
```bash
docker inspect silent-scribe | grep NetworkMode
# Should show: "NetworkMode": "none"
```

## Development Context

This is a **security-first, air-gapped video transcription system** designed for sensitive data:

- **Completely offline at runtime**: Container runs with `--network none`, zero internet access
- **All models bundled**: 10 AI models (5 sizes × 2 engines) pre-downloaded at build time (~15-20 GB)
- **Single Docker container**: Designed for distribution via flash drive (load pre-built image, run immediately)
- **Cross-platform**: Works on Mac (Intel & Apple Silicon) and Linux

## High-Level Architecture

### Backend
- **FastAPI + Uvicorn** (single worker) listening on port 7860
- **Single-process design**: `--workers 1` to prevent resource conflicts

### Dual Engine System
Two transcription engines with a shared abstraction:

1. **faster-whisper** (CTranslate2-based)
   - Better progress tracking
   - CPU-optimized
   - Recommended default

2. **whisper.cpp** (GGML-based)
   - Faster on Apple Silicon
   - Compiled at build time for target architecture

**Engine Interface** (`app/backend/engines/`):
```python
transcribe(
    audio_path: Path,
    output_dir: Path,
    model: str,
    settings: Dict[str, Any],
    progress_callback: Callable[[int], None]
) -> Dict[str, Path]  # Returns {format: file_path} for txt, srt, vtt
```

### Job Management
- **Single-job processing**: `JobManager` (in `job_manager.py`) enforces only one transcription at a time using an asyncio lock
- **Job state**: Stored in `/data/results/<job_id>/job.json` with status, progress, and result file paths
- **Background tasks**: Transcriptions run via `asyncio.create_task()` to avoid blocking API

### Progress Tracking
Progress flows through the system via callbacks:
```
Engine → JobManager → API → Frontend
```

- **faster-whisper**: Progress calculated from audio duration vs segment end time
- **whisper.cpp**: Progress estimated from stdout parsing (timestamps in output)

### Audio Pipeline
```
Video file → ffmpeg extraction → 16 kHz mono WAV → Whisper engine → TXT/SRT/VTT outputs
```

### Air-Gap Security Model
- **Build time**: Network access allowed for model downloads only
- **Runtime**: 
  - `--network none` flag on container
  - Environment: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`
  - All models pre-loaded under `/opt/models/`
  - No CDN dependencies in web UI

## Key Code Locations

- `app/backend/main.py` — FastAPI routes and background processing
- `app/backend/config.py` — Configuration and available options (models, engines, compute types)
- `app/backend/job_manager.py` — Single-job locking and job state management
- `app/backend/engines/faster_whisper_engine.py` — CTranslate2 engine adapter
- `app/backend/engines/whisper_cpp_engine.py` — GGML engine adapter
- `docker/Dockerfile` — Multi-stage build (base → whisper.cpp → models → runtime)
- `scripts/fetch_models.py` — Downloads all models at build time

## Important Patterns

### Single-Job Processing
Only one transcription can run at a time. The `JobManager` uses an asyncio lock to enforce this:
```python
async with self._lock:
    if self.current_job and self.current_job.status == "processing":
        return None  # Busy
```

This prevents resource exhaustion on systems with limited RAM/CPU.

### Background Tasks
Transcriptions are scheduled as background tasks to keep the API responsive:
```python
asyncio.create_task(process_transcription(...))
```

### Progress Estimation
- **faster-whisper**: Tracks segment timestamps against total audio duration
- **whisper.cpp**: Parses progress indicators from stdout (e.g., `[00:00:10.000 --> 00:00:12.000]`)

### Air-Gap Security
- **Build time**: Network access for downloading models from Hugging Face
- **Runtime**: 
  - Container runs with `--network none`
  - Offline environment variables prevent any network calls
  - Models loaded from local `/opt/models/` directories

## Model Information

### Available Sizes
- **tiny** (~75 MB) - Fastest, lowest quality
- **base** (~150 MB) - Fast, decent quality
- **small** (~500 MB) - **Default** - Good balance
- **medium** (~1.5 GB) - Slower, better quality
- **large-v3** (~3 GB) - Slowest, best quality

### Storage Layout
- **faster-whisper**: `/opt/models/faster_whisper/<size>/` (CTranslate2 format)
- **whisper.cpp**: `/opt/models/whisper_cpp/<size>/*.bin` (GGML format)

### Default Configuration
- Model: `small`
- Compute type: `int8_float16`
- Threads: Auto-detected from CPU cores

## Data Flow

1. **Upload**: Video saved to `/data/uploads/<job_id>_<filename>`
2. **Audio extraction**: Extracted to `/data/results/<job_id>/audio.wav` (16 kHz mono)
3. **Transcription**: Outputs written to `/data/results/<job_id>/`:
   - `transcript.txt` - Plain text
   - `transcript.srt` - SubRip subtitles
   - `transcript.vtt` - WebVTT subtitles
4. **Cleanup**: On completion or failure, original upload and `audio.wav` are deleted

## Testing Notes

- **No test suite**: The `tests/` directory is currently empty
- **Manual testing**: Use the web UI at http://localhost:7860
- **API testing**: Hit endpoints directly (see `app/backend/main.py` for routes):
  - `GET /api/config` - Get available options
  - `POST /api/transcribe` - Start transcription
  - `GET /api/jobs/<job_id>/status` - Check job status
  - `GET /api/jobs/<job_id>/result.<format>` - Download results
  - `GET /api/history` - List recent jobs

## UI Development & Testing

### Frontend Stack
- **Location**: `app/templates/index.html` (single-file HTML/CSS/JS)
- **Icons**: Lucide icons loaded via CDN (`https://unpkg.com/lucide@latest`)
- **Styling**: CSS custom properties (CSS variables) for theming
- **State Management**: Vanilla JavaScript with localStorage persistence

### UI Update Workflow

#### 1. Making Changes
Edit `app/templates/index.html` directly. The file contains:
- HTML structure
- Embedded `<style>` block (CSS)
- Embedded `<script>` block (JavaScript)

#### 2. Building & Testing Changes
**CRITICAL**: Docker caching can prevent UI updates from appearing. Always use `--no-cache` flag:

```bash
# Stop existing container
docker stop silent-scribe
docker rm silent-scribe

# Rebuild image WITHOUT cache (forces UI changes to be picked up)
docker build --no-cache -t silent-scribe:latest -f docker/Dockerfile .

# Start fresh container
docker run -d --name silent-scribe --network none -p 7860:7860 -v silent-scribe-data:/data silent-scribe:latest

# Wait a few seconds for startup
sleep 3

# Verify container is running
docker logs silent-scribe --tail 10

# Test health endpoint
curl -s http://localhost:7860/health | jq .
```

#### 3. Verification Checklist
After rebuilding, **always** verify these before testing UI:

```bash
# 1. Check container is running
docker ps | grep silent-scribe
# Should show: STATUS = Up X seconds

# 2. Verify health endpoint
curl -s http://localhost:7860/health
# Should return: {"status":"ok","summarization_available":false}

# 3. Check frontend loads
curl -s http://localhost:7860/ | head -n 20
# Should return HTML with <!DOCTYPE html>

# 4. Verify network isolation (air-gapped mode)
docker inspect silent-scribe | grep -A 3 NetworkMode
# Should show: "NetworkMode": "none"
```

#### 4. Browser Testing
1. Open **http://localhost:7860** in browser
2. **Hard refresh** to bypass browser cache:
   - Chrome/Edge: `Ctrl+Shift+R` (Linux/Win) or `Cmd+Shift+R` (Mac)
   - Firefox: `Ctrl+F5` or `Cmd+Shift+R`
3. Check browser console (F12) for JavaScript errors
4. Verify all UI elements render correctly

### Common UI Testing Scenarios

#### Test 1: Visual Appearance
- [ ] Color scheme matches design (slate backgrounds, amber accents)
- [ ] Typography is readable and properly sized
- [ ] Spacing and padding look balanced
- [ ] Icons load correctly (Lucide)
- [ ] Hover effects work on buttons/tabs
- [ ] Focus states visible on form inputs

#### Test 2: File Upload
- [ ] Click upload zone → file picker opens
- [ ] Drag and drop file → border highlights
- [ ] File selected → name and size display
- [ ] Transcription title auto-fills with filename

#### Test 3: Settings & Controls
- [ ] Engine dropdown works (faster-whisper, whisper.cpp)
- [ ] Model selection updates
- [ ] Compute type visible only for faster-whisper
- [ ] Threads slider updates value display
- [ ] Language dropdown functional
- [ ] Speaker detection checkbox toggles

#### Test 4: Tab Navigation
- [ ] Tabs switch correctly (Transcribe, History, Models)
- [ ] Active tab visually distinct
- [ ] Tab content loads properly
- [ ] Back button works between tabs

#### Test 5: Models Tab
- [ ] Models list loads
- [ ] Disk usage displays
- [ ] Download buttons work (if offline mode off)
- [ ] Delete buttons work (except tiny)
- [ ] Badges show correct install status

#### Test 6: History Tab
- [ ] History loads past transcriptions
- [ ] Search filters by filename/content
- [ ] Collapse/Expand all works
- [ ] Format tabs (TXT/SRT/VTT) switch
- [ ] Download links work
- [ ] Delete individual items works

#### Test 7: Transcription Flow
- [ ] Upload file → settings persist from localStorage
- [ ] Start transcription → progress bar animates
- [ ] Status messages update during processing
- [ ] Completion → results display
- [ ] Download links functional
- [ ] Preview shows transcript text

### Debug Tips

#### UI Not Updating After Rebuild?
**Cause**: Docker layer caching kept old `index.html`

**Solution**:
```bash
# Force rebuild without cache
docker build --no-cache -t silent-scribe:latest -f docker/Dockerfile .

# Or clean everything and rebuild
docker stop silent-scribe
docker rm silent-scribe
docker rmi silent-scribe:latest
make build
```

#### Browser Shows Old UI?
**Cause**: Browser cache

**Solution**:
1. Hard refresh: `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)
2. Clear browser cache completely
3. Try incognito/private window

#### Icons Not Showing?
**Cause**: Lucide CDN not loading or icons not initialized

**Solution**:
1. Check browser console for network errors
2. Verify `<script src="https://unpkg.com/lucide@latest"></script>` in HTML head
3. Confirm `lucide.createIcons()` called in JavaScript
4. Check air-gapped mode doesn't block CDN (it shouldn't for initial load)

#### JavaScript Errors?
**Cause**: Syntax error or undefined variable

**Solution**:
1. Open browser console (F12)
2. Look for red error messages
3. Check line numbers in `index.html` `<script>` section
4. Verify all function definitions and variable declarations

#### Settings Not Persisting?
**Cause**: localStorage issues

**Solution**:
```javascript
// Check in browser console
localStorage.getItem('silentScribe.settings')

// Clear if corrupted
localStorage.removeItem('silentScribe.settings')

// Verify settings save
// (change a setting, refresh page, check if persisted)
```

### Performance Testing

#### Page Load Speed
```bash
# Measure page load time
curl -w "@-" -o /dev/null -s http://localhost:7860/ <<'EOF'
    time_namelookup:  %{time_namelookup}s
       time_connect:  %{time_connect}s
    time_appconnect:  %{time_appconnect}s
   time_pretransfer:  %{time_pretransfer}s
      time_redirect:  %{time_redirect}s
 time_starttransfer:  %{time_starttransfer}s
                    ----------
         time_total:  %{time_total}s
EOF
```

#### Memory Usage
```bash
# Check container memory consumption
docker stats silent-scribe --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

### Current UI Design (as of 2025-10-31)

**Theme**: Professional light theme with slate/amber color scheme (recording studio aesthetic)

**Design Philosophy**:
- Clean, calm, professional appearance
- No gradients or pulsing animations
- Subtle hover states and transitions
- Consistent spacing and border radius
- Scalable SVG icons throughout

**Color Palette** (CSS Custom Properties):
```css
--slate-900: #0f172a;  /* Primary text */
--slate-800: #1e293b;
--slate-700: #334155;  /* Secondary text */
--slate-600: #475569;
--slate-500: #64748b;  /* Muted text, inactive tabs */
--slate-400: #94a3b8;
--slate-300: #cbd5e1;  /* Borders */
--slate-200: #e2e8f0;  /* Light borders */
--slate-100: #f1f5f9;  /* Light backgrounds */
--slate-50: #f8fafc;   /* Body background */

--amber-600: #d97706;  /* Primary buttons, active tabs */
--amber-500: #f59e0b;  /* Hover states, accents */
--amber-400: #fbbf24;

--red-600: #dc2626;    /* Delete buttons, errors */
--green-600: #16a34a;  /* Success states */
--blue-600: #2563eb;   /* Info states */
```

**Color Usage Guidelines**:
- **Backgrounds**: White containers on slate-50 body, slate-50/100 for secondary surfaces
- **Text**: Slate-900 for primary, slate-700 for labels, slate-500/600 for muted
- **Borders**: Slate-200/300 for standard borders
- **Primary Actions**: Amber-600 background, amber-500 on hover
- **Secondary Actions**: White background with slate-300 border
- **Destructive Actions**: Red-600 background
- **Active States**: Amber-600 for tabs, slider thumbs, focus rings

**Typography**:
- Font stack: `-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif`
- Heading: 36px, weight 700, slate-900
- Subtitle: 16px, weight 400, slate-600
- Body: 14-15px, slate-900
- Labels: 13px, weight 600, slate-700

**Spacing & Layout**:
- Container: max-width 1000px, padding 48px, border-radius 12px
- Buttons: padding 12px 24px (primary), 8px 16px (small)
- Border radius: 6px (buttons, inputs), 8px (containers), 12px (main container)
- Gap: 6px (inline icons), 12px (section spacing)

**Icons System** (Lucide v0.x):
- **CDN**: `https://unpkg.com/lucide@latest`
- **License**: MIT
- **Format**: SVG via `data-lucide` attributes
- **Initialization**: `lucide.createIcons()` after DOM updates
- **Sizing**: 14-16px (inline), 18-24px (headings), 36-48px (large displays)

**Icon Usage Map**:
```javascript
// Branding & Navigation
'mic-off'         → Silent Scribe logo
'video'           → Transcribe tab
'book-open'       → History tab
'brain'           → Models tab

// Actions
'upload'          → File upload zone
'download'        → Download links
'trash-2'         → Delete actions
'refresh-cw'      → Refresh/retry
'sparkles'        → AI summary generation

// Status & Indicators
'check-circle'    → Success/completed/installed
'x-circle'        → Error/failed/not installed
'clock'           → Processing/pending
'alert-circle'    → Warning/error message
'lock'            → Air-gapped mode active
'globe'           → Internet enabled

// UI Controls
'chevron-down'    → Expanded state
'chevron-right'   → Collapsed state
'chevrons-up'     → Collapse all
'chevrons-down'   → Expand all

// Content Types
'file-text'       → Text format
'file-video'      → Video file
'film'            → SRT/VTT subtitle formats
'list'            → Bullet points
'users'           → Speaker detection

// Processing
'cpu'             → Model loading
'mic'             → Transcribing audio
'loader'          → Generic loading (with spin animation)
'info'            → Information notice
```

**Animation Guidelines**:
- Use `animation: spin 1s linear infinite` for loading indicators only
- Transitions: 0.2s for UI interactions
- Hover effects: `translateY(-1px)` for buttons
- NO pulsing, NO gradients, NO complex animations

**Tab Navigation Design**:
- Transparent background, clean underline for active tab
- Slate-500 inactive, amber-600 active
- 2px bottom border on active tab
- Icons inline with 6px gap

**Button Variants**:
```css
/* Primary (amber) */
background: var(--amber-600);
hover: var(--amber-500) + translateY(-1px);

/* Secondary (white) */
background: white;
border: 1px solid var(--slate-300);
hover: var(--slate-50) background;

/* Destructive (red) */
background: var(--red-600);
hover: #b91c1c + translateY(-1px);
```

**Form Controls**:
- Inputs: 1px solid slate-300 border, 6px radius
- Focus: amber-500 border + 3px rgba amber glow
- Hover: slate-400 border
- Range slider thumb: amber-500 circle, 18px

**Key Features**:
- Single-page application with tab navigation
- Drag-and-drop file upload with amber hover state
- Real-time progress tracking with amber progress bar
- Format switching (TXT/SRT/VTT) with inline icons
- Model management with download/delete
- History with search, filtering, and collapse/expand
- Settings persistence via localStorage
- Responsive design (mobile-friendly)
- All icons from Lucide library (scalable SVG)

**Accessibility**:
- ARIA labels on tabs and controls
- Focus states visible on all interactive elements
- Color contrast meets WCAG AA standards
- Icon + text labels for clarity

## Important Constraints

- **Single-process design**: Uvicorn runs with `--workers 1` to avoid concurrency issues
- **No parallel transcriptions**: Only one job at a time (enforced by JobManager lock)
- **Memory requirements**: 
  - Minimum: 8 GB RAM
  - Recommended: 16 GB RAM for larger models
- **Build time**: One-time build per machine; pre-built images can be distributed via `docker save`/`docker load`
- **Non-root user**: Application runs as `appuser` (UID 1000) for security
- **Read-only filesystem**: Only `/data` is writable at runtime

---

## Recent Development Session (2025-10-27)

### What We Did

#### 1. Created Lite Docker Image Build (2.73 GB)
**Problem**: Original Docker image was 19.1 GB (all 5 Whisper models + Llama 2 + Pyannote), causing GitHub Actions builds to fail with disk space errors.

**Solution**: 
- Modified `docker/Dockerfile` line 72 to add `--skip-optional` flag
- Now builds with only `tiny` Whisper model (~150 MB)
- Reduces image from 19.1 GB → 2.73 GB
- Successfully pushed to private GHCR: `ghcr.io/jesuscdev/offline-scribe:latest`

**Files Changed**:
- `docker/Dockerfile` - Added `--skip-optional` to fetch_models.py call

#### 2. Implemented Offline Mode Toggle
**Problem**: Users couldn't download additional models at runtime because container runs with `HF_HUB_OFFLINE=1` (air-gapped mode).

**Solution**: Added UI toggle to enable/disable offline mode with container restart
- **Backend** (`electron/main.js`, `docker-manager.js`, `preload.js`):
  - Settings persistence in `~/.config/Silent Scribe/settings.json`
  - `offlineMode` default: `true` (air-gapped)
  - Container starts with `HF_HUB_OFFLINE` env var based on setting
  - Automatic container restart when toggled
  - IPC handlers: `settings:getOfflineMode`, `settings:setOfflineMode`

- **Frontend** (`electron/splash.html`):
  - Toggle switch: "🔒 Air-Gapped Mode"
  - Clear subtitle: "Disable internet access for model downloads"
  - Feedback messages on toggle

**Usage Flow**:
1. App starts in air-gapped mode (offline = true)
2. User un-toggles to enable internet
3. Container restarts with `HF_HUB_OFFLINE=0`
4. User can download models from Hugging Face
5. Toggle back on to re-enable air-gap

**Files Changed**:
- `electron/main.js` - Settings storage, IPC handlers, container restart logic
- `electron/docker-manager.js` - Added `offlineMode` parameter to `startContainer()`
- `electron/preload.js` - Exposed settings API
- `electron/splash.html` - Added toggle UI

#### 3. Added Comprehensive Logging System
**Problem**: No way to debug user issues or track application behavior.

**Solution**: Implemented rotating file logs with UI access
- **Logger Module** (`electron/logger.js`):
  - JSON-formatted logs with timestamps and levels
  - Rotating files: 10 MB max, keeps 3 files
  - Location: `~/.config/Silent Scribe/logs/silent-scribe-YYYY-MM-DD.log`
  - Methods: `debug()`, `info()`, `warn()`, `error()`, `docker()`
  - Console + file output

- **Integration** (`electron/main.js`):
  - Logs app startup/shutdown
  - Docker operations (check, start, stop)
  - Container state changes
  - Settings changes
  - All errors captured

- **UI** (`electron/splash.html`):
  - Displays log file path
  - "Open Folder" button to access logs
  - Users can easily share logs for debugging

**Log Format Example**:
```json
{"timestamp":"2025-10-27T07:36:14.123Z","level":"INFO","message":"Silent Scribe starting","data":{"version":"0.1.0","platform":"linux"}}
```

**Files Created/Changed**:
- `electron/logger.js` - New logger module
- `electron/main.js` - Logging integration
- `electron/preload.js` - Exposed log API (`getLogPath`, `getRecentLogs`, `openPath`)
- `electron/splash.html` - Log viewer UI

#### 4. Fixed GitHub Actions Workflow Issues
**Problems Fixed**:
1. Repository name case sensitivity (jesusCDev → jesuscdev for GHCR)
2. Missing `packages: read` permission for private GHCR access
3. Deprecated `directories` field in `package.json`
4. Missing author email for `.deb` package builds
5. electron-builder auto-publish errors (added `"publish": null`)

**Files Changed**:
- `.github/workflows/build.yml` - Fixed GHCR pull, added permissions
- `package.json` - Removed deprecated fields, added author email, disabled publish

### Current Status

**Branch**: `feat/tabbed-ui-models-management`

**GitHub Actions Build**: ✅ RUNNING (triggered 2025-10-27 12:08 UTC)
- Build type: `full` (bundles 2.73 GB Docker image)
- Expected artifacts:
  - `Silent Scribe-0.1.0-mac-arm64.dmg` (~3 GB)
  - `Silent Scribe-0.1.0-linux-x86_64.AppImage` (~3 GB)
  - `Silent Scribe-0.1.0-linux-amd64.deb` (~3 GB)
  - `Silent Scribe-0.1.0-win-x64.exe` (~3 GB)

**Private Package**: `ghcr.io/jesuscdev/offline-scribe:latest` (2.73 GB, lite build)

### Testing TODO

Once the GitHub Actions build completes:

1. **Download AppImage** from artifacts
2. **Test on Fedora**:
   ```bash
   chmod +x Silent\ Scribe-0.1.0-linux-x86_64.AppImage
   ./Silent\ Scribe-0.1.0-linux-x86_64.AppImage
   ```

3. **Verify Features**:
   - ✅ App launches and shows splash screen
   - ✅ Docker image loads from bundle (bundled in AppImage)
   - ✅ Container starts successfully
   - ✅ Default: Air-gapped mode ON (offline)
   - ✅ Toggle offline mode OFF
   - ✅ Container restarts automatically
   - ✅ Download `base` model (should work now with offline mode off)
   - ✅ Toggle back ON (container restarts again)
   - ✅ Setting persists across app restarts
   - ✅ Log file created in `~/.config/Silent Scribe/logs/`
   - ✅ "Open Folder" button works
   - ✅ Logs contain all operations

4. **Test Log File Sharing**:
   - Find log file path in UI
   - Open logs folder
   - Verify logs are readable JSON
   - Confirm all major operations logged

### Known Issues / Future Work

1. **Docker container log capture**: Not yet implemented. Logs from inside the Docker container (model downloads, transcriptions) aren't automatically captured to the Electron log file.

2. **RPM packaging**: Currently builds `.deb` and AppImage for Linux. Native `.rpm` for Fedora/RHEL not yet configured (AppImage works fine on Fedora though).

3. **Model download progress UI**: Model downloads show status polling but no real-time progress bar. The backend logs progress but UI doesn't display it.

4. **Full build size**: Even with lite image (2.73 GB), the bundled installers are ~3 GB each. Consider ultra-lite version (no models bundled at all) for faster distribution.

### Next Session Starting Point

**Current state**: Waiting for GitHub Actions build to complete (check: https://github.com/jesusCDev/offline-scribe/actions)

**Next steps**:
1. Download and test the AppImage build
2. Verify offline mode toggle works end-to-end
3. Test model downloads with offline mode disabled
4. Check logs are being written properly
5. If all works, consider merging `feat/tabbed-ui-models-management` branch to main
6. Tag a release (e.g., `v0.1.0`) to create distributable packages

**Commands to resume**:
```bash
cd ~/Programming/silent-scribe
git status
gh run list --workflow build.yml --limit 5
gh run view <RUN_ID>  # Check build status
gh run download <RUN_ID> -D ./dist  # Download artifacts when complete
```
