import logging
from pathlib import Path
from typing import Dict, Any, Optional

from utils.config import get_settings

logger = logging.getLogger(__name__)

class UnifiedWhisperService:
    """Unified service that can use either OpenAI Whisper or local Whisper models"""
    
    def __init__(self):
        self.settings = get_settings()
        self.whisper_service = None
        self.local_whisper_service = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize the appropriate Whisper service based on configuration"""
        try:
            if self.settings.whisper_use_local:
                logger.info("Initializing local Whisper service")
                from .local_whisper_service import LocalWhisperService
                self.local_whisper_service = LocalWhisperService()
                if not self.local_whisper_service.is_available():
                    logger.warning("Local Whisper service failed to initialize, falling back to OpenAI Whisper")
                    self._initialize_openai_whisper()
            else:
                logger.info("Initializing OpenAI Whisper service")
                self._initialize_openai_whisper()
                
        except Exception as e:
            logger.error(f"Failed to initialize Whisper services: {e}")
            # Try to fall back to OpenAI Whisper
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
        if self.settings.whisper_use_local and self.local_whisper_service:
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
            if self.settings.whisper_use_local and self.local_whisper_service and self.local_whisper_service.is_available():
                logger.info("Using local Whisper service for transcription")
                return self.local_whisper_service.transcribe(audio_path)
            elif self.whisper_service and self.whisper_service.is_available():
                logger.info("Using OpenAI Whisper service for transcription")
                return self.whisper_service.transcribe(audio_path)
            else:
                raise RuntimeError("No available Whisper service for transcription")
                
        except Exception as e:
            # If local Whisper fails, try to fall back to OpenAI Whisper
            if (self.settings.whisper_use_local and 
                self.whisper_service and 
                self.whisper_service.is_available()):
                logger.warning(f"Local Whisper failed ({e}), falling back to OpenAI Whisper")
                return self.whisper_service.transcribe(audio_path)
            else:
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
            if (self.settings.whisper_use_local and
                self.local_whisper_service and
                self.local_whisper_service.is_available() and
                hasattr(self.local_whisper_service, 'transcribe_with_progress')):
                logger.info("Using local Whisper service for streaming transcription")
                async for progress_data in self.local_whisper_service.transcribe_with_progress(audio_path):
                    yield progress_data
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
        if self.settings.whisper_use_local and self.local_whisper_service and self.local_whisper_service.is_available():
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
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of both services"""
        status = {
            "current_service": "local" if self.settings.whisper_use_local else "openai",
            "local_available": False,
            "openai_available": False,
            "local_model_info": None,
            "openai_model_info": None
        }
        
        if self.local_whisper_service:
            status["local_available"] = self.local_whisper_service.is_available()
            if status["local_available"]:
                status["local_model_info"] = self.local_whisper_service.get_model_info()
        
        if self.whisper_service:
            status["openai_available"] = self.whisper_service.is_available()
            if status["openai_available"]:
                status["openai_model_info"] = self.whisper_service.get_model_info()
        
        return status
