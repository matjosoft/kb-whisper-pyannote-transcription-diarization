"""
Mock services for testing the application without AI dependencies
These provide dummy implementations for development and testing
"""

import time
import random
from pathlib import Path
from typing import Dict, Any, List

class MockWhisperService:
    """Mock Whisper service for testing"""
    
    def __init__(self):
        self.available = True
    
    def is_available(self) -> bool:
        return self.available
    
    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        """Mock transcription that returns dummy data"""
        # Simulate processing time
        time.sleep(2)
        
        # Generate mock segments
        segments = [
            {
                "start": 0.0,
                "end": 3.5,
                "text": "Det var en gång en liten gubbe som bodde i en stubbe.",
                "words": [
                    {"start": 0.0, "end": 0.5, "word": "Det"},
                    {"start": 0.5, "end": 0.8, "word": "var"},
                    {"start": 0.8, "end": 1.0, "word": "en"},
                    {"start": 1.0, "end": 1.5, "word": "gång"},
                ]
            },
            {
                "start": 5.5,
                "end": 9.8,
                "text": "Sen pratar jag med en annan röst som är helt annorlunda.",
                "words": []
            },
            {
                "start": 11.2,
                "end": 17.5,
                "text": "Och så här jag ju den tredje rösten med en annan dialekt liksom då.",
                "words": []
            }
        ]
        
        return {
            "text": " ".join(seg["text"] for seg in segments),
            "language": "sv",
            "segments": segments,
            "duration": 17.5
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "available": True,
            "model_name": "mock-whisper",
            "device": "cpu",
            "language": "auto"
        }

class MockPyannoteService:
    """Mock Pyannote service for testing"""
    
    def __init__(self):
        self.available = True
    
    def is_available(self) -> bool:
        return self.available
    
    def diarize(self, audio_path: Path) -> Dict[str, Any]:
        """Mock diarization that returns dummy speaker data"""
        # Simulate processing time
        time.sleep(1.5)
        
        # Generate mock speaker segments
        segments = [
            {
                "start": 0.0,
                "end": 4.5,
                "speaker": "SPEAKER_00",
                "speaker_label": "Speaker 1",
                "speaker_id": 1,
                "duration": 4.5
            },
            {
                "start": 5.0,
                "end": 10.0,
                "speaker": "SPEAKER_01",
                "speaker_label": "Speaker 2",
                "speaker_id": 2,
                "duration": 5.0
            },
            {
                "start": 11.0,
                "end": 18.0,
                "speaker": "SPEAKER_02",
                "speaker_label": "Speaker 3",
                "speaker_id": 3,
                "duration": 7.0
            }
        ]
        
        speaker_mapping = {
            "SPEAKER_00": "Speaker 1",
            "SPEAKER_01": "Speaker 2", 
            "SPEAKER_02": "Speaker 3"
        }
        
        return {
            "num_speakers": 3,
            "speakers": speaker_mapping,
            "segments": segments,
            "duration": 18.0
        }
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        return {
            "available": True,
            "model_name": "mock-pyannote",
            "device": "cpu",
            "min_speakers": 1,
            "max_speakers": 10
        }