#!/usr/bin/env python3
"""
Audio Scribe AI - Main entry point
Run this script to start the application
"""

import os
import sys
import logging
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if required dependencies are available"""
    try:
        import fastapi
        import uvicorn
        logger.info("Core web dependencies found")
        
        # Check AI dependencies
        ai_deps_available = True
        try:
            import torch
            import whisper
            import pyannote.audio
            logger.info("AI dependencies found - full functionality available")
        except ImportError as e:
            logger.warning(f"AI dependencies missing ({e}) - using mock services for testing")
            ai_deps_available = False
        
        return True
    except ImportError as e:
        logger.error(f"Missing core dependency: {e}")
        logger.error("Please install requirements: pip install fastapi uvicorn")
        return False

def check_ffmpeg():
    """Check if FFmpeg is available"""
    import subprocess
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      capture_output=True, check=True)
        logger.info("FFmpeg found")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("FFmpeg not found. Audio conversion may not work properly.")
        logger.warning("Please install FFmpeg: https://ffmpeg.org/download.html")
        return False

def check_gpu():
    """Check GPU availability and enable TF32 for performance"""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"CUDA GPU available: {gpu_name}")

            # Enable TF32 for better performance on Ampere+ GPUs
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            logger.info("TF32 enabled for improved GPU performance")

            return True
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            logger.info("Apple Silicon GPU (MPS) available")
            return True
        else:
            logger.info("No GPU acceleration available, using CPU")
            return False
    except Exception as e:
        logger.warning(f"Error checking GPU: {e}")
        return False

def main():
    """Main entry point"""
    logger.info("Starting Audio Scribe AI...")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check FFmpeg
    check_ffmpeg()
    
    # Check GPU
    check_gpu()
    
    # Create necessary directories
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    
    logger.info("Directories created")
    
    # Import and run the FastAPI app
    try:
        from app import app
        import uvicorn
        
        logger.info("Starting server on http://localhost:8000")
        logger.info("Press Ctrl+C to stop the server")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()