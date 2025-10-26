# Docker Image Version Management

## Overview

Silent Scribe uses a version management system to ensure users always have the correct Docker image for the Electron app they're running. This is critical for air-gapped deployments where automatic updates aren't possible.

## How It Works

### 1. **Version Metadata in Docker Image**

When building the Docker image, version information is embedded as OCI labels:

```dockerfile
LABEL org.opencontainers.image.version="${IMAGE_VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
```

The build script (`scripts/build.sh`) automatically pulls the version from `package.json`:

```bash
IMAGE_VERSION=$(grep '"version":' package.json | head -1 | sed 's/.*"version": "\(.*\)".*/\1/')
```

### 2. **Expected Version Manifest**

The Electron app contains `electron/image-version.json` which specifies:

```json
{
  "expectedVersion": "0.1.0",
  "description": "Expected Docker image version for this Electron app release",
  "updateInstructions": "A new Docker image is bundled with this update. Please load it to get the latest models and features."
}
```

### 3. **Version Check on Startup**

When the Electron app starts, it:

1. Checks if the Docker image exists
2. Reads the image's version label
3. Compares with the expected version in `image-version.json`
4. If mismatch → Prompts user to load the new image

### 4. **User Experience**

**Scenario A: Up-to-date image**
- ✅ App starts normally
- Container launches
- User can transcribe

**Scenario B: Outdated image (version mismatch)**
- ⚠️ App detects version mismatch
- Shows: "Current: 0.1.0, Expected: 0.2.0"
- Options:
  - **"Load New Image"** - Loads bundled image from app resources
  - **"Continue with Current Version"** - Proceeds anyway (not recommended)

**Scenario C: No version label (old image built before versioning)**
- ⚠️ Detected as outdated
- Prompts to load new image

---

## Workflow for Releasing Updates

### When to Bump Version

**Increment version when:**
- ✅ New AI models added
- ✅ Backend API changes
- ✅ Python dependencies updated
- ✅ Whisper/Llama engines updated

**No version bump needed for:**
- ⭕ Electron UI changes only
- ⭕ Documentation updates
- ⭕ Bug fixes in Electron wrapper

### Release Process

#### Step 1: Update Version

Edit `package.json`:
```json
{
  "version": "0.2.0"
}
```

Edit `electron/image-version.json`:
```json
{
  "expectedVersion": "0.2.0",
  "updateInstructions": "This update includes improved Whisper models and bug fixes. Please load the new image."
}
```

#### Step 2: Build Docker Image

```bash
./scripts/build.sh
```

This automatically:
- Reads version from `package.json`
- Embeds it as Docker labels
- Builds the image (~27 GB)

#### Step 3: Export Docker Image

```bash
npm run image:save
```

Creates `resources/silent-scribe.tar.gz` (~15-20 GB compressed)

#### Step 4: Build Electron App

```bash
# Linux
npm run dist:linux

# macOS (via GitHub Actions)
npm run dist:mac

# Windows (via GitHub Actions)
npm run dist:win
```

The bundled image (`resources/silent-scribe.tar.gz`) is automatically included in the app package via `electron-builder` configuration.

#### Step 5: Distribute

**For macOS users:**
- Upload `.dmg` to GitHub Releases or distribution server
- Users download and install
- On first run, app detects old image and prompts to load new one
- **User data is preserved** (in `~/Library/Application Support/silent-scribe/`)

**For Linux users:**
- Upload `.AppImage` and `.deb` files
- Same behavior as macOS

**For Windows users:**
- Upload `.exe` installer
- Same behavior as macOS

---

## Technical Details

### Version Check Implementation

**Location:** `electron/main.js` → `ipcMain.handle('image:check-version')`

**Logic:**
1. Check if image exists
2. Query image labels: `docker image inspect silent-scribe:latest --format '{{index .Config.Labels "org.opencontainers.image.version"}}'`
3. Load expected version from `electron/image-version.json`
4. Compare versions
5. Return result to UI

### Bundle Path Resolution

**Development:**
```javascript
path.resolve(process.cwd(), 'resources', 'silent-scribe.tar.gz')
```

**Packaged App:**
```javascript
path.join(process.resourcesPath, 'resources', 'silent-scribe.tar.gz')
```

On macOS packaged app:
```
Silent Scribe.app/
  Contents/
    Resources/
      resources/
        silent-scribe.tar.gz  ← 15-20 GB here
```

### Image Loading Process

When user clicks "Load New Image":

1. App resolves bundle path
2. Checks if file exists
3. Runs: `docker load -i /path/to/silent-scribe.tar.gz`
4. Shows progress (10-20 minutes)
5. On success → Restarts startup flow
6. Launches container with new image

---

## Security Considerations

✅ **Air-gapped safe:** No internet required for updates
✅ **Version enforcement:** Users are warned about mismatches
✅ **User choice:** Can proceed with old version if needed (not recommended)
✅ **Data preservation:** User transcriptions are not affected by image updates

---

## Troubleshooting

### "Bundled image not found"

**Cause:** The `resources/silent-scribe.tar.gz` file is missing.

**Solution:**
1. Run `npm run image:save` before building the app
2. Ensure file is not excluded in `.gitignore`
3. Check `electron-builder` configuration includes `extraResources`

### "Version check fails"

**Cause:** Old image doesn't have version labels.

**Solution:** This is expected. App will prompt to load new image.

### "Image loads but container won't start"

**Cause:** Image loaded successfully but has incompatible changes.

**Solution:** Check backend logs with `docker logs silent-scribe-electron`

---

## Future Enhancements

- [ ] Delta updates (only download model changes, not full image)
- [ ] Checksum verification of bundled images
- [ ] Automatic rollback if new image fails to start
- [ ] Version history in UI ("You're 2 versions behind")
- [ ] Skip version check option in settings (for advanced users)

---

## Summary

The version management system ensures that:
1. Users always know when their Docker image is outdated
2. Updates are delivered bundled with the app (no internet needed)
3. User data is preserved across updates
4. The update process is simple and user-friendly

For air-gapped deployments, this is the only safe way to distribute model updates and backend improvements.
