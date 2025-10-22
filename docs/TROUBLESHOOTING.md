# 🔧 Troubleshooting Guide

**Having issues? Here's how to fix them.**

---

## 🚨 Quick Fixes (Try These First!)

### App won't start?
```bash
./scripts/stop.sh   # Clean up
./scripts/run.sh    # Try again
```

### Transcription failed?
- Try a smaller model (tiny or base)
- Close other programs to free up RAM
- Check if the video file is corrupted

### Can't access http://localhost:7860?
1. Check the terminal - is the app running?
2. Try refreshing your browser
3. Try a different browser
4. Make sure you're using `http://` not `https://`

---

## 📝 Common Problems & Solutions

### Problem: "Port 7860 already in use"

**Why?** Another program (or old container) is using that port.

**Fix:**
```bash
# Option 1: Stop the old container
./scripts/stop.sh
./scripts/run.sh

# Option 2: Find what's using it
lsof -i :7860
# Then stop that process
```

**Prevention:** Always use `Ctrl+C` or `./scripts/stop.sh` to stop the app properly.

---

### Problem: "Docker is not running"

**Why?** Docker Desktop or Docker daemon is not started.

**Fix:**
- **Mac/Windows:** Open Docker Desktop application
- **Linux:** 
  ```bash
  sudo systemctl start docker
  # or
  sudo service docker start
  ```

---

### Problem: "Permission denied" when running scripts

**Why?** Scripts don't have execute permission.

**Fix:**
```bash
chmod +x scripts/*.sh
```

---

### Problem: Out of disk space during build

**Why?** Build needs ~30 GB to download models.

**Fix:**
```bash
# Check available space
df -h

# Free up space by removing old Docker stuff
docker system prune -a

# Then try again
./scripts/build.sh
```

---

### Problem: Transcription is very slow

**Why?** Model is too large for your hardware, or too many threads.

**Fix:**
1. Use **small** or **base** model (not medium/large)
2. Reduce thread count to match your CPU cores
3. Use **faster-whisper** engine (better optimized)
4. Close other programs to free resources

---

### Problem: "Out of memory" error

**Why?** Not enough RAM for the selected model.

**Fix:**
1. Use a smaller model:
   - **large-v3** → switch to **medium** or **small**
   - **medium** → switch to **small** or **base**
   - **small** → switch to **base** or **tiny**
2. Close other programs
3. If using Docker Desktop, increase memory limit:
   - Docker Desktop → Settings → Resources → Memory

---

### Problem: Container starts but crashes immediately

**Check logs:**
```bash
docker logs silent-scribe
```

**Common causes:**
- Corrupted image → rebuild: `./scripts/build.sh`
- Permission issues → fix: `chmod -R 777 data/`
- Old container conflict → clean: `./scripts/stop.sh`

---

### Problem: Video upload fails

**Why?** File too large, unsupported format, or permissions issue.

**Fix:**
1. Check file size (very large files may timeout)
2. Check format (supported: MP4, AVI, MOV, MKV, etc.)
3. Try converting to MP4 first:
   ```bash
   ffmpeg -i input.avi output.mp4
   ```
4. Check `data/uploads/` permissions:
   ```bash
   chmod -R 777 data/
   ```

---

### Problem: Generated files won't download

**Fix:**
```bash
# Check if files exist
ls -lh data/results/

# Fix permissions
chmod -R 777 data/results/

# Restart app
./scripts/stop.sh
./scripts/run.sh
```

---

### Problem: Can't stop the app

**Try these (in order):**
1. Press `Ctrl+C` in the terminal
2. Run `./scripts/stop.sh`
3. Force stop:
   ```bash
   docker stop -t 0 silent-scribe
   docker rm silent-scribe
   ```
4. Nuclear option:
   ```bash
   docker kill silent-scribe
   docker rm -f silent-scribe
   ```

---

## 🧪 Testing Edge Cases

Want to verify the scripts handle weird situations?

```bash
./scripts/test-edge-cases.sh
```

This tests:
- Orphaned running containers
- Stopped but not removed containers
- Port conflicts
- Auto-cleanup on Ctrl+C

---

## 🆘 Still Stuck?

### Collect Debug Info

```bash
# 1. Check Docker version
docker --version

# 2. Check if image exists
docker images | grep silent-scribe

# 3. Check container status
docker ps -a | grep silent-scribe

# 4. Check logs
docker logs silent-scribe 2>&1 | tail -50

# 5. Check system resources
free -h   # RAM
df -h     # Disk
```

### Complete Reset (Nuclear Option)

**Warning:** This deletes everything and starts fresh!

```bash
# Stop and remove everything
./scripts/stop.sh
docker rmi silent-scribe:latest
rm -rf data/uploads/* data/results/*

# Rebuild from scratch
./scripts/build.sh
./scripts/run.sh
```

---

## ✅ Preventive Maintenance

Keep things running smoothly:

```bash
# Weekly cleanup
docker system prune -f

# Check disk space
df -h

# Verify permissions
chmod -R 777 data/
```

---

## 📚 More Help

- **Quick Start:** [QUICKSTART.md](QUICKSTART.md)
- **Full Manual:** [README.md](README.md)
- **Implementation:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Test Checklist:** [TEST_CHECKLIST.md](TEST_CHECKLIST.md)
