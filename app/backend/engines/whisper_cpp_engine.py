"""Whisper.cpp engine adapter."""
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, Callable

class WhisperCppEngine:
    """Adapter for whisper.cpp transcription."""
    
    def __init__(self, models_dir: Path, binary_path: str = "/opt/whisper.cpp/main"):
        self.models_dir = models_dir / "whisper_cpp"
        self.binary_path = binary_path
    
    def transcribe(
        self,
        audio_path: Path,
        output_dir: Path,
        model: str,
        settings: Dict[str, Any],
        progress_callback: Callable[[int], None]
    ) -> Dict[str, Path]:
        """
        Transcribe audio using whisper.cpp.
        
        Returns dict of output format -> file path.
        """
        # Find model file
        model_dir = self.models_dir / model
        if not model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {model_dir}")
        
        # Find .bin file in model directory
        model_files = list(model_dir.glob("*.bin"))
        if not model_files:
            raise FileNotFoundError(f"No .bin model file found in {model_dir}")
        
        model_path = model_files[0]
        
        # Extract settings
        threads = settings.get("threads", 4)
        beam_size = settings.get("beam_size", 5)
        temperature = settings.get("temperature", 0.0)
        language = settings.get("language", "auto")
        
        # Output base (without extension)
        output_base = output_dir / "transcript"
        
        # Build command
        cmd = [
            self.binary_path,
            "-m", str(model_path),
            "-f", str(audio_path),
            "-t", str(threads),
            "-bs", str(beam_size),
            "-of", str(output_base),
            "-otxt",
            "-osrt",
            "-ovtt"
        ]
        
        if language != "auto":
            cmd.extend(["-l", language])
        
        # Run transcription with progress tracking
        progress_callback(10)  # Starting
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Parse output for progress
            last_progress = 10
            for line in process.stdout:
                # Look for progress indicators in output
                # whisper.cpp typically outputs progress like: "[00:00:10.000 --> 00:00:12.000]"
                if "-->" in line:
                    # Rough progress estimate based on timestamps
                    progress = min(last_progress + 5, 95)
                    if progress > last_progress:
                        progress_callback(progress)
                        last_progress = progress
            
            process.wait()
            
            if process.returncode != 0:
                raise RuntimeError(f"whisper.cpp exited with code {process.returncode}")
            
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {e}")
        
        progress_callback(100)
        
        # Return generated files
        outputs = {}
        
        txt_path = Path(f"{output_base}.txt")
        if txt_path.exists():
            outputs["txt"] = txt_path
        
        srt_path = Path(f"{output_base}.srt")
        if srt_path.exists():
            outputs["srt"] = srt_path
        
        vtt_path = Path(f"{output_base}.vtt")
        if vtt_path.exists():
            outputs["vtt"] = vtt_path
        
        if not outputs:
            raise RuntimeError("No output files generated")
        
        return outputs
