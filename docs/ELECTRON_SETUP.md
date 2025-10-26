# Electron App Development Setup

This guide covers how to develop, test, and package the Silent Scribe Electron application.

---

## Prerequisites

### Required Software

1. **Docker** (version 20.10+)
   - **Linux**: Docker Engine or Docker Desktop
   - **macOS**: Docker Desktop
   - **Windows**: Docker Desktop with WSL2

2. **Node.js** (version 20+)
   ```bash
   node --version  # Should be v20 or higher
   ```

3. **npm** (comes with Node.js)
   ```bash
   npm --version
   ```

### Optional Tools

- **pigz** - Faster compression for image export
  ```bash
  # Fedora/RHEL
  sudo dnf install pigz
  
  # Ubuntu/Debian
  sudo apt install pigz
  
  # macOS
  brew install pigz
  ```

---

## Project Structure

```
silent-scribe/
├── electron/                    # Electron app code
│   ├── main.js                  # Main process (IPC, Docker management)
│   ├── preload.js               # Secure IPC bridge
│   ├── splash.html              # Loading/setup UI
│   ├── docker-manager.js        # Docker CLI wrapper
│   ├── image-version.json       # Expected Docker image version
│   └── assets/                  # Icons and static assets
│       ├── icon.svg
│       ├── icon.png
│       └── README.md
├── app/                         # FastAPI backend (runs in Docker)
│   ├── backend/
│   │   ├── main.py
│   │   ├── job_manager.py
│   │   └── engines/
│   └── templates/
│       └── index.html           # Web UI
├── docker/
│   └── Dockerfile               # Multi-stage Docker build
├── scripts/
│   ├── build.sh                 # Build Docker image
│   ├── save-image.sh            # Export Docker image for bundling
│   └── run.sh                   # Run Docker container (standalone)
├── resources/                   # Large files (not in git)
│   └── silent-scribe.tar.gz    # Bundled Docker image (~15-20 GB)
├── package.json                 # npm config + electron-builder settings
└── dist/                        # Build output (AppImage, dmg, exe)
```

---

## Development Workflow

### 1. Initial Setup

Clone the repository and install dependencies:

```bash
cd silent-scribe
npm install
```

### 2. Build Docker Image

Build the Docker image with all models bundled:

```bash
./scripts/build.sh
# or
make build
```

**Time:** 30-60 minutes (one-time)  
**Disk space:** ~27 GB

This creates the `silent-scribe:latest` Docker image with version metadata embedded from `package.json`.

### 3. Run in Development Mode

Start the Electron app in development mode:

```bash
npm run dev
```

**What happens:**
1. Splash window opens
2. Checks Docker status
3. Checks for image (uses existing `silent-scribe:latest`)
4. Verifies image version
5. Starts container (`silent-scribe-electron`)
6. Opens main window at `http://localhost:7860`

**Development features:**
- Uses project `data/` directory for transcriptions
- Loads image from `resources/silent-scribe.tar.gz` if needed
- Can build from source if no image available
- Hot-reload not supported (Electron limitation)

### 4. Test Changes

After modifying Electron code:

```bash
# Quit the app (Ctrl+C or close window)
npm run dev  # Restart
```

After modifying backend code:

```bash
# Rebuild Docker image
./scripts/build.sh

# Restart Electron app
npm run dev
```

---

## Building for Distribution

### Step 1: Export Docker Image

Create the bundled image file:

```bash
npm run image:save
# or
./scripts/save-image.sh
```

**Output:** `resources/silent-scribe.tar.gz` (~15-20 GB compressed)

**Time:** 5-15 minutes

**Note:** This file is **not tracked by git** (in `.gitignore`). It must be created before packaging.

### Step 2: Package the App

#### Linux (on Linux)

```bash
npm run dist:linux
```

**Output:**
- `dist/Silent Scribe-0.1.0-linux-x64.AppImage` (~15-20 GB)
- `dist/Silent Scribe_0.1.0_amd64.deb` (~15-20 GB)

#### macOS (requires macOS or CI)

```bash
npm run dist:mac
```

**Output:**
- `dist/Silent Scribe-0.1.0-mac-arm64.dmg` (Apple Silicon)
- `dist/Silent Scribe-0.1.0-mac-x64.dmg` (Intel)

#### Windows (requires Windows or CI)

```bash
npm run dist:win
```

**Output:**
- `dist/Silent Scribe-0.1.0-win-x64.exe`

### Step 3: Test Packaged Build

#### Linux

```bash
# AppImage (portable)
chmod +x dist/*.AppImage
./dist/*.AppImage

# .deb (system install)
sudo dpkg -i dist/*.deb
silent-scribe
```

#### macOS

```bash
# Mount DMG and drag to Applications
open dist/*.dmg
```

#### Windows

```bash
# Run installer
dist\*.exe
```

---

## Environment Variables

### Build-time

Set in `.env` file (not committed):

```bash
# Optional: For speaker diarization model download
HF_TOKEN=your_huggingface_token
```

### Runtime

Set by Electron app automatically:

- `NODE_ENV=development` - Dev mode flag
- `HF_HUB_OFFLINE=1` - Offline mode for Hugging Face
- `TRANSFORMERS_OFFLINE=1` - Offline mode for transformers

---

## Path Resolution

The app uses different paths in dev vs packaged mode:

### Development Mode

```javascript
// Docker image bundle
resources/silent-scribe.tar.gz

// User data
data/uploads/
data/results/
```

### Packaged Mode

```javascript
// Docker image bundle (macOS example)
Silent Scribe.app/Contents/Resources/resources/silent-scribe.tar.gz

// User data
~/Library/Application Support/silent-scribe/data/  // macOS
~/.config/silent-scribe/data/                      // Linux
%APPDATA%\silent-scribe\data\                      // Windows
```

---

## Debugging

### Enable Electron DevTools

Edit `electron/main.js`:

```javascript
// In createSplashWindow() or createMainWindow()
splashWindow.webContents.openDevTools();
```

### View Container Logs

```bash
docker logs silent-scribe-electron
```

### Check Container Status

```bash
docker ps -a | grep silent-scribe
```

### View Electron Console

```bash
npm run dev
# Console output shows main process logs
```

### Common Issues

#### "Docker not running"

**Solution:**
```bash
# Linux
systemctl --user start docker-desktop
# or
sudo systemctl start docker

# macOS
open -a Docker

# Windows
start "Docker Desktop"
```

#### "Image not found"

**Solution:**
```bash
./scripts/build.sh
```

#### "Port 7860 already in use"

The app auto-detects and uses next available port (7861, 7862, etc.)

#### "Bundled image not found" during packaging

**Solution:**
```bash
npm run image:save
npm run dist:linux
```

---

## electron-builder Configuration

Located in `package.json` under `"build"`:

### Key Settings

```json
{
  "build": {
    "asar": true,                    // Package app code
    "asarUnpack": ["resources/**"],  // Keep resources outside asar
    "extraResources": [              // Bundle Docker image
      {
        "from": "resources",
        "to": "resources",
        "filter": ["**/*", "!models/**"]
      }
    ]
  }
}
```

### Why `extraResources`?

- Docker image is too large for asar archive
- Must be accessible as a file (not in-memory)
- Placed outside main app bundle

---

## Version Management

See [VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md) for full details.

### Quick Reference

**Update version:**

1. Edit `package.json`:
   ```json
   {
     "version": "0.2.0"
   }
   ```

2. Edit `electron/image-version.json`:
   ```json
   {
     "expectedVersion": "0.2.0"
   }
   ```

3. Rebuild Docker image (version auto-embedded):
   ```bash
   ./scripts/build.sh
   ```

4. Export and package:
   ```bash
   npm run image:save
   npm run dist:linux
   ```

---

## Security Best Practices

✅ **Implemented:**

- Context isolation enabled
- Node integration disabled
- Sandbox enabled
- Content Security Policy in splash.html
- IPC input validation
- Single instance lock
- External links open in browser

⚠️ **Additional considerations:**

- Don't commit `.env` with tokens
- Don't bundle unnecessary files
- Verify Docker image checksums (future enhancement)

---

## Performance Tips

### Faster Development

1. **Keep Docker image loaded** - Don't delete between sessions
2. **Use pigz** - Faster image compression
3. **SSD recommended** - Docker image I/O is intensive

### Faster Builds

1. **Build once, distribute** - Use CI to build for all platforms
2. **Layer caching** - Docker caches intermediate layers
3. **Parallel builds** - Use GitHub Actions matrix

---

## Troubleshooting Packaging

### Linux Packaging Issues

**Problem:** AppImage won't run on older distros

**Solution:** Target older glibc version or use electron-builder's `--linux target=dir` for manual packaging

**Problem:** .deb conflicts with existing packages

**Solution:** Increment version number or use `dpkg --force-overwrite`

### macOS Packaging Issues

**Problem:** "App is damaged" on macOS

**Solution:** Requires code signing (see DISTRIBUTION.md)

**Problem:** Can't build .dmg on Linux

**Solution:** Use GitHub Actions with macOS runner

### Windows Packaging Issues

**Problem:** Windows Defender flags .exe

**Solution:** Code signing required for production (see DISTRIBUTION.md)

---

## Next Steps

- [Distribution Workflow](DISTRIBUTION.md) - How to release
- [Version Management](VERSION_MANAGEMENT.md) - Update strategy
- [Testing Checklist](TEST_CHECKLIST.md) - Manual testing guide
- [GitHub Actions Setup](../.github/workflows/build.yml) - CI/CD

---

## Support

For development questions:
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Review [WARP.md](WARP.md) for project conventions
3. Check existing GitHub Issues
4. Create new issue with debug logs
