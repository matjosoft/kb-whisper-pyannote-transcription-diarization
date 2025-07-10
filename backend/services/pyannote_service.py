import torch
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from pyannote.audio import Pipeline
from pyannote.core import Annotation, Segment

from utils.config import get_settings
import os

logger = logging.getLogger(__name__)

class PyannoteService:
    """Service for handling Pyannote speaker diarization"""
    
    def __init__(self):
        self.settings = get_settings()
        self.pipeline: Optional[Pipeline] = None
        self._load_pipeline()
    
    def _load_pipeline(self):
        """Load the Pyannote diarization pipeline"""
        try:
            logger.info(f"Loading Pyannote pipeline '{self.settings.pyannote_model}' on device '{self.settings.device}'")
            
            hf_auth_token = os.getenv("HF_AUTH_TOKEN")
            # Load the pre-trained pipeline
            self.pipeline = Pipeline.from_pretrained(
                self.settings.pyannote_model,
                use_auth_token=hf_auth_token  # You may need to set this for some models
            )
            
            # Move to appropriate device
            if self.settings.device != "cpu":
                self.pipeline = self.pipeline.to(torch.device(self.settings.device))
            
            logger.info("Pyannote pipeline loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Pyannote pipeline: {e}")
            logger.warning("Pyannote service will not be available")
            self.pipeline = None
    
    def is_available(self) -> bool:
        """Check if Pyannote service is available"""
        return self.pipeline is not None
    
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
            "model_name": self.settings.pyannote_model,
            "device": self.settings.device,
            "min_speakers": self.settings.min_speakers,
            "max_speakers": self.settings.max_speakers
        }