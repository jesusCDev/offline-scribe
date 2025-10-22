"""Llama.cpp engine for text summarization."""
import subprocess
import re
from pathlib import Path
from typing import Callable, Optional


class LlamaSummarizer:
    """Wrapper for llama.cpp CLI to generate summaries."""
    
    def __init__(self, model_path: Path, llama_bin: Path, threads: int = 4):
        """
        Initialize the summarizer.
        
        Args:
            model_path: Path to the GGUF model file
            llama_bin: Path to llama-cli binary
            threads: Number of CPU threads to use
        """
        self.model_path = model_path
        self.llama_bin = llama_bin
        self.threads = threads
        self.max_chunk_chars = 10000  # ~2500 tokens per chunk
        
        # Llama 2 Chat prompt format
        self.system_prompt = "You are a helpful assistant that summarizes transcripts accurately and concisely."
    
    def _format_prompt(self, instruction: str, content: str) -> str:
        """Format prompt in Llama 2 Chat format."""
        return f"[INST] <<SYS>>\n{self.system_prompt}\n<</SYS>>\n\n{instruction}\n\nTranscript:\n{content}\n[/INST]"
    
    def _run_llama(self, prompt: str, max_tokens: int = 512, temp: float = 0.3, timeout: int = 300) -> str:
        """
        Run llama-cli with the given prompt.
        
        Args:
            prompt: Formatted prompt
            max_tokens: Maximum tokens to generate
            temp: Temperature for sampling
            timeout: Timeout in seconds
            
        Returns:
            Generated text
        """
        cmd = [
            str(self.llama_bin),
            "-m", str(self.model_path),
            "-p", prompt,
            "-n", str(max_tokens),
            "-c", "4096",  # Context size
            "-t", str(self.threads),
            "-ngl", "0",  # CPU only
            "--temp", str(temp),
            "--top-p", "0.95",
            "--repeat-penalty", "1.1",
            "--no-display-prompt"  # Don't echo the prompt
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"llama-cli failed: {result.stderr[:500]}")
            
            # Clean up output
            output = result.stdout.strip()
            
            # Remove common artifacts
            output = re.sub(r'\[INST\].*?\[/INST\]', '', output, flags=re.DOTALL)
            output = re.sub(r'<<SYS>>.*?<</SYS>>', '', output, flags=re.DOTALL)
            
            return output.strip()
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Summarization timed out after {timeout} seconds")
        except Exception as e:
            raise RuntimeError(f"Failed to run llama-cli: {e}")
    
    def _chunk_text(self, text: str) -> list[str]:
        """
        Split text into chunks that fit within context window.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= self.max_chunk_chars:
            return [text]
        
        chunks = []
        # Split on paragraphs first
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= self.max_chunk_chars:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def generate_bullet_summary(
        self, 
        transcript: str, 
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> str:
        """
        Generate bullet point summary.
        
        Args:
            transcript: Full transcript text
            progress_callback: Optional callback for progress updates
            
        Returns:
            Bullet point summary
        """
        instruction = (
            "Produce 5 to 10 bullet points covering the key facts, decisions, "
            "and action items from the transcript below. Do not invent content. "
            "Use hyphen-prefixed bullets (- ). Output only the bullet list, "
            "nothing else."
        )
        
        chunks = self._chunk_text(transcript)
        
        if len(chunks) == 1:
            # Single chunk - direct summarization
            if progress_callback:
                progress_callback(30)
            
            prompt = self._format_prompt(instruction, chunks[0])
            summary = self._run_llama(prompt, max_tokens=512, temp=0.2)
            
            if progress_callback:
                progress_callback(90)
            
            return summary
        else:
            # Multiple chunks - map-reduce approach
            chunk_summaries = []
            
            for i, chunk in enumerate(chunks):
                if progress_callback:
                    progress = 20 + int((i / len(chunks)) * 50)
                    progress_callback(progress)
                
                prompt = self._format_prompt(
                    "Summarize the key points from this transcript segment in 5 bullet points:",
                    chunk
                )
                chunk_summary = self._run_llama(prompt, max_tokens=256, temp=0.2)
                chunk_summaries.append(chunk_summary)
            
            # Combine chunk summaries
            if progress_callback:
                progress_callback(75)
            
            combined = "\n\n".join(chunk_summaries)
            final_prompt = self._format_prompt(
                "Combine these bullet points into a final list of 5 to 10 key points. "
                "Remove duplicates and keep only the most important information:",
                combined
            )
            final_summary = self._run_llama(final_prompt, max_tokens=512, temp=0.2)
            
            if progress_callback:
                progress_callback(95)
            
            return final_summary
    
    def generate_paragraph_summary(
        self,
        transcript: str,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> str:
        """
        Generate paragraph summary.
        
        Args:
            transcript: Full transcript text
            progress_callback: Optional callback for progress updates
            
        Returns:
            Paragraph summary
        """
        instruction = (
            "Write one coherent paragraph summarizing the transcript below. "
            "Focus on who did what, key topics, decisions, and outcomes. "
            "Keep it 150 to 250 words. Do not invent content. "
            "Output only the paragraph, nothing else."
        )
        
        chunks = self._chunk_text(transcript)
        
        if len(chunks) == 1:
            # Single chunk - direct summarization
            if progress_callback:
                progress_callback(30)
            
            prompt = self._format_prompt(instruction, chunks[0])
            summary = self._run_llama(prompt, max_tokens=512, temp=0.4)
            
            if progress_callback:
                progress_callback(90)
            
            return summary
        else:
            # Multiple chunks - map-reduce approach
            chunk_summaries = []
            
            for i, chunk in enumerate(chunks):
                if progress_callback:
                    progress = 20 + int((i / len(chunks)) * 50)
                    progress_callback(progress)
                
                prompt = self._format_prompt(
                    "Write a short paragraph summarizing this transcript segment:",
                    chunk
                )
                chunk_summary = self._run_llama(prompt, max_tokens=256, temp=0.4)
                chunk_summaries.append(chunk_summary)
            
            # Combine chunk summaries
            if progress_callback:
                progress_callback(75)
            
            combined = "\n\n".join(chunk_summaries)
            final_prompt = self._format_prompt(
                "Combine these summaries into one coherent paragraph of 150 to 250 words. "
                "Focus on the main themes, decisions, and outcomes:",
                combined
            )
            final_summary = self._run_llama(final_prompt, max_tokens=512, temp=0.4)
            
            if progress_callback:
                progress_callback(95)
            
            return final_summary
    
    def generate_summaries(
        self,
        transcript: str,
        output_dir: Path,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> dict[str, Path]:
        """
        Generate both bullet and paragraph summaries.
        
        Args:
            transcript: Full transcript text
            output_dir: Directory to save summaries
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict mapping format to file path
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate bullet summary (0-50%)
        if progress_callback:
            progress_callback(10)
        
        bullet_summary = self.generate_bullet_summary(
            transcript,
            lambda p: progress_callback(int(p * 0.45)) if progress_callback else None
        )
        
        bullet_path = output_dir / "summary_bullets.txt"
        bullet_path.write_text(bullet_summary, encoding="utf-8")
        
        # Generate paragraph summary (50-100%)
        if progress_callback:
            progress_callback(50)
        
        paragraph_summary = self.generate_paragraph_summary(
            transcript,
            lambda p: progress_callback(50 + int(p * 0.45)) if progress_callback else None
        )
        
        paragraph_path = output_dir / "summary_paragraph.txt"
        paragraph_path.write_text(paragraph_summary, encoding="utf-8")
        
        if progress_callback:
            progress_callback(100)
        
        return {
            "bullets": bullet_path,
            "paragraph": paragraph_path
        }
