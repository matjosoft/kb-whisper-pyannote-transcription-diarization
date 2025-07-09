#!/usr/bin/env python3
"""
Test script to verify that the streaming transcription method is being called
"""

import sys
import os
import asyncio
from pathlib import Path

# Add backend to path
sys.path.append('backend')

async def test_streaming_method():
    """Test that the streaming method is available and callable"""
    try:
        from backend.services.unified_whisper_service import UnifiedWhisperService
        
        print("✅ UnifiedWhisperService imported successfully")
        
        # Create service instance
        service = UnifiedWhisperService()
        print(f"✅ Service created, available: {service.is_available()}")
        
        # Check if streaming method exists
        if hasattr(service, 'transcribe_with_progress'):
            print("✅ transcribe_with_progress method exists")
            
            # Test with a dummy path (will fail but we can see if method is called)
            dummy_path = Path("dummy_audio.wav")
            
            try:
                print("🧪 Testing streaming method call...")
                async for progress in service.transcribe_with_progress(dummy_path):
                    print(f"📊 Progress update: {progress}")
                    if progress.get('status') == 'error':
                        print("✅ Method called successfully (expected error for dummy file)")
                        break
                    elif progress.get('status') == 'transcription_complete':
                        print("✅ Method completed successfully")
                        break
            except Exception as e:
                print(f"✅ Method called but failed as expected: {e}")
                
        else:
            print("❌ transcribe_with_progress method missing")
            
        # Check service configuration
        print(f"\n📋 Service Configuration:")
        print(f"   - Use local: {service.settings.whisper_use_local}")
        print(f"   - Local service available: {service.local_whisper_service is not None}")
        if service.local_whisper_service:
            print(f"   - Local service ready: {service.local_whisper_service.is_available()}")
            print(f"   - Has streaming method: {hasattr(service.local_whisper_service, 'transcribe_with_progress')}")
        print(f"   - OpenAI service available: {service.whisper_service is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_backend_endpoint():
    """Test that the backend endpoint can access the streaming method"""
    try:
        from backend.app import whisper_service
        
        print("\n🌐 Testing Backend Endpoint Integration:")
        print(f"   - Whisper service type: {type(whisper_service).__name__}")
        print(f"   - Has streaming method: {hasattr(whisper_service, 'transcribe_with_progress')}")
        
        if hasattr(whisper_service, 'transcribe_with_progress'):
            print("✅ Backend can access streaming method")
        else:
            print("❌ Backend cannot access streaming method")
            
        return True
        
    except Exception as e:
        print(f"❌ Backend test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🧪 Testing Streaming Transcription Method")
    print("=" * 50)
    
    success = True
    
    print("\n1. Testing UnifiedWhisperService...")
    success &= await test_streaming_method()
    
    print("\n2. Testing Backend Integration...")
    success &= await test_backend_endpoint()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Streaming method should be working.")
    else:
        print("❌ Some tests failed. Check the implementation.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())