"""Main FastAPI application."""
import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import settings, AVAILABLE_ENGINES, AVAILABLE_MODELS, AVAILABLE_COMPUTE_TYPES
from .job_manager import JobManager
from .engines.faster_whisper_engine import FasterWhisperEngine
from .engines.whisper_cpp_engine import WhisperCppEngine

# Initialize app
app = FastAPI(title="Silent Scribe - Air-Gapped Video Transcription")

# Ensure directories exist
settings.uploads_dir.mkdir(parents=True, exist_ok=True)
settings.results_dir.mkdir(parents=True, exist_ok=True)

# Initialize components
job_manager = JobManager(settings.results_dir)
fw_engine = FasterWhisperEngine(settings.models_dir)
wc_engine = WhisperCppEngine(settings.models_dir)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="/app/frontend"), name="static")
except:
    pass  # Frontend may not exist yet during development

# Models
class ConfigResponse(BaseModel):
    engines: list[str]
    models: list[str]
    compute_types: list[str]
    defaults: dict

class JobStatusResponse(BaseModel):
    job_id: str
    filename: str
    engine: str
    model: str
    status: str
    progress: int
    created_at: str
    completed_at: Optional[str]
    error: Optional[str]
    result_files: Optional[dict]

# Routes
@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the web UI."""
    try:
        with open("/app/templates/index.html") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Helen Keller - Air-Gapped Transcription</h1><p>UI not yet available. Use API directly.</p>"

@app.get("/api/config")
async def get_config():
    """Get available configuration options."""
    import os
    cpu_count = os.cpu_count() or 4
    return ConfigResponse(
        engines=AVAILABLE_ENGINES,
        models=AVAILABLE_MODELS,
        compute_types=AVAILABLE_COMPUTE_TYPES,
        defaults={
            "engine": settings.default_engine,
            "model": settings.default_model,
            "compute_type": settings.default_compute_type,
            "threads": settings.default_threads,
            "min_threads": 1,
            "max_threads": cpu_count,
            "beam_size": 5,
            "temperature": 0.0,
            "vad_filter": True,
            "language": "auto"
        }
    )

@app.post("/api/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    engine: str = Form(...),
    model: str = Form(...),
    compute_type: str = Form("int8_float16"),
    threads: int = Form(4),
    beam_size: int = Form(5),
    temperature: float = Form(0.0),
    vad_filter: bool = Form(True),
    language: str = Form("auto")
):
    """Upload and transcribe a video file."""
    
    # Validate inputs
    if engine not in AVAILABLE_ENGINES:
        raise HTTPException(400, f"Invalid engine: {engine}")
    if model not in AVAILABLE_MODELS:
        raise HTTPException(400, f"Invalid model: {model}")
    
    # Create job
    job = await job_manager.create_job(file.filename, engine, model)
    if not job:
        raise HTTPException(409, "A transcription is already in progress")
    
    # Save uploaded file
    upload_path = settings.uploads_dir / f"{job.job_id}_{file.filename}"
    try:
        with open(upload_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        job_manager.update_job(job.job_id, status="failed", error=str(e))
        raise HTTPException(500, f"Failed to save upload: {e}")
    
    # Start transcription in background
    asyncio.create_task(
        process_transcription(
            job.job_id,
            upload_path,
            engine,
            model,
            {
                "compute_type": compute_type,
                "threads": threads,
                "beam_size": beam_size,
                "temperature": temperature,
                "vad_filter": vad_filter,
                "language": language
            }
        )
    )
    
    return {"job_id": job.job_id, "status": "pending"}

@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get job status."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    return JobStatusResponse(
        job_id=job.job_id,
        filename=job.filename,
        engine=job.engine,
        model=job.model,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error=job.error,
        result_files=job.result_files
    )

@app.get("/api/jobs/{job_id}/result.{format}")
async def download_result(job_id: str, format: str):
    """Download transcription result."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    if job.status != "completed":
        raise HTTPException(400, "Job not completed")
    
    if not job.result_files or format not in job.result_files:
        raise HTTPException(404, f"Format {format} not available")
    
    file_path = Path(job.result_files[format])
    if not file_path.exists():
        raise HTTPException(404, "Result file not found")
    
    return FileResponse(
        file_path,
        media_type="text/plain",
        filename=f"{job.filename}.{format}"
    )

@app.get("/api/history")
async def get_history(limit: int = 20):
    """Get transcription history."""
    jobs = job_manager.list_jobs(limit=limit)
    return [
        JobStatusResponse(
            job_id=job.job_id,
            filename=job.filename,
            engine=job.engine,
            model=job.model,
            status=job.status,
            progress=job.progress,
            created_at=job.created_at,
            completed_at=job.completed_at,
            error=job.error,
            result_files=job.result_files
        )
        for job in jobs
    ]

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}

# Background processing
async def process_transcription(
    job_id: str,
    video_path: Path,
    engine: str,
    model: str,
    settings_dict: dict
):
    """Process transcription in background."""
    
    def update_progress(progress: int):
        """Callback for progress updates."""
        job_manager.update_job(job_id, progress=progress)
    
    try:
        # Update status to processing
        job_manager.update_job(job_id, status="processing", progress=0)
        
        # Extract audio to WAV
        job_dir = settings.results_dir / job_id
        audio_path = job_dir / "audio.wav"
        
        update_progress(5)
        
        subprocess.run(
            [
                "ffmpeg",
                "-i", str(video_path),
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                "-y",
                str(audio_path)
            ],
            check=True,
            capture_output=True
        )
        
        update_progress(10)
        
        # Transcribe
        if engine == "faster-whisper":
            outputs = fw_engine.transcribe(
                audio_path,
                job_dir,
                model,
                settings_dict,
                update_progress
            )
        else:  # whisper.cpp
            outputs = wc_engine.transcribe(
                audio_path,
                job_dir,
                model,
                settings_dict,
                update_progress
            )
        
        # Store result paths
        result_files = {k: str(v) for k, v in outputs.items()}
        job_manager.update_job(
            job_id,
            status="completed",
            progress=100,
            result_files=result_files
        )
        
        # Clean up
        video_path.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)
        
    except Exception as e:
        job_manager.update_job(
            job_id,
            status="failed",
            error=str(e)
        )
        # Clean up on failure
        video_path.unlink(missing_ok=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.app_port)
