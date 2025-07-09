#!/usr/bin/env python3
"""
Test script for local Whisper functionality
"""

import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from services.local_whisper_service import LocalWhisperService
from services.unified_whisper_service import UnifiedWhisperService
from utils.config import get_settings

def test_local_whisper():
    """Test local Whisper service"""
    print("🧪 Testing Local Whisper Service")
    print("=" * 50)
    
    # Test configuration
    settings = get_settings()
    print(f"Device: {settings.device}")
    print(f"Use Local Whisper: {settings.whisper_use_local}")
    print(f"Local Model Name: {settings.whisper_local_model_name}")
    print(f"Local Model Path: {settings.whisper_local_model_path}")
    print()
    
    # Test local Whisper service
    try:
        print("Initializing Local Whisper Service...")
        local_service = LocalWhisperService()
        
        if local_service.is_available():
            print("✅ Local Whisper service is available")
            model_info = local_service.get_model_info()
            print(f"Model Info: {model_info}")
        else:
            print("❌ Local Whisper service is not available")
            print("This might be because:")
            print("- The model hasn't been downloaded yet")
            print("- Missing dependencies (transformers, torch, etc.)")
            print("- Insufficient memory or GPU resources")
    except Exception as e:
        print(f"❌ Error initializing Local Whisper service: {e}")
    
    print()
    
    # Test unified Whisper service
    try:
        print("Initializing Unified Whisper Service...")
        unified_service = UnifiedWhisperService()
        
        if unified_service.is_available():
            print("✅ Unified Whisper service is available")
            model_info = unified_service.get_model_info()
            print(f"Model Info: {model_info}")
            
            status = unified_service.get_service_status()
            print(f"Service Status: {status}")
        else:
            print("❌ Unified Whisper service is not available")
    except Exception as e:
        print(f"❌ Error initializing Unified Whisper service: {e}")

def test_model_download():
    """Test downloading a local model"""
    print("\n🔽 Testing Model Download")
    print("=" * 50)
    
    try:
        local_service = LocalWhisperService()
        
        # Try to download the default model
        print("Attempting to download default model...")
        success = local_service.download_model()
        
        if success:
            print("✅ Model download successful")
        else:
            print("❌ Model download failed")
            
    except Exception as e:
        print(f"❌ Error during model download: {e}")

def print_environment_info():
    """Print environment information"""
    print("🔧 Environment Information")
    print("=" * 50)
    
    # Check Python version
    print(f"Python Version: {sys.version}")
    
    # Check if torch is available
    try:
        import torch
        print(f"PyTorch Version: {torch.__version__}")
        print(f"CUDA Available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"CUDA Version: {torch.version.cuda}")
            print(f"GPU Count: {torch.cuda.device_count()}")
    except ImportError:
        print("❌ PyTorch not available")
    
    # Check if transformers is available
    try:
        import transformers
        print(f"Transformers Version: {transformers.__version__}")
    except ImportError:
        print("❌ Transformers not available")
    
    # Check if torchaudio is available
    try:
        import torchaudio
        print(f"TorchAudio Version: {torchaudio.__version__}")
    except ImportError:
        print("❌ TorchAudio not available")
    
    print()

def main():
    """Main test function"""
    print("🎤 Local Whisper Test Suite")
    print("=" * 50)
    print()
    
    # Print environment info
    print_environment_info()
    
    # Test local Whisper
    test_local_whisper()
    
    # Ask if user wants to test model download
    print("\n" + "=" * 50)
    response = input("Do you want to test model download? (y/N): ").strip().lower()
    if response in ['y', 'yes']:
        test_model_download()
    
    print("\n✅ Test suite completed!")

if __name__ == "__main__":
    main()
