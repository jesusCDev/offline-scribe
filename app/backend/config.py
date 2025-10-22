"""Application configuration."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    app_port: int = 7860
    default_engine: str = "faster-whisper"
    default_model: str = "small"
    default_compute_type: str = "int8_float16"
    default_threads: int = os.cpu_count() or 4
    results_keep_days: int = 30
    max_upload_size_mb: int = 2000
    
    # Paths
    data_dir: Path = Path("/data")
    models_dir: Path = Path("/opt/models")
    
    @property
    def uploads_dir(self) -> Path:
        """Uploads directory."""
        return self.data_dir / "uploads"
    
    @property
    def results_dir(self) -> Path:
        """Results directory."""
        return self.data_dir / "results"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

# Available options for UI
AVAILABLE_ENGINES = ["faster-whisper", "whisper.cpp"]
AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
AVAILABLE_COMPUTE_TYPES = ["int8", "int8_float16", "int16", "float32"]
