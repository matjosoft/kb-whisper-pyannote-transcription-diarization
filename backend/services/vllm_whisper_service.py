from pathlib import Path
from typing import Dict, Any, Optional
import logging
from openai import OpenAI

from utils.config import get_settings

logger = logging.getLogger(__name__)

class VllmWhisperService:
    """Service for handling Whisper transcription via vLLM server"""

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[OpenAI] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the OpenAI client for vLLM server"""
        try:
            logger.info(f"Initializing vLLM client with base URL: {self.settings.vllm_base_url}")
            self.client = OpenAI(
                base_url=self.settings.vllm_base_url,
                api_key=self.settings.vllm_api_key,
            )
            logger.info("vLLM client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vLLM client: {e}")
            self.client = None

    def is_available(self) -> bool:
        """Check if vLLM service is available"""
        return self.client is not None

    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        """
        Transcribe audio file using vLLM server

        Args:
            audio_path: Path to the audio file

        Returns:
            Dictionary containing transcription results with segments and timestamps
        """
        if not self.is_available():
            raise RuntimeError("vLLM service not available")

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            logger.info(f"Transcribing audio file with vLLM: {audio_path}")

            # Check file size
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.settings.vllm_max_audio_filesize_mb:
                raise ValueError(
                    f"Audio file size ({file_size_mb:.1f}MB) exceeds maximum allowed "
                    f"({self.settings.vllm_max_audio_filesize_mb}MB)"
                )

            # Open and send audio file to vLLM server
            with open(audio_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model=self.settings.vllm_model_name,
                    file=audio_file,
                    language=self.settings.whisper_language if self.settings.whisper_language != "auto" else None,
                    response_format="verbose_json",
                )

            # Convert response to expected format
            segments = []
            if hasattr(transcription, 'segments') and transcription.segments:
                for segment in transcription.segments:
                    segment_data = {
                        "start": segment.get("start", 0),
                        "end": segment.get("end", 0),
                        "text": segment.get("text", "").strip(),
                        "words": []
                    }
                    # Check if word-level timestamps are available
                    if hasattr(segment, 'words') and segment.words:
                        segment_data["words"] = [
                            {
                                "start": word.get("start", 0),
                                "end": word.get("end", 0),
                                "word": word.get("word", "")
                            }
                            for word in segment.words
                        ]
                    segments.append(segment_data)

            # Calculate duration from segments or use provided duration
            duration = 0
            if segments:
                duration = max([seg["end"] for seg in segments])
            elif hasattr(transcription, 'duration'):
                duration = transcription.duration

            transcription_result = {
                "text": transcription.text,
                "language": transcription.language if hasattr(transcription, 'language') else "unknown",
                "segments": segments,
                "duration": duration,
                "model_type": "vllm"
            }

            logger.info(f"vLLM transcription completed. Found {len(segments)} segments")
            return transcription_result

        except Exception as e:
            logger.error(f"vLLM transcription failed: {e}")
            raise RuntimeError(f"vLLM transcription failed: {str(e)}")

    async def transcribe_with_progress(self, audio_path: Path, progress_callback=None):
        """
        Transcribe audio file with progress updates

        Note: vLLM server doesn't support streaming progress, so this will yield
        initial and final status updates only.

        Args:
            audio_path: Path to the audio file
            progress_callback: Optional callback function for progress updates

        Yields:
            Progress updates as dictionaries
        """
        if not self.is_available():
            raise RuntimeError("vLLM service not available")

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            logger.info(f"Transcribing audio file with vLLM (streaming mode): {audio_path}")

            # Yield initial progress
            yield {
                "status": "transcribing",
                "message": "Sending audio to vLLM server for transcription...",
                "total_chunks": 1,
                "duration": 0
            }

            # Perform transcription (blocking call)
            result = self.transcribe(audio_path)

            # Yield completion progress
            yield {
                "status": "completed",
                "message": "Transcription completed",
                "result": result
            }

        except Exception as e:
            logger.error(f"vLLM transcription with progress failed: {e}")
            yield {
                "status": "error",
                "message": f"Transcription failed: {str(e)}"
            }
            raise

    def get_service_status(self) -> Dict[str, Any]:
        """Get the current status of the vLLM service"""
        return {
            "available": self.is_available(),
            "base_url": self.settings.vllm_base_url,
            "model_name": self.settings.vllm_model_name,
            "max_filesize_mb": self.settings.vllm_max_audio_filesize_mb
        }
