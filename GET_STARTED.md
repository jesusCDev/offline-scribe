# 🚀 Get Started with Silent Scribe

**The simplest way to use Silent Scribe!**

---

## Two Ways to Get Started

### Option A: Build from Scratch (30-60 min)

If you have internet access:

```bash
./build
```

This downloads all AI models and builds the container. **Only needs to be done once!**

### Option B: Load Pre-Built Image (5-10 min)

If someone gave you `silent-scribe-image.tar.gz`:

```bash
./load
```

This loads the pre-built image. **Much faster!** See [DISTRIBUTION.md](DISTRIBUTION.md) for details.

---

## Using Silent Scribe

### 1. Start

---

### 2. Start

```bash
./start
```

This starts the application at **http://localhost:7860**

Open your browser and start transcribing!

---

### 3. Stop

Just press **Ctrl+C** in the terminal where `./start` is running.

The container will automatically clean up. Done!

---

## That's It! 🎉

Really. Three commands. That's all you need to know.

---

## Need More Help?

- **First time?** Read [docs/DEMO.md](docs/DEMO.md)
- **Quick reference:** [docs/QUICKSTART.md](docs/QUICKSTART.md)
- **Having issues?** Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **Full documentation:** [README.md](README.md)

---

## Alternative: Use Make

If you prefer, you can also use `make`:

```bash
make build    # Build the image
make run      # Start the app
make stop     # Stop the app
```

Both work exactly the same way!
