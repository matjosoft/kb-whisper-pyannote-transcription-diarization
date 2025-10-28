from pathlib import Path
from typing import Dict, Any, Optional
import logging
from openai import OpenAI

from utils.config import get_settings

logger = logging.getLogger(__name__)

class VllmWhisperService:
    """Service for handling Whisper transcription via vLLM server"""

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[OpenAI] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the OpenAI client for vLLM server"""
        try:
            logger.info(f"Initializing vLLM client with base URL: {self.settings.vllm_base_url}")
            self.client = OpenAI(
                base_url=self.settings.vllm_base_url,
                api_key=self.settings.vllm_api_key,
            )
            logger.info("vLLM client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vLLM client: {e}")
            self.client = None

    def is_available(self) -> bool:
        """Check if vLLM service is available"""
        return self.client is not None

    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        """
        Transcribe audio file using vLLM server

        Args:
            audio_path: Path to the audio file

        Returns:
            Dictionary containing transcription results with segments and timestamps
        """
        if not self.is_available():
            raise RuntimeError("vLLM service not available")

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            logger.info(f"Transcribing audio file with vLLM: {audio_path}")

            # Check file size
            file_size_mb = audio_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.settings.vllm_max_audio_filesize_mb:
                raise ValueError(
                    f"Audio file size ({file_size_mb:.1f}MB) exceeds maximum allowed "
                    f"({self.settings.vllm_max_audio_filesize_mb}MB)"
                )

            # Open and send audio file to vLLM server
            # Note: vLLM currently only supports 'text' or 'json' response formats, not 'verbose_json'
            with open(audio_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model=self.settings.vllm_model_name,
                    file=audio_file,
                    language=self.settings.whisper_language if self.settings.whisper_language != "auto" else None,
                    response_format="json",
                    timestamp_granularities=["segment"],
                )

            # Debug: log what we received
            logger.info(f"vLLM response type: {type(transcription)}")
            logger.info(f"vLLM response has segments: {hasattr(transcription, 'segments')}")
            if hasattr(transcription, 'segments') and transcription.segments:
                logger.info(f"vLLM returned {len(transcription.segments)} segments")

            # Convert response to expected format
            segments = []

            # Check if the response has segments (verbose mode)
            if hasattr(transcription, 'segments') and transcription.segments:
                for segment in transcription.segments:
                    # Handle both dict and object access
                    if isinstance(segment, dict):
                        start = segment.get("start", 0)
                        end = segment.get("end", 0)
                        text = segment.get("text", "").strip()
                        words = segment.get("words", [])
                    else:
                        start = getattr(segment, "start", 0)
                        end = getattr(segment, "end", 0)
                        text = getattr(segment, "text", "").strip()
                        words = getattr(segment, "words", [])

                    segment_data = {
                        "start": start,
                        "end": end,
                        "text": text,
                        "words": []
                    }

                    # Check if word-level timestamps are available
                    if words:
                        segment_data["words"] = [
                            {
                                "start": w.get("start", 0) if isinstance(w, dict) else getattr(w, "start", 0),
                                "end": w.get("end", 0) if isinstance(w, dict) else getattr(w, "end", 0),
                                "word": w.get("word", "") if isinstance(w, dict) else getattr(w, "word", "")
                            }
                            for w in words
                        ]
                    segments.append(segment_data)
                    logger.info(f"Segment: {start:.2f}s - {end:.2f}s: {text[:50]}...")

            # If no segments or only one big segment, try to split it
            if len(segments) <= 1:
                logger.info("vLLM returned only one segment, attempting to split for better diarization...")

                # Try to get word-level timestamps
                if hasattr(transcription, 'words') and transcription.words:
                    logger.info(f"Found {len(transcription.words)} words with timestamps")
                    segments = self._split_words_into_segments(transcription.words, transcription.text if hasattr(transcription, 'text') else "")
                # Otherwise create segments from the text
                elif hasattr(transcription, 'text') and transcription.text:
                    logger.info("No word timestamps, splitting text by sentences...")
                    segments = self._split_text_into_segments(transcription.text, audio_path)

            # If we still don't have segments, create one from the text
            if not segments and hasattr(transcription, 'text') and transcription.text:
                import torchaudio
                try:
                    waveform, sample_rate = torchaudio.load(str(audio_path))
                    duration = waveform.shape[1] / sample_rate
                except:
                    duration = 0

                segments.append({
                    "start": 0.0,
                    "end": duration,
                    "text": transcription.text.strip(),
                    "words": []
                })

            # Calculate duration from segments or audio file
            duration = 0
            if segments:
                duration = max([seg["end"] for seg in segments])

            if hasattr(transcription, 'duration'):
                duration = transcription.duration

            transcription_result = {
                "text": transcription.text if hasattr(transcription, 'text') else "",
                "language": transcription.language if hasattr(transcription, 'language') else "unknown",
                "segments": segments,
                "duration": duration,
                "model_type": "vllm"
            }

            logger.info(f"vLLM transcription completed. Found {len(segments)} segments")
            return transcription_result

        except Exception as e:
            logger.error(f"vLLM transcription failed: {e}")
            raise RuntimeError(f"vLLM transcription failed: {str(e)}")

    async def transcribe_with_progress(self, audio_path: Path, progress_callback=None):
        """
        Transcribe audio file with progress updates

        Note: vLLM server doesn't support streaming progress, so this simulates
        progress updates during the blocking transcription call.

        Args:
            audio_path: Path to the audio file
            progress_callback: Optional callback function for progress updates

        Yields:
            Progress updates as dictionaries
        """
        if not self.is_available():
            raise RuntimeError("vLLM service not available")

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            import asyncio
            import torchaudio

            logger.info(f"Transcribing audio file with vLLM (streaming mode): {audio_path}")

            # Get audio duration for progress simulation
            try:
                waveform, sample_rate = torchaudio.load(str(audio_path))
                duration = waveform.shape[1] / sample_rate
            except:
                duration = 60  # Default estimate

            # Calculate simulated chunks
            total_chunks = max(1, int(duration / 30))

            # Yield initial progress
            yield {
                "status": "transcribing",
                "message": f"Starting transcription of {duration:.1f}s audio in {total_chunks} chunks...",
                "total_chunks": total_chunks,
                "duration": duration
            }

            # Start transcription in background
            import concurrent.futures
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = executor.submit(self.transcribe, audio_path)

            # Simulate progress while waiting
            for chunk_idx in range(total_chunks):
                chunk_start = chunk_idx * 30
                chunk_end = min((chunk_idx + 1) * 30, duration)

                yield {
                    "status": "processing_chunk",
                    "chunk_index": chunk_idx,
                    "chunk_start": chunk_start,
                    "chunk_end": chunk_end,
                    "total_chunks": total_chunks,
                    "message": f"Processing chunk {chunk_idx + 1}/{total_chunks} ({chunk_start:.1f}s - {chunk_end:.1f}s)"
                }

                # Wait a bit between progress updates
                await asyncio.sleep(0.5)

                # Check if transcription finished
                if future.done():
                    break

            # Get the result
            result = future.result()

            # Yield completion progress
            yield {
                "status": "transcription_complete",
                "message": "Transcription completed successfully",
                "result": result
            }

        except Exception as e:
            logger.error(f"vLLM transcription with progress failed: {e}")
            yield {
                "status": "error",
                "message": f"Transcription failed: {str(e)}"
            }
            raise

    def get_service_status(self) -> Dict[str, Any]:
        """Get the current status of the vLLM service"""
        return {
            "available": self.is_available(),
            "base_url": self.settings.vllm_base_url,
            "model_name": self.settings.vllm_model_name,
            "max_filesize_mb": self.settings.vllm_max_audio_filesize_mb
        }

    def _split_words_into_segments(self, words, full_text: str) -> list:
        """Split word-level timestamps into segments for better diarization"""
        segments = []
        if not words:
            return segments

        # Group words into segments of ~30 seconds or ~10 words
        current_segment = []
        segment_start = None

        for word in words:
            # Get word data - handle both dict and object
            if isinstance(word, dict):
                w_start = word.get("start", 0)
                w_end = word.get("end", 0)
                w_text = word.get("word", "")
            else:
                w_start = getattr(word, "start", 0)
                w_end = getattr(word, "end", 0)
                w_text = getattr(word, "word", "")

            if segment_start is None:
                segment_start = w_start

            current_segment.append({"start": w_start, "end": w_end, "word": w_text})

            # Create a new segment every ~10 words or every 30 seconds
            if len(current_segment) >= 10 or (w_end - segment_start) >= 30:
                segment_text = " ".join([w["word"] for w in current_segment])
                segments.append({
                    "start": segment_start,
                    "end": current_segment[-1]["end"],
                    "text": segment_text.strip(),
                    "words": current_segment
                })
                current_segment = []
                segment_start = None

        # Add remaining words as final segment
        if current_segment:
            segment_text = " ".join([w["word"] for w in current_segment])
            segments.append({
                "start": current_segment[0]["start"],
                "end": current_segment[-1]["end"],
                "text": segment_text.strip(),
                "words": current_segment
            })

        logger.info(f"Split {len(words)} words into {len(segments)} segments")
        return segments

    def _split_text_into_segments(self, text: str, audio_path: Path) -> list:
        """Split text into segments based on sentences for better diarization"""
        import re
        import torchaudio

        segments = []

        # Get audio duration
        try:
            waveform, sample_rate = torchaudio.load(str(audio_path))
            total_duration = waveform.shape[1] / sample_rate
        except:
            total_duration = 60  # Default fallback

        # Split text by sentences (simple approach)
        # Look for sentence endings: . ! ? followed by space or end
        sentence_pattern = r'[.!?]+[\s]+'
        sentences = re.split(sentence_pattern, text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return segments

        # Estimate time per sentence based on text length
        total_chars = sum(len(s) for s in sentences)
        if total_chars == 0:
            return segments

        current_time = 0.0
        for sentence in sentences:
            # Estimate duration based on character count proportion
            sentence_duration = (len(sentence) / total_chars) * total_duration

            segments.append({
                "start": current_time,
                "end": current_time + sentence_duration,
                "text": sentence,
                "words": []
            })
            current_time += sentence_duration

        logger.info(f"Split text into {len(segments)} sentence-based segments")
        return segments
