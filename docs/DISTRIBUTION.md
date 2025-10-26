# Distribution & Release Workflow

This guide covers how to build, test, and distribute Silent Scribe to end users.

---

## Overview

Silent Scribe is distributed as:
- **Linux**: `.AppImage` (portable) and `.deb` (installable)
- **macOS**: `.dmg` (disk image with installer)
- **Windows**: `.exe` (NSIS installer)

All packages include the complete Docker image (~15-20 GB) for offline, air-gapped operation.

---

## Release Types

### 1. Full/Offline Release (Recommended)

**What:** Bundled with complete Docker image  
**Size:** 15-20 GB per platform  
**Use case:** Air-gapped deployments, no internet access  
**Distribution:** USB drive, internal network, direct download

### 2. Lite Release (Future)

**What:** App only, no Docker image bundled  
**Size:** ~100 MB  
**Use case:** Users who can build image themselves  
**Distribution:** GitHub Releases, website

**Note:** Lite builds are not currently implemented. All releases are "full" releases.

---

## Release Checklist

### Pre-Release

- [ ] All tests passing (`npm run dev` works)
- [ ] Docker image built successfully
- [ ] Version bumped in `package.json` and `electron/image-version.json`
- [ ] CHANGELOG.md updated with release notes
- [ ] Documentation updated (if needed)

### Build

- [ ] Docker image exported to `resources/silent-scribe.tar.gz`
- [ ] Electron app packaged for all platforms
- [ ] Package sizes verified
- [ ] Installation tested on clean systems

### Distribution

- [ ] Packages uploaded to distribution method
- [ ] Release notes published
- [ ] Users notified
- [ ] Support channels prepared

---

## Step-by-Step Release Process

### Step 1: Version Update

**1.1 Update package.json**

```bash
# Edit package.json
{
  "version": "0.2.0"  # Increment version
}
```

**1.2 Update image version manifest**

```bash
# Edit electron/image-version.json
{
  "expectedVersion": "0.2.0",
  "updateInstructions": "This update includes improved models and bug fixes. Please load the new image."
}
```

**1.3 Update CHANGELOG**

```bash
# Edit CHANGELOG.md
## [0.2.0] - 2025-01-15

### Added
- Feature X
- Feature Y

### Fixed
- Bug A
- Bug B
```

### Step 2: Build Docker Image

```bash
./scripts/build.sh
```

**Verify:**
```bash
docker images silent-scribe:latest
docker image inspect silent-scribe:latest --format '{{index .Config.Labels "org.opencontainers.image.version"}}'
# Should show: 0.2.0
```

**Time:** 30-60 minutes  
**Disk:** ~27 GB

### Step 3: Push Docker Image to GitHub Container Registry

**3.1 Create GitHub Personal Access Token**

First time only:
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Scopes: `write:packages`, `read:packages`
4. Save token securely

**3.2 Login to GHCR**

```bash
export GITHUB_TOKEN="your_token_here"
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

**3.3 Push Image**

```bash
npm run image:push
```

**Verify:**
- Go to: https://github.com/YOUR_USERNAME/offline-scribe/pkgs/container/offline-scribe
- Make package **public** (Settings → Change visibility)

**Time:** 10-20 minutes (uploads ~15-20 GB)  
**Required:** Once per new version

### Step 4: Build Electron Apps

#### Option A: Build Locally (Linux only)

**4.1 Export image locally:**
```bash
npm run image:save
```

**4.2 Build packages:**
```bash
npm run dist:linux
```

**Output:**
- `dist/Silent Scribe-0.2.0-linux-x64.AppImage`
- `dist/Silent Scribe_0.2.0_amd64.deb`

**Time:** 15-30 minutes total

#### Option B: Build via GitHub Actions (All platforms - Recommended)

GitHub Actions automatically pulls your pre-built image from GHCR and builds for all platforms.

See "GitHub Actions" section below.

### Step 5: Test Packages

#### Linux Testing

**AppImage:**
```bash
chmod +x dist/*.AppImage
./dist/*.AppImage
```

**Test checklist:**
- [ ] App launches without terminal
- [ ] Docker check works
- [ ] Image version matches (0.2.0)
- [ ] Container starts
- [ ] Transcription works
- [ ] App quit cleansmup container

**.deb:**
```bash
sudo dpkg -i dist/*.deb
silent-scribe
```

**Test checklist:**
- [ ] Installs without errors
- [ ] Desktop icon appears
- [ ] App launches from menu
- [ ] All functionality works
- [ ] Uninstall works: `sudo apt remove silent-scribe`

#### macOS Testing (requires Mac)

```bash
open dist/*.dmg
# Drag to Applications
# Launch from Applications
```

**Test checklist:**
- [ ] DMG mounts without warnings
- [ ] Drag-to-install works
- [ ] App launches (may show "unidentified developer" warning)
- [ ] Docker Desktop integration works
- [ ] All functionality works

#### Windows Testing (requires Windows)

```bash
dist\*.exe
# Follow installer
# Launch from Start Menu
```

**Test checklist:**
- [ ] Installer runs without warnings
- [ ] Installation completes
- [ ] Desktop shortcut created
- [ ] App launches
- [ ] Docker Desktop integration works
- [ ] All functionality works

### Step 6: Tag Release

```bash
git add .
git commit -m "Release v0.2.0"
git tag -a v0.2.0 -m "Version 0.2.0 - Description"
git push origin main --tags
```

### Step 7: Upload Packages

#### Option A: GitHub Releases

```bash
# Go to: https://github.com/YOUR_USERNAME/silent-scribe/releases/new
# Create release from tag v0.2.0
# Upload dist/*.AppImage, dist/*.deb, dist/*.dmg, dist/*.exe
# Publish release
```

#### Option B: Internal Distribution

```bash
# Copy to file server, USB drive, or internal network location
cp dist/* /path/to/distribution/location/
```

#### Option C: Direct Distribution

Email, USB drive, or secure file transfer to specific users.

### Step 8: Announce Release

- Update README.md with download links
- Notify users via email/Slack/Teams
- Post in support channels
- Update documentation site

---

## GitHub Actions (CI/CD)

### Overview

GitHub Actions automatically builds packages for **Linux, macOS, and Windows** by:
1. Pulling your pre-built Docker image from GitHub Container Registry (GHCR)
2. Packaging it with Electron for each platform
3. Creating a draft GitHub Release with all installers

**Advantages:**
- ✅ No need for Mac or Windows machines
- ✅ Builds all platforms in parallel
- ✅ Automatic draft releases
- ✅ Avoids GitHub's disk space limits (image pre-built locally)

### Prerequisites

1. Docker image pushed to GHCR (Step 3 above)
2. GHCR package set to **public** visibility

### Workflow

The workflow is at `.github/workflows/build.yml` and runs on:
- **Tag push**: `v*` (e.g., `v0.2.0`)
- **Manual**: Actions tab → "Build Silent Scribe" → Run workflow

### Trigger Release Build

```bash
# After pushing image to GHCR:
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin --tags
```

### Monitor Progress

1. Go to: https://github.com/YOUR_USERNAME/offline-scribe/actions
2. Click the running workflow
3. Watch the three parallel build jobs (Linux, macOS, Windows)

**Time:** 20-30 minutes total

### Download Artifacts

After workflow completes:

**Option 1: From GitHub Release (automatic)**
- Go to: https://github.com/YOUR_USERNAME/offline-scribe/releases
- Find the draft release
- Review and publish

**Option 2: From Actions artifacts**
- Go to the completed workflow
- Download `linux-build`, `mac-build`, `windows-build` artifacts

### Build Modes

**Full (default):** Bundles Docker image (~15-20 GB per platform)
**Lite:** App only, no image (future feature)

### Troubleshooting

**Error: "Cannot pull image"**
- Ensure GHCR package is public
- Verify image exists: `docker pull ghcr.io/YOUR_USERNAME/offline-scribe:latest`

**Error: "Insufficient disk space"**
- GitHub runners have limited space after pulling the image
- This is expected; image is split and reassembled automatically

**Build fails on specific platform:**
- Check the specific platform job logs
- Verify electron-builder configuration in package.json

---

## Distribution Methods

### 1. USB Drive / Flash Drive

**Best for:** Secure, air-gapped environments

**Process:**
1. Copy packages to USB drive
2. Include README with install instructions
3. Physically hand off to users

**Structure:**
```
USB_Drive/
├── README.txt
├── linux/
│   ├── Silent_Scribe-0.2.0.AppImage
│   └── Silent_Scribe_0.2.0_amd64.deb
├── mac/
│   └── Silent_Scribe-0.2.0-mac-arm64.dmg
└── windows/
    └── Silent_Scribe-0.2.0-win-x64.exe
```

### 2. Internal File Server

**Best for:** Organizations with internal networks

**Process:**
1. Upload to internal server
2. Share download link internally
3. Provide install guide

### 3. GitHub Releases

**Best for:** Public or semi-public distribution

**Process:**
1. Create GitHub release
2. Upload packages as release assets
3. Users download from Releases page

**Note:** Large file sizes may cause slow downloads.

### 4. Cloud Storage (S3, GCS, etc.)

**Best for:** Controlled distribution with analytics

**Process:**
1. Upload to cloud storage
2. Generate signed/temporary download URLs
3. Track downloads via access logs

---

## Code Signing

### Why Sign?

- **macOS:** Prevents "App is damaged" warnings
- **Windows:** Prevents SmartScreen warnings
- **Trust:** Users know the app is authentic

### macOS Code Signing

**Requirements:**
- Apple Developer Account ($99/year)
- Developer ID Application certificate
- Xcode Command Line Tools

**Process:**
```bash
# Install certificate to keychain
# Configure electron-builder
```

Edit `package.json`:
```json
{
  "build": {
    "mac": {
      "hardenedRuntime": true,
      "gatekeeperAssess": false,
      "entitlements": "build/entitlements.mac.plist",
      "entitlementsInherit": "build/entitlements.mac.plist"
    }
  }
}
```

**Notarization:**
```bash
# After build
xcrun notarytool submit dist/*.dmg --wait
xcrun stapler staple dist/*.dmg
```

### Windows Code Signing

**Requirements:**
- Code Signing Certificate (from DigiCert, Sectigo, etc.)
- Certificate file (.pfx)

**Configuration:**
```json
{
  "build": {
    "win": {
      "certificateFile": "path/to/cert.pfx",
      "certificatePassword": "${process.env.CSC_PASSWORD}"
    }
  }
}
```

**Note:** Never commit certificate or password to git.

### Linux

Code signing not required for Linux distributions.

---

## Update Mechanism

### Current: Manual Updates

Users must:
1. Download new version
2. Install/replace old version
3. Launch app
4. App detects outdated image and prompts to load new one

### Future: Auto-Update (Planned)

- Electron's `autoUpdater` module
- Check for updates on launch
- Download and install in background
- Restart to apply

**Challenges with air-gapped:**
- Can't check for updates over internet
- Solution: Check for updates on USB/network drive

---

## Storage Considerations

### Disk Space Requirements

**Development:**
- Docker image (uncompressed): ~27 GB
- Docker image (compressed): ~15-20 GB
- Build output per platform: ~15-20 GB
- **Total:** ~100+ GB for full multi-platform build

**Distribution:**
- Per user: ~15-20 GB download
- USB drive: 64 GB+ recommended for all platforms

### Compression

Already using gzip compression for Docker image export. Further compression not recommended (minimal gains, much longer times).

---

## Troubleshooting Distribution

### "File too large" errors

**Problem:** GitHub Releases has 2GB file limit per file

**Solution:** 
- Use GitHub Packages (10GB limit)
- Use cloud storage
- Use split archives (not recommended)

### Slow downloads

**Problem:** 15-20 GB files are slow to download

**Solution:**
- Use CDN or cloud storage with fast network
- Provide torrent files
- USB drive distribution

### Installation failures

**Problem:** Users report installation errors

**Solution:**
- Provide detailed error logs
- Test on clean VMs before release
- Document known issues

---

## Support & Maintenance

### User Support

**Common issues:**
- Docker not installed/running
- Insufficient disk space
- Permission errors
- Port conflicts

**Resolution:**
- Direct users to TROUBLESHOOTING.md
- Provide support via GitHub Issues
- Create FAQ based on common questions

### Monitoring

Track:
- Download counts
- Installation success rate
- Error reports
- Feature requests

---

## Checklist Summary

Before releasing:

- [ ] Version updated everywhere
- [ ] Docker image built and exported
- [ ] All platforms packaged
- [ ] Packages tested on clean systems
- [ ] Release notes written
- [ ] Git tagged
- [ ] Packages uploaded
- [ ] Users notified
- [ ] Support channels ready

---

## Next Steps

- Set up GitHub Actions for automated builds
- Obtain code signing certificates
- Implement auto-update mechanism
- Create public download page
- Set up usage analytics (optional)
