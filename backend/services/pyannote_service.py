import torch
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import requests
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
        self.use_remote = self.settings.pyannote_use_remote
        self.remote_url = self.settings.pyannote_remote_url

        if self.use_remote:
            logger.info(f"Using remote Pyannote service at: {self.remote_url}")
            self._check_remote_service()
        else:
            logger.info("Using local Pyannote service")
            self._load_pipeline()
    
    def _check_remote_service(self):
        """Check if remote Pyannote service is available"""
        try:
            response = requests.get(f"{self.remote_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("available"):
                    logger.info("✅ Remote Pyannote service is available")
                else:
                    logger.warning("⚠️ Remote Pyannote service is running but not available")
            else:
                logger.warning(f"⚠️ Remote Pyannote service health check failed: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to remote Pyannote service: {e}")
            logger.error(f"Make sure the service is running at {self.remote_url}")

    def _load_pipeline(self):
        """Load the Pyannote diarization pipeline"""
        try:
            logger.info(f"Loading Pyannote pipeline '{self.settings.pyannote_model}' on device '{self.settings.device}'")

            hf_auth_token = os.getenv("HF_AUTH_TOKEN")
            # Load the pre-trained pipeline
            self.pipeline = Pipeline.from_pretrained(
                self.settings.pyannote_model,
                token=hf_auth_token  # You may need to set this for some models
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
        if self.use_remote:
            try:
                response = requests.get(f"{self.remote_url}/health", timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    return health_data.get("available", False)
            except Exception:
                return False
        return self.pipeline is not None
    
    def diarize(self, audio_path: Path) -> Dict[str, Any]:
        """
        Perform speaker diarization on audio file

        Args:
            audio_path: Path to the audio file

        Returns:
            Dictionary containing diarization results with speaker segments
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Use remote service if configured
        if self.use_remote:
            return self._diarize_remote(audio_path)
        else:
            return self._diarize_local(audio_path)

    def _diarize_remote(self, audio_path: Path) -> Dict[str, Any]:
        """Perform diarization using remote service"""
        try:
            logger.info(f"Performing remote speaker diarization on: {audio_path}")

            # Send audio file to remote service
            with open(audio_path, 'rb') as f:
                files = {'file': (audio_path.name, f, 'audio/wav')}
                response = requests.post(
                    f"{self.remote_url}/diarize",
                    files=files,
                    timeout=300  # 5 minutes timeout for large files
                )

            if response.status_code != 200:
                raise RuntimeError(f"Remote service returned status code {response.status_code}: {response.text}")

            result = response.json()
            if not result.get("success"):
                raise RuntimeError(f"Remote diarization failed: {result.get('detail', 'Unknown error')}")

            diarization_result = result.get("result")
            logger.info(f"Remote diarization completed. Found {diarization_result['num_speakers']} speakers in {len(diarization_result['segments'])} segments")
            return diarization_result

        except Exception as e:
            logger.error(f"Remote diarization failed: {e}")
            raise RuntimeError(f"Remote diarization failed: {str(e)}")

    def _diarize_local(self, audio_path: Path) -> Dict[str, Any]:
        """Perform diarization using local pipeline"""
        if not self.pipeline:
            raise RuntimeError("Pyannote pipeline not available")

        try:
            logger.info(f"Performing local speaker diarization on: {audio_path}")

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

            logger.info(f"Local diarization completed. Found {len(speakers)} speakers in {len(segments)} segments")
            return diarization_result

        except Exception as e:
            logger.error(f"Local diarization failed: {e}")
            raise RuntimeError(f"Local diarization failed: {str(e)}")
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """Get information about the loaded pipeline"""
        if self.use_remote:
            try:
                response = requests.get(f"{self.remote_url}/info", timeout=5)
                if response.status_code == 200:
                    remote_info = response.json()
                    return {
                        "available": remote_info.get("available", False),
                        "mode": "remote",
                        "remote_url": self.remote_url,
                        "model_name": remote_info.get("model_name"),
                        "device": remote_info.get("device"),
                        "min_speakers": self.settings.min_speakers,
                        "max_speakers": self.settings.max_speakers
                    }
            except Exception as e:
                logger.error(f"Failed to get remote service info: {e}")
                return {
                    "available": False,
                    "mode": "remote",
                    "remote_url": self.remote_url,
                    "error": str(e)
                }

        if not self.pipeline:
            return {"available": False, "mode": "local"}

        return {
            "available": True,
            "mode": "local",
            "model_name": self.settings.pyannote_model,
            "device": self.settings.device,
            "min_speakers": self.settings.min_speakers,
            "max_speakers": self.settings.max_speakers
        }