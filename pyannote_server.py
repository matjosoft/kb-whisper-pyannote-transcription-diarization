#!/usr/bin/env python3
"""
Standalone Pyannote Speaker Diarization Service

This service runs independently and provides speaker diarization via REST API.
It can be deployed on a separate machine with GPU resources.

Usage:
    python pyannote_server.py [--host HOST] [--port PORT] [--device DEVICE]

Environment Variables:
    PYANNOTE_MODEL: Model to use (default: pyannote/speaker-diarization-3.1)
    HF_AUTH_TOKEN: HuggingFace authentication token (required for some models)
    DEVICE: Device to use (cuda/cpu/mps, auto-detected if not set)
    MIN_SPEAKERS: Minimum number of speakers (default: 1)
    MAX_SPEAKERS: Maximum number of speakers (default: 10)
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import pyannote dependencies
try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    logger.error("Pyannote not installed. Install with: pip install pyannote.audio")
    PYANNOTE_AVAILABLE = False


class PyannoteServer:
    """Standalone Pyannote speaker diarization server"""

    def __init__(self,
                 model_name: str = None,
                 device: str = None,
                 min_speakers: int = 1,
                 max_speakers: int = 10):
        """
        Initialize the Pyannote server

        Args:
            model_name: Model to use for diarization
            device: Device to use (cuda/cpu/mps)
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers
        """
        self.model_name = model_name or os.getenv("PYANNOTE_MODEL", "pyannote/speaker-diarization-3.1")
        self.device = device or self._get_device()
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        self.pipeline: Optional[Pipeline] = None
        self.hf_auth_token = os.getenv("HF_AUTH_TOKEN")

        logger.info(f"Initializing Pyannote Server")
        logger.info(f"Model: {self.model_name}")
        logger.info(f"Device: {self.device}")
        logger.info(f"Speaker range: {self.min_speakers}-{self.max_speakers}")

        self._load_pipeline()

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

    def _load_pipeline(self):
        """Load the Pyannote diarization pipeline"""
        if not PYANNOTE_AVAILABLE:
            logger.error("Pyannote not available")
            return

        try:
            logger.info(f"Loading Pyannote pipeline '{self.model_name}'...")

            # Load the pre-trained pipeline
            self.pipeline = Pipeline.from_pretrained(
                self.model_name,
                token=self.hf_auth_token
            )

            # Move to appropriate device
            if self.device != "cpu":
                self.pipeline = self.pipeline.to(torch.device(self.device))

            logger.info("✅ Pyannote pipeline loaded successfully")

        except Exception as e:
            logger.error(f"❌ Failed to load Pyannote pipeline: {e}")
            logger.error("Make sure you have accepted the model license at:")
            logger.error(f"https://huggingface.co/{self.model_name}")
            self.pipeline = None

    def is_available(self) -> bool:
        """Check if the service is available"""
        return self.pipeline is not None

    def diarize(self, audio_path: str) -> Dict[str, Any]:
        """
        Perform speaker diarization on audio file

        Args:
            audio_path: Path to the audio file

        Returns:
            Dictionary containing diarization results with speaker segments
        """
        if not self.pipeline:
            raise RuntimeError("Pyannote pipeline not available")

        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            logger.info(f"Performing speaker diarization on: {audio_path}")

            # Apply the pipeline to the audio file
            diarization = self.pipeline(audio_path)

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

            logger.info(f"✅ Diarization completed: {len(speakers)} speakers in {len(segments)} segments")
            return diarization_result

        except Exception as e:
            logger.error(f"❌ Diarization failed: {e}")
            raise RuntimeError(f"Diarization failed: {str(e)}")

    def get_info(self) -> Dict[str, Any]:
        """Get information about the server"""
        return {
            "available": self.is_available(),
            "model_name": self.model_name,
            "device": self.device,
            "min_speakers": self.min_speakers,
            "max_speakers": self.max_speakers,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        }


# Create FastAPI app
app = FastAPI(
    title="Pyannote Diarization Service",
    description="Standalone speaker diarization service using Pyannote",
    version="1.0.0"
)

# Global server instance
server: Optional[PyannoteServer] = None


@app.on_event("startup")
async def startup_event():
    """Initialize the server on startup"""
    global server
    server = PyannoteServer(
        min_speakers=int(os.getenv("MIN_SPEAKERS", "1")),
        max_speakers=int(os.getenv("MAX_SPEAKERS", "10"))
    )
    if not server.is_available():
        logger.warning("⚠️ Server started but Pyannote pipeline is not available")
    else:
        logger.info("🚀 Pyannote server is ready")


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Pyannote Diarization Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
            "/info": "Server information",
            "/diarize": "POST - Perform diarization on uploaded audio"
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
        "message": "Service is running" if server.is_available() else "Pipeline not loaded"
    }


@app.get("/info")
async def get_info():
    """Get server information"""
    if server is None:
        raise HTTPException(status_code=503, detail="Server not initialized")

    return server.get_info()


@app.post("/diarize")
async def diarize_audio(file: UploadFile = File(...)):
    """
    Perform speaker diarization on uploaded audio file

    Args:
        file: Audio file (WAV, MP3, etc.)

    Returns:
        Diarization results with speaker segments
    """
    if server is None or not server.is_available():
        raise HTTPException(
            status_code=503,
            detail="Pyannote service not available"
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

        # Perform diarization
        result = server.diarize(temp_path)

        return JSONResponse({
            "success": True,
            "filename": file.filename,
            "result": result
        })

    except Exception as e:
        logger.error(f"Diarization request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Diarization failed: {str(e)}"
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
        description="Pyannote Speaker Diarization Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  PYANNOTE_MODEL     Model to use (default: pyannote/speaker-diarization-3.1)
  HF_AUTH_TOKEN      HuggingFace authentication token (required)
  DEVICE             Device to use (cuda/cpu/mps, auto-detected if not set)
  MIN_SPEAKERS       Minimum number of speakers (default: 1)
  MAX_SPEAKERS       Maximum number of speakers (default: 10)

Example:
  python pyannote_server.py --host 0.0.0.0 --port 8001

  # With custom model
  export PYANNOTE_MODEL=pyannote/speaker-diarization-3.1
  export HF_AUTH_TOKEN=your_token_here
  python pyannote_server.py
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
        default=8001,
        help="Port to bind to (default: 8001)"
    )

    parser.add_argument(
        "--device",
        type=str,
        choices=["cuda", "cpu", "mps"],
        help="Device to use (auto-detected if not specified)"
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

    # Check for HF token
    if not os.getenv("HF_AUTH_TOKEN"):
        logger.warning("⚠️ HF_AUTH_TOKEN not set. You may need it for some models.")
        logger.warning("Set it with: export HF_AUTH_TOKEN=your_token_here")

    # Print startup information
    print("\n" + "="*60)
    print("🎙️  Pyannote Speaker Diarization Service")
    print("="*60)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Model: {os.getenv('PYANNOTE_MODEL', 'pyannote/speaker-diarization-3.1')}")
    print("="*60 + "\n")

    # Run the server
    uvicorn.run(
        "pyannote_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
