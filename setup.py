#!/usr/bin/env python3
"""
Setup script for Audio Scribe AI
This script helps set up the environment and install dependencies
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python version {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing Python dependencies...")
    
    # Upgrade pip first
    if not run_command(f"{sys.executable} -m pip install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install PyTorch with CUDA support if available
    system = platform.system().lower()
    if system == "windows" or system == "linux":
        print("Installing PyTorch with CUDA support...")
        torch_command = f"{sys.executable} -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118"
        if not run_command(torch_command, "Installing PyTorch with CUDA"):
            print("⚠️  CUDA installation failed, trying CPU version...")
            torch_command = f"{sys.executable} -m pip install torch torchaudio"
            if not run_command(torch_command, "Installing PyTorch (CPU)"):
                return False
    else:
        # macOS or other systems
        torch_command = f"{sys.executable} -m pip install torch torchaudio"
        if not run_command(torch_command, "Installing PyTorch"):
            return False
    
    # Install other requirements
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt", "Installing other dependencies"):
        return False
    
    return True

def check_ffmpeg():
    """Check if FFmpeg is installed"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✅ FFmpeg is installed")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ FFmpeg not found")
        system = platform.system().lower()
        
        if system == "windows":
            print("Please install FFmpeg:")
            print("1. Download from https://ffmpeg.org/download.html")
            print("2. Extract to a folder (e.g., C:\\ffmpeg)")
            print("3. Add C:\\ffmpeg\\bin to your PATH environment variable")
        elif system == "darwin":  # macOS
            print("Please install FFmpeg using Homebrew:")
            print("brew install ffmpeg")
        else:  # Linux
            print("Please install FFmpeg:")
            print("sudo apt update && sudo apt install ffmpeg")
        
        return False

def create_directories():
    """Create necessary directories"""
    directories = ["uploads", "temp"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    print("✅ Created necessary directories")

def main():
    """Main setup function"""
    print("🎙️ Audio Scribe AI Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Failed to install dependencies")
        sys.exit(1)
    
    # Check FFmpeg
    ffmpeg_ok = check_ffmpeg()
    
    # Create directories
    create_directories()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed!")
    
    if ffmpeg_ok:
        print("\n✅ All dependencies are installed and ready")
        print("\nTo start the application:")
        print("python run.py")
    else:
        print("\n⚠️  Setup completed but FFmpeg is missing")
        print("Please install FFmpeg before running the application")
        print("\nAfter installing FFmpeg, start the application with:")
        print("python run.py")
    
    print("\nFor more information, see README.md")

if __name__ == "__main__":
    main()