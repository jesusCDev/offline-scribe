#!/usr/bin/env python3
"""
Fetch all required whisper models during Docker build.
This script runs with network access during build time only.
"""
import os
import sys
import shutil
from pathlib import Path
from huggingface_hub import hf_hub_download, snapshot_download, login

MODELS_BASE = Path("/opt/models")
FW_BASE = MODELS_BASE / "faster_whisper"
WC_BASE = MODELS_BASE / "whisper_cpp"
PYANNOTE_BASE = MODELS_BASE / "pyannote"
LLAMA_BASE = MODELS_BASE / "llama"

# Model sizes to download
SIZES = ["tiny", "base", "small", "medium", "large-v3"]

def fetch_faster_whisper_models():
    """Download faster-whisper CTranslate2 models."""
    print("📦 Fetching faster-whisper models...")
    FW_BASE.mkdir(parents=True, exist_ok=True)
    
    for size in SIZES:
        print(f"  - Downloading {size}...")
        # Use correct model names
        if size == "large-v3":
            model_name = "Systran/faster-whisper-large-v3"
        else:
            model_name = f"guillaumekln/faster-whisper-{size}"
        
        try:
            cache_dir = snapshot_download(
                repo_id=model_name,
                cache_dir="/tmp/fw_cache"
            )
            
            target = FW_BASE / size
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(cache_dir, target)
            print(f"    ✓ Saved to {target}")
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            sys.exit(1)

def fetch_whisper_cpp_models():
    """Download whisper.cpp GGML models."""
    print("\n📦 Fetching whisper.cpp GGML models...")
    WC_BASE.mkdir(parents=True, exist_ok=True)
    
    models = {
        "tiny": "ggml-tiny.bin",
        "base": "ggml-base.bin",
        "small": "ggml-small.bin",
        "medium": "ggml-medium.bin",
        "large-v3": "ggml-large-v3.bin"
    }
    
    for size, filename in models.items():
        print(f"  - Downloading {filename}...")
        target_dir = WC_BASE / size
        target_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            file_path = hf_hub_download(
                repo_id="ggerganov/whisper.cpp",
                filename=filename,
                cache_dir="/tmp/wc_cache"
            )
            
            target_file = target_dir / filename
            shutil.copy2(file_path, target_file)
            size_mb = target_file.stat().st_size / (1024 * 1024)
            print(f"    ✓ Saved to {target_file} ({size_mb:.1f} MB)")
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            sys.exit(1)

def fetch_pyannote_models(skip_existing=False):
    """Download pyannote speaker diarization models."""
    print("\n📦 Fetching pyannote models...")
    
    # Check if already exists
    target = PYANNOTE_BASE / "speaker-diarization-3.1"
    if skip_existing and target.exists() and any(target.iterdir()):
        print(f"  ⚡ Model already exists at {target}, skipping")
        return True
    
    # Login with HF token if available (required for gated models)
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("  ⚠️  No HF_TOKEN found, skipping pyannote models (diarization will be disabled)")
        return False
    
    try:
        login(token=hf_token)
        print("  ✓ Authenticated with Hugging Face")
    except Exception as e:
        print(f"  ✗ Authentication failed: {e}")
        print("  ⚠️  Skipping pyannote models (diarization will be disabled)")
        return False
    
    PYANNOTE_BASE.mkdir(parents=True, exist_ok=True)
    
    # Download speaker diarization pipeline and its dependencies
    # Keep them in HF cache format so pyannote can load them properly
    models_to_download = [
        "pyannote/speaker-diarization-3.1",
        "pyannote/segmentation-3.0",
        "pyannote/wespeaker-voxceleb-resnet34-LM"
    ]
    
    for model_name in models_to_download:
        print(f"  - Downloading {model_name}...")
        
        try:
            # Download directly to the pyannote cache directory
            # This keeps the HF cache structure that pyannote expects
            snapshot_download(
                repo_id=model_name,
                cache_dir=str(PYANNOTE_BASE)
            )
            print(f"    ✓ Cached {model_name}")
        except Exception as e:
            print(f"    ✗ Failed: {e}")
            print("  ⚠️  Diarization will be disabled")
            return False
    
    return True

def fetch_llama2_chat_model(skip_existing=False):
    """Download Llama 2 7B Chat GGUF model for summarization."""
    print("\n📦 Fetching Llama 2 7B Chat model...")
    
    LLAMA_BASE.mkdir(parents=True, exist_ok=True)
    target_file = LLAMA_BASE / "llama-2-7b-chat.Q4_K_M.gguf"
    
    # Check if already exists
    if skip_existing and target_file.exists():
        size_mb = target_file.stat().st_size / (1024 * 1024)
        print(f"  ⚡ Model already exists at {target_file} ({size_mb:.1f} MB), skipping")
        return True
    
    print(f"  - Downloading llama-2-7b-chat.Q4_K_M.gguf...")
    
    try:
        file_path = hf_hub_download(
            repo_id="TheBloke/Llama-2-7B-Chat-GGUF",
            filename="llama-2-7b-chat.Q4_K_M.gguf",
            cache_dir="/tmp/llama_cache"
        )
        
        shutil.copy2(file_path, target_file)
        size_mb = target_file.stat().st_size / (1024 * 1024)
        print(f"    ✓ Saved to {target_file} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        print("  ⚠️  Summarization feature will be disabled")
        return False

def verify_models():
    """Verify all models are present."""
    print("\n🔍 Verifying models...")
    
    missing = []
    
    # Check faster-whisper
    for size in SIZES:
        path = FW_BASE / size
        if not path.exists() or not any(path.iterdir()):
            missing.append(f"faster-whisper/{size}")
    
    # Check whisper.cpp
    models = {
        "tiny": "ggml-tiny.bin",
        "base": "ggml-base.bin",
        "small": "ggml-small.bin",
        "medium": "ggml-medium.bin",
        "large-v3": "ggml-large-v3.bin"
    }
    
    for size, filename in models.items():
        path = WC_BASE / size / filename
        if not path.exists():
            missing.append(f"whisper.cpp/{size}/{filename}")
    
    if missing:
        print("  ✗ Missing models:")
        for m in missing:
            print(f"    - {m}")
        sys.exit(1)
    
    print("  ✓ All models present!")
    
    # Print summary
    total_size = sum(f.stat().st_size for f in MODELS_BASE.rglob("*") if f.is_file())
    print(f"\n📊 Total models size: {total_size / (1024**3):.2f} GB")

if __name__ == "__main__":
    import sys
    skip_existing = "--skip-existing" in sys.argv
    
    print("🚀 Starting model fetch...\n")
    if skip_existing:
        print("⚡ Skip-existing mode: Only downloading missing models\n")
    
    fetch_faster_whisper_models()
    fetch_whisper_cpp_models()
    pyannote_available = fetch_pyannote_models(skip_existing=skip_existing)
    llama_available = fetch_llama2_chat_model(skip_existing=skip_existing)
    verify_models()
    
    features = []
    if pyannote_available:
        features.append("diarization")
    if llama_available:
        features.append("summarization")
    
    print("\n✅ Whisper models fetched successfully!")
    if features:
        print(f"✅ Optional features available: {', '.join(features)}")
    if not pyannote_available:
        print("⚠️  Diarization models skipped - feature will be disabled")
    if not llama_available:
        print("⚠️  Llama model skipped - summarization feature will be disabled")
