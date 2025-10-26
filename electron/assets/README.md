# Icon Assets

## Current Status
- ✅ `icon.svg` - Source vector icon
- ✅ `icon.png` - 1024x1024 PNG (placeholder)
- ⏳ `icon.icns` - macOS icon (needs generation)
- ⏳ `icon.ico` - Windows icon (needs generation)

## Generate Platform-Specific Icons

### macOS (.icns)
```bash
# Install iconutil (comes with Xcode on Mac) or use electron-icon-builder
npm install -g electron-icon-builder
electron-icon-builder --input=./icon.png --output=. --flatten
```

Or use online tools like https://cloudconvert.com/png-to-icns

### Windows (.ico)
```bash
# Use ImageMagick
magick convert icon.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico
```

Or use online tools like https://convertio.co/png-ico/

### Linux
Linux uses PNG files directly. electron-builder will auto-generate required sizes from icon.png.

## TODO
- [ ] Generate icon.icns for macOS builds
- [ ] Generate icon.ico for Windows builds  
- [ ] Replace placeholder icon with final design
- [ ] Test icons on all platforms

## Notes
The current icon is a placeholder showing a "muted microphone" with a slash, representing "silent" transcription. Feel free to replace `icon.svg` and regenerate all formats.
