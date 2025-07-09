import whisper
import torch
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from utils.config import get_settings

logger = logging.getLogger(__name__)

class WhisperService:
    """Service for handling Whisper speech-to-text transcription"""
    
    def __init__(self):
        self.settings = get_settings()
        self.model: Optional[whisper.Whisper] = None
        self._load_model()
    
    def _load_model(self):
        """Load the Whisper model"""
        try:
            logger.info(f"Loading Whisper model '{self.settings.whisper_model}' on device '{self.settings.device}'")
            self.model = whisper.load_model(
                self.settings.whisper_model,
                device=self.settings.device
            )
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.model = None
    
    def is_available(self) -> bool:
        """Check if Whisper service is available"""
        return self.model is not None
    
    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        """
        Transcribe audio file using Whisper
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dictionary containing transcription results with segments and timestamps
        """
        if not self.model:
            raise RuntimeError("Whisper model not available")
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            logger.info(f"Transcribing audio file: {audio_path}")
            
            # Transcribe with word-level timestamps
            result = self.model.transcribe(
                str(audio_path),
                language=None if self.settings.whisper_language == "auto" else self.settings.whisper_language,
                word_timestamps=True,
                verbose=False
            )
            
            # Process the result to extract segments with timestamps
            segments = []
            for segment in result.get("segments", []):
                segment_data = {
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip(),
                    "words": []
                }
                
                # Add word-level timestamps if available
                if "words" in segment:
                    for word in segment["words"]:
                        segment_data["words"].append({
                            "start": word.get("start", segment["start"]),
                            "end": word.get("end", segment["end"]),
                            "word": word.get("word", "").strip()
                        })
                
                segments.append(segment_data)
            
            transcription_result = {
                "text": result.get("text", "").strip(),
                "language": result.get("language", "unknown"),
                "segments": segments,
                "duration": max([seg["end"] for seg in segments]) if segments else 0
            }
            
            logger.info(f"Transcription completed. Found {len(segments)} segments")
            return transcription_result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        if not self.model:
            return {"available": False}
        
        return {
            "available": True,
            "model_name": self.settings.whisper_model,
            "device": self.settings.device,
            "language": self.settings.whisper_language
        }