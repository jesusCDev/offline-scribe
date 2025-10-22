# 📦 Distributing Silent Scribe to Other Machines

**How to copy Silent Scribe to another computer without re-downloading 27 GB of models.**

---

## Overview

Instead of building on every machine (which downloads 27 GB), you:
1. Build once on your machine
2. Save the Docker image to a file
3. Copy that file to other machines
4. Load it there

**Benefit:** Users skip the 30-60 minute build process!

---

## Step 1: Build on Your Machine (One Time)

```bash
./build
```

Wait 30-60 minutes for models to download and build.

---

## Step 2: Save the Image

```bash
./save-image
```

This creates `silent-scribe-image.tar.gz` (~27 GB compressed).

**Takes:** 5-10 minutes to compress and save.

---

## Step 3: Copy to Target Machine

Choose your method:

### Option A: USB Drive
```bash
# Copy to USB drive
cp silent-scribe-image.tar.gz /Volumes/USB_DRIVE/

# Also copy the entire project folder
cp -r silent-scribe /Volumes/USB_DRIVE/
```

### Option B: Network Transfer
```bash
# Using scp
scp silent-scribe-image.tar.gz user@target-machine:~/

# Or rsync (better for large files)
rsync -avz --progress silent-scribe-image.tar.gz user@target-machine:~/
```

### Option C: Cloud Storage
Upload to Dropbox, Google Drive, etc. (if allowed by your security policy).

---

## Step 4: On the Target Machine

### Install Docker (if not already installed)

**Mac:**
1. Download Docker Desktop from docker.com
2. Install and start it

**Linux:**
```bash
# Fedora/RHEL
sudo dnf install docker
sudo systemctl start docker
sudo systemctl enable docker

# Ubuntu/Debian
sudo apt install docker.io
sudo systemctl start docker
sudo systemctl enable docker
```

### Load the Image

```bash
cd silent-scribe
./load
```

This imports the image into Docker. **Takes:** 5-10 minutes.

---

## Step 5: Start Using It!

```bash
./start
```

Open browser to **http://localhost:7860** and start transcribing!

---

## What Gets Copied?

### Required Files (Must Copy):
```
silent-scribe/
├── app/                           # Application code
├── docker/                        # Dockerfile (for reference)
├── docs/                          # All documentation
├── scripts/                       # Helper scripts
├── build                          # Build script
├── start                          # Start script
├── stop                           # Stop script
├── load                           # Load image script
├── save-image                     # Save image script
├── GET_STARTED.md                 # Simple guide
├── README.md                      # Full docs
├── Makefile                       # Make shortcuts
├── requirements.txt               # Python deps (for reference)
└── silent-scribe-image.tar.gz     # THE DOCKER IMAGE (27 GB!)
```

### NOT Required (Skip These):
- `data/` - This is created automatically
- `.git/` - Version control (skip for users)
- `tests/` - Only needed for development
- Build logs, temp files, etc.

---

## Simplified Distribution Package

For the absolute simplest distribution:

```bash
# Create a clean package
mkdir silent-scribe-portable
cd silent-scribe-portable

# Copy only what's needed
cp -r ../silent-scribe/{app,docker,docs,scripts} .
cp ../silent-scribe/{build,start,stop,load,save-image} .
cp ../silent-scribe/{GET_STARTED.md,README.md,Makefile,requirements.txt} .
cp ../silent-scribe/silent-scribe-image.tar.gz .

# Create simple README
cat > INSTRUCTIONS.txt << 'EOF'
SILENT SCRIBE - QUICK START
============================

1. Install Docker Desktop (if not already installed)
   Mac: Download from docker.com
   
2. Load the image:
   ./load
   
3. Start the app:
   ./start
   
4. Open browser to: http://localhost:7860

5. Stop the app:
   ./stop
   or press Ctrl+C

For full docs, see GET_STARTED.md or README.md
EOF

# Package it
cd ..
tar -czf silent-scribe-portable.tar.gz silent-scribe-portable/
```

Now you have `silent-scribe-portable.tar.gz` ready to distribute!

---

## File Size Expectations

- **Docker image (.tar.gz):** ~27 GB
- **Project files:** ~50 MB
- **Total package:** ~27 GB

**Tip:** Use a 64 GB+ USB drive or external SSD.

---

## User Instructions (Give Them This)

**SILENT SCRIBE - SETUP INSTRUCTIONS**

1. **Install Docker Desktop**
   - Mac: Download from docker.com and install
   - Follow the Docker Desktop setup wizard

2. **Copy Files**
   - Copy the entire `silent-scribe` folder to your computer
   - Make sure `silent-scribe-image.tar.gz` is inside it

3. **Load the Image**
   - Open Terminal (Mac: Applications → Utilities → Terminal)
   - Navigate to the folder: `cd path/to/silent-scribe`
   - Run: `./load`
   - Wait 5-10 minutes

4. **Start Transcribing**
   - Run: `./start`
   - Open browser to: http://localhost:7860
   - Upload videos and transcribe!

5. **Stop When Done**
   - Press Ctrl+C in the terminal
   - Or run: `./stop`

**That's it!** No internet needed after setup.

---

## Updating the Image

If you update the code or models:

```bash
# On build machine
./build          # Rebuild with changes
./save-image     # Save new image

# Distribute new silent-scribe-image.tar.gz

# On target machines
./load           # Reload the updated image
./start          # Run new version
```

---

## Troubleshooting Distribution

### "Image file not found"
Make sure `silent-scribe-image.tar.gz` is in the same directory as `./load`.

### "Docker is not running"
Start Docker Desktop on Mac, or run `sudo systemctl start docker` on Linux.

### "Permission denied"
Run `chmod +x load start stop build` to make scripts executable.

### Large file transfer fails
- Use `rsync` instead of `scp` for better reliability
- Or split into chunks: `split -b 5G silent-scribe-image.tar.gz chunk-`
- Then reassemble: `cat chunk-* > silent-scribe-image.tar.gz`

---

## FAQ

**Q: Do users need internet access?**
A: Only to download Docker Desktop initially. After that, 100% offline.

**Q: Can I update just the code without redistributing the image?**
A: Yes, but only if models don't change. Copy the `app/` folder and restart.

**Q: How much disk space do users need?**
A: 30 GB minimum (27 GB image + 3 GB working space).

**Q: Does this work on Windows?**
A: Yes, with Docker Desktop. The scripts work in Git Bash or WSL2.

**Q: Can I distribute via cloud storage?**
A: Yes, but 27 GB uploads may be slow. Split files help.

---

**Happy distributing!** 🚀
