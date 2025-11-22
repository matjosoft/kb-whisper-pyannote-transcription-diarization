import torch
import torchaudio
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging
import numpy as np
from safetensors import safe_open

from transformers import (
    WhisperProcessor, 
    WhisperForConditionalGeneration,
    AutoConfig,
    AutoProcessor,
    AutoModelForSpeechSeq2Seq,
    pipeline
)

from utils.config import get_settings

logger = logging.getLogger(__name__)

class LocalWhisperService:
    """Service for handling local Whisper speech-to-text transcription using Hugging Face transformers"""
    
    def __init__(self):
        self.settings = get_settings()
        self.processor: Optional[WhisperProcessor] = None
        self.model: Optional[WhisperForConditionalGeneration] = None
        self.pipe: Optional[pipeline] = None
        #self._load_model()
        self._load_safetensors_whisper()

    def _load_safetensors_whisper(self, revision: str = None):
        device = "cuda:0" if torch.cuda.is_available() else "cpu"

        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        model_id = "KBLab/kb-whisper-large"

        # Determine revision to use
        revision_to_use = revision or self.settings.whisper_revision

        # Load model with explicit revision parameter
        if revision_to_use and revision_to_use != "default":
            logger.info(f"Loading model with revision: {revision_to_use}")
            self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                model_id,
                torch_dtype=torch_dtype,
                use_safetensors=True,
                cache_dir="cache",
                revision=revision_to_use
            )
            self.processor = AutoProcessor.from_pretrained(model_id, revision=revision_to_use)
        else:
            logger.info("Loading model with default revision")
            self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                model_id,
                torch_dtype=torch_dtype,
                use_safetensors=True,
                cache_dir="cache"
            )
            self.processor = AutoProcessor.from_pretrained(model_id)

        self.model.to(device)

        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=self.model,
            tokenizer=self.processor.tokenizer,
            feature_extractor=self.processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=device,
            model_kwargs={"use_cache": False}
        )
       

    
    def _load_model(self):
        """Load the local Whisper model"""
        try:
            model_name_or_path = self._get_model_path()
            logger.info(f"Loading local Whisper model '{model_name_or_path}' on device '{self.settings.device}'")
            
            # Load processor and model
            self.processor = WhisperProcessor.from_pretrained(model_name_or_path)
            self.model = WhisperForConditionalGeneration.from_pretrained(
                model_name_or_path,
                torch_dtype=torch.float16 if self.settings.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True,
                use_safetensors=True
            )
            
            # Move model to device
            self.model.to(self.settings.device)
            
            # Create pipeline for easier inference
            self.pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model,
                tokenizer=self.processor.tokenizer,
                feature_extractor=self.processor.feature_extractor,
                torch_dtype=torch.float16 if self.settings.device == "cuda" else torch.float32,
                device=self.settings.device,
                return_timestamps=True
            )
            
            logger.info("Local Whisper model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load local Whisper model: {e}")
            self.processor = None
            self.model = None
            self.pipe = None
    
    def _get_model_path(self) -> str:
        """Get the model path or name"""
        if self.settings.whisper_local_model_path and Path(self.settings.whisper_local_model_path).exists():
            return self.settings.whisper_local_model_path
        else:
            return self.settings.whisper_local_model_name
    
    def is_available(self) -> bool:
        """Check if local Whisper service is available"""
        return self.model is not None and self.processor is not None and self.pipe is not None
    
    def _load_audio(self, audio_path: Path) -> np.ndarray:
        """Load and preprocess audio file"""
        try:
            # Load audio using torchaudio
            waveform, sample_rate = torchaudio.load(str(audio_path))
            
            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Resample to 16kHz if needed (Whisper expects 16kHz)
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(sample_rate, 16000)
                waveform = resampler(waveform)
            
            # Convert to numpy array and flatten
            audio_array = waveform.squeeze().numpy()
            
            return audio_array
            
        except Exception as e:
            logger.error(f"Failed to load audio: {e}")
            raise RuntimeError(f"Audio loading failed: {str(e)}")
    
    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        """
        Transcribe audio file using local Whisper model
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dictionary containing transcription results with segments and timestamps
        """
        if not self.is_available():
            raise RuntimeError("Local Whisper model not available")
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            logger.info(f"Transcribing audio file with local Whisper: {audio_path}")
            
            # Load and preprocess audio
            audio_array = self._load_audio(audio_path)
            
            # Set language if specified
            generate_kwargs = {}
            if self.settings.whisper_language != "auto":
                generate_kwargs["language"] = self.settings.whisper_language
            
            # Transcribe with timestamps
            result = self.pipe(
                audio_array,
                chunk_length_s=30,
                stride_length_s=5,
                return_timestamps=True,
                generate_kwargs=generate_kwargs
            )
            
            # Process the result to match the expected format
            segments = []
            full_text = ""
            
            if "chunks" in result:
                for chunk in result["chunks"]:
                    timestamp = chunk.get("timestamp", [0, 0])
                    start_time = timestamp[0] if timestamp[0] is not None else 0
                    end_time = timestamp[1] if timestamp[1] is not None else start_time + 1
                    text = chunk.get("text", "").strip()
                    
                    if text:
                        segment_data = {
                            "start": start_time,
                            "end": end_time,
                            "text": text,
                            "words": []  # Word-level timestamps not available with this pipeline
                        }
                        segments.append(segment_data)
                        full_text += text + " "
            else:
                # Fallback if chunks are not available
                text = result.get("text", "").strip()
                if text:
                    segments.append({
                        "start": 0.0,
                        "end": len(audio_array) / 16000,  # Approximate duration
                        "text": text,
                        "words": []
                    })
                    full_text = text
            
            # Detect language if auto-detection was used
            detected_language = "unknown"
            if hasattr(self.model.config, 'lang_to_id') and self.settings.whisper_language == "auto":
                # Try to detect language from the model's output
                # This is a simplified approach - in practice, you might want to use the model's language detection
                detected_language = "auto-detected"
            elif self.settings.whisper_language != "auto":
                detected_language = self.settings.whisper_language
            
            transcription_result = {
                "text": full_text.strip(),
                "language": detected_language,
                "segments": segments,
                "duration": max([seg["end"] for seg in segments]) if segments else 0,
                "model_type": "local_whisper"
            }
            
            logger.info(f"Local transcription completed. Found {len(segments)} segments")
            return transcription_result
            
        except Exception as e:
            logger.error(f"Local transcription failed: {e}")
            raise RuntimeError(f"Local transcription failed: {str(e)}")
    
    async def transcribe_with_progress(self, audio_path: Path, progress_callback=None):
        """
        Transcribe audio file with progress updates for streaming
        
        Args:
            audio_path: Path to the audio file
            progress_callback: Optional callback function for progress updates
            
        Yields:
            Progress updates as dictionaries
        """
        if not self.is_available():
            raise RuntimeError("Local Whisper model not available")
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            logger.info(f"Transcribing audio file with progress tracking: {audio_path}")
            
            # Load and preprocess audio
            audio_array = self._load_audio(audio_path)
            duration = len(audio_array) / 16000  # Sample rate is 16kHz
            chunk_duration = 30  # 30 second chunks
            total_chunks = max(1, int(duration / chunk_duration) + (1 if duration % chunk_duration > 0 else 0))
            
            # Yield initial progress
            yield {
                "status": "transcribing",
                "message": f"Starting transcription of {duration:.1f}s audio in {total_chunks} chunks...",
                "total_chunks": total_chunks,
                "duration": duration
            }
            
            # Set language if specified
            generate_kwargs = {}
            if self.settings.whisper_language != "auto":
                generate_kwargs["language"] = self.settings.whisper_language
            
            # Process audio in chunks with progress updates
            segments = []
            full_text = ""
            
            # Split audio into chunks for progress tracking
            chunk_size = int(chunk_duration * 16000)  # 30 seconds worth of samples
            
            for chunk_idx in range(total_chunks):
                start_sample = chunk_idx * chunk_size
                end_sample = min((chunk_idx + 1) * chunk_size, len(audio_array))
                chunk_audio = audio_array[start_sample:end_sample]
                
                chunk_start_time = chunk_idx * chunk_duration
                chunk_end_time = min((chunk_idx + 1) * chunk_duration, duration)
                
                # Yield chunk processing status
                yield {
                    "status": "processing_chunk",
                    "chunk_index": chunk_idx,
                    "chunk_start": chunk_start_time,
                    "chunk_end": chunk_end_time,
                    "total_chunks": total_chunks,
                    "message": f"Processing chunk {chunk_idx + 1}/{total_chunks} ({chunk_start_time:.1f}s - {chunk_end_time:.1f}s)"
                }
                
                # Process this chunk
                try:
                    chunk_result = self.pipe(
                        chunk_audio,
                        chunk_length_s=30,
                        stride_length_s=5,
                        return_timestamps=True,
                        generate_kwargs=generate_kwargs
                    )
                    
                    # Process chunk results
                    if "chunks" in chunk_result:
                        for sub_chunk in chunk_result["chunks"]:
                            timestamp = sub_chunk.get("timestamp", [0, 0])
                            start_time = (timestamp[0] if timestamp[0] is not None else 0) + chunk_start_time
                            end_time = (timestamp[1] if timestamp[1] is not None else start_time + 1) + chunk_start_time
                            text = sub_chunk.get("text", "").strip()
                            
                            if text:
                                segment_data = {
                                    "start": start_time,
                                    "end": end_time,
                                    "text": text,
                                    "words": []
                                }
                                segments.append(segment_data)
                                full_text += text + " "
                    else:
                        # Fallback for chunk without sub-chunks
                        text = chunk_result.get("text", "").strip()
                        if text:
                            segments.append({
                                "start": chunk_start_time,
                                "end": chunk_end_time,
                                "text": text,
                                "words": []
                            })
                            full_text += text + " "
                            
                except Exception as chunk_error:
                    logger.warning(f"Failed to process chunk {chunk_idx}: {chunk_error}")
                    # Continue with next chunk
                    continue
            
            # Yield finalization status
            yield {
                "status": "finalizing_transcription",
                "message": "Finalizing transcription results..."
            }
            
            # Detect language if auto-detection was used
            detected_language = "unknown"
            if hasattr(self.model.config, 'lang_to_id') and self.settings.whisper_language == "auto":
                detected_language = "auto-detected"
            elif self.settings.whisper_language != "auto":
                detected_language = self.settings.whisper_language
            
            transcription_result = {
                "text": full_text.strip(),
                "language": detected_language,
                "segments": segments,
                "duration": max([seg["end"] for seg in segments]) if segments else duration,
                "model_type": "local_whisper"
            }
            
            # Yield final result
            yield {
                "status": "transcription_complete",
                "result": transcription_result,
                "message": f"Transcription completed. Found {len(segments)} segments"
            }
            
            logger.info(f"Local transcription with progress completed. Found {len(segments)} segments")
            
        except Exception as e:
            logger.error(f"Local transcription with progress failed: {e}")
            yield {
                "status": "error",
                "error": str(e),
                "message": f"Transcription failed: {str(e)}"
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        if not self.is_available():
            return {"available": False}

        return {
            "available": True,
            "model_name": self._get_model_path(),
            "model_type": "local_whisper",
            "device": self.settings.device,
            "language": self.settings.whisper_language,
            "revision": self.settings.whisper_revision,
            "torch_dtype": str(self.model.dtype) if self.model else "unknown"
        }
    
    def download_model(self, model_name: str = None) -> bool:
        """
        Download a model from Hugging Face Hub
        
        Args:
            model_name: Name of the model to download (e.g., "openai/whisper-base")
            
        Returns:
            True if successful, False otherwise
        """
        if model_name is None:
            model_name = self.settings.whisper_local_model_name
        
        try:
            logger.info(f"Downloading model: {model_name}")
            
            # Download processor and model
            processor = WhisperProcessor.from_pretrained(model_name)
            model = WhisperForConditionalGeneration.from_pretrained(model_name)
            
            logger.info(f"Model {model_name} downloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download model {model_name}: {e}")
            return False
