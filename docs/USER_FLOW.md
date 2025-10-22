# 🗺️ Silent Scribe User Flow

Visual guide showing how users interact with the system and how it handles edge cases.

---

## 📱 Normal User Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     1. FIRST TIME SETUP                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User runs: ./scripts/build.sh                                  │
│             ↓                                                    │
│  [Download Models] → [Build Container] → [Image Ready]          │
│       (30-60 min)                                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     2. START APPLICATION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User runs: ./scripts/run.sh                                    │
│             ↓                                                    │
│  [Check Docker] → [Check Image] → [Cleanup Old]                 │
│                                         ↓                        │
│  [Start Container] → Browser opens http://localhost:7860        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     3. TRANSCRIBE VIDEO                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Upload Video] → [Choose Settings] → [Start Transcription]     │
│        ↓                                                         │
│  [Processing...] → [Progress Bar] → [Complete!]                 │
│                                ↓                                 │
│  [Download TXT/SRT/VTT files]                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     4. GENERATE SUMMARY (Optional)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Click "Generate Summary"] → [AI Processing] → [Complete!]     │
│            ↓                    (30-90 sec)                      │
│  [View Bullet Points] + [View Paragraph]                        │
│            ↓                                                     │
│  [Download Summary Files]                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     5. STOP APPLICATION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User presses: Ctrl+C                                           │
│         OR                                                       │
│  User runs: ./scripts/stop.sh                                   │
│             ↓                                                    │
│  [Container Stops] → [Auto-cleanup] → [Done!]                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Edge Case Handling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│         User runs: ./scripts/run.sh                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
            ┌────────────────────────┐
            │  Is Docker running?    │
            └────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
        NO                      YES
         │                       │
         ↓                       ↓
   ┌──────────┐          ┌──────────────┐
   │  ERROR:  │          │ Image exists?│
   │  Start   │          └──────────────┘
   │  Docker  │               │
   └──────────┘    ┌──────────┴──────────┐
                   │                     │
                  NO                    YES
                   │                     │
                   ↓                     ↓
            ┌──────────┐        ┌──────────────────┐
            │  ERROR:  │        │ Container exists?│
            │  Run     │        └──────────────────┘
            │  build   │                │
            └──────────┘    ┌───────────┼───────────┐
                            │           │           │
                         RUNNING     STOPPED       NO
                            │           │           │
                            ↓           ↓           │
                    ┌────────────┐ ┌────────────┐  │
                    │ Stop &     │ │ Remove it  │  │
                    │ Remove it  │ └────────────┘  │
                    └────────────┘        │         │
                            │             │         │
                            └─────────────┴─────────┘
                                      │
                                      ↓
                            ┌────────────────────┐
                            │ Start new container│
                            └────────────────────┘
                                      │
                                      ↓
                            ┌────────────────────┐
                            │  App running at    │
                            │  localhost:7860    │
                            └────────────────────┘
```

---

## 🔐 Security & Network Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         BUILD TIME                               │
│                    (Network Enabled)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Internet → [Download Whisper Models] → Local Storage          │
│            → [Download Llama 2 Model]  → Local Storage          │
│            → [Python Dependencies]     → Container Image         │
│            → [Compile llama.cpp]       → Container Image         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

                              ↓

┌─────────────────────────────────────────────────────────────────┐
│                         RUNTIME                                  │
│                   (--network none)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ╔════════════════════════════════════════════════════════════╗ │
│  ║  Container (Air-Gapped)                                    ║ │
│  ║                                                            ║ │
│  ║  ┌────────────┐    ┌──────────────┐   ┌────────────────┐ ║ │
│  ║  │ Web UI     │←──→│ FastAPI      │←─→│ Job Manager    │ ║ │
│  ║  │ (Browser)  │    │ Backend      │   └────────────────┘ ║ │
│  ║  └────────────┘    └──────────────┘           │          ║ │
│  ║       ↑                                        ↓          ║ │
│  ║       │              ┌──────────────┐   ┌────────────────┐ ║ │
│  ║       │              │ Whisper      │   │ Llama 2        │ ║ │
│  ║       │              │ Engines      │   │ Summarizer     │ ║ │
│  ║       │              └──────────────┘   └────────────────┘ ║ │
│  ║       │                     ↓                   ↓          ║ │
│  ║       │              ┌─────────────────────────────────┐  ║ │
│  ║       └──────────────│ /data (Mounted Volume)          │  ║ │
│  ║                      │  - uploads/                     │  ║ │
│  ║                      │  - results/                     │  ║ │
│  ║                      └─────────────────────────────────┘  ║ │
│  ║                                                            ║ │
│  ║  🔒 NO INTERNET ACCESS - All models and dependencies      ║ │
│  ║     are bundled inside the container at build time        ║ │
│  ╚════════════════════════════════════════════════════════════╝ │
│                                                                  │
│  Only port 7860 exposed to localhost (not network)              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 User Journey Map

### First-Time User

```
Step 1: Discovery
└─> Read DEMO.md or README.md
    └─> Understand what the app does
        └─> Check requirements (Docker, disk, RAM)

Step 2: Build
└─> Run ./scripts/build.sh
    └─> Wait 30-60 minutes ☕
        └─> Models downloaded successfully

Step 3: First Use
└─> Run ./scripts/run.sh
    └─> Open browser to localhost:7860
        └─> Upload first video
            └─> Adjust settings
                └─> Start transcription
                    └─> Wait for completion
                        └─> Download results ✅

Step 4: Try Summary
└─> Click "Generate Summary"
    └─> Wait 30-90 seconds
        └─> View bullet points + paragraph
            └─> Download summary files ✅

Step 5: Stop
└─> Press Ctrl+C
    └─> Container auto-cleans up ✅
```

### Returning User

```
Step 1: Start
└─> Run ./scripts/run.sh
    └─> [Automatic cleanup if needed]
        └─> App starts immediately

Step 2: Work
└─> Upload videos
    └─> Transcribe (settings remembered!)
        └─> Generate summaries
            └─> Download files

Step 3: Stop
└─> Ctrl+C or ./scripts/stop.sh
    └─> Done! ✅
```

---

## 📊 State Machine

```
┌──────────┐
│  INITIAL │
│  (Image  │
│not built)│
└────┬─────┘
     │ ./build.sh
     ↓
┌──────────┐
│ BUILT    │
│ (Image   │
│ ready)   │
└────┬─────┘
     │ ./run.sh
     ↓
┌──────────┐ ←──────────┐
│ RUNNING  │            │
│(Container│            │
│  active) │            │ ./run.sh
└────┬─────┘            │ (auto-cleanup
     │                  │  + restart)
     │ Ctrl+C or        │
     │ ./stop.sh        │
     ↓                  │
┌──────────┐            │
│ STOPPED  │────────────┘
│(Container│
│ removed) │
└──────────┘
     │ ./run.sh
     ↓
┌──────────┐
│ RUNNING  │
│  again   │
└──────────┘
```

---

## 🚦 Error Handling Paths

```
START: ./scripts/run.sh
    │
    ├─→ Docker not running
    │   └─> ERROR: "Start Docker first"
    │       └─> User starts Docker
    │           └─> RETRY
    │
    ├─→ Image not found
    │   └─> ERROR: "Run build.sh first"
    │       └─> User runs build.sh
    │           └─> RETRY
    │
    ├─→ Port 7860 busy (our old container)
    │   └─> AUTO-FIX: Stop and remove old container
    │       └─> SUCCESS
    │
    ├─→ Port 7860 busy (other app)
    │   └─> ERROR: "Port in use"
    │       └─> User kills other app
    │           └─> RETRY
    │
    ├─→ Permission denied on /data
    │   └─> WARNING: "May need sudo"
    │       └─> Usually continues anyway
    │           └─> SUCCESS (or manual fix)
    │
    └─→ All checks passed
        └─> SUCCESS: Container running
```

---

## 💡 Key Insights

### What Makes This UX Good?

1. **Self-Healing**: Auto-cleans up old containers
2. **Clear Feedback**: Every step has a status message
3. **Fail-Fast**: Checks prerequisites before starting
4. **Idempotent**: Running `./run.sh` multiple times is safe
5. **Forgiving**: Ctrl+C just works, no manual cleanup needed

### What Users Don't Need to Know

- Docker container lifecycle
- Port binding mechanics
- Network isolation details
- Volume mounting
- Image layers

They just run the scripts and it works! ✨

---

## 📝 Supporting Documentation

- **[DEMO.md](DEMO.md)** - Follow this flow as a beginner
- **[QUICKSTART.md](QUICKSTART.md)** - Reference this for quick commands
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Use when you hit an error
- **[EDGE_CASES.md](EDGE_CASES.md)** - Understand the internals
