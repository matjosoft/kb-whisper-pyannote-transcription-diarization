import logging
from pathlib import Path
from typing import Dict, Any
import requests

from utils.config import get_settings

logger = logging.getLogger(__name__)


class RemoteWhisperService:
    """Service for handling remote Whisper transcription via standalone server"""

    def __init__(self):
        self.settings = get_settings()
        self.remote_url = self.settings.whisper_remote_url
        logger.info(f"Using remote Whisper service at: {self.remote_url}")
        self._check_remote_service()

    def _check_remote_service(self):
        """Check if remote Whisper service is available"""
        try:
            response = requests.get(f"{self.remote_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("available"):
                    logger.info("✅ Remote Whisper service is available")
                else:
                    logger.warning("⚠️ Remote Whisper service is running but not available")
            else:
                logger.warning(f"⚠️ Remote Whisper service health check failed: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to remote Whisper service: {e}")
            logger.error(f"Make sure the service is running at {self.remote_url}")

    def is_available(self) -> bool:
        """Check if remote Whisper service is available"""
        try:
            response = requests.get(f"{self.remote_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                return health_data.get("available", False)
        except Exception as e:
            logger.debug(f"Remote Whisper service not available: {e}")
            return False

    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        """
        Perform transcription using remote Whisper service

        Args:
            audio_path: Path to the audio file

        Returns:
            Dictionary containing transcription results with segments and timestamps
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            logger.info(f"Performing remote transcription on: {audio_path}")

            # Send audio file to remote service
            with open(audio_path, 'rb') as f:
                files = {'file': (audio_path.name, f, 'audio/wav')}
                response = requests.post(
                    f"{self.remote_url}/transcribe",
                    files=files,
                    timeout=600  # 10 minutes timeout for large files
                )

            if response.status_code != 200:
                raise RuntimeError(f"Remote service returned status code {response.status_code}: {response.text}")

            result = response.json()
            if not result.get("success"):
                raise RuntimeError(f"Remote transcription failed: {result.get('detail', 'Unknown error')}")

            transcription_result = result.get("result")
            logger.info(f"Remote transcription completed. Found {len(transcription_result.get('segments', []))} segments")
            return transcription_result

        except Exception as e:
            logger.error(f"Remote transcription failed: {e}")
            raise RuntimeError(f"Remote transcription failed: {str(e)}")

    async def transcribe_with_progress(self, audio_path: Path):
        """
        Transcribe audio file with progress updates

        Note: Remote service doesn't support streaming progress yet,
        so we simulate progress updates while the transcription runs.

        Args:
            audio_path: Path to the audio file

        Yields:
            Progress updates as dictionaries
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            # Yield initial progress
            yield {
                "status": "starting",
                "message": "Sending audio to remote Whisper service..."
            }

            # Estimate duration for progress simulation
            import torchaudio
            try:
                waveform, sample_rate = torchaudio.load(str(audio_path))
                duration = waveform.shape[1] / sample_rate
            except:
                duration = 120.0  # Default estimate

            yield {
                "status": "transcribing",
                "message": f"Remote transcription in progress ({duration:.1f}s audio)...",
                "duration": duration
            }

            # Perform actual transcription (blocking call)
            result = self.transcribe(audio_path)

            # Yield completion
            yield {
                "status": "transcription_complete",
                "result": result,
                "message": f"Remote transcription completed. Found {len(result.get('segments', []))} segments"
            }

        except Exception as e:
            logger.error(f"Remote transcription with progress failed: {e}")
            yield {
                "status": "error",
                "error": str(e),
                "message": f"Remote transcription failed: {str(e)}"
            }

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the remote service"""
        try:
            response = requests.get(f"{self.remote_url}/info", timeout=5)
            if response.status_code == 200:
                info = response.json()
                info["service_type"] = "remote_whisper"
                return info
            else:
                return {
                    "available": False,
                    "service_type": "remote_whisper",
                    "error": f"Failed to get info: status code {response.status_code}"
                }
        except Exception as e:
            return {
                "available": False,
                "service_type": "remote_whisper",
                "error": str(e)
            }
