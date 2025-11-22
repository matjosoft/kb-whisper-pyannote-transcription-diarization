import logging
from pathlib import Path
from typing import Dict, Any
import requests
import tempfile
import asyncio
import concurrent.futures

from utils.config import get_settings

logger = logging.getLogger(__name__)


class RemoteWhisperService:
    """Service for handling remote Whisper transcription via standalone server"""

    def __init__(self):
        self.settings = get_settings()
        self.remote_url = self.settings.whisper_remote_url
        logger.info(f"Using remote Whisper service at: {self.remote_url}")
        self._check_remote_service()

    def _check_remote_service(self):
        """Check if remote Whisper service is available"""
        try:
            response = requests.get(f"{self.remote_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("available"):
                    logger.info("✅ Remote Whisper service is available")
                else:
                    logger.warning("⚠️ Remote Whisper service is running but not available")
            else:
                logger.warning(f"⚠️ Remote Whisper service health check failed: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to remote Whisper service: {e}")
            logger.error(f"Make sure the service is running at {self.remote_url}")

    def is_available(self) -> bool:
        """Check if remote Whisper service is available"""
        try:
            response = requests.get(f"{self.remote_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                return health_data.get("available", False)
        except Exception as e:
            logger.debug(f"Remote Whisper service not available: {e}")
            return False

    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        """
        Perform transcription using remote Whisper service

        Args:
            audio_path: Path to the audio file

        Returns:
            Dictionary containing transcription results with segments and timestamps
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            logger.info(f"Performing remote transcription on: {audio_path}")

            # Send audio file to remote service
            with open(audio_path, 'rb') as f:
                files = {'file': (audio_path.name, f, 'audio/wav')}
                response = requests.post(
                    f"{self.remote_url}/transcribe",
                    files=files,
                    timeout=600  # 10 minutes timeout for large files
                )

            if response.status_code != 200:
                raise RuntimeError(f"Remote service returned status code {response.status_code}: {response.text}")

            result = response.json()
            if not result.get("success"):
                raise RuntimeError(f"Remote transcription failed: {result.get('detail', 'Unknown error')}")

            transcription_result = result.get("result")
            logger.info(f"Remote transcription completed. Found {len(transcription_result.get('segments', []))} segments")
            return transcription_result

        except Exception as e:
            logger.error(f"Remote transcription failed: {e}")
            raise RuntimeError(f"Remote transcription failed: {str(e)}")

    def _transcribe_chunk(self, chunk_path: Path, time_offset: float = 0.0) -> Dict[str, Any]:
        """
        Transcribe a single audio chunk via remote service

        Args:
            chunk_path: Path to the audio chunk file
            time_offset: Time offset to add to all timestamps

        Returns:
            Dictionary containing transcription results with adjusted timestamps
        """
        if not chunk_path.exists():
            raise FileNotFoundError(f"Chunk file not found: {chunk_path}")

        try:
            # Send chunk to remote service
            with open(chunk_path, 'rb') as f:
                files = {'file': (chunk_path.name, f, 'audio/wav')}
                response = requests.post(
                    f"{self.remote_url}/transcribe",
                    files=files,
                    timeout=300  # 5 minutes per chunk
                )

            if response.status_code != 200:
                raise RuntimeError(f"Remote service returned status code {response.status_code}: {response.text}")

            result = response.json()
            if not result.get("success"):
                raise RuntimeError(f"Remote transcription failed: {result.get('detail', 'Unknown error')}")

            chunk_result = result.get("result", {})

            # Adjust timestamps with offset
            if time_offset > 0:
                for segment in chunk_result.get("segments", []):
                    segment["start"] = segment.get("start", 0) + time_offset
                    segment["end"] = segment.get("end", 0) + time_offset
                    # Adjust word timestamps if present
                    for word in segment.get("words", []):
                        word["start"] = word.get("start", 0) + time_offset
                        word["end"] = word.get("end", 0) + time_offset

            return chunk_result

        except Exception as e:
            logger.error(f"Remote chunk transcription failed: {e}")
            raise RuntimeError(f"Remote chunk transcription failed: {str(e)}")

    async def _transcribe_chunked_with_progress(self, audio_path: Path):
        """
        Transcribe audio by splitting into chunks and sending each to remote service.
        Yields real progress updates for each chunk.

        Args:
            audio_path: Path to the audio file

        Yields:
            Progress updates as dictionaries
        """
        import torchaudio

        logger.info(f"Starting chunked remote transcription for: {audio_path}")

        try:
            # Load audio to get duration and waveform
            waveform, sample_rate = torchaudio.load(str(audio_path))
            total_duration = waveform.shape[1] / sample_rate
            logger.info(f"Audio duration: {total_duration:.1f}s, Sample rate: {sample_rate}Hz")

            # Use configured chunk duration (default 30 seconds)
            chunk_duration = self.settings.remote_whisper_chunk_duration
            total_chunks = max(1, int(total_duration / chunk_duration) + (1 if total_duration % chunk_duration > 0 else 0))

            logger.info(f"Splitting into {total_chunks} chunks of {chunk_duration}s each")

            # Yield initial progress
            yield {
                "status": "transcribing",
                "message": f"Starting remote transcription of {total_duration:.1f}s audio in {total_chunks} chunks...",
                "total_chunks": total_chunks,
                "duration": total_duration
            }

            # Create chunks list
            chunks = []
            current_time = 0.0
            while current_time < total_duration:
                chunk_end = min(current_time + chunk_duration, total_duration)
                chunks.append((current_time, chunk_end))
                current_time = chunk_end

            # Process each chunk
            all_segments = []
            full_text = ""

            with tempfile.TemporaryDirectory() as temp_dir:
                for chunk_idx, (start_time, end_time) in enumerate(chunks):
                    # Yield chunk processing status
                    yield {
                        "status": "processing_chunk",
                        "chunk_index": chunk_idx,
                        "chunk_start": start_time,
                        "chunk_end": end_time,
                        "total_chunks": total_chunks,
                        "message": f"Processing chunk {chunk_idx + 1}/{total_chunks} ({start_time:.1f}s - {end_time:.1f}s)"
                    }

                    # Extract chunk audio
                    start_sample = int(start_time * sample_rate)
                    end_sample = int(end_time * sample_rate)
                    chunk_waveform = waveform[:, start_sample:end_sample]

                    # Save chunk to temporary file
                    chunk_path = Path(temp_dir) / f"chunk_{chunk_idx}.wav"
                    torchaudio.save(str(chunk_path), chunk_waveform, sample_rate)

                    chunk_size_mb = chunk_path.stat().st_size / (1024 * 1024)
                    logger.info(f"Chunk {chunk_idx + 1} size: {chunk_size_mb:.1f}MB")

                    try:
                        # Transcribe chunk in thread pool to avoid blocking
                        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                        future = executor.submit(self._transcribe_chunk, chunk_path, start_time)

                        # Wait for chunk to complete
                        chunk_result = await asyncio.get_event_loop().run_in_executor(None, future.result)

                        # Merge results
                        if chunk_result.get("segments"):
                            all_segments.extend(chunk_result["segments"])
                        if chunk_result.get("text"):
                            full_text += " " + chunk_result["text"]

                        logger.info(f"Chunk {chunk_idx + 1} completed: {len(chunk_result.get('segments', []))} segments")

                    except Exception as e:
                        logger.error(f"Failed to transcribe chunk {chunk_idx + 1}: {e}")
                        yield {
                            "status": "error",
                            "chunk_index": chunk_idx,
                            "error": str(e),
                            "message": f"Chunk {chunk_idx + 1} failed: {str(e)}"
                        }
                        # Continue with other chunks
                        continue

            # Calculate final duration
            duration = total_duration
            if all_segments:
                duration = max([seg["end"] for seg in all_segments])

            transcription_result = {
                "text": full_text.strip(),
                "language": "unknown",
                "segments": all_segments,
                "duration": duration,
                "model_type": "remote_whisper_chunked"
            }

            # Yield completion
            yield {
                "status": "transcription_complete",
                "message": f"Remote transcription completed. Found {len(all_segments)} segments",
                "result": transcription_result
            }

            logger.info(f"Chunked remote transcription completed. Total segments: {len(all_segments)}")

        except Exception as e:
            logger.error(f"Chunked remote transcription failed: {e}")
            yield {
                "status": "error",
                "error": str(e),
                "message": f"Remote transcription failed: {str(e)}"
            }

    async def transcribe_with_progress(self, audio_path: Path):
        """
        Transcribe audio file with real progress updates.
        Splits audio into chunks and sends each to the remote service,
        yielding progress updates after each chunk is processed.

        Args:
            audio_path: Path to the audio file

        Yields:
            Progress updates as dictionaries
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            import torchaudio

            # Yield starting status
            yield {
                "status": "starting",
                "message": "Preparing audio for remote Whisper service..."
            }

            # Get audio duration to determine chunking
            try:
                waveform, sample_rate = torchaudio.load(str(audio_path))
                duration = waveform.shape[1] / sample_rate
            except Exception as e:
                logger.error(f"Failed to load audio: {e}")
                duration = 0

            # Always use chunked transcription for real progress feedback
            if duration > 0:
                logger.info(f"Using chunked remote transcription for {duration:.1f}s audio")
                async for progress_data in self._transcribe_chunked_with_progress(audio_path):
                    yield progress_data
            else:
                # Fallback for audio loading issues - send entire file
                logger.warning("Could not determine audio duration, falling back to single-file transcription")
                yield {
                    "status": "transcribing",
                    "message": "Remote transcription in progress...",
                    "duration": 0
                }

                result = self.transcribe(audio_path)

                yield {
                    "status": "transcription_complete",
                    "result": result,
                    "message": f"Remote transcription completed. Found {len(result.get('segments', []))} segments"
                }

        except Exception as e:
            logger.error(f"Remote transcription with progress failed: {e}")
            yield {
                "status": "error",
                "error": str(e),
                "message": f"Remote transcription failed: {str(e)}"
            }

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the remote service"""
        try:
            response = requests.get(f"{self.remote_url}/info", timeout=5)
            if response.status_code == 200:
                info = response.json()
                info["service_type"] = "remote_whisper"
                return info
            else:
                return {
                    "available": False,
                    "service_type": "remote_whisper",
                    "error": f"Failed to get info: status code {response.status_code}"
                }
        except Exception as e:
            return {
                "available": False,
                "service_type": "remote_whisper",
                "error": str(e)
            }
