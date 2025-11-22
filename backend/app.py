import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
import json
import logging
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import uvicorn

logger = logging.getLogger(__name__)

from services.audio_service import AudioService
from services.export_service import ExportService
from utils.config import get_settings

# Try to import real AI services, fall back to mock services
try:
    from services.unified_whisper_service import UnifiedWhisperService as WhisperService
    print("✅ Unified Whisper service loaded successfully")
    WHISPER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Whisper not available ({e}), using mock service")
    from services.mock_services import MockWhisperService as WhisperService
    WHISPER_AVAILABLE = False

try:
    from services.pyannote_service import PyannoteService
    print("✅ Pyannote service loaded successfully")
    PYANNOTE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Pyannote not available ({e}), using mock service")
    from services.mock_services import MockPyannoteService as PyannoteService
    PYANNOTE_AVAILABLE = False

USE_REAL_AI = WHISPER_AVAILABLE and PYANNOTE_AVAILABLE
if USE_REAL_AI:
    print("🎉 Full AI functionality available!")
else:
    print("🔧 Running with limited functionality (some services mocked)")

# Initialize FastAPI app
app = FastAPI(title="Audio Scribe AI", version="1.0.0")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend")

# Initialize services
settings = get_settings()
whisper_service = WhisperService()
pyannote_service = PyannoteService()
audio_service = AudioService()
export_service = ExportService()

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main application page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/upload")
async def upload_audio(file: UploadFile = File(...)):
    """Handle audio file upload"""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix if file.filename else '.wav'
        temp_filename = f"{file_id}{file_extension}"
        temp_path = UPLOAD_DIR / temp_filename
        
        # Save uploaded file
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return JSONResponse({
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "size": len(content),
            "message": "File uploaded successfully"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/transcribe/{file_id}")
async def transcribe_audio(file_id: str):
    """Transcribe and diarize audio file"""
    try:
        # Find the uploaded file
        audio_file = None
        for file_path in UPLOAD_DIR.glob(f"{file_id}.*"):
            audio_file = file_path
            break
        
        if not audio_file or not audio_file.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Convert audio to WAV format if needed
        wav_path = audio_service.convert_to_wav(audio_file)
        
        # Perform transcription with Whisper
        transcription_result = whisper_service.transcribe(wav_path)
        
        # Perform speaker diarization with Pyannote
        try:
            diarization_result = pyannote_service.diarize(wav_path)
            logger.info("Diarization completed successfully")
        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            # Fallback to single speaker if diarization fails
            diarization_result = {
                "num_speakers": 1,
                "speakers": {"SPEAKER_00": "Speaker 1"},
                "segments": [{
                    "start": 0.0,
                    "end": transcription_result.get("duration", 0),
                    "speaker": "SPEAKER_00",
                    "speaker_label": "Speaker 1",
                    "speaker_id": 1,
                    "duration": transcription_result.get("duration", 0)
                }],
                "duration": transcription_result.get("duration", 0)
            }
        
        # Merge transcription and diarization results
        try:
            merged_result = audio_service.merge_transcription_diarization(
                transcription_result, diarization_result
            )
            logger.info("Results merged successfully")
        except Exception as e:
            logger.error(f"Merging failed: {e}")
            # Fallback to transcription only
            merged_result = audio_service._assign_single_speaker(transcription_result)
        
        # Clean up temporary files
        if wav_path != audio_file:
            wav_path.unlink(missing_ok=True)
        audio_file.unlink(missing_ok=True)
        
        return JSONResponse({
            "success": True,
            "result": merged_result,
            "message": "Transcription completed successfully"
        })
        
    except Exception as e:
        # Clean up files on error
        for file_path in UPLOAD_DIR.glob(f"{file_id}.*"):
            file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

from fastapi.responses import StreamingResponse
import asyncio
import json

@app.get("/api/transcribe-stream/{file_id}")
async def transcribe_audio_stream(file_id: str, transcription_only: bool = False, revision: str = None):
    """Transcribe and diarize audio file with streaming progress updates"""
    logger.info(f"Starting streaming transcription for file_id: {file_id}, transcription_only: {transcription_only}, revision: {revision}")

    # Update revision setting if provided
    if revision:
        if hasattr(whisper_service, 'set_revision'):
            whisper_service.set_revision(revision)
        else:
            settings.whisper_revision = revision
            logger.info(f"Revision setting updated to: {revision}")
    
    async def generate_progress():
        try:
            logger.info(f"EventSource connection established for file_id: {file_id}")
            # Find the uploaded file
            audio_file = None
            for file_path in UPLOAD_DIR.glob(f"{file_id}.*"):
                audio_file = file_path
                break
            
            if not audio_file or not audio_file.exists():
                yield f"data: {json.dumps({'error': 'Audio file not found'})}\n\n"
                return
            
            # Send initial status
            yield f"data: {json.dumps({'status': 'starting', 'message': 'Preparing audio file...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Convert audio to WAV format if needed
            wav_path = audio_service.convert_to_wav(audio_file)
            
            # Get audio duration for progress calculation
            import torchaudio
            try:
                waveform, sample_rate = torchaudio.load(str(wav_path))
                duration = waveform.shape[1] / sample_rate
                chunk_duration = 30  # 30 second chunks
                total_chunks = max(1, int(duration / chunk_duration) + (1 if duration % chunk_duration > 0 else 0))
            except:
                duration = 0
                total_chunks = 1
            
            yield f"data: {json.dumps({'status': 'transcribing', 'message': f'Starting transcription of {duration:.1f}s audio in {total_chunks} chunks...', 'total_chunks': total_chunks, 'duration': duration})}\n\n"
            await asyncio.sleep(0.1)
            
            # Perform transcription with progress updates using the unified whisper service
            transcription_result = None
            
            # Use the unified whisper service's streaming method
            if hasattr(whisper_service, 'transcribe_with_progress'):
                logger.info("Using unified whisper service streaming transcription")
                async for progress_data in whisper_service.transcribe_with_progress(wav_path):
                    yield f"data: {json.dumps(progress_data)}\n\n"
                    await asyncio.sleep(0.01)
                    if progress_data.get('status') == 'transcription_complete' and 'result' in progress_data:
                        transcription_result = progress_data['result']
            else:
                # Fallback to regular transcription with simulated progress
                logger.info("Using fallback transcription with simulated progress")
                for chunk_idx in range(total_chunks):
                    chunk_start = chunk_idx * chunk_duration
                    chunk_end = min((chunk_idx + 1) * chunk_duration, duration)
                    
                    yield f"data: {json.dumps({'status': 'processing_chunk', 'chunk_index': chunk_idx, 'chunk_start': chunk_start, 'chunk_end': chunk_end, 'total_chunks': total_chunks, 'message': f'Processing chunk {chunk_idx + 1}/{total_chunks} ({chunk_start:.1f}s - {chunk_end:.1f}s)'})}\n\n"
                    await asyncio.sleep(0.5)  # Simulate processing time
                
                # Perform actual transcription
                yield f"data: {json.dumps({'status': 'finalizing_transcription', 'message': 'Finalizing transcription...'})}\n\n"
                transcription_result = whisper_service.transcribe(wav_path)

            # Conditionally perform diarization based on transcription_only flag
            if transcription_only:
                # Skip diarization and assign single speaker
                logger.info("Transcription-only mode: Skipping diarization")
                yield f"data: {json.dumps({'status': 'merging', 'message': 'Formatting transcription results...'})}\n\n"
                await asyncio.sleep(0.1)
                merged_result = audio_service.format_transcription_only(transcription_result)
            else:
                # Perform speaker diarization
                yield f"data: {json.dumps({'status': 'diarizing', 'message': 'Analyzing speakers...'})}\n\n"
                await asyncio.sleep(0.1)

                try:
                    diarization_result = pyannote_service.diarize(wav_path)
                    logger.info("Diarization completed successfully")
                except Exception as e:
                    logger.error(f"Diarization failed: {e}")
                    # Fallback to single speaker if diarization fails
                    diarization_result = {
                        "num_speakers": 1,
                        "speakers": {"SPEAKER_00": "Speaker 1"},
                        "segments": [{
                            "start": 0.0,
                            "end": transcription_result.get("duration", 0),
                            "speaker": "SPEAKER_00",
                            "speaker_label": "Speaker 1",
                            "speaker_id": 1,
                            "duration": transcription_result.get("duration", 0)
                        }],
                        "duration": transcription_result.get("duration", 0)
                    }

                yield f"data: {json.dumps({'status': 'merging', 'message': 'Merging transcription and speaker data...'})}\n\n"
                await asyncio.sleep(0.1)

                # Merge transcription and diarization results
                try:
                    merged_result = audio_service.merge_transcription_diarization(
                        transcription_result, diarization_result
                    )
                    logger.info("Results merged successfully")
                except Exception as e:
                    logger.error(f"Merging failed: {e}")
                    # Fallback to transcription only
                    merged_result = audio_service.format_transcription_only(transcription_result)
            
            # Send final result
            yield f"data: {json.dumps({'status': 'completed', 'result': merged_result, 'message': 'Transcription completed successfully'})}\n\n"
            
            # Clean up temporary files
            if wav_path != audio_file:
                wav_path.unlink(missing_ok=True)
            audio_file.unlink(missing_ok=True)
            
        except Exception as e:
            logger.error(f"Streaming transcription failed: {e}")
            yield f"data: {json.dumps({'status': 'error', 'error': str(e), 'message': f'Transcription failed: {str(e)}'})}\n\n"
            # Clean up files on error
            for file_path in UPLOAD_DIR.glob(f"{file_id}.*"):
                file_path.unlink(missing_ok=True)
    
    return StreamingResponse(
        generate_progress(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.post("/api/save-recording")
async def save_recording(request: Request):
    """Save recorded audio from browser"""
    try:
        # Get the audio data from request
        form_data = await request.form()
        audio_file = form_data.get("audio")
        
        if not audio_file:
            raise HTTPException(status_code=400, detail="No audio data received")
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        temp_filename = f"{file_id}.webm"
        temp_path = UPLOAD_DIR / temp_filename
        
        # Save recorded audio
        with open(temp_path, "wb") as buffer:
            content = await audio_file.read()
            buffer.write(content)
        
        return JSONResponse({
            "success": True,
            "file_id": file_id,
            "size": len(content),
            "message": "Recording saved successfully"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recording save failed: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "services": {
        "whisper": whisper_service.is_available(),
        "pyannote": pyannote_service.is_available()
    }}

@app.get("/api/whisper/status")
async def get_whisper_status():
    """Get detailed status of Whisper services"""
    try:
        if hasattr(whisper_service, 'get_service_status'):
            status = whisper_service.get_service_status()
        else:
            # Fallback for mock service
            status = {
                "current_service": "mock",
                "local_available": False,
                "openai_available": False,
                "local_model_info": None,
                "openai_model_info": None
            }
        
        return JSONResponse({
            "success": True,
            "status": status
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Whisper status: {str(e)}")

@app.post("/api/whisper/switch-to-local")
async def switch_to_local_whisper():
    """Switch to local Whisper service"""
    try:
        if hasattr(whisper_service, 'switch_to_local'):
            success = whisper_service.switch_to_local()
            if success:
                return JSONResponse({
                    "success": True,
                    "message": "Switched to local Whisper service"
                })
            else:
                raise HTTPException(status_code=400, detail="Failed to switch to local Whisper service")
        else:
            raise HTTPException(status_code=400, detail="Local Whisper switching not supported")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to switch to local Whisper: {str(e)}")

@app.post("/api/whisper/switch-to-openai")
async def switch_to_openai_whisper():
    """Switch to OpenAI Whisper service"""
    try:
        if hasattr(whisper_service, 'switch_to_openai'):
            success = whisper_service.switch_to_openai()
            if success:
                return JSONResponse({
                    "success": True,
                    "message": "Switched to OpenAI Whisper service"
                })
            else:
                raise HTTPException(status_code=400, detail="Failed to switch to OpenAI Whisper service")
        else:
            raise HTTPException(status_code=400, detail="OpenAI Whisper switching not supported")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to switch to OpenAI Whisper: {str(e)}")

@app.post("/api/whisper/download-model")
async def download_local_model(request: Request):
    """Download a local Whisper model"""
    try:
        data = await request.json()
        model_name = data.get("model_name")

        if hasattr(whisper_service, 'download_local_model'):
            success = whisper_service.download_local_model(model_name)
            if success:
                return JSONResponse({
                    "success": True,
                    "message": f"Model {model_name or 'default'} downloaded successfully"
                })
            else:
                raise HTTPException(status_code=400, detail="Failed to download model")
        else:
            raise HTTPException(status_code=400, detail="Model downloading not supported")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download model: {str(e)}")

@app.post("/api/export/word")
async def export_to_word(request: Request):
    """Export transcription results to Word document"""
    try:
        data = await request.json()
        transcription_data = data.get("transcription_data")
        template_name = data.get("template_name")  # Optional

        if not transcription_data:
            raise HTTPException(status_code=400, detail="No transcription data provided")

        # Get template path if specified
        template_path = None
        if template_name:
            template_path = export_service.templates_dir / template_name
            if not template_path.exists():
                logger.warning(f"Template not found: {template_name}, using default format")
                template_path = None

        # Create temporary output path
        output_dir = Path("exports")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"transcription_{timestamp}.docx"
        output_path = output_dir / output_filename

        # Generate Word document
        result_path = export_service.export_to_word(
            transcription_data=transcription_data,
            template_path=template_path,
            output_path=output_path
        )

        # Return the file as a download
        return FileResponse(
            path=str(result_path),
            filename=output_filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename={output_filename}"
            }
        )

    except Exception as e:
        logger.error(f"Word export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.post("/api/export/txt")
async def export_to_txt(request: Request):
    """Export transcription results to plain text file"""
    try:
        data = await request.json()
        transcription_data = data.get("transcription_data")
        include_speakers = data.get("include_speakers", True)  # Default to True

        if not transcription_data:
            raise HTTPException(status_code=400, detail="No transcription data provided")

        # Create temporary output path
        output_dir = Path("exports")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"transcription_{timestamp}.txt"
        output_path = output_dir / output_filename

        # Generate text file
        result_path = export_service.export_to_txt(
            transcription_data=transcription_data,
            include_speakers=include_speakers,
            output_path=output_path
        )

        # Return the file as a download
        return FileResponse(
            path=str(result_path),
            filename=output_filename,
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename={output_filename}"
            }
        )

    except Exception as e:
        logger.error(f"TXT export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/api/export/templates")
async def get_available_templates():
    """Get list of available Word templates"""
    try:
        templates = export_service.get_available_templates()
        template_names = [t.name for t in templates]

        return JSONResponse({
            "success": True,
            "templates": template_names
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
