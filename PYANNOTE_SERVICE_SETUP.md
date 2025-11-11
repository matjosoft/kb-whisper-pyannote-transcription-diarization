# Pyannote Remote Service Setup Guide

This guide explains how to set up and use the standalone Pyannote speaker diarization service on a separate machine.

## Overview

The Pyannote service can now run in two modes:

1. **Local Mode** (default): Runs pyannote directly in the main application
2. **Remote Mode**: Connects to a standalone pyannote service running on another machine (potentially with GPU)

## Why Use Remote Mode?

- **GPU Resources**: Run diarization on a powerful GPU machine while keeping the main app on a lighter server
- **Scalability**: Separate compute-intensive diarization from transcription
- **Flexibility**: Deploy services independently
- **Cost Optimization**: Use GPU resources only for diarization

## Quick Start

### 1. Start the Remote Pyannote Server

On the machine with GPU (or the machine you want to run diarization on):

```bash
# Set your HuggingFace token (required for pyannote models)
export HF_AUTH_TOKEN=your_huggingface_token_here

# Start the server
python pyannote_server.py --host 0.0.0.0 --port 8001
```

### 2. Configure the Main Application

On the main application machine, create or update `.env`:

```bash
# Enable remote pyannote service
PYANNOTE_USE_REMOTE=true
PYANNOTE_REMOTE_URL=http://your-gpu-server:8001
```

### 3. Start the Main Application

```bash
cd backend
python app.py
```

The application will now use the remote pyannote service for speaker diarization!

## Detailed Setup

### Prerequisites

#### For the Remote Pyannote Server

Install required dependencies:

```bash
pip install fastapi uvicorn pyannote.audio torch torchaudio
```

**Note**: For GPU support, install PyTorch with CUDA:

```bash
# For CUDA 11.8
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### HuggingFace Authentication

1. Create a HuggingFace account at https://huggingface.co
2. Accept the pyannote model license at https://huggingface.co/pyannote/speaker-diarization-3.1
3. Create an access token at https://huggingface.co/settings/tokens
4. Export the token:

```bash
export HF_AUTH_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx
```

### Server Configuration

The server can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `PYANNOTE_MODEL` | Model to use | `pyannote/speaker-diarization-3.1` |
| `HF_AUTH_TOKEN` | HuggingFace auth token | Required |
| `DEVICE` | Device (cuda/cpu/mps) | Auto-detected |
| `MIN_SPEAKERS` | Minimum speakers | 1 |
| `MAX_SPEAKERS` | Maximum speakers | 10 |

### Server Command Line Options

```bash
python pyannote_server.py --help

Options:
  --host HOST        Host to bind to (default: 0.0.0.0)
  --port PORT        Port to bind to (default: 8001)
  --device DEVICE    Device to use (cuda/cpu/mps, auto-detected)
  --reload           Enable auto-reload for development
```

### Example Configurations

#### Production Setup (GPU Server)

```bash
# On GPU server (192.168.1.100)
export HF_AUTH_TOKEN=hf_xxxxx
export PYANNOTE_MODEL=pyannote/speaker-diarization-3.1
python pyannote_server.py --host 0.0.0.0 --port 8001

# On main app server
# In .env file:
PYANNOTE_USE_REMOTE=true
PYANNOTE_REMOTE_URL=http://192.168.1.100:8001
```

#### Development Setup (Different Ports on Same Machine)

```bash
# Terminal 1: Start pyannote server
export HF_AUTH_TOKEN=hf_xxxxx
python pyannote_server.py --port 8001

# Terminal 2: Start main app
cd backend
# In .env:
PYANNOTE_USE_REMOTE=true
PYANNOTE_REMOTE_URL=http://localhost:8001
python app.py
```

#### Local Mode (No Remote Service)

```bash
# In .env file:
PYANNOTE_USE_REMOTE=false
# or just comment out/remove the PYANNOTE_USE_REMOTE line
```

## API Endpoints

The standalone pyannote server provides the following REST API endpoints:

### GET /

Returns service information and available endpoints.

```bash
curl http://localhost:8001/
```

### GET /health

Health check endpoint.

```bash
curl http://localhost:8001/health
```

Response:
```json
{
  "status": "healthy",
  "available": true,
  "message": "Service is running"
}
```

### GET /info

Get detailed server information.

```bash
curl http://localhost:8001/info
```

Response:
```json
{
  "available": true,
  "model_name": "pyannote/speaker-diarization-3.1",
  "device": "cuda",
  "min_speakers": 1,
  "max_speakers": 10,
  "cuda_available": true,
  "cuda_device": "NVIDIA GeForce RTX 3090"
}
```

### POST /diarize

Perform speaker diarization on an audio file.

```bash
curl -X POST http://localhost:8001/diarize \
  -F "file=@audio.wav"
```

Response:
```json
{
  "success": true,
  "filename": "audio.wav",
  "result": {
    "num_speakers": 2,
    "speakers": {
      "SPEAKER_00": "Speaker 1",
      "SPEAKER_01": "Speaker 2"
    },
    "segments": [
      {
        "start": 0.5,
        "end": 5.2,
        "speaker": "SPEAKER_00",
        "speaker_label": "Speaker 1",
        "speaker_id": 1,
        "duration": 4.7
      }
    ],
    "duration": 120.5
  }
}
```

## Testing the Setup

### 1. Test the Remote Server

```bash
# Check if server is running
curl http://your-server:8001/health

# Check server info
curl http://your-server:8001/info

# Test diarization (replace with your audio file)
curl -X POST http://your-server:8001/diarize \
  -F "file=@test_audio.wav"
```

### 2. Test from Main Application

```python
# In Python shell
from backend.services.pyannote_service import PyannoteService
from pathlib import Path

service = PyannoteService()
print(service.get_pipeline_info())

# Should show mode: "remote" if configured correctly
```

### 3. Integration Test

1. Start the remote server
2. Configure the main app to use remote mode
3. Upload an audio file through the web interface
4. Verify that diarization works correctly

## Troubleshooting

### Server Won't Start

**Issue**: `Pyannote pipeline not available`

**Solution**:
- Make sure you've accepted the model license at https://huggingface.co/pyannote/speaker-diarization-3.1
- Verify your HF_AUTH_TOKEN is correct
- Check that pyannote.audio is installed: `pip install pyannote.audio`

### Connection Refused

**Issue**: Main app can't connect to remote server

**Solution**:
- Verify server is running: `curl http://server:8001/health`
- Check firewall settings
- Ensure port 8001 is open
- Verify PYANNOTE_REMOTE_URL in .env is correct

### CUDA Out of Memory

**Issue**: Server crashes with CUDA OOM error

**Solution**:
- Use CPU mode: `python pyannote_server.py --device cpu`
- Or reduce batch size by processing smaller audio chunks
- Upgrade to a GPU with more memory

### Remote Diarization Fails

**Issue**: Diarization works locally but fails remotely

**Solution**:
- Check server logs for errors
- Verify audio file format is supported (WAV, MP3, etc.)
- Ensure network timeout is sufficient for large files (default: 5 minutes)
- Check server has enough disk space for temporary files

## Performance Considerations

### Network Transfer

- Audio files are uploaded to the remote server for processing
- For large files, network bandwidth may be a bottleneck
- Consider compressing audio or using lower sample rates when appropriate

### Timeout Settings

The default timeout for remote diarization is 5 minutes (300 seconds). For very large files, you may need to increase this:

```python
# In backend/services/pyannote_service.py
response = requests.post(
    f"{self.remote_url}/diarize",
    files=files,
    timeout=600  # Increase to 10 minutes
)
```

### Concurrent Requests

The pyannote server handles one request at a time by default. For production use with multiple concurrent users, consider:

- Running multiple pyannote server instances
- Using a load balancer
- Implementing a queue system

## Security Considerations

### Network Security

- **Production**: Use HTTPS/TLS for encrypted communication
- **Firewall**: Restrict access to the pyannote server port
- **Authentication**: Consider adding API key authentication for production

### Example with HTTPS and Authentication

For production deployments, consider:

1. Use nginx or traefik as a reverse proxy with SSL
2. Add authentication middleware to the FastAPI app
3. Use VPN or private network for internal communication

## Monitoring

### Health Checks

Set up regular health checks:

```bash
# Add to cron or monitoring system
*/5 * * * * curl -f http://localhost:8001/health || systemctl restart pyannote
```

### Logging

Server logs are output to stdout/stderr. For production:

```bash
# Redirect logs to file
python pyannote_server.py 2>&1 | tee -a /var/log/pyannote/server.log
```

### Metrics

Monitor these metrics for the pyannote server:

- Request rate and latency
- GPU memory usage
- Error rate
- Queue depth (if using async processing)

## Systemd Service (Linux)

For production deployment, run as a systemd service:

```ini
# /etc/systemd/system/pyannote.service
[Unit]
Description=Pyannote Diarization Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/project
Environment="HF_AUTH_TOKEN=your_token"
Environment="PYANNOTE_MODEL=pyannote/speaker-diarization-3.1"
ExecStart=/usr/bin/python3 pyannote_server.py --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable pyannote
sudo systemctl start pyannote
sudo systemctl status pyannote
```

## Docker Deployment

Example Dockerfile for the pyannote server:

```dockerfile
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3 python3-pip

WORKDIR /app

COPY pyannote_server.py .
RUN pip3 install fastapi uvicorn pyannote.audio torch torchaudio

ENV HF_AUTH_TOKEN=""
ENV PYANNOTE_MODEL="pyannote/speaker-diarization-3.1"

EXPOSE 8001

CMD ["python3", "pyannote_server.py", "--host", "0.0.0.0", "--port", "8001"]
```

Build and run:

```bash
docker build -t pyannote-server .
docker run -d \
  --gpus all \
  -p 8001:8001 \
  -e HF_AUTH_TOKEN=your_token \
  pyannote-server
```

## Summary

The standalone pyannote service provides flexibility in deployment:

- **Development**: Run locally for testing
- **Production**: Deploy on GPU server for performance
- **Hybrid**: Mix local and remote based on requirements

Choose the mode that best fits your infrastructure and requirements!
