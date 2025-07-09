import os
from pathlib import Path
from typing import Optional

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

class Settings:
    """Application configuration settings"""
    
    def __init__(self):
        # Audio processing settings
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", 100 * 1024 * 1024))  # 100MB
        self.supported_formats = [".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"]
        
        # Whisper settings
        self.whisper_model = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large
        self.whisper_language = os.getenv("WHISPER_LANGUAGE", "sv")  # auto-detect or specific language
        self.whisper_use_local = os.getenv("WHISPER_USE_LOCAL", "true").lower() == "true"
        self.whisper_local_model_path = os.getenv("WHISPER_LOCAL_MODEL_PATH", f"D:\Develop\AI\kb-whisper\model\model.safetensors")
        self.whisper_local_model_name = os.getenv("WHISPER_LOCAL_MODEL_NAME", "KBLab/kb-whisper-large")
        
        # Pyannote settings
        self.pyannote_model = os.getenv("PYANNOTE_MODEL", "pyannote/speaker-diarization-3.1")
        self.min_speakers = int(os.getenv("MIN_SPEAKERS", 1))
        self.max_speakers = int(os.getenv("MAX_SPEAKERS", 10))
        
        # Device settings
        self.device = self._get_device()
        
        # Paths
        self.upload_dir = Path("uploads")
        self.temp_dir = Path("temp")
        
        # Create directories
        self.upload_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
    
    def _get_device(self) -> str:
        """Determine the best available device for processing"""
        if not TORCH_AVAILABLE:
            return "cpu"
        
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"  # Apple Silicon
        else:
            return "cpu"
    
    @property
    def is_gpu_available(self) -> bool:
        """Check if GPU acceleration is available"""
        return self.device != "cpu"

# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get or create global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
