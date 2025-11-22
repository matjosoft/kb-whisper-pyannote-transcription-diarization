import ffmpeg
import librosa
import soundfile as sf
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import logging
import tempfile
import numpy as np

try:
    from utils.config import get_settings
except ImportError:
    # Fallback config if torch is not available
    class MockSettings:
        def __init__(self):
            self.upload_dir = Path("uploads")
            self.temp_dir = Path("temp")
    
    def get_settings():
        return MockSettings()

logger = logging.getLogger(__name__)

class AudioService:
    """Service for handling audio file operations and processing"""
    
    def __init__(self):
        self.settings = get_settings()
    
    # Video formats that ffmpeg can extract audio from
    VIDEO_FORMATS = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.mpeg', '.mpg', '.3gp']

    def convert_to_wav(self, input_path: Path) -> Path:
        """
        Convert audio or video file to WAV format for consistent processing.
        For video files, extracts the audio track.

        Args:
            input_path: Path to the input audio/video file

        Returns:
            Path to the converted WAV file
        """
        if input_path.suffix.lower() == '.wav':
            return input_path

        is_video = input_path.suffix.lower() in self.VIDEO_FORMATS

        try:
            # Create output path
            output_path = input_path.with_suffix('.wav')

            if is_video:
                logger.info(f"Extracting audio from video file: {input_path}")
            else:
                logger.info(f"Converting audio file to WAV format: {input_path}")

            # Use ffmpeg to convert to WAV (works for both audio and video)
            # For video files, ffmpeg automatically extracts the audio track
            (
                ffmpeg
                .input(str(input_path))
                .output(
                    str(output_path),
                    acodec='pcm_s16le',  # 16-bit PCM
                    ac=1,  # Mono
                    ar=16000  # 16kHz sample rate
                )
                .overwrite_output()
                .run(quiet=True)
            )

            if is_video:
                logger.info(f"Audio extracted successfully from video to {output_path}")
            else:
                logger.info(f"Audio converted successfully to {output_path}")
            return output_path

        except Exception as e:
            file_type = "video" if is_video else "audio"
            logger.error(f"{file_type.capitalize()} conversion failed: {e}")
            raise RuntimeError(f"Failed to convert {file_type}: {str(e)}")
    
    def get_audio_info(self, audio_path: Path) -> Dict[str, Any]:
        """
        Get information about an audio file
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dictionary containing audio file information
        """
        try:
            # Load audio file to get info
            y, sr = librosa.load(str(audio_path), sr=None)
            duration = len(y) / sr
            
            return {
                "duration": duration,
                "sample_rate": sr,
                "channels": 1 if y.ndim == 1 else y.shape[0],
                "samples": len(y),
                "format": audio_path.suffix.lower()
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio info: {e}")
            return {}
    
    def merge_transcription_diarization(
        self, 
        transcription: Dict[str, Any], 
        diarization: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge Whisper transcription results with Pyannote diarization results
        
        Args:
            transcription: Results from Whisper transcription
            diarization: Results from Pyannote diarization
            
        Returns:
            Merged results with speaker-attributed text segments
        """
        try:
            logger.info("Merging transcription and diarization results")
            
            transcription_segments = transcription.get("segments", [])
            diarization_segments = diarization.get("segments", [])
            
            if not transcription_segments:
                logger.warning("No transcription segments found")
                return self._create_empty_result()
            
            if not diarization_segments:
                logger.warning("No diarization segments found, using single speaker")
                return self._assign_single_speaker(transcription)
            
            # Merge segments by finding overlaps
            merged_segments = []
            
            for trans_seg in transcription_segments:
                trans_start = trans_seg["start"]
                trans_end = trans_seg["end"]
                trans_text = trans_seg["text"]
                
                # Find the diarization segment with the most overlap
                best_speaker = "Speaker 1"  # Default fallback
                best_overlap = 0
                
                for diar_seg in diarization_segments:
                    diar_start = diar_seg["start"]
                    diar_end = diar_seg["end"]
                    
                    # Calculate overlap
                    overlap_start = max(trans_start, diar_start)
                    overlap_end = min(trans_end, diar_end)
                    overlap_duration = max(0, overlap_end - overlap_start)
                    
                    if overlap_duration > best_overlap:
                        best_overlap = overlap_duration
                        best_speaker = diar_seg["speaker_label"]
                
                # Create merged segment
                merged_segment = {
                    "start": trans_start,
                    "end": trans_end,
                    "text": trans_text.strip(),
                    "speaker": best_speaker,
                    "duration": trans_end - trans_start
                }
                
                merged_segments.append(merged_segment)
            
            # Group consecutive segments by the same speaker
            grouped_segments = self._group_consecutive_speaker_segments(merged_segments)
            
            # Create speaker mapping for the frontend
            speakers = list(set(seg["speaker"] for seg in grouped_segments))
            speaker_mapping = {speaker: speaker for speaker in sorted(speakers)}
            
            result = {
                "segments": grouped_segments,
                "speakers": speaker_mapping,
                "num_speakers": len(speakers),
                "language": transcription.get("language", "unknown"),
                "duration": transcription.get("duration", 0),
                "full_text": " ".join(seg["text"] for seg in grouped_segments)
            }
            
            logger.info(f"Merge completed. {len(grouped_segments)} final segments with {len(speakers)} speakers")
            return result
            
        except Exception as e:
            logger.error(f"Failed to merge results: {e}")
            return self._create_empty_result()
    
    def _group_consecutive_speaker_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group consecutive segments from the same speaker"""
        if not segments:
            return []
        
        grouped = []
        current_group = segments[0].copy()
        
        for i in range(1, len(segments)):
            segment = segments[i]
            
            # If same speaker and segments are close together (within 1 second gap)
            if (segment["speaker"] == current_group["speaker"] and 
                segment["start"] - current_group["end"] <= 1.0):
                
                # Merge with current group
                current_group["text"] += " " + segment["text"]
                current_group["end"] = segment["end"]
                current_group["duration"] = current_group["end"] - current_group["start"]
            else:
                # Start new group
                grouped.append(current_group)
                current_group = segment.copy()
        
        # Add the last group
        grouped.append(current_group)
        
        return grouped
    
    def format_transcription_only(self, transcription: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format transcription results for transcription-only mode (no diarization)

        Args:
            transcription: Results from Whisper transcription

        Returns:
            Formatted results with all segments assigned to a single speaker
        """
        segments = []
        for seg in transcription.get("segments", []):
            segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"].strip(),
                "speaker": "Speaker 1",
                "duration": seg["end"] - seg["start"]
            })

        return {
            "segments": segments,
            "speakers": {"Speaker 1": "Speaker 1"},
            "num_speakers": 1,
            "language": transcription.get("language", "unknown"),
            "duration": transcription.get("duration", 0),
            "full_text": transcription.get("text", "")
        }

    def _assign_single_speaker(self, transcription: Dict[str, Any]) -> Dict[str, Any]:
        """Assign all transcription to a single speaker when diarization fails"""
        # Delegate to the public method
        return self.format_transcription_only(transcription)
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """Create an empty result structure"""
        return {
            "segments": [],
            "speakers": {},
            "num_speakers": 0,
            "language": "unknown",
            "duration": 0,
            "full_text": ""
        }