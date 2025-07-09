# Local Whisper Setup Guide

This guide explains how to set up and use local Whisper models in the transcription service.

## Overview

The transcription service now supports both OpenAI Whisper (original) and local Whisper models using Hugging Face transformers. Local models provide:

- **Privacy**: Audio processing happens entirely on your machine
- **Offline capability**: No internet connection required for transcription
- **Cost savings**: No API costs for transcription
- **Customization**: Use fine-tuned or specialized models

## Prerequisites

### System Requirements

- **RAM**: Minimum 8GB, recommended 16GB+ for larger models
- **Storage**: 1-10GB depending on model size
- **GPU** (optional but recommended): NVIDIA GPU with CUDA support for faster processing

### Dependencies

The following packages are required and included in `requirements.txt`:

```
transformers>=4.35.0
torch>=2.0.0
torchaudio>=2.0.0
accelerate>=0.20.0
datasets>=2.14.0
```

## Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify installation**:
   ```bash
   python test_local_whisper.py
   ```

## Configuration

### Environment Variables

Set these environment variables to configure local Whisper:

```bash
# Enable local Whisper
export WHISPER_USE_LOCAL=true

# Model configuration
export WHISPER_LOCAL_MODEL_NAME="openai/whisper-base"
export WHISPER_LOCAL_MODEL_PATH=""  # Optional: path to local model files

# Language setting (optional)
export WHISPER_LANGUAGE="auto"  # or specific language code like "en", "es", etc.
```

### Available Models

You can use any Whisper model from Hugging Face Hub:

| Model | Size | VRAM | Speed | Quality |
|-------|------|------|-------|---------|
| `openai/whisper-tiny` | 39MB | ~1GB | Fastest | Basic |
| `openai/whisper-base` | 74MB | ~1GB | Fast | Good |
| `openai/whisper-small` | 244MB | ~2GB | Medium | Better |
| `openai/whisper-medium` | 769MB | ~5GB | Slow | Very Good |
| `openai/whisper-large-v2` | 1.5GB | ~10GB | Slowest | Best |
| `openai/whisper-large-v3` | 1.5GB | ~10GB | Slowest | Best |

### Custom Models

You can also use fine-tuned or specialized models:

```bash
export WHISPER_LOCAL_MODEL_NAME="your-username/your-whisper-model"
```

## Usage

### Automatic Switching

The service automatically uses local Whisper when `WHISPER_USE_LOCAL=true`. If local Whisper fails, it falls back to OpenAI Whisper.

### API Endpoints

#### Check Status
```bash
curl http://localhost:8000/api/whisper/status
```

#### Switch to Local Whisper
```bash
curl -X POST http://localhost:8000/api/whisper/switch-to-local
```

#### Switch to OpenAI Whisper
```bash
curl -X POST http://localhost:8000/api/whisper/switch-to-openai
```

#### Download Model
```bash
curl -X POST http://localhost:8000/api/whisper/download-model \
  -H "Content-Type: application/json" \
  -d '{"model_name": "openai/whisper-base"}'
```

### Python API

```python
from backend.services.unified_whisper_service import UnifiedWhisperService

# Initialize service
whisper = UnifiedWhisperService()

# Check status
status = whisper.get_service_status()
print(status)

# Switch to local
success = whisper.switch_to_local()

# Transcribe audio
result = whisper.transcribe(Path("audio.wav"))
```

## Performance Optimization

### GPU Acceleration

For NVIDIA GPUs with CUDA:

1. **Install CUDA-enabled PyTorch**:
   ```bash
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

2. **Verify GPU detection**:
   ```python
   import torch
   print(f"CUDA available: {torch.cuda.is_available()}")
   print(f"GPU count: {torch.cuda.device_count()}")
   ```

### Memory Management

For systems with limited RAM:

1. **Use smaller models**: Start with `whisper-tiny` or `whisper-base`
2. **Enable CPU offloading**: Set `low_cpu_mem_usage=True` (already enabled)
3. **Use float16 precision**: Automatically enabled for CUDA

### Batch Processing

For multiple files, the service automatically handles batching and memory management.

## Troubleshooting

### Common Issues

#### 1. Out of Memory Error
```
RuntimeError: CUDA out of memory
```
**Solutions**:
- Use a smaller model (`whisper-tiny` or `whisper-base`)
- Reduce batch size
- Close other GPU applications

#### 2. Model Download Fails
```
HTTPError: 404 Client Error
```
**Solutions**:
- Check model name spelling
- Verify internet connection
- Try a different model

#### 3. Slow Performance
**Solutions**:
- Use GPU acceleration (CUDA)
- Use smaller model for faster processing
- Ensure sufficient RAM

#### 4. Import Errors
```
ModuleNotFoundError: No module named 'transformers'
```
**Solutions**:
- Install missing dependencies: `pip install -r requirements.txt`
- Check Python environment

### Debug Mode

Run the test script for detailed diagnostics:

```bash
python test_local_whisper.py
```

This will show:
- Environment information
- Available dependencies
- Model status
- Service availability

## Model Storage

Downloaded models are cached in:
- **Linux/Mac**: `~/.cache/huggingface/transformers/`
- **Windows**: `%USERPROFILE%\.cache\huggingface\transformers\`

You can set a custom cache directory:
```bash
export HF_HOME="/path/to/custom/cache"
```

## Security Considerations

### Local Processing
- Audio never leaves your machine
- No data sent to external APIs
- Full control over model and processing

### Model Verification
- Models are downloaded from Hugging Face Hub
- Verify model authenticity before use
- Use trusted model sources

## Performance Benchmarks

Approximate processing times on different hardware:

| Hardware | Model | Audio Length | Processing Time |
|----------|-------|--------------|-----------------|
| CPU (Intel i7) | whisper-base | 1 minute | ~30 seconds |
| GPU (RTX 3080) | whisper-base | 1 minute | ~5 seconds |
| CPU (Intel i7) | whisper-large | 1 minute | ~2 minutes |
| GPU (RTX 3080) | whisper-large | 1 minute | ~15 seconds |

## Advanced Configuration

### Custom Model Path

To use a locally stored model:

```bash
export WHISPER_LOCAL_MODEL_PATH="/path/to/your/model"
```

### Language-Specific Models

For better accuracy with specific languages:

```bash
export WHISPER_LOCAL_MODEL_NAME="openai/whisper-medium.en"  # English-only
export WHISPER_LANGUAGE="en"
```

### Fine-tuned Models

Use domain-specific fine-tuned models:

```bash
export WHISPER_LOCAL_MODEL_NAME="your-org/medical-whisper-base"
```

## Support

For issues and questions:

1. Check this documentation
2. Run the test script: `python test_local_whisper.py`
3. Check the application logs
4. Review Hugging Face transformers documentation

## Contributing

To add support for new model types or improve performance:

1. Modify `backend/services/local_whisper_service.py`
2. Update configuration in `backend/utils/config.py`
3. Add tests to `test_local_whisper.py`
4. Update this documentation
