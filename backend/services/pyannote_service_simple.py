import torch
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
    print("✅ Pyannote.audio Pipeline imported successfully")
except ImportError as e:
    print(f"❌ Failed to import pyannote.audio: {e}")
    PYANNOTE_AVAILABLE = False

from utils.config import get_settings

logger = logging.getLogger(__name__)

class PyannoteService:
    """Service for handling Pyannote speaker diarization"""
    
    def __init__(self):
        self.settings = get_settings()
        self.pipeline: Optional[Pipeline] = None
        if PYANNOTE_AVAILABLE:
            self._load_pipeline()
        else:
            logger.warning("Pyannote not available, service will not work")
    
    def _load_pipeline(self):
        """Load the Pyannote diarization pipeline"""
        try:
            logger.info("Attempting to load Pyannote pipeline...")
            
            # Try to load a pre-trained pipeline
            # Note: This might require HuggingFace authentication for some models
            try:
                self.pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token="REMOVED"
                )
                logger.info("Successfully loaded pyannote/speaker-diarization-3.1")
            except Exception as e:
                logger.warning(f"Failed to load speaker-diarization-3.1: {e}")
                try:
                    # Try an older version that might not require auth
                    self.pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization",
                        use_auth_token=None
                    )
                    logger.info("Successfully loaded pyannote/speaker-diarization")
                except Exception as e2:
                    logger.error(f"Failed to load any Pyannote pipeline: {e2}")
                    self.pipeline = None
                    return
            
            # Move to appropriate device if pipeline loaded successfully
            if self.pipeline and self.settings.device != "cpu":
                try:
                    self.pipeline = self.pipeline.to(torch.device(self.settings.device))
                    logger.info(f"Moved pipeline to {self.settings.device}")
                except Exception as e:
                    logger.warning(f"Failed to move pipeline to {self.settings.device}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to load Pyannote pipeline: {e}")
            self.pipeline = None
    
    def is_available(self) -> bool:
        """Check if Pyannote service is available"""
        return PYANNOTE_AVAILABLE and self.pipeline is not None
    
    def diarize(self, audio_path: Path) -> Dict[str, Any]:
        """
        Perform speaker diarization on audio file
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dictionary containing diarization results with speaker segments
        """
        if not self.pipeline:
            raise RuntimeError("Pyannote pipeline not available")
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            logger.info(f"Performing speaker diarization on: {audio_path}")
            
            # Apply the pipeline to the audio file
            diarization = self.pipeline(str(audio_path))
            
            # Process the diarization results
            speakers = set()
            segments = []
            
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speakers.add(speaker)
                segments.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker,
                    "duration": turn.end - turn.start
                })
            
            # Sort segments by start time
            segments.sort(key=lambda x: x["start"])
            
            # Create speaker mapping (SPEAKER_00 -> Speaker 1, etc.)
            speaker_list = sorted(list(speakers))
            speaker_mapping = {
                speaker: f"Speaker {i+1}" 
                for i, speaker in enumerate(speaker_list)
            }
            
            # Update segments with friendly speaker names
            for segment in segments:
                segment["speaker_label"] = speaker_mapping[segment["speaker"]]
                segment["speaker_id"] = speaker_list.index(segment["speaker"]) + 1
            
            diarization_result = {
                "num_speakers": len(speakers),
                "speakers": speaker_mapping,
                "segments": segments,
                "duration": max([seg["end"] for seg in segments]) if segments else 0
            }
            
            logger.info(f"Diarization completed. Found {len(speakers)} speakers in {len(segments)} segments")
            return diarization_result
            
        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            raise RuntimeError(f"Diarization failed: {str(e)}")
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """Get information about the loaded pipeline"""
        if not self.pipeline:
            return {"available": False}
        
        return {
            "available": True,
            "model_name": "pyannote/speaker-diarization",
            "device": self.settings.device,
            "min_speakers": self.settings.min_speakers,
            "max_speakers": self.settings.max_speakers
        }