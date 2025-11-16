# KB-Whisper Pyannote Transcription Application - Architecture Overview

This document provides a comprehensive overview of the project architecture, focusing on transcript display and editing capabilities.

## Quick Summary

**Project Type:** Web application for audio transcription with speaker diarization
**Tech Stack:** FastAPI (Python) backend + Vanilla JavaScript frontend
**Key Features:** Audio recording/upload, AI transcription, speaker identification, real-time display, export to Word/TXT/JSON

---

## 1. PROJECT STRUCTURE & TECHNOLOGY STACK

### Directory Layout
```
kb-whisper-pyannote-transcription-diarization/
├── backend/
│   ├── app.py                           # Main FastAPI application (535 lines)
│   ├── services/
│   │   ├── audio_service.py             # Audio processing and merging (257 lines)
│   │   ├── export_service.py            # Word/TXT export (370+ lines)
│   │   ├── pyannote_service.py          # Speaker diarization (245 lines)
│   │   ├── unified_whisper_service.py   # Whisper abstraction (130+ lines)
│   │   ├── local_whisper_service.py     # Local model support
│   │   ├── vllm_whisper_service.py      # vLLM integration
│   │   └── whisper_service.py           # OpenAI API support
│   ├── utils/config.py                  # Configuration management (94 lines)
│   └── templates/                       # Word export templates
├── frontend/
│   ├── index.html                       # Main HTML (208 lines)
│   └── static/
│       ├── css/style.css                # Professional dark mode (900+ lines)
│       └── js/
│           ├── app.js                   # Main application logic (905+ lines)
│           ├── karaoke-player.js        # Playback with sync (469 lines)
│           ├── recorder.js              # Audio recording
│           └── toast.js                 # Notifications
├── requirements.txt                     # Python dependencies
└── run.py                               # Entry point
```

### Technology Stack

**Backend:**
- FastAPI 0.104.1 + Uvicorn ASGI server
- OpenAI Whisper (local KB-whisper-large model, vLLM, or OpenAI API)
- Pyannote.audio 3.1.1 for speaker diarization
- PyTorch 2.0+ with CUDA support
- FFmpeg for audio conversion
- python-docx for Word document generation

**Frontend:**
- Vanilla JavaScript (no frameworks)
- HTML5 + CSS3 with CSS custom properties
- Web Audio API + MediaRecorder for recording
- Server-Sent Events (SSE) for real-time progress

---

## 2. HOW TRANSCRIPTS ARE STORED & DISPLAYED

### Data Flow Diagram

```
Audio Upload/Recording
    ↓
Convert to WAV (16kHz mono)
    ↓
┌─ Whisper Transcription (returns text + timestamps)
├─ Pyannote Diarization (returns speaker segments)
    ↓
Merge by time overlap (assign speakers to text)
    ↓
Group consecutive same-speaker segments
    ↓
Send to Frontend as JSON
    ↓
Display in DOM + Store in JavaScript memory
```

### Transcript Data Structure

**Final Segment Format (sent to frontend):**
```javascript
{
    start: 0.42,              // Start time in seconds
    end: 3.87,                // End time in seconds
    text: "Transcribed text",
    speaker: "Speaker 1",     // Display name
    duration: 3.45            // Duration in seconds
}
```

**Complete Result Object:**
```javascript
{
    segments: [{start, end, text, speaker, duration}, ...],
    speakers: {
        "Speaker 1": "Speaker 1",
        "Speaker 2": "Speaker 2"
    },
    num_speakers: 2,
    language: "sv",
    duration: 120.5,
    full_text: "Complete transcription..."
}
```

### Frontend Display Architecture

**Transcription Display Component:**
- HTML Container: `#transcriptionDisplay` (scrollable, 500px max height)
- Each segment rendered as: `.transcription-segment.speaker-N`
- Contains: speaker name, timestamp, and text
- Color-coded with 6 speaker colors (CSS variables)

**Speaker Editor Component:**
- HTML Container: `#speakerEditor`
- Grid layout with input fields per speaker
- Changes trigger immediate DOM update
- Data stored in `app.speakerNames` object

**Real-time Updates:**
- Speaker name changes: `updateTranscriptionDisplay()` updates DOM
- Karaoke player: Synchronized playback with highlighting

---

## 3. UI FRAMEWORK & DESIGN SYSTEM

### Framework Choice
- **No Framework:** Lightweight vanilla JS + HTML/CSS
- Benefits: Fast load time, no dependencies, full control
- Structure: Object-oriented JS class `AudioScribeApp`

### Professional Dark Mode Design System

**Color Palette:**
- Background: `#0a0e1a` (deep dark blue)
- Surface: `#1a1f2e` (elevated elements)
- Primary: Blue (`#3b82f6`)
- Semantic: Success (green), Warning (orange), Error (red)
- Accent: 6 speaker colors (blue, green, orange, pink, purple, cyan)

**Typography System:**
- Font stack: Inter, Roboto, system sans-serif
- Sizes: 0.75rem to 2.25rem (12px to 36px)
- Weights: 400 (normal), 500 (medium), 600 (semibold), 700 (bold)
- Monospace for timestamps

**Component Styling:**
- Consistent spacing scale (4px to 64px)
- Rounded corners: 4px to 9999px
- Shadows: xs to 2xl for elevation
- Transitions: 150ms to 300ms for smoothness
- Focus rings: 3px color with opacity

**Responsive Design:**
- Mobile breakpoint: 768px
- Flexible grids and layouts
- Touch-friendly button sizes
- Adaptive typography

---

## 4. DATA STRUCTURES FOR TRANSCRIPTS & SEGMENTS

### Whisper Transcription Output
```python
{
    "text": "Full transcription",
    "language": "sv",
    "duration": 120.5,
    "segments": [
        {
            "id": 0,
            "start": 0.0,
            "end": 3.0,
            "text": "Segment text",
            "seek": 0,
            "avg_logprob": -0.23,
            "compression_ratio": 1.23,
            "no_speech_prob": 0.001,
            "temperature": 0.0
        }
    ]
}
```

### Pyannote Diarization Output
```python
{
    "num_speakers": 2,
    "speakers": {
        "Speaker 1": "Speaker 1",
        "Speaker 2": "Speaker 2"
    },
    "segments": [
        {
            "start": 0.0,
            "end": 5.0,
            "speaker": "Speaker 1",
            "speaker_label": "Speaker 1",
            "speaker_id": 1,
            "duration": 5.0
        }
    ],
    "duration": 120.5
}
```

### Merged & Formatted Result
```python
{
    "segments": [
        {
            "start": 0.42,
            "end": 3.87,
            "text": "Transcribed text",
            "speaker": "Speaker 1",
            "duration": 3.45
        }
    ],
    "speakers": {"Speaker 1": "Speaker 1", "Speaker 2": "Speaker 2"},
    "num_speakers": 2,
    "language": "sv",
    "duration": 120.5,
    "full_text": "Complete text..."
}
```

### Frontend Speaker Mapping
```javascript
// Stored in app.speakerNames
{
    "Speaker 1": "John Doe",    // Original name: Custom name
    "Speaker 2": "Jane Smith"
}
```

---

## 5. SPEAKER DIARIZATION IMPLEMENTATION

### Pyannote Service Architecture

**File:** `/backend/services/pyannote_service.py` (245 lines)

**Dual Mode Support:**
1. **Local:** Loads pipeline directly on server
   - Model: `pyannote/speaker-diarization-3.1` (default)
   - Device: CUDA/GPU, CPU, or Apple MPS
   - Auth: HuggingFace token via environment

2. **Remote:** Communicates with separate Pyannote server
   - HTTP endpoint at `PYANNOTE_REMOTE_URL`
   - Health check monitoring
   - Timeout: 5 minutes for large files

**API Compatibility:**
- Old API (< 3.0): Uses `.itertracks(yield_label=True)`
- New API (3.0+): Uses `.segments` attribute
- Graceful fallback for unknown formats

**Output Processing:**
- Sorts segments by start time
- Creates speaker mapping: `SPEAKER_00` → `"Speaker 1"`
- Assigns numeric speaker IDs
- Calculates segment durations

### Whisper Transcription Hierarchy

**File:** `/backend/services/unified_whisper_service.py`

Priority order:
1. **vLLM** (if enabled): High-performance inference server
2. **Local Whisper** (if enabled): Privacy-focused local models
3. **OpenAI API** (default): Cloud-based fallback

**Features:**
- Auto-chunking: 30-second segments for long audio
- Progress updates: Streaming status via SSE
- Model flexibility: Supports tiny to large models
- GPU acceleration: CUDA support built-in

### Merge Algorithm

**File:** `/backend/services/audio_service.py::merge_transcription_diarization()`

Steps:
1. For each transcription segment:
   - Find diarization segment with maximum time overlap
   - Assign speaker based on overlap percentage
2. Group consecutive segments from same speaker
3. Merge if gap ≤ 1 second
4. Combine texts with space

```python
# Grouping logic
if (segment["speaker"] == current_group["speaker"] and 
    segment["start"] - current_group["end"] <= 1.0):
    current_group["text"] += " " + segment["text"]
    current_group["end"] = segment["end"]
else:
    # Start new group
```

---

## 6. FILE UPLOAD & PROCESSING FLOW

### Upload Phase

**POST /api/upload** (file upload)
```
Input: FormData with audio file
Processing:
  1. Validate content-type (must start with "audio/")
  2. Generate UUID for file_id
  3. Save to uploads/{file_id}.{extension}
Output: {success, file_id, filename, size}
```

**POST /api/save-recording** (browser recording)
```
Input: FormData with WebM blob
Processing:
  1. Extract audio from form
  2. Generate UUID for file_id
  3. Save to uploads/{file_id}.webm
Output: {success, file_id, size}
```

### Processing Phase

**GET /api/transcribe-stream/{file_id}?transcription_only=true**

Protocol: Server-Sent Events (SSE) for real-time updates

Sequence:
```
1. "starting" status
   → Convert audio to WAV (16kHz mono)
   → Load with torchaudio to get duration
   
2. "transcribing" status
   → Process in 30-second chunks
   → Send progress: chunk_index, total_chunks
   → Collect transcript segments
   
3. "diarizing" status (if transcription_only=false)
   → Run Pyannote on full audio
   → Collect speaker segments
   
4. "merging" status
   → Combine transcription + diarization
   → Assign speakers to text segments
   
5. "completed" status
   → Send final merged result as JSON
   → Clean up temporary files
```

**Progress Message Example:**
```javascript
{
    status: "processing_chunk",
    chunk_index: 0,
    chunk_start: 0.0,
    chunk_end: 30.0,
    total_chunks: 3,
    message: "Processing chunk 1/3..."
}
```

### Transcription Services

**Local Whisper:**
- Loads model from HuggingFace or local path
- 30-second chunk processing for long audio
- Supports: tiny, base, small, medium, large models
- GPU acceleration with CUDA

**vLLM:**
- Connects to external vLLM server
- Auto-chunks files > 25MB
- Compatible with OpenAI API format
- Distributed processing capability

**OpenAI API:**
- Cloud-based Whisper models
- No local resources needed
- Configurable via OPENAI_API_KEY

### Cleanup & Export

**File Management:**
- Temporary files: `uploads/` directory
- Export files: `exports/` directory with timestamp
- Auto-cleanup after processing success
- Error cleanup: Removes all {file_id}.* files

**Export Formats:**

1. **Word (.docx):** `POST /api/export/word`
   - Includes metadata (date, duration, speakers, language)
   - Speaker names and timestamps per segment
   - Optional template support
   - Transcription-only mode: removes speaker info

2. **Plain Text (.txt):** `POST /api/export/txt`
   - Toggle: include speaker names
   - Simple line-by-line format
   - No timestamps in transcription-only mode

3. **JSON:** Client-side generation
   - Full data structure with all metadata
   - Updated speaker names included
   - Browser download triggered

---

## 7. CURRENT UI STATE & FEATURES

### Recording & Upload
- **Record Button:** Start/stop browser recording (WebM)
- **Drag & Drop:** Audio file upload area
- **File Support:** MP3, WAV, M4A, FLAC, OGG, WebM

### Processing Options
- **Transcription-Only Toggle:** Skip diarization for speed
- **Real-time Progress:** Chunk visualization with status

### Results Display

**Speaker Editor:**
- Grid of input fields (one per speaker)
- Real-time name editing
- Immediate transcription update

**Transcription Display:**
- Scrollable list of segments
- Color-coded by speaker (6 colors)
- Speaker name, timestamp, and text per segment
- Hover highlighting

**Karaoke Player:**
- Play/pause, seek, volume controls
- Speaker lanes visualization
- Current speaker and text display
- Synchronized highlighting during playback
- Keyboard shortcuts (spacebar to play/pause)

### Export Options
- **Export to Word:** Formatted .docx with metadata
- **Export to TXT:** Plain text with optional speaker names
- **Export JSON:** Full data structure download
- **Clear:** Reset and start over

---

## 8. KEY FILES FOR TRANSCRIPT DISPLAY & EDITING

### Backend

**Main Application:** `/backend/app.py`
- Routes: upload, transcribe (streaming), export
- Service initialization and error handling
- SSE streaming implementation

**Audio Service:** `/backend/services/audio_service.py`
- Audio format conversion to WAV
- Transcription + Diarization merging
- Segment grouping logic
- Empty result fallbacks

**Export Service:** `/backend/services/export_service.py`
- Word document generation (python-docx)
- Plain text export with formatting
- Template support for custom layouts

**Pyannote Service:** `/backend/services/pyannote_service.py`
- Local and remote diarization
- Pipeline initialization and caching
- Speaker mapping and labeling

**Configuration:** `/backend/utils/config.py`
- Environment variable loading
- Device detection (CUDA/MPS/CPU)
- Settings singleton pattern

### Frontend

**Main App Logic:** `/frontend/static/js/app.js` (905+ lines)
- `AudioScribeApp` class with lifecycle methods
- Key functions:
  - `displayResults()`: Show transcription results
  - `createSpeakerEditor()`: Generate speaker inputs
  - `displayTranscription()`: Render segments to DOM
  - `updateTranscriptionDisplay()`: Update on speaker name change
  - `transcribeWithStreaming()`: Handle SSE connection
  - `exportToWord()`, `exportToTxt()`, `exportToJSON()`

**Karaoke Player:** `/frontend/static/js/karaoke-player.js` (469 lines)
- `KaraokePlayer` class for synchronized playback
- Speaker lanes visualization
- Time-based segment highlighting
- Playback controls

**Audio Recording:** `/frontend/static/js/recorder.js`
- `AudioRecorder` class for browser recording
- MediaRecorder API wrapper
- WebM blob generation

**Notifications:** `/frontend/static/js/toast.js`
- Toast notification system
- Success, warning, error, info types

**HTML Structure:** `/frontend/index.html` (208 lines)
- Recording section with duration display
- File upload drag-and-drop area
- Processing status with progress visualization
- Speaker editor section
- Transcription display container
- Karaoke player UI
- Export options

**Styling:** `/frontend/static/css/style.css` (900+ lines)
- CSS custom properties for design system
- Component styles (.transcription-segment, .speaker-editor, etc.)
- Speaker color classes (.speaker-1 through .speaker-6)
- Responsive design with media queries
- Professional dark mode with shadows and transitions

---

## 9. IMPORTANT ARCHITECTURAL NOTES

### State Management
- **Frontend:** In-memory JavaScript
  - `app.currentResults`: Holds transcription data
  - `app.speakerNames`: Maps speaker IDs to display names
  - `app.currentAudioFile`: Blob/File for karaoke player
  
- **Backend:** Session-based file storage
  - `uploads/` directory: Temporary audio files
  - `exports/` directory: Generated download files
  - No persistent database

### Limitations & Design Decisions

**No Features:**
- Persistent transcript storage
- Undo/redo for transcript edits
- Real-time collaboration
- User authentication
- Segment-level editing (only speaker renaming)
- Timestamp adjustment
- Text correction UI

**Choices Made:**
- Vanilla JS instead of framework (simplicity, performance)
- SSE instead of WebSocket (simpler, stateless)
- 30-second chunks for transcription (balance speed/accuracy)
- Client-side speaker name storage (stateless backend)
- 1-second merge gap for segment grouping (UX preference)

### Performance Characteristics
- **Transcription:** 30-second chunks, parallel with other files
- **Diarization:** Full audio processing (one shot)
- **Merging:** O(n*m) where n=transcription segments, m=diarization segments
- **Display:** DOM-based, scrollable container max 500px
- **Export:** Synchronous, generates on-the-fly

### Extensibility Points

1. **New Whisper backends:** Implement `transcribe()` method
2. **New diarization services:** Implement `diarize()` method
3. **Custom Word templates:** Place .docx in `templates/word/`
4. **Additional export formats:** Add to `ExportService`
5. **CSS customization:** Modify CSS variables in `:root`
6. **UI components:** Add new sections to HTML and app.js

---

## Summary

This application provides a complete pipeline for:
1. Recording or uploading audio
2. Transcribing with Whisper (3 backend options)
3. Identifying speakers with Pyannote
4. Merging results intelligently
5. Editing speaker names in real-time
6. Exporting to multiple formats
7. Viewing with synchronized karaoke-style playback

The architecture is clean and modular, making it easy to extend with transcript editing features like segment splitting, text correction, speaker reassignment, and more.
