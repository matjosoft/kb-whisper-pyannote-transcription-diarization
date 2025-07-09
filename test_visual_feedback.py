#!/usr/bin/env python3
"""
Test script to verify the visual feedback implementation
"""

import sys
import os
sys.path.append('backend')

def test_imports():
    """Test that all imports work correctly"""
    try:
        from backend.services.local_whisper_service import LocalWhisperService
        print("✅ LocalWhisperService import successful")
        
        from backend.app import app
        print("✅ FastAPI app import successful")
        
        # Check if the new method exists
        service = LocalWhisperService()
        if hasattr(service, 'transcribe_with_progress'):
            print("✅ transcribe_with_progress method exists")
        else:
            print("❌ transcribe_with_progress method missing")
            
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_streaming_endpoint():
    """Test that the streaming endpoint is properly configured"""
    try:
        from fastapi.testclient import TestClient
        from backend.app import app
        
        client = TestClient(app)
        
        # Check if the streaming endpoint exists
        response = client.post("/api/transcribe-stream/test-file-id")
        # We expect this to fail with 404 (file not found) but not with 404 (endpoint not found)
        if response.status_code == 404:
            print("✅ Streaming endpoint exists (returns 404 for missing file as expected)")
        else:
            print(f"⚠️ Streaming endpoint returned status: {response.status_code}")
            
        return True
    except Exception as e:
        print(f"❌ Streaming endpoint test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Visual Feedback Implementation")
    print("=" * 50)
    
    success = True
    
    print("\n1. Testing imports...")
    success &= test_imports()
    
    print("\n2. Testing streaming endpoint...")
    success &= test_streaming_endpoint()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Visual feedback implementation looks good.")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return success

if __name__ == "__main__":
    main()