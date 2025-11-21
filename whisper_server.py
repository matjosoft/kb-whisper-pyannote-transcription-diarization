#!/usr/bin/env python3
"""
Standalone Whisper Transcription Service

This service runs independently and provides speech transcription via REST API.
It can be deployed on a separate machine with GPU resources.

Usage:
    python whisper_server.py [--host HOST] [--port PORT] [--device DEVICE]

Environment Variables:
    WHISPER_MODEL: Model to use (default: KBLab/kb-whisper-large)
    HF_AUTH_TOKEN: HuggingFace authentication token (optional for some models)
    DEVICE: Device to use (cuda/cpu/mps, auto-detected if not set)
    WHISPER_LANGUAGE: Language code (default: sv for Swedish, or 'auto')
"""

import os
import sys
import argparse
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import torch
import torchaudio
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Whisper dependencies
try:
    from transformers import (
        AutoProcessor,
        AutoModelForSpeechSeq2Seq,
        pipeline
    )
    WHISPER_AVAILABLE = True
except ImportError:
    logger.error("Transformers not installed. Install with: pip install transformers")
    WHISPER_AVAILABLE = False


class WhisperServer:
    """Standalone Whisper transcription server"""

    def __init__(self,
                 model_name: str = None,
                 device: str = None,
                 language: str = None):
        """
        Initialize the Whisper server

        Args:
            model_name: Model to use for transcription
            device: Device to use (cuda/cpu/mps)
            language: Language code (e.g., 'sv', 'en', 'auto')
        """
        self.model_name = model_name or os.getenv("WHISPER_MODEL", "KBLab/kb-whisper-large")
        self.device = device or self._get_device()
        self.language = language or os.getenv("WHISPER_LANGUAGE", "sv")
        self.processor: Optional[AutoProcessor] = None
        self.model: Optional[AutoModelForSpeechSeq2Seq] = None
        self.pipe: Optional[pipeline] = None
        self.hf_auth_token = os.getenv("HF_AUTH_TOKEN")

        logger.info(f"Initializing Whisper Server")
        logger.info(f"Model: {self.model_name}")
        logger.info(f"Device: {self.device}")
        logger.info(f"Language: {self.language}")

        self._load_model()

    def _get_device(self) -> str:
        """Auto-detect the best available device"""
        if torch.cuda.is_available():
            device = "cuda"
            logger.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = "mps"
            logger.info("Apple Silicon (MPS) available")
        else:
            device = "cpu"
            logger.info("Using CPU")
        return device

    def _load_model(self):
        """Load the Whisper model"""
        if not WHISPER_AVAILABLE:
            logger.error("Transformers library not available")
            return

        try:
            logger.info(f"Loading Whisper model '{self.model_name}'...")

            # Determine torch dtype based on device
            torch_dtype = torch.float16 if self.device == "cuda" else torch.float32

            # Load the model with safetensors
            self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                self.model_name,
                torch_dtype=torch_dtype,
                use_safetensors=True,
                low_cpu_mem_usage=True,
                token=self.hf_auth_token
            )

            # Move model to device
            self.model.to(self.device)

            # Load processor
            self.processor = AutoProcessor.from_pretrained(
                self.model_name,
                token=self.hf_auth_token
            )

            # Create pipeline for easier inference
            self.pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model,
                tokenizer=self.processor.tokenizer,
                feature_extractor=self.processor.feature_extractor,
                torch_dtype=torch_dtype,
                device=self.device,
                model_kwargs={"use_cache": False}
            )

            logger.info("✅ Whisper model loaded successfully")

        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            logger.error("Make sure you have accepted the model license if required:")
            logger.error(f"https://huggingface.co/{self.model_name}")
            self.model = None
            self.processor = None
            self.pipe = None

    def is_available(self) -> bool:
        """Check if the service is available"""
        return self.pipe is not None and self.model is not None

    def _load_audio(self, audio_path: str) -> np.ndarray:
        """Load and preprocess audio file"""
        try:
            # Load audio using torchaudio
            waveform, sample_rate = torchaudio.load(audio_path)

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

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Perform transcription on audio file

        Args:
            audio_path: Path to the audio file

        Returns:
            Dictionary containing transcription results with segments and timestamps
        """
        if not self.pipe or not self.model:
            raise RuntimeError("Whisper model not available")

        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            logger.info(f"Performing transcription on: {audio_path}")

            # Load and preprocess audio
            audio_array = self._load_audio(audio_path)

            # Set language if specified
            generate_kwargs = {}
            if self.language != "auto":
                generate_kwargs["language"] = self.language

            # Transcribe with timestamps
            result = self.pipe(
                audio_array,
                chunk_length_s=30,
                stride_length_s=5,
                return_timestamps=True,
                generate_kwargs=generate_kwargs
            )

            # Process the result to match expected format
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
                            "words": []
                        }
                        segments.append(segment_data)
                        full_text += text + " "
            else:
                # Fallback if chunks are not available
                text = result.get("text", "").strip()
                if text:
                    segments.append({
                        "start": 0.0,
                        "end": len(audio_array) / 16000,
                        "text": text,
                        "words": []
                    })
                    full_text = text

            # Determine detected language
            detected_language = self.language if self.language != "auto" else "auto-detected"

            transcription_result = {
                "text": full_text.strip(),
                "language": detected_language,
                "segments": segments,
                "duration": max([seg["end"] for seg in segments]) if segments else 0,
                "model_type": "local_whisper"
            }

            logger.info(f"✅ Transcription completed: {len(segments)} segments, {transcription_result['duration']:.2f}s")
            return transcription_result

        except Exception as e:
            logger.error(f"❌ Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {str(e)}")

    def get_info(self) -> Dict[str, Any]:
        """Get information about the server"""
        return {
            "available": self.is_available(),
            "model_name": self.model_name,
            "device": self.device,
            "language": self.language,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "torch_dtype": str(self.model.dtype) if self.model else None
        }


# Create FastAPI app
app = FastAPI(
    title="Whisper Transcription Service",
    description="Standalone speech transcription service using Whisper",
    version="1.0.0"
)

# Global server instance
server: Optional[WhisperServer] = None


@app.on_event("startup")
async def startup_event():
    """Initialize the server on startup"""
    global server
    server = WhisperServer()
    if not server.is_available():
        logger.warning("⚠️ Server started but Whisper model is not available")
    else:
        logger.info("🚀 Whisper server is ready")


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Whisper Transcription Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
            "/info": "Server information",
            "/transcribe": "POST - Perform transcription on uploaded audio"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if server is None:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "message": "Server not initialized"}
        )

    return {
        "status": "healthy" if server.is_available() else "degraded",
        "available": server.is_available(),
        "message": "Service is running" if server.is_available() else "Model not loaded"
    }


@app.get("/info")
async def get_info():
    """Get server information"""
    if server is None:
        raise HTTPException(status_code=503, detail="Server not initialized")

    return server.get_info()


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Perform transcription on uploaded audio file

    Args:
        file: Audio file (WAV, MP3, etc.)

    Returns:
        Transcription results with segments and timestamps
    """
    if server is None or not server.is_available():
        raise HTTPException(
            status_code=503,
            detail="Whisper service not available"
        )

    # Create temporary file to save uploaded audio
    temp_file = None
    try:
        # Save uploaded file to temporary location
        suffix = Path(file.filename).suffix if file.filename else '.wav'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        logger.info(f"Processing uploaded file: {file.filename} ({len(content)} bytes)")

        # Perform transcription
        result = server.transcribe(temp_path)

        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "result": result
        })

    except Exception as e:
        logger.error(f"Transcription request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )

    finally:
        # Clean up temporary file
        if temp_file and Path(temp_file.name).exists():
            try:
                Path(temp_file.name).unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")


def main():
    """Main entry point for the server"""
    parser = argparse.ArgumentParser(
        description="Whisper Speech Transcription Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  WHISPER_MODEL      Model to use (default: KBLab/kb-whisper-large)
  HF_AUTH_TOKEN      HuggingFace authentication token (optional)
  DEVICE             Device to use (cuda/cpu/mps, auto-detected if not set)
  WHISPER_LANGUAGE   Language code (default: sv for Swedish, or 'auto')

Example:
  python whisper_server.py --host 0.0.0.0 --port 8002

  # With custom model
  export WHISPER_MODEL=openai/whisper-large-v3
  export HF_AUTH_TOKEN=your_token_here
  export WHISPER_LANGUAGE=en
  python whisper_server.py
        """
    )

    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="Port to bind to (default: 8002)"
    )

    parser.add_argument(
        "--device",
        type=str,
        choices=["cuda", "cpu", "mps"],
        help="Device to use (auto-detected if not specified)"
    )

    parser.add_argument(
        "--language",
        type=str,
        help="Language code (e.g., 'sv', 'en', 'auto')"
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )

    args = parser.parse_args()

    # Set device if specified
    if args.device:
        os.environ["DEVICE"] = args.device

    # Set language if specified
    if args.language:
        os.environ["WHISPER_LANGUAGE"] = args.language

    # Check for HF token (optional for some models)
    if not os.getenv("HF_AUTH_TOKEN"):
        logger.info("ℹ️  HF_AUTH_TOKEN not set (optional for some models)")

    # Print startup information
    print("\n" + "="*60)
    print("🎤  Whisper Speech Transcription Service")
    print("="*60)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Model: {os.getenv('WHISPER_MODEL', 'KBLab/kb-whisper-large')}")
    print(f"Language: {os.getenv('WHISPER_LANGUAGE', 'sv')}")
    print("="*60 + "\n")

    # Run the server
    uvicorn.run(
        "whisper_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
