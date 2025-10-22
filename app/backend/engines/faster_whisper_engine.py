"""Faster-whisper engine adapter."""
import subprocess
from pathlib import Path
from typing import Dict, Any, Callable
from faster_whisper import WhisperModel
import srt
import webvtt

class FasterWhisperEngine:
    """Adapter for faster-whisper transcription."""
    
    def __init__(self, models_dir: Path):
        self.models_dir = models_dir / "faster_whisper"
    
    def transcribe(
        self,
        audio_path: Path,
        output_dir: Path,
        model: str,
        settings: Dict[str, Any],
        progress_callback: Callable[[int], None]
    ) -> Dict[str, Path]:
        """
        Transcribe audio using faster-whisper.
        
        Returns dict of output format -> file path.
        """
        model_path = self.models_dir / model
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        # Extract settings
        compute_type = settings.get("compute_type", "int8_float16")
        threads = settings.get("threads", 4)
        beam_size = settings.get("beam_size", 5)
        temperature = settings.get("temperature", 0.0)
        vad_filter = settings.get("vad_filter", True)
        language = settings.get("language")
        
        # Get audio duration for progress estimation
        try:
            duration = self._get_audio_duration(audio_path)
        except:
            duration = None
        
        # Load model (path only, no network)
        model_obj = WhisperModel(
            str(model_path),
            device="cpu",
            compute_type=compute_type,
            cpu_threads=threads,
            num_workers=1
        )
        
        # Transcribe with progress tracking
        segments_list = []
        last_progress = 0
        
        segments, info = model_obj.transcribe(
            str(audio_path),
            beam_size=beam_size,
            temperature=temperature,
            vad_filter=vad_filter,
            language=language if language != "auto" else None
        )
        
        for segment in segments:
            segments_list.append(segment)
            
            # Update progress based on audio time if available
            if duration and duration > 0:
                progress = int((segment.end / duration) * 100)
                if progress > last_progress:
                    progress_callback(min(progress, 99))
                    last_progress = progress
        
        # Generate outputs
        outputs = {}
        
        # Plain text
        txt_path = output_dir / "transcript.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            for seg in segments_list:
                f.write(seg.text.strip() + "\n")
        outputs["txt"] = txt_path
        
        # SRT subtitles
        srt_path = output_dir / "transcript.srt"
        srt_content = self._generate_srt(segments_list)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        outputs["srt"] = srt_path
        
        # VTT subtitles
        vtt_path = output_dir / "transcript.vtt"
        vtt_content = self._generate_vtt(segments_list)
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write(vtt_content)
        outputs["vtt"] = vtt_path
        
        progress_callback(100)
        
        return outputs
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration in seconds using ffprobe."""
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        return float(result.stdout.strip())
    
    def _generate_srt(self, segments) -> str:
        """Generate SRT format from segments."""
        srt_items = []
        for i, seg in enumerate(segments, 1):
            srt_items.append(
                srt.Subtitle(
                    index=i,
                    start=self._timedelta_from_seconds(seg.start),
                    end=self._timedelta_from_seconds(seg.end),
                    content=seg.text.strip()
                )
            )
        return srt.compose(srt_items)
    
    def _generate_vtt(self, segments) -> str:
        """Generate WebVTT format from segments."""
        vtt = webvtt.WebVTT()
        for seg in segments:
            caption = webvtt.Caption(
                self._format_timestamp_vtt(seg.start),
                self._format_timestamp_vtt(seg.end),
                seg.text.strip()
            )
            vtt.captions.append(caption)
        
        # Write to string
        import io
        buffer = io.StringIO()
        vtt.write(buffer)
        return buffer.getvalue()
    
    @staticmethod
    def _timedelta_from_seconds(seconds: float):
        """Convert seconds to timedelta."""
        from datetime import timedelta
        return timedelta(seconds=seconds)
    
    @staticmethod
    def _format_timestamp_vtt(seconds: float) -> str:
        """Format timestamp for VTT."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
