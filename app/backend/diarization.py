"""Speaker diarization using pyannote.audio."""
from pathlib import Path
from typing import List, Tuple, Optional
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

def perform_diarization(audio_path: Path) -> Optional[List[Tuple[float, float, str]]]:
    """
    Perform simple speaker diarization using audio features and clustering.
    This is a lightweight offline approach that doesn't require external models.
    
    Returns list of (start_time, end_time, speaker_label) tuples.
    Returns None if diarization fails or is not available.
    """
    try:
        import numpy as np
        import librosa
        from sklearn.cluster import AgglomerativeClustering
        from scipy.ndimage import median_filter
        
        # Load audio
        y, sr = librosa.load(str(audio_path), sr=16000, mono=True)
        
        # Parameters
        window_size = 1.5  # seconds
        hop_size = 0.75    # seconds (50% overlap)
        window_samples = int(window_size * sr)
        hop_samples = int(hop_size * sr)
        
        # Extract features for each window
        features = []
        timestamps = []
        
        for i in range(0, len(y) - window_samples, hop_samples):
            window = y[i:i + window_samples]
            
            # Extract MFCC features (voice characteristics)
            mfcc = librosa.feature.mfcc(y=window, sr=sr, n_mfcc=13)
            mfcc_mean = np.mean(mfcc, axis=1)
            mfcc_std = np.std(mfcc, axis=1)
            
            # Extract spectral features
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=window, sr=sr))
            spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=window, sr=sr))
            zero_crossing = np.mean(librosa.feature.zero_crossing_rate(window))
            
            # Combine features
            feature_vector = np.concatenate([
                mfcc_mean,
                mfcc_std,
                [spectral_centroid, spectral_rolloff, zero_crossing]
            ])
            
            features.append(feature_vector)
            timestamps.append(i / sr)
        
        if len(features) < 2:
            print("Audio too short for diarization")
            return None
        
        features = np.array(features)
        
        # Normalize features
        features = (features - features.mean(axis=0)) / (features.std(axis=0) + 1e-10)
        
        # Determine number of speakers (simple heuristic: 2-4 speakers)
        # Use silhouette score or default to 2
        n_clusters = 2
        audio_duration = len(y) / sr
        if audio_duration > 300:  # > 5 minutes, likely more speakers
            n_clusters = min(3, len(features) // 20)
        
        # Cluster windows by speaker
        clustering = AgglomerativeClustering(
            n_clusters=n_clusters,
            linkage='ward'
        )
        labels = clustering.fit_predict(features)
        
        # Smooth labels (reduce speaker switching noise)
        labels = median_filter(labels, size=3)
        
        # Convert to segments
        segments = []
        current_speaker = labels[0]
        segment_start = timestamps[0]
        
        for i in range(1, len(labels)):
            if labels[i] != current_speaker:
                # Speaker changed, save previous segment
                segments.append((
                    segment_start,
                    timestamps[i],
                    f"SPEAKER_{current_speaker:02d}"
                ))
                current_speaker = labels[i]
                segment_start = timestamps[i]
        
        # Add final segment
        segments.append((
            segment_start,
            timestamps[-1] + window_size,
            f"SPEAKER_{current_speaker:02d}"
        ))
        
        print(f"Diarization complete: detected {n_clusters} speakers, {len(segments)} segments")
        return segments
        
    except Exception as e:
        print(f"Diarization failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def merge_transcription_with_speakers(
    transcription_segments: List,
    speaker_segments: Optional[List[Tuple[float, float, str]]]
) -> List:
    """
    Merge transcription segments with speaker labels.
    
    Args:
        transcription_segments: List of transcription segments with .start, .end, .text
        speaker_segments: List of (start, end, speaker_label) tuples
        
    Returns:
        List of NEW segments with speaker labels added (does not mutate originals)
    """
    if not speaker_segments:
        return transcription_segments

    class SimpleSegment:
        __slots__ = ("start", "end", "text", "speaker")
        def __init__(self, start: float, end: float, text: str, speaker: str | None = None):
            self.start = start
            self.end = end
            self.text = text
            self.speaker = speaker

    merged: List[SimpleSegment] = []

    # Assign speakers to transcription segments based on overlap
    for segment in transcription_segments:
        # Find which speaker overlaps most with this transcription segment
        best_speaker = "SPEAKER_00"  # Default
        max_overlap = 0.0

        for start, end, speaker in speaker_segments:
            # Calculate overlap between transcription segment and speaker segment
            overlap_start = max(segment.start, start)
            overlap_end = min(segment.end, end)
            overlap = max(0.0, overlap_end - overlap_start)

            if overlap > max_overlap:
                max_overlap = overlap
                best_speaker = speaker

        merged.append(SimpleSegment(segment.start, segment.end, segment.text, best_speaker))

    return merged


def format_transcript_with_speakers(segments: List, include_speakers: bool = True) -> str:
    """
    Format transcription segments as text with speaker labels.
    
    Args:
        segments: List of segments with .text and optionally .speaker attributes
        include_speakers: Whether to include speaker labels
        
    Returns:
        Formatted transcript string
    """
    if not segments:
        return ""
    
    lines = []
    current_speaker = None
    
    for segment in segments:
        speaker = getattr(segment, 'speaker', None) if include_speakers else None
        text = segment.text.strip()
        
        if speaker and speaker != current_speaker:
            # New speaker, add label
            lines.append(f"\n[{speaker}]")
            current_speaker = speaker
        
        lines.append(text)
    
    return "\n".join(lines).strip()
