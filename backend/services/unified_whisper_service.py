import logging
from pathlib import Path
from typing import Dict, Any, Optional

from utils.config import get_settings

logger = logging.getLogger(__name__)

class UnifiedWhisperService:
    """Unified service that can use remote Whisper, vLLM, local Whisper, or OpenAI Whisper models"""

    def __init__(self):
        self.settings = get_settings()
        self.whisper_service = None
        self.local_whisper_service = None
        self.vllm_whisper_service = None
        self.remote_whisper_service = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize the appropriate Whisper service based on configuration"""
        try:
            # Priority 1: Remote Whisper (if enabled)
            if self.settings.whisper_use_remote:
                logger.info("Initializing remote Whisper service")
                from .remote_whisper_service import RemoteWhisperService
                self.remote_whisper_service = RemoteWhisperService()
                if not self.remote_whisper_service.is_available():
                    logger.warning("Remote Whisper service failed to initialize, falling back to vLLM, local, or OpenAI Whisper")
                    if self.settings.whisper_use_vllm:
                        self._initialize_vllm_whisper()
                    elif self.settings.whisper_use_local:
                        self._initialize_local_whisper()
                    else:
                        self._initialize_openai_whisper()
            # Priority 2: vLLM (if enabled and remote not enabled)
            elif self.settings.whisper_use_vllm:
                self._initialize_vllm_whisper()
            # Priority 3: Local Whisper (if enabled and vLLM not enabled)
            elif self.settings.whisper_use_local:
                self._initialize_local_whisper()
            # Priority 4: OpenAI Whisper (default fallback)
            else:
                logger.info("Initializing OpenAI Whisper service")
                self._initialize_openai_whisper()

        except Exception as e:
            logger.error(f"Failed to initialize Whisper services: {e}")
            # Try to fall back to OpenAI Whisper
            self._initialize_openai_whisper()

    def _initialize_vllm_whisper(self):
        """Initialize vLLM Whisper service"""
        try:
            logger.info("Initializing vLLM Whisper service")
            from .vllm_whisper_service import VllmWhisperService
            self.vllm_whisper_service = VllmWhisperService()
            if not self.vllm_whisper_service.is_available():
                logger.warning("vLLM Whisper service failed to initialize, falling back to local or OpenAI Whisper")
                if self.settings.whisper_use_local:
                    self._initialize_local_whisper()
                else:
                    self._initialize_openai_whisper()
        except Exception as e:
            logger.error(f"Failed to initialize vLLM Whisper service: {e}")
            if self.settings.whisper_use_local:
                self._initialize_local_whisper()
            else:
                self._initialize_openai_whisper()

    def _initialize_local_whisper(self):
        """Initialize local Whisper service"""
        try:
            logger.info("Initializing local Whisper service")
            from .local_whisper_service import LocalWhisperService
            self.local_whisper_service = LocalWhisperService()
            if not self.local_whisper_service.is_available():
                logger.warning("Local Whisper service failed to initialize, falling back to OpenAI Whisper")
                self._initialize_openai_whisper()
        except Exception as e:
            logger.error(f"Failed to initialize local Whisper service: {e}")
            self._initialize_openai_whisper()

    def _initialize_openai_whisper(self):
        """Initialize OpenAI Whisper service"""
        try:
            from .whisper_service import WhisperService
            self.whisper_service = WhisperService()
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI Whisper service: {e}")
            self.whisper_service = None
    
    def is_available(self) -> bool:
        """Check if any Whisper service is available"""
        if self.settings.whisper_use_remote and self.remote_whisper_service:
            return self.remote_whisper_service.is_available()
        elif self.settings.whisper_use_vllm and self.vllm_whisper_service:
            return self.vllm_whisper_service.is_available()
        elif self.settings.whisper_use_local and self.local_whisper_service:
            return self.local_whisper_service.is_available()
        elif self.whisper_service:
            return self.whisper_service.is_available()
        return False
    
    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        """
        Transcribe audio file using the configured Whisper service

        Args:
            audio_path: Path to the audio file

        Returns:
            Dictionary containing transcription results with segments and timestamps
        """
        if not self.is_available():
            raise RuntimeError("No Whisper service available")

        try:
            # Priority 1: Remote Whisper
            if self.settings.whisper_use_remote and self.remote_whisper_service and self.remote_whisper_service.is_available():
                logger.info("Using remote Whisper service for transcription")
                return self.remote_whisper_service.transcribe(audio_path)
            # Priority 2: vLLM
            elif self.settings.whisper_use_vllm and self.vllm_whisper_service and self.vllm_whisper_service.is_available():
                logger.info("Using vLLM Whisper service for transcription")
                return self.vllm_whisper_service.transcribe(audio_path)
            # Priority 3: Local Whisper
            elif self.settings.whisper_use_local and self.local_whisper_service and self.local_whisper_service.is_available():
                logger.info("Using local Whisper service for transcription")
                return self.local_whisper_service.transcribe(audio_path)
            # Priority 4: OpenAI Whisper
            elif self.whisper_service and self.whisper_service.is_available():
                logger.info("Using OpenAI Whisper service for transcription")
                return self.whisper_service.transcribe(audio_path)
            else:
                raise RuntimeError("No available Whisper service for transcription")

        except Exception as e:
            # Fallback chain: Remote -> vLLM -> Local -> OpenAI
            if self.settings.whisper_use_remote:
                # Try vLLM next
                if self.vllm_whisper_service and self.vllm_whisper_service.is_available():
                    logger.warning(f"Remote Whisper failed ({e}), falling back to vLLM Whisper")
                    return self.vllm_whisper_service.transcribe(audio_path)
                # Try local next
                elif self.local_whisper_service and self.local_whisper_service.is_available():
                    logger.warning(f"Remote Whisper failed ({e}), falling back to local Whisper")
                    return self.local_whisper_service.transcribe(audio_path)
                # Then try OpenAI
                elif self.whisper_service and self.whisper_service.is_available():
                    logger.warning(f"Remote Whisper failed ({e}), falling back to OpenAI Whisper")
                    return self.whisper_service.transcribe(audio_path)
            elif self.settings.whisper_use_vllm:
                # Try local next
                if self.local_whisper_service and self.local_whisper_service.is_available():
                    logger.warning(f"vLLM Whisper failed ({e}), falling back to local Whisper")
                    return self.local_whisper_service.transcribe(audio_path)
                # Then try OpenAI
                elif self.whisper_service and self.whisper_service.is_available():
                    logger.warning(f"vLLM Whisper failed ({e}), falling back to OpenAI Whisper")
                    return self.whisper_service.transcribe(audio_path)
            elif self.settings.whisper_use_local:
                # If local fails, try OpenAI
                if self.whisper_service and self.whisper_service.is_available():
                    logger.warning(f"Local Whisper failed ({e}), falling back to OpenAI Whisper")
                    return self.whisper_service.transcribe(audio_path)
            raise e
    
    async def transcribe_with_progress(self, audio_path: Path):
        """
        Transcribe audio file with progress updates (streaming)

        Args:
            audio_path: Path to the audio file

        Yields:
            Progress updates as dictionaries
        """
        if not self.is_available():
            raise RuntimeError("No Whisper service available")

        try:
            # Priority 1: Remote Whisper
            if (self.settings.whisper_use_remote and
                self.remote_whisper_service and
                self.remote_whisper_service.is_available() and
                hasattr(self.remote_whisper_service, 'transcribe_with_progress')):
                logger.info("Using remote Whisper service for streaming transcription")
                async for progress_data in self.remote_whisper_service.transcribe_with_progress(audio_path):
                    yield progress_data
            # Priority 2: vLLM
            elif (self.settings.whisper_use_vllm and
                self.vllm_whisper_service and
                self.vllm_whisper_service.is_available() and
                hasattr(self.vllm_whisper_service, 'transcribe_with_progress')):
                logger.info("Using vLLM Whisper service for streaming transcription")
                async for progress_data in self.vllm_whisper_service.transcribe_with_progress(audio_path):
                    yield progress_data
            # Priority 3: Local Whisper
            elif (self.settings.whisper_use_local and
                self.local_whisper_service and
                self.local_whisper_service.is_available() and
                hasattr(self.local_whisper_service, 'transcribe_with_progress')):
                logger.info("Using local Whisper service for streaming transcription")
                async for progress_data in self.local_whisper_service.transcribe_with_progress(audio_path):
                    yield progress_data
            # Priority 4: Fallback with simulated progress
            else:
                # Fallback to regular transcription with simulated progress
                logger.info("Using fallback transcription with simulated progress")
                
                # Simulate progress for non-streaming services
                yield {
                    "status": "starting",
                    "message": "Preparing transcription..."
                }
                
                # Estimate duration and chunks
                import torchaudio
                try:
                    waveform, sample_rate = torchaudio.load(str(audio_path))
                    duration = waveform.shape[1] / sample_rate
                    total_chunks = max(1, int(duration / 30) + (1 if duration % 30 > 0 else 0))
                except:
                    duration = 120.0  # Default estimate
                    total_chunks = 4
                
                yield {
                    "status": "transcribing",
                    "message": f"Starting transcription of {duration:.1f}s audio in {total_chunks} chunks...",
                    "total_chunks": total_chunks,
                    "duration": duration
                }
                
                # Simulate chunk processing
                for chunk_idx in range(total_chunks):
                    chunk_start = chunk_idx * 30
                    chunk_end = min((chunk_idx + 1) * 30, duration)
                    
                    yield {
                        "status": "processing_chunk",
                        "chunk_index": chunk_idx,
                        "chunk_start": chunk_start,
                        "chunk_end": chunk_end,
                        "total_chunks": total_chunks,
                        "message": f"Processing chunk {chunk_idx + 1}/{total_chunks} ({chunk_start:.1f}s - {chunk_end:.1f}s)"
                    }
                    
                    # Small delay to make progress visible
                    import asyncio
                    await asyncio.sleep(0.5)
                
                yield {
                    "status": "finalizing_transcription",
                    "message": "Finalizing transcription..."
                }
                
                # Perform actual transcription using regular method for non-streaming services
                if self.settings.whisper_use_local and self.local_whisper_service and self.local_whisper_service.is_available():
                    result = self.local_whisper_service.transcribe(audio_path)
                elif self.whisper_service and self.whisper_service.is_available():
                    result = self.whisper_service.transcribe(audio_path)
                else:
                    raise RuntimeError("No available Whisper service for transcription")
                
                yield {
                    "status": "transcription_complete",
                    "result": result,
                    "message": "Transcription completed successfully"
                }
                
        except Exception as e:
            logger.error(f"Streaming transcription failed: {e}")
            yield {
                "status": "error",
                "error": str(e),
                "message": f"Transcription failed: {str(e)}"
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the active model"""
        if self.settings.whisper_use_remote and self.remote_whisper_service and self.remote_whisper_service.is_available():
            info = self.remote_whisper_service.get_model_info()
            info["service_type"] = "remote_whisper"
            return info
        elif self.settings.whisper_use_vllm and self.vllm_whisper_service and self.vllm_whisper_service.is_available():
            info = self.vllm_whisper_service.get_service_status()
            info["service_type"] = "vllm"
            return info
        elif self.settings.whisper_use_local and self.local_whisper_service and self.local_whisper_service.is_available():
            info = self.local_whisper_service.get_model_info()
            info["service_type"] = "local"
            return info
        elif self.whisper_service and self.whisper_service.is_available():
            info = self.whisper_service.get_model_info()
            info["service_type"] = "openai"
            return info
        else:
            return {
                "available": False,
                "service_type": "none",
                "error": "No Whisper service available"
            }
    
    def switch_to_local(self) -> bool:
        """Switch to local Whisper service"""
        try:
            if not self.local_whisper_service:
                from .local_whisper_service import LocalWhisperService
                self.local_whisper_service = LocalWhisperService()
            
            if self.local_whisper_service.is_available():
                self.settings.whisper_use_local = True
                logger.info("Switched to local Whisper service")
                return True
            else:
                logger.error("Local Whisper service not available")
                return False
                
        except Exception as e:
            logger.error(f"Failed to switch to local Whisper: {e}")
            return False
    
    def switch_to_openai(self) -> bool:
        """Switch to OpenAI Whisper service"""
        try:
            if not self.whisper_service:
                self._initialize_openai_whisper()
            
            if self.whisper_service and self.whisper_service.is_available():
                self.settings.whisper_use_local = False
                logger.info("Switched to OpenAI Whisper service")
                return True
            else:
                logger.error("OpenAI Whisper service not available")
                return False
                
        except Exception as e:
            logger.error(f"Failed to switch to OpenAI Whisper: {e}")
            return False
    
    def download_local_model(self, model_name: str = None) -> bool:
        """Download a local model"""
        try:
            if not self.local_whisper_service:
                from .local_whisper_service import LocalWhisperService
                self.local_whisper_service = LocalWhisperService()
            
            return self.local_whisper_service.download_model(model_name)
            
        except Exception as e:
            logger.error(f"Failed to download local model: {e}")
            return False
    
    def get_current_revision(self) -> str:
        """Get the current revision setting"""
        return self.settings.whisper_revision

    def set_revision(self, revision: str) -> bool:
        """
        Set the revision for the whisper model.
        Note: For local service, this will reload the model.
        For remote service, the server must be restarted with the new revision.

        Args:
            revision: The revision to use ('default', 'strict', 'subtitle')

        Returns:
            True if successful, False otherwise
        """
        if revision not in ['default', 'strict', 'subtitle']:
            logger.error(f"Invalid revision: {revision}. Must be 'default', 'strict', or 'subtitle'")
            return False

        old_revision = self.settings.whisper_revision
        self.settings.whisper_revision = revision

        # If using local service and revision changed, reinitialize
        if self.settings.whisper_use_local and old_revision != revision:
            logger.info(f"Revision changed from '{old_revision}' to '{revision}', reloading local model...")
            try:
                from .local_whisper_service import LocalWhisperService
                self.local_whisper_service = LocalWhisperService()
                if self.local_whisper_service.is_available():
                    logger.info(f"Local Whisper model reloaded with revision: {revision}")
                    return True
                else:
                    logger.error("Failed to reload local Whisper model")
                    return False
            except Exception as e:
                logger.error(f"Failed to reload local Whisper model: {e}")
                return False

        logger.info(f"Revision set to: {revision}")
        return True

    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services"""
        # Determine current service
        current_service = "openai"  # default
        if self.settings.whisper_use_remote:
            current_service = "remote_whisper"
        elif self.settings.whisper_use_vllm:
            current_service = "vllm"
        elif self.settings.whisper_use_local:
            current_service = "local"

        status = {
            "current_service": current_service,
            "revision": self.settings.whisper_revision,
            "remote_available": False,
            "vllm_available": False,
            "local_available": False,
            "openai_available": False,
            "remote_info": None,
            "vllm_info": None,
            "local_model_info": None,
            "openai_model_info": None
        }

        if self.remote_whisper_service:
            status["remote_available"] = self.remote_whisper_service.is_available()
            if status["remote_available"]:
                status["remote_info"] = self.remote_whisper_service.get_model_info()

        if self.vllm_whisper_service:
            status["vllm_available"] = self.vllm_whisper_service.is_available()
            if status["vllm_available"]:
                status["vllm_info"] = self.vllm_whisper_service.get_service_status()

        if self.local_whisper_service:
            status["local_available"] = self.local_whisper_service.is_available()
            if status["local_available"]:
                status["local_model_info"] = self.local_whisper_service.get_model_info()

        if self.whisper_service:
            status["openai_available"] = self.whisper_service.is_available()
            if status["openai_available"]:
                status["openai_model_info"] = self.whisper_service.get_model_info()

        return status
