"""Job management with single-job locking."""
import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class Job:
    """Transcription job."""
    job_id: str
    filename: str
    engine: str
    model: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result_files: Optional[Dict[str, str]] = None

class JobManager:
    """Manages transcription jobs with single-job enforcement."""
    
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.current_job: Optional[Job] = None
        self._lock = asyncio.Lock()
    
    async def create_job(
        self,
        filename: str,
        engine: str,
        model: str
    ) -> Optional[Job]:
        """Create a new job if no job is currently processing."""
        async with self._lock:
            if self.current_job and self.current_job.status == "processing":
                return None  # Busy
            
            job = Job(
                job_id=str(uuid.uuid4()),
                filename=filename,
                engine=engine,
                model=model,
                status="pending",
                progress=0,
                created_at=datetime.utcnow().isoformat()
            )
            
            self.current_job = job
            
            # Create job directory
            job_dir = self.results_dir / job.job_id
            job_dir.mkdir(parents=True, exist_ok=True)
            
            # Save job metadata
            self._save_job(job)
            
            return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        if self.current_job and self.current_job.job_id == job_id:
            return self.current_job
        
        # Try to load from disk
        job_file = self.results_dir / job_id / "job.json"
        if job_file.exists():
            with open(job_file) as f:
                data = json.load(f)
                return Job(**data)
        
        return None
    
    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        error: Optional[str] = None,
        result_files: Optional[Dict[str, str]] = None
    ):
        """Update job status."""
        job = self.get_job(job_id)
        if not job:
            return
        
        if status:
            job.status = status
        if progress is not None:
            job.progress = progress
        if error:
            job.error = error
        if result_files:
            job.result_files = result_files
        
        if status in ("completed", "failed"):
            job.completed_at = datetime.utcnow().isoformat()
        
        self._save_job(job)
        
        if self.current_job and self.current_job.job_id == job_id:
            self.current_job = job
    
    def _save_job(self, job: Job):
        """Save job metadata to disk."""
        job_file = self.results_dir / job.job_id / "job.json"
        with open(job_file, "w") as f:
            json.dump(asdict(job), f, indent=2)
    
    def list_jobs(self, limit: int = 50) -> list[Job]:
        """List recent jobs."""
        jobs = []
        
        for job_dir in sorted(
            self.results_dir.iterdir(),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        ):
            if not job_dir.is_dir():
                continue
            
            job_file = job_dir / "job.json"
            if not job_file.exists():
                continue
            
            try:
                with open(job_file) as f:
                    data = json.load(f)
                    jobs.append(Job(**data))
                
                if len(jobs) >= limit:
                    break
            except:
                continue
        
        return jobs
