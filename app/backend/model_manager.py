"""Model management for runtime downloads and cleanup."""
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import asyncio

class ModelInfo:
    """Information about a Whisper model."""
    
    # Approximate sizes in MB (compressed downloads)
    SIZES = {
        "tiny": 75,
        "base": 145,
        "small": 465,
        "medium": 1500,
        "large-v3": 2900
    }
    
    def __init__(self, name: str, models_dir: Path):
        self.name = name
        self.models_dir = models_dir
        self.fw_path = models_dir / "faster_whisper" / name
        self.wc_path = models_dir / "whisper_cpp" / name
    
    @property
    def is_installed(self) -> bool:
        """Check if model is installed (both FW and WC versions exist)."""
        fw_installed = self.fw_path.exists() and any(self.fw_path.iterdir())
        
        # Check whisper.cpp model file
        wc_files = {
            "tiny": "ggml-tiny.bin",
            "base": "ggml-base.bin",
            "small": "ggml-small.bin",
            "medium": "ggml-medium.bin",
            "large-v3": "ggml-large-v3.bin"
        }
        wc_file = self.wc_path / wc_files.get(self.name, f"ggml-{self.name}.bin")
        wc_installed = wc_file.exists()
        
        return fw_installed and wc_installed
    
    @property
    def estimated_size_mb(self) -> int:
        """Get estimated download size in MB."""
        return self.SIZES.get(self.name, 500)
    
    @property
    def actual_size_mb(self) -> Optional[int]:
        """Get actual disk usage in MB if installed."""
        if not self.is_installed:
            return None
        
        total_bytes = 0
        
        # Calculate FW model size
        if self.fw_path.exists():
            for item in self.fw_path.rglob("*"):
                if item.is_file():
                    total_bytes += item.stat().st_size
        
        # Calculate WC model size
        if self.wc_path.exists():
            for item in self.wc_path.rglob("*"):
                if item.is_file():
                    total_bytes += item.stat().st_size
        
        return int(total_bytes / (1024 * 1024))
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "name": self.name,
            "installed": self.is_installed,
            "estimated_size_mb": self.estimated_size_mb,
            "actual_size_mb": self.actual_size_mb,
            "can_delete": self.name != "tiny"  # Don't allow deleting tiny (minimum)
        }


class ModelManager:
    """Manage Whisper model downloads and deletions."""
    
    AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
    
    def __init__(self, models_dir: Path):
        self.models_dir = models_dir
        self._download_tasks = {}  # model_name -> asyncio.Task
        self._download_progress = {}  # model_name -> progress %
    
    def list_models(self) -> List[Dict]:
        """List all available models with their status."""
        models = []
        for model_name in self.AVAILABLE_MODELS:
            model_info = ModelInfo(model_name, self.models_dir)
            models.append(model_info.to_dict())
        return models
    
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """Get info for a specific model."""
        if model_name not in self.AVAILABLE_MODELS:
            return None
        return ModelInfo(model_name, self.models_dir)
    
    async def download_model(self, model_name: str, progress_callback=None) -> bool:
        """
        Download a specific model.
        
        Returns True if successful, False otherwise.
        """
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(f"Invalid model name: {model_name}")
        
        # Check if already downloading
        if model_name in self._download_tasks:
            task = self._download_tasks[model_name]
            if not task.done():
                raise RuntimeError(f"Model {model_name} is already being downloaded")
        
        # Check if already installed
        model_info = ModelInfo(model_name, self.models_dir)
        if model_info.is_installed:
            if progress_callback:
                progress_callback(100, "Model already installed")
            return True
        
        # Download using fetch_models.py script
        try:
            if progress_callback:
                progress_callback(0, f"Starting download of {model_name}...")
            
            # Run the fetch script for this specific model
            process = await asyncio.create_subprocess_exec(
                "python3",
                "/tmp/fetch_models.py",
                "--models", model_name,
                "--skip-existing",
                "--skip-optional",  # Don't download pyannote/llama during runtime
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd="/app/backend"
            )
            
            # Track progress by reading output
            progress = 0
            async for line in process.stdout:
                line_str = line.decode().strip()
                print(f"[ModelManager] {line_str}")
                
                # Update progress based on output
                if "Downloading" in line_str:
                    progress = min(progress + 10, 90)
                elif "Saved to" in line_str:
                    progress = min(progress + 10, 95)
                elif "present" in line_str:
                    progress = 100
                
                if progress_callback:
                    progress_callback(progress, line_str)
            
            await process.wait()
            
            if process.returncode == 0:
                if progress_callback:
                    progress_callback(100, f"Model {model_name} downloaded successfully")
                return True
            else:
                if progress_callback:
                    progress_callback(-1, f"Download failed with code {process.returncode}")
                return False
        
        except Exception as e:
            if progress_callback:
                progress_callback(-1, f"Download error: {str(e)}")
            return False
    
    async def delete_model(self, model_name: str) -> bool:
        """
        Delete a model to free up space.
        
        Returns True if successful, False otherwise.
        """
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(f"Invalid model name: {model_name}")
        
        # Don't allow deleting tiny (it's the default minimum)
        if model_name == "tiny":
            raise ValueError("Cannot delete the 'tiny' model (it's the minimum required model)")
        
        model_info = ModelInfo(model_name, self.models_dir)
        
        if not model_info.is_installed:
            return False  # Already deleted/not installed
        
        try:
            # Delete faster-whisper model
            if model_info.fw_path.exists():
                shutil.rmtree(model_info.fw_path)
            
            # Delete whisper.cpp model
            if model_info.wc_path.exists():
                shutil.rmtree(model_info.wc_path)
            
            return True
        
        except Exception as e:
            print(f"Error deleting model {model_name}: {e}")
            return False
    
    def get_total_models_size_mb(self) -> int:
        """Get total size of all installed models in MB."""
        total = 0
        for model_name in self.AVAILABLE_MODELS:
            model_info = ModelInfo(model_name, self.models_dir)
            if model_info.actual_size_mb:
                total += model_info.actual_size_mb
        return total
