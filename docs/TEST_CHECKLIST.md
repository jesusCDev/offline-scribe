# Silent Scribe - Testing Checklist

## Pre-Build Checklist
- [ ] All changes committed to git
- [ ] Sufficient disk space (~25 GB free recommended)
- [ ] Docker daemon running

## Build Phase
```bash
make build
```

- [ ] Build starts successfully
- [ ] llama.cpp compiles without errors
- [ ] Llama 2 model downloads (~4 GB)
- [ ] Build completes with "✅ Optional features available: summarization"
- [ ] No critical errors in build output

## Run Phase
```bash
make run
```

- [ ] Container starts successfully
- [ ] Accessible at http://localhost:7860
- [ ] No immediate errors in `docker logs silent-scribe`

## Health Check
```bash
curl http://localhost:7860/health
```

- [ ] Returns `{"status": "ok", "summarization_available": true}`

## UI Tests

### Settings Persistence
- [ ] Change engine to "whisper.cpp"
- [ ] Change model to "medium"
- [ ] Change language to "Spanish"
- [ ] Enable speaker detection
- [ ] Change thread count
- [ ] Refresh page
- [ ] ✓ All settings remembered

### Speaker Detection UI
- [ ] Green box visible and prominent
- [ ] Larger checkbox (easy to click)
- [ ] Description text clear and informative
- [ ] Checkbox state persists after reload

### Default Language
- [ ] Clear browser localStorage
- [ ] Reload page
- [ ] ✓ Language defaults to "English"

## Transcription Test

### Basic Transcription
- [ ] Upload a short video file (1-2 min recommended)
- [ ] Click "Start Transcription"
- [ ] Progress bar updates smoothly
- [ ] Transcription completes successfully
- [ ] TXT file available and readable
- [ ] SRT file available and readable
- [ ] VTT file available and readable
- [ ] "Generate Summary" button appears

### Concurrent Job Blocking
- [ ] Start a transcription
- [ ] Try to upload another video while first is processing
- [ ] ✓ Second upload should be blocked or queued

## Summarization Test

### Summary Generation
- [ ] Click "✨ Generate Summary" button
- [ ] Button shows spinner: "Generating Summary..."
- [ ] Summary completes in reasonable time (30-120 seconds)
- [ ] Summary tab appears
- [ ] Bullet points displayed (5-10 bullets)
- [ ] Paragraph summary displayed (150-250 words)
- [ ] Both summaries are coherent and relevant

### Summary Persistence
- [ ] Refresh page after summary generated
- [ ] ✓ Summary tab still visible
- [ ] ✓ Bullet points load correctly
- [ ] ✓ Paragraph loads correctly
- [ ] ✓ "Generate Summary" button no longer visible

### Summary Download
- [ ] Click "⬇️ Download Bullets"
- [ ] ✓ File downloads and opens correctly
- [ ] Click "⬇️ Download Paragraph"
- [ ] ✓ File downloads and opens correctly

## Network Isolation
```bash
docker inspect silent-scribe | grep NetworkMode
```

- [ ] Output shows `"NetworkMode": "none"`

## Performance Tests

### Transcription Performance
- [ ] Short video (1-2 min): Completes in reasonable time
- [ ] Progress updates regularly
- [ ] CPU usage high but not frozen
- [ ] Memory usage stable

### Summarization Performance
Test with different transcript lengths:
- [ ] Short transcript (<1000 words): ~30 seconds
- [ ] Medium transcript (1000-5000 words): ~60 seconds
- [ ] Long transcript (>5000 words): ~120 seconds
- [ ] CPU usage high during generation
- [ ] Memory usage stable (~4-6 GB)

## Error Handling

### Invalid File
- [ ] Upload a non-video file
- [ ] ✓ Error message appears
- [ ] ✓ System doesn't crash

### System Busy
- [ ] Start transcription
- [ ] Try to generate summary for another job
- [ ] ✓ "System is busy" message appears

### Network Isolation
Try to access external resources:
```bash
docker exec silent-scribe curl -I https://google.com --max-time 5
```
- [ ] ✓ Connection should fail/timeout

## Cleanup Tests

### Delete Job
- [ ] Click delete on a job
- [ ] ✓ Job removed from history
- [ ] ✓ Files removed from disk

### Delete All
- [ ] Click "🗑️ Delete All"
- [ ] Confirm deletion
- [ ] ✓ All jobs removed
- [ ] ✓ History shows empty state

## Integration Tests

### Full Workflow
1. [ ] Upload video
2. [ ] Transcribe with speaker detection enabled
3. [ ] Verify transcription completed
4. [ ] Generate summary
5. [ ] Verify summary appears
6. [ ] Download all files (TXT, SRT, VTT, Bullets, Paragraph)
7. [ ] Refresh page
8. [ ] Verify all data persists
9. [ ] Delete job
10. [ ] Verify cleanup complete

## Browser Compatibility
Test in multiple browsers:
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari (if on Mac)
- [ ] Edge

## Known Issues to Watch For
- [ ] Summarization takes longer on ARM (M2) - normal
- [ ] Large transcripts (>10k chars) trigger chunking - normal
- [ ] Summary generation blocks transcription - by design
- [ ] Summaries in English only - by design

## Success Criteria
✅ All critical tests pass
✅ No data loss
✅ Network isolation maintained
✅ Settings persist correctly
✅ Summarization works end-to-end
✅ UI/UX improvements visible and functional

## Notes
- First build takes 30-60 minutes
- Summarization requires ~6 GB free RAM
- Performance varies by CPU (better on recent processors)
- M2 Mac: Expect slightly slower summarization but should work fine

---

**Test Date**: _______________
**Tester**: _______________
**Version**: _______________
**Platform**: [ ] Linux x86_64  [ ] Mac ARM64  [ ] Other: _______________
**Result**: [ ] PASS  [ ] FAIL  [ ] PARTIAL

**Issues Found**:
