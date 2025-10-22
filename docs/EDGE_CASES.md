# Edge Case Handling

This document explains how Silent Scribe handles various edge cases to ensure a smooth user experience, even for non-technical users.

## 🎯 Design Goal

**"It should just work"** - no matter how the user stops the app or what state things are in.

---

## ✅ Handled Edge Cases

### 1. User hits Ctrl+C on `./run.sh`

**What happens:**
- Docker's `-it` flag makes the container interactive
- Docker's `--rm` flag auto-removes the container when it stops
- Container cleanly stops and removes itself automatically

**Result:** ✅ No orphaned container, port is freed immediately

**Code:**
```bash path=/home/jesuscdev/Programming/silent-scribe/scripts/run.sh start=71
docker run --rm -it \
  -p 7860:7860 \
  -v "$(pwd)/data:/data:z" \
  --name silent-scribe \
  --network none \
  silent-scribe:latest
```

---

### 2. Terminal is force-killed (kill -9, crash, etc.)

**What happens:**
- Container keeps running in background (edge case where `--rm` doesn't trigger)
- Next run of `./run.sh` detects the running container
- Automatically stops and removes it before starting new one

**Result:** ✅ Old container cleaned up, new one starts successfully

**Code:**
```bash path=/home/jesuscdev/Programming/silent-scribe/scripts/run.sh start=31
if docker ps -q -f name=silent-scribe | grep -q .; then
    echo "♻️  Found running container, stopping..."
    docker stop silent-scribe 2>/dev/null || true
    docker rm silent-scribe 2>/dev/null || true
    echo "✓ Cleaned up running container"
```

---

### 3. Container stopped but not removed

**What happens:**
- Sometimes Docker might stop the container but fail to remove it
- Next run detects stopped (but not removed) container
- Removes it before starting new one

**Result:** ✅ Dead container cleaned up, new one starts successfully

**Code:**
```bash path=/home/jesuscdev/Programming/silent-scribe/scripts/run.sh start=36
elif docker ps -aq -f name=silent-scribe | grep -q .; then
    echo "♻️  Found stopped container, removing..."
    docker rm silent-scribe 2>/dev/null || true
    echo "✓ Cleaned up stopped container"
```

---

### 4. Port 7860 already in use by different process

**What happens:**
- Docker will fail to bind port with clear error message
- User sees: `Error: port is already allocated`

**Fix:**
```bash
./scripts/stop.sh    # Won't help if it's not our container
lsof -i :7860        # Find what's using it
# Kill that process, then retry
```

**Result:** ⚠️ User needs to free the port manually (rare case)

---

### 5. Docker daemon not running

**What happens:**
- Script checks `docker info` before doing anything
- Fails immediately with helpful message

**Result:** ✅ Clear error message tells user to start Docker

**Code:**
```bash path=/home/jesuscdev/Programming/silent-scribe/scripts/run.sh start=11
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi
```

---

### 6. Image not built yet

**What happens:**
- Script checks if `silent-scribe:latest` image exists
- Fails immediately with instructions on how to build

**Result:** ✅ Clear guidance to run build first

**Code:**
```bash path=/home/jesuscdev/Programming/silent-scribe/scripts/run.sh start=18
if ! docker images silent-scribe:latest | grep -q silent-scribe; then
    echo ""
    echo "❌ Image 'silent-scribe:latest' not found."
    echo "   Please build it first:"
    echo "     ./scripts/build.sh"
    exit 1
fi
```

---

### 7. Permission issues with data directory

**What happens:**
- Script creates directories if missing: `data/uploads` and `data/results`
- Attempts to set permissive permissions (777) for container access
- If it fails (needs sudo), shows warning but continues

**Result:** ✅ Usually works, warns if permission fix failed

**Code:**
```bash path=/home/jesuscdev/Programming/silent-scribe/scripts/run.sh start=46
mkdir -p data/uploads data/results
chmod -R 777 data/ 2>/dev/null || {
    echo "⚠️  Could not set permissions on data/ (may need sudo)"
}
```

---

### 8. User runs multiple instances simultaneously

**What happens:**
- Docker enforces unique container names
- Second `./run.sh` will detect and stop first container
- New container takes over

**Result:** ✅ Only one instance runs (last one wins)

**Note:** This is intentional - running multiple instances would cause:
- Port conflicts (both trying to use 7860)
- Resource exhaustion (multiple models in RAM)
- Data directory conflicts

---

### 9. Out of disk space

**What happens:**
- Docker will fail to create container
- Error message indicates disk space issue

**Fix:**
```bash
docker system prune -a    # Free up Docker space
df -h                     # Check available space
```

**Result:** ⚠️ User must free space manually

---

### 10. Container crashes after starting

**What happens:**
- Container exits with error code
- Due to `--rm` flag, container auto-removes itself
- User sees error logs in terminal

**Debug:**
```bash
# If crash is intermittent, run without --rm to preserve logs
docker run -it -p 7860:7860 -v $(pwd)/data:/data --name silent-scribe --network none silent-scribe:latest

# Then check logs
docker logs silent-scribe
```

**Result:** ⚠️ User needs to investigate logs

---

## 🧪 Testing Edge Cases

Run the test suite:
```bash
./scripts/test-edge-cases.sh
```

This simulates all common edge cases and verifies the cleanup logic works.

---

## 📊 Edge Case Summary

| Edge Case | Handled Automatically? | User Action Required |
|-----------|----------------------|---------------------|
| Ctrl+C stop | ✅ Yes | None |
| Force-kill terminal | ✅ Yes | None |
| Stopped but not removed | ✅ Yes | None |
| Running old container | ✅ Yes | None |
| Docker not running | ✅ Yes | Start Docker |
| Image not built | ✅ Yes | Run build script |
| Port conflict (other app) | ⚠️ Partial | Kill other app |
| Permission issues | ✅ Usually | Sometimes sudo |
| Multiple instances | ✅ Yes | None (last wins) |
| Out of disk space | ❌ No | Free space |
| Container crash | ⚠️ Partial | Check logs |

**Summary:** 9/11 edge cases are fully or partially handled automatically! 🎉

---

## 🔒 Security Note

The auto-cleanup logic uses:
- `|| true` to prevent script failures on cleanup errors
- `2>/dev/null` to hide expected error messages
- No `sudo` or privileged operations
- Explicit container name filtering to avoid touching other containers

This ensures the scripts are safe and won't accidentally affect other Docker containers.

---

## 👥 Non-Technical User Experience

**Goal:** User shouldn't need to understand Docker, containers, or ports.

**Reality:**
1. Run `./scripts/run.sh` → App starts at http://localhost:7860
2. Press `Ctrl+C` → App stops cleanly
3. Run again → Works perfectly, no leftover junk

**Edge cases are invisible** - the scripts handle them automatically! ✨
