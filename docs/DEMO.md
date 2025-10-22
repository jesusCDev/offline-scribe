# 🎬 Silent Scribe Demo

## For Non-Technical Users

**You don't need to know anything about Docker, containers, or command lines.**

Just follow these three steps:

---

## Step 1: Build (First Time Only - 30-60 minutes)

Open a terminal and navigate to the project folder, then run:

```bash
./scripts/build.sh
```

**What's happening?**
- Downloading AI models from the internet
- Building a self-contained package
- This takes 30-60 minutes but only needs to be done once!

☕ Go grab a coffee, this will take a while...

---

## Step 2: Start the App

```bash
./scripts/run.sh
```

**That's it!** The terminal will show:
```
🚀 Starting Silent Scribe
==============================

🔒 Security: Air-gapped mode (--network none)
🌐 Web UI:  http://localhost:7860

Features:
  ✓ Whisper transcription
  ✓ Llama 2 summarization
  ✓ Settings persistence
  ✓ No internet access

📝 Tip: Press Ctrl+C to stop (container will auto-cleanup)
```

Open your web browser and go to: **http://localhost:7860**

---

## Step 3: Use It!

### Upload a Video
1. Drag and drop a video file onto the upload area
2. Or click "Choose File" to browse

### Choose Settings (or use defaults)
- **Model**: small (recommended)
- **Engine**: faster-whisper (recommended)
- **Language**: English (or auto-detect)

### Start Transcription
1. Click the big "Start Transcription" button
2. Watch the progress bar fill up
3. Wait for it to complete

### Get AI Summary ✨
1. After transcription completes, click "✨ Generate Summary"
2. Wait 30-60 seconds
3. View bullet points and paragraph summary in the "Summary" tab

### Download Your Files
Click the download buttons to get:
- Plain text transcript (.txt)
- Subtitle files (.srt, .vtt)
- Summary files (.txt)

---

## Stop the App

Just press **Ctrl+C** in the terminal where you ran `./run.sh`

Or run:
```bash
./scripts/stop.sh
```

**That's it!** The app will automatically clean up after itself.

---

## 🎯 Real-World Usage Example

### Scenario: Transcribing a Meeting Recording

1. **Start the app** → `./scripts/run.sh`
2. **Open browser** → http://localhost:7860
3. **Upload video** → Drag meeting.mp4 onto the page
4. **Click "Start"** → Wait 5-10 minutes (for a 1-hour video)
5. **Generate summary** → Click "✨ Generate Summary", wait 30 seconds
6. **Download results**:
   - `transcript.txt` - Full meeting transcript
   - `transcript.srt` - Subtitles for video editing
   - `summary_bullets.txt` - Key points and action items
   - `summary_paragraph.txt` - Executive summary
7. **Stop app** → Press Ctrl+C

**Total time**: ~15 minutes for 1-hour video + AI summary

---

## 🛡️ What Makes This Special?

### 100% Offline & Secure
- ✅ No internet connection after build
- ✅ Your data never leaves your computer
- ✅ Perfect for sensitive meetings, interviews, legal depositions
- ✅ HIPAA/GDPR friendly (data stays local)

### No Subscriptions or API Keys
- ✅ No monthly fees
- ✅ No usage limits
- ✅ No cloud API costs
- ✅ Unlimited transcriptions and summaries

### Truly Portable
- ✅ Run on any Mac or Linux machine
- ✅ Can be distributed on a flash drive
- ✅ Works completely offline (after initial build)

---

## 🤔 Common Questions

### Q: Do I need to rebuild every time?
**A:** No! Build once, use forever. Only rebuild if you want to update models.

### Q: Can I use it on multiple videos in a row?
**A:** Yes! Just upload a new video after the previous one finishes. No need to restart.

### Q: What if I press Ctrl+C by accident?
**A:** No problem! Just run `./scripts/run.sh` again. Everything is saved.

### Q: Where are my files saved?
**A:** In the `data/results/` folder. Each transcription gets its own folder.

### Q: Can I delete old transcriptions?
**A:** Yes! Just delete folders from `data/results/`. Won't affect the app.

### Q: Does this work without internet?
**A:** Yes! After the initial build (which needs internet), it works 100% offline.

### Q: How much does this cost?
**A:** Zero! It's free and open source. No subscriptions, no API fees.

---

## 💡 Tips for Best Results

### For Speed
- Use **tiny** or **base** model
- Short videos process faster than long ones

### For Quality
- Use **small** (default) or **medium** model
- Clear audio = better transcription
- English works best (most training data)

### For Memory
- If your computer has 8 GB RAM, stick with **small** or **base**
- If you have 16+ GB RAM, you can use **medium** or **large-v3**

---

## 🆘 Help! Something's Wrong

### App won't start?
```bash
./scripts/stop.sh    # Clean up
./scripts/run.sh     # Try again
```

### Can't access the web page?
- Make sure you're using **http://** not https://
- Try http://127.0.0.1:7860 instead
- Check the terminal - is the app still running?

### Transcription failed?
- Is the video file corrupted? (Try playing it first)
- Try a smaller model (base or tiny)
- Close other programs to free up RAM

### Still stuck?
Check the **[Troubleshooting Guide](TROUBLESHOOTING.md)** for detailed solutions!

---

## 🎉 You're Ready!

That's all there is to it. Silent Scribe is designed to be:
- **Simple** - Just run the script
- **Reliable** - Handles errors gracefully
- **Secure** - Completely offline after build
- **Powerful** - Professional transcription + AI summaries

**Go transcribe something!** 🎬➡️📝
