import torch
import torchaudio
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from sklearn.cluster import AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
import librosa

logger = logging.getLogger(__name__)

class SimpleDiarizationService:
    """Simple speaker diarization using audio features and clustering"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Simple diarization service initialized on {self.device}")
    
    def is_available(self) -> bool:
        """Always available as it uses basic audio processing"""
        return True
    
    def diarize(self, audio_path: Path) -> Dict[str, Any]:
        """
        Perform simple speaker diarization using audio features
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dictionary containing diarization results with speaker segments
        """
        try:
            logger.info(f"Performing simple diarization on: {audio_path}")
            
            # Load audio
            audio, sr = librosa.load(str(audio_path), sr=16000)
            duration = len(audio) / sr
            
            # Extract features for diarization
            segments = self._extract_speaker_segments(audio, sr)
            
            # Create speaker mapping
            num_speakers = len(set(seg["speaker_id"] for seg in segments))
            speaker_mapping = {
                f"SPEAKER_{i:02d}": f"Speaker {i+1}" 
                for i in range(num_speakers)
            }
            
            # Update segments with speaker labels
            for segment in segments:
                speaker_key = f"SPEAKER_{segment['speaker_id']:02d}"
                segment["speaker"] = speaker_key
                segment["speaker_label"] = speaker_mapping[speaker_key]
            
            result = {
                "num_speakers": num_speakers,
                "speakers": speaker_mapping,
                "segments": segments,
                "duration": duration
            }
            
            logger.info(f"Simple diarization completed. Found {num_speakers} speakers in {len(segments)} segments")
            return result
            
        except Exception as e:
            logger.error(f"Simple diarization failed: {e}")
            raise RuntimeError(f"Diarization failed: {str(e)}")
    
    def _extract_speaker_segments(self, audio: np.ndarray, sr: int) -> List[Dict[str, Any]]:
        """Extract speaker segments using audio features and clustering"""
        
        # Parameters
        window_size = 2.0  # seconds
        hop_size = 1.0     # seconds
        
        window_samples = int(window_size * sr)
        hop_samples = int(hop_size * sr)
        
        # Extract features for each window
        features = []
        timestamps = []
        
        for start in range(0, len(audio) - window_samples, hop_samples):
            end = start + window_samples
            window = audio[start:end]
            
            # Extract MFCC features
            mfcc = librosa.feature.mfcc(y=window, sr=sr, n_mfcc=13)
            mfcc_mean = np.mean(mfcc, axis=1)
            
            # Extract spectral features
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=window, sr=sr))
            spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=window, sr=sr))
            zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(window))
            
            # Combine features
            feature_vector = np.concatenate([
                mfcc_mean,
                [spectral_centroid, spectral_rolloff, zero_crossing_rate]
            ])
            
            features.append(feature_vector)
            timestamps.append((start / sr, end / sr))
        
        if len(features) == 0:
            # Fallback for very short audio
            return [{
                "start": 0.0,
                "end": len(audio) / sr,
                "speaker_id": 0,
                "duration": len(audio) / sr
            }]
        
        # Normalize features
        features = np.array(features)
        scaler = StandardScaler()
        features_normalized = scaler.fit_transform(features)
        
        # Determine number of speakers using clustering
        max_speakers = min(5, len(features))  # Limit to reasonable number
        best_n_speakers = self._estimate_num_speakers(features_normalized, max_speakers)
        
        # Perform clustering
        if best_n_speakers > 1:
            clustering = AgglomerativeClustering(n_clusters=best_n_speakers)
            speaker_labels = clustering.fit_predict(features_normalized)
        else:
            speaker_labels = np.zeros(len(features))
        
        # Create segments
        segments = []
        current_speaker = speaker_labels[0]
        segment_start = timestamps[0][0]
        
        for i, (timestamp, speaker) in enumerate(zip(timestamps, speaker_labels)):
            if speaker != current_speaker or i == len(timestamps) - 1:
                # End current segment
                segment_end = timestamp[0] if i < len(timestamps) - 1 else timestamps[i][1]
                
                segments.append({
                    "start": segment_start,
                    "end": segment_end,
                    "speaker_id": int(current_speaker),
                    "duration": segment_end - segment_start
                })
                
                # Start new segment
                if i < len(timestamps) - 1:
                    current_speaker = speaker
                    segment_start = timestamp[0]
        
        # Merge very short segments
        segments = self._merge_short_segments(segments, min_duration=1.0)
        
        return segments
    
    def _estimate_num_speakers(self, features: np.ndarray, max_speakers: int) -> int:
        """Estimate the optimal number of speakers using silhouette analysis"""
        if len(features) < 2:
            return 1
        
        from sklearn.metrics import silhouette_score
        
        best_score = -1
        best_n = 1
        
        for n in range(2, min(max_speakers + 1, len(features))):
            try:
                clustering = AgglomerativeClustering(n_clusters=n)
                labels = clustering.fit_predict(features)
                score = silhouette_score(features, labels)
                
                if score > best_score:
                    best_score = score
                    best_n = n
            except:
                continue
        
        return best_n
    
    def _merge_short_segments(self, segments: List[Dict[str, Any]], min_duration: float) -> List[Dict[str, Any]]:
        """Merge segments that are too short with adjacent segments"""
        if not segments:
            return segments
        
        merged = []
        current = segments[0].copy()
        
        for next_seg in segments[1:]:
            if current["duration"] < min_duration:
                # Merge with next segment
                current["end"] = next_seg["end"]
                current["duration"] = current["end"] - current["start"]
                # Keep the speaker of the longer segment
                if next_seg["duration"] > current["duration"] / 2:
                    current["speaker_id"] = next_seg["speaker_id"]
            else:
                merged.append(current)
                current = next_seg.copy()
        
        merged.append(current)
        return merged
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """Get information about the diarization service"""
        return {
            "available": True,
            "model_name": "simple-clustering-diarization",
            "device": self.device,
            "method": "MFCC + Spectral Features + Agglomerative Clustering"
        }