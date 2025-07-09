# Audio Scribe AI (KB-whisper + Pyannote)

A web application for audio transcription and speaker diarization using OpenAI Whisper variant KB-whisper (Swedish) and Pyannote.audio. Upload audio files or record directly in the browser to get timestamped transcriptions with speaker identification.
KB-Whisper info: https://huggingface.co/KBLab/kb-whisper-large
Everything it run locally.

Edit local_whisper_service.py to change model from kw-whisper-large (default)


## Features

- 🎙️ **Browser Recording**: Record audio directly in your browser
- 📁 **File Upload**: Support for multiple audio formats (MP3, WAV, M4A, FLAC, OGG, WebM)
- 🤖 **AI Transcription**: Powered by OpenAI Whisper and local Whisper models for accurate speech-to-text
- 🏠 **Local Processing**: Option to use local Whisper models for privacy and offline processing
- 👥 **Speaker Diarization**: Automatic speaker identification using Pyannote.audio
- ✏️ **Editable Speaker Names**: Rename speakers from "Speaker 1, 2, 3..." to actual names
- ⏱️ **Timestamped Results**: Precise start/end times for each speaker segment
- 📤 **Export Options**: Download results as JSON
- 🎨 **Modern UI**: Clean, responsive interface with dark theme
- ⚡ **GPU Acceleration**: Automatic CUDA support for faster processing

## Screenshots

The application provides an intuitive interface matching the design shown in the project requirements, featuring:
- Recording controls with real-time duration display
- Drag-and-drop file upload area
- Speaker name editor with color-coded segments
- Scrollable transcription display with timestamps

<p float="left">
  <img src="screenshots/screenshot-1.png" width="45%" />
  <br>
  <img src="screenshots/screenshot-2.png" width="45%" />
</p>


## Installation

### Prerequisites

- Python 3.8 or higher
- CUDA-capable GPU (optional, but recommended for faster processing)
- FFmpeg installed on your system

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd transcribe2
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg**
   
   **Windows:**
   - Download from https://ffmpeg.org/download.html
   - Add to PATH environment variable
   
   **macOS:**
   ```bash
   brew install ffmpeg
   ```
   
   **Linux:**
   ```bash
   sudo apt update
   sudo apt install ffmpeg
   ```

4. **Set up Pyannote.audio (optional)**
   
   For some Pyannote models, you may need to accept the user agreement and set up authentication:
   ```bash
   # Visit https://huggingface.co/pyannote/speaker-diarization-3.1
   # Accept the user agreement, then set your token:
   export HUGGINGFACE_TOKEN="your_token_here"
   ```

## Usage

### Starting the Application

1. **Start the FastAPI server**
   ```bash
   cd backend
   python app.py
   ```
   
   The server will start on `http://localhost:8000`

2. **Open your browser**
   
   Navigate to `http://localhost:8000` to access the application

### Using the Application

1. **Record Audio**
   - Click "Start Recording" to begin recording
   - Click "Stop Recording" when finished
   - The app will automatically process the recording

2. **Upload Audio File**
   - Drag and drop an audio file onto the upload area
   - Or click the upload area to browse for files
   - Supported formats: MP3, WAV, M4A, FLAC, OGG, WebM

3. **View Results**
   - Wait for processing to complete
   - Edit speaker names in the "Edit Speaker Names" section
   - View timestamped transcription with color-coded speakers
   - Export results as JSON using the Export button

## Configuration

### Environment Variables

You can customize the application behavior using environment variables:

```bash
# Whisper model size (tiny, base, small, medium, large)
export WHISPER_MODEL="base"

# Language for transcription (auto for auto-detection)
export WHISPER_LANGUAGE="auto"

# Pyannote model
export PYANNOTE_MODEL="pyannote/speaker-diarization-3.1"

# Speaker limits
export MIN_SPEAKERS="1"
export MAX_SPEAKERS="10"

# File size limit (bytes)
export MAX_FILE_SIZE="104857600"  # 100MB
```

### Local Whisper Configuration

For privacy and offline processing, you can use local Whisper models:

```bash
# Enable local Whisper
export WHISPER_USE_LOCAL=true

# Choose local model (Hugging Face format)
export WHISPER_LOCAL_MODEL_NAME="openai/whisper-base"

# Optional: path to local model files
export WHISPER_LOCAL_MODEL_PATH="/path/to/local/model"
```

**Available Local Models:**
- `openai/whisper-tiny`: 39MB, fastest processing
- `openai/whisper-base`: 74MB, good balance
- `openai/whisper-small`: 244MB, better accuracy
- `openai/whisper-medium`: 769MB, high accuracy
- `openai/whisper-large-v2`: 1.5GB, best accuracy
- `openai/whisper-large-v3`: 1.5GB, latest version

For detailed setup instructions, see [LOCAL_WHISPER_SETUP.md](LOCAL_WHISPER_SETUP.md).

### Model Selection

**Whisper Models:**
- `tiny`: Fastest, least accurate (~39 MB)
- `base`: Good balance of speed and accuracy (~74 MB)
- `small`: Better accuracy (~244 MB)
- `medium`: High accuracy (~769 MB)
- `large`: Best accuracy (~1550 MB)

**GPU Requirements:**
- Recommended: 4GB+ VRAM for base model
- Required: 8GB+ VRAM for large model

## API Endpoints

The application provides a REST API:

- `GET /` - Main application interface
- `POST /api/upload` - Upload audio file
- `POST /api/save-recording` - Save browser recording
- `POST /api/transcribe/{file_id}` - Transcribe and diarize audio
- `GET /api/health` - Health check

### Local Whisper Management

- `GET /api/whisper/status` - Get detailed Whisper service status
- `POST /api/whisper/switch-to-local` - Switch to local Whisper service
- `POST /api/whisper/switch-to-openai` - Switch to OpenAI Whisper service
- `POST /api/whisper/download-model` - Download a local Whisper model

## Project Structure

```
transcribe2/
├── backend/
│   ├── app.py                 # FastAPI main application
│   ├── services/
│   │   ├── whisper_service.py # Whisper integration
│   │   ├── pyannote_service.py# Pyannote integration
│   │   └── audio_service.py   # Audio processing
│   └── utils/
│       └── config.py          # Configuration settings
├── frontend/
│   ├── index.html            # Main application page
│   └── static/
│       ├── css/style.css     # Styling
│       └── js/
│           ├── app.js        # Main application logic
│           └── recorder.js   # Audio recording
├── uploads/                  # Temporary file storage
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## Troubleshooting

### Common Issues

1. **"Recording not supported"**
   - Ensure you're using HTTPS or localhost
   - Check browser permissions for microphone access

2. **"Pyannote pipeline not available"**
   - Check if you need to accept the model's user agreement
   - Verify HUGGINGFACE_TOKEN if required

3. **Slow processing**
   - Consider using a smaller Whisper model
   - Ensure CUDA is properly installed for GPU acceleration

4. **FFmpeg errors**
   - Verify FFmpeg is installed and in PATH
   - Check audio file format compatibility

### Performance Tips

- Use GPU acceleration when available
- Choose appropriate Whisper model size for your hardware
- Limit audio file length for faster processing
- Use WAV format to skip conversion step

## Development

### Running in Development Mode

```bash
# Backend with auto-reload
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# The frontend is served by FastAPI
```

### Adding New Features

The application is designed to be easily extensible:
- Add new audio formats in `audio_service.py`
- Implement additional export formats
- Add real-time processing updates
- Integrate additional AI models

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
