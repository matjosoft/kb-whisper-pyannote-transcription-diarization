import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
# Search for .env in the project root (parent of backend directory)
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"✅ Loaded environment variables from {env_path}")
else:
    # Try loading from current directory
    load_dotenv()
    print("⚠️ No .env file found in project root, using system environment variables")

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
        self.whisper_use_vllm = os.getenv("WHISPER_USE_VLLM", "false").lower() == "true"
        self.whisper_use_remote = os.getenv("WHISPER_USE_REMOTE", "false").lower() == "true"
        self.whisper_local_model_path = os.getenv("WHISPER_LOCAL_MODEL_PATH", f"D:\Develop\AI\kb-whisper\model\model.safetensors")
        self.whisper_local_model_name = os.getenv("WHISPER_LOCAL_MODEL_NAME", "KBLab/kb-whisper-large")
        self.whisper_remote_url = os.getenv("WHISPER_REMOTE_URL", "http://localhost:8002")

        # vLLM settings
        self.vllm_base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
        self.vllm_api_key = os.getenv("VLLM_API_KEY", "token-abc123")
        self.vllm_model_name = os.getenv("VLLM_MODEL_NAME", "KBLab/kb-whisper-large")
        self.vllm_max_audio_filesize_mb = int(os.getenv("VLLM_MAX_AUDIO_FILESIZE_MB", "25"))

        # Debug print Whisper settings if remote or vLLM is enabled
        if self.whisper_use_remote:
            print(f"🔧 Remote Whisper enabled: {self.whisper_remote_url}")
        if self.whisper_use_vllm:
            print(f"🔧 vLLM enabled: {self.vllm_base_url} | Model: {self.vllm_model_name}")
            print(f"🔧 vLLM max file size: {self.vllm_max_audio_filesize_mb}MB (large files split into 30s chunks)")
        
        # Pyannote settings
        self.pyannote_model = os.getenv("PYANNOTE_MODEL", "pyannote/speaker-diarization-3.1")
        self.pyannote_use_remote = os.getenv("PYANNOTE_USE_REMOTE", "false").lower() == "true"
        self.pyannote_remote_url = os.getenv("PYANNOTE_REMOTE_URL", "http://localhost:8001")
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
