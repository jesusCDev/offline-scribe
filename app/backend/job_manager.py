"""Job management with single-job locking."""
import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class SummaryInfo:
    """Summary status information."""
    status: str = "idle"  # idle, processing, completed, error
    progress: int = 0
    bullets_path: Optional[str] = None
    paragraph_path: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None

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
    summary: Optional[Dict[str, Any]] = None  # Summary information

class JobManager:
    """Manages transcription jobs with single-job enforcement."""
    
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.current_job: Optional[Job] = None
        self._lock = asyncio.Lock()
        self._is_busy = False  # Track if transcription OR summarization is running
    
    async def create_job(
        self,
        filename: str,
        engine: str,
        model: str
    ) -> Optional[Job]:
        """Create a new job if no job is currently processing."""
        async with self._lock:
            if self._is_busy:
                return None  # Busy with transcription or summarization
            
            job = Job(
                job_id=str(uuid.uuid4()),
                filename=filename,
                engine=engine,
                model=model,
                status="pending",
                progress=0,
                created_at=datetime.utcnow().isoformat(),
                summary={"status": "idle", "progress": 0}
            )
            
            self._is_busy = True
            
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
            # Release busy lock when transcription completes or fails
            if self._is_busy and self.current_job and self.current_job.job_id == job_id:
                self._is_busy = False
        
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
    
    async def can_start_summarization(self, job_id: str) -> bool:
        """Check if summarization can start for this job."""
        async with self._lock:
            if self._is_busy:
                return False
            
            job = self.get_job(job_id)
            if not job:
                return False
            
            # Can only summarize completed transcriptions
            if job.status != "completed":
                return False
            
            # Check if transcript file exists
            transcript_path = self.results_dir / job_id / "transcript.txt"
            return transcript_path.exists()
    
    async def start_summarization(self, job_id: str) -> bool:
        """Mark summarization as starting."""
        async with self._lock:
            # Check conditions inline to avoid deadlock
            if self._is_busy:
                return False
            
            job = self.get_job(job_id)
            if not job or job.status != "completed":
                return False
            
            transcript_path = self.results_dir / job_id / "transcript.txt"
            if not transcript_path.exists():
                return False
            
            self._is_busy = True
            return True
    
    def update_summary(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        error: Optional[str] = None,
        bullets_path: Optional[str] = None,
        paragraph_path: Optional[str] = None
    ):
        """Update summary status."""
        job = self.get_job(job_id)
        if not job:
            return
        
        if not job.summary:
            job.summary = {"status": "idle", "progress": 0}
        
        if status:
            job.summary["status"] = status
            if status == "processing" and not job.summary.get("started_at"):
                job.summary["started_at"] = datetime.utcnow().isoformat()
        
        if progress is not None:
            job.summary["progress"] = progress
        
        if error:
            job.summary["error"] = error
        
        if bullets_path:
            job.summary["bullets_path"] = str(bullets_path)
        
        if paragraph_path:
            job.summary["paragraph_path"] = str(paragraph_path)
        
        if status in ("completed", "error"):
            job.summary["completed_at"] = datetime.utcnow().isoformat()
            # Release busy lock when summarization completes or errors
            self._is_busy = False
        
        self._save_job(job)
        
        if self.current_job and self.current_job.job_id == job_id:
            self.current_job = job
