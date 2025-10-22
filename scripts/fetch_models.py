#!/usr/bin/env python3
"""
Fetch all required whisper models during Docker build.
This script runs with network access during build time only.
"""
import os
import sys
import shutil
from pathlib import Path
from huggingface_hub import hf_hub_download, snapshot_download

MODELS_BASE = Path("/opt/models")
FW_BASE = MODELS_BASE / "faster_whisper"
WC_BASE = MODELS_BASE / "whisper_cpp"

# Model sizes to download
SIZES = ["tiny", "base", "small", "medium", "large-v3"]

def fetch_faster_whisper_models():
    """Download faster-whisper CTranslate2 models."""
    print("📦 Fetching faster-whisper models...")
    FW_BASE.mkdir(parents=True, exist_ok=True)
    
    for size in SIZES:
        print(f"  - Downloading {size}...")
        model_name = f"guillaumekln/faster-whisper-{size}"
        if size == "large-v3":
            model_name = "guillaumekln/faster-whisper-large-v3"
        
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
    print("🚀 Starting model fetch...\n")
    fetch_faster_whisper_models()
    fetch_whisper_cpp_models()
    verify_models()
    print("\n✅ All models fetched successfully!")
