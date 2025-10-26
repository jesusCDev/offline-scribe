#!/usr/bin/env python3
"""
Fetch whisper models. Can fetch all models or specific ones.
Supports both Docker build time and runtime downloads.

Usage:
    # Fetch all models
    python fetch_models.py
    
    # Fetch specific models only
    python fetch_models.py --models tiny base
    
    # Skip already downloaded models
    python fetch_models.py --skip-existing
"""
import os
import sys
import shutil
import argparse
from pathlib import Path
from huggingface_hub import hf_hub_download, snapshot_download, login

MODELS_BASE = Path("/opt/models")
FW_BASE = MODELS_BASE / "faster_whisper"
WC_BASE = MODELS_BASE / "whisper_cpp"
PYANNOTE_BASE = MODELS_BASE / "pyannote"
LLAMA_BASE = MODELS_BASE / "llama"

# All available model sizes
ALL_SIZES = ["tiny", "base", "small", "medium", "large-v3"]

def fetch_faster_whisper_models(sizes_to_fetch=None, skip_existing=False):
    """Download faster-whisper CTranslate2 models."""
    if sizes_to_fetch is None:
        sizes_to_fetch = ALL_SIZES
    
    print("📦 Fetching faster-whisper models...")
    FW_BASE.mkdir(parents=True, exist_ok=True)
    
    for size in sizes_to_fetch:
        target = FW_BASE / size
        if skip_existing and target.exists() and any(target.iterdir()):
            print(f"  ⚡ {size} already exists, skipping")
            continue
            
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

def fetch_whisper_cpp_models(sizes_to_fetch=None, skip_existing=False):
    """Download whisper.cpp GGML models."""
    if sizes_to_fetch is None:
        sizes_to_fetch = ALL_SIZES
    
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
        if size not in sizes_to_fetch:
            continue
            
        target_file = WC_BASE / size / filename
        if skip_existing and target_file.exists():
            size_mb = target_file.stat().st_size / (1024 * 1024)
            print(f"  ⚡ {filename} already exists ({size_mb:.1f} MB), skipping")
            continue
            
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

def verify_models(expected_sizes=None):
    """Verify expected models are present."""
    if expected_sizes is None:
        expected_sizes = ALL_SIZES
        
    print("\n🔍 Verifying models...")
    
    missing = []
    
    # Check faster-whisper
    for size in expected_sizes:
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
        if size not in expected_sizes:
            continue
        path = WC_BASE / size / filename
        if not path.exists():
            missing.append(f"whisper.cpp/{size}/{filename}")
    
    if missing:
        print("  ✗ Missing expected models:")
        for m in missing:
            print(f"    - {m}")
        sys.exit(1)
    
    print("  ✓ All expected models present!")
    
    # Print summary
    total_size = sum(f.stat().st_size for f in MODELS_BASE.rglob("*") if f.is_file())
    print(f"\n📊 Total models size: {total_size / (1024**3):.2f} GB")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Whisper models")
    parser.add_argument(
        "--models",
        nargs="*",
        choices=ALL_SIZES,
        help="Specific models to fetch (default: all)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip models that are already downloaded"
    )
    parser.add_argument(
        "--skip-optional",
        action="store_true",
        help="Skip optional models (pyannote, llama)"
    )
    
    args = parser.parse_args()
    
    # Determine which models to fetch
    models_to_fetch = args.models if args.models else ALL_SIZES
    
    print("🚀 Starting model fetch...\n")
    print(f"📋 Models to fetch: {', '.join(models_to_fetch)}")
    if args.skip_existing:
        print("⚡ Skip-existing mode enabled\n")
    
    fetch_faster_whisper_models(models_to_fetch, args.skip_existing)
    fetch_whisper_cpp_models(models_to_fetch, args.skip_existing)
    
    # Optional models
    pyannote_available = False
    llama_available = False
    
    if not args.skip_optional:
        pyannote_available = fetch_pyannote_models(skip_existing=args.skip_existing)
        llama_available = fetch_llama2_chat_model(skip_existing=args.skip_existing)
    
    verify_models(models_to_fetch)
    
    features = []
    if pyannote_available:
        features.append("diarization")
    if llama_available:
        features.append("summarization")
    
    print("\n✅ Whisper models fetched successfully!")
    if features:
        print(f"✅ Optional features available: {', '.join(features)}")
    if not args.skip_optional:
        if not pyannote_available:
            print("⚠️  Diarization models skipped - feature will be disabled")
        if not llama_available:
            print("⚠️  Llama model skipped - summarization feature will be disabled")
