"""
Advanced Content Fingerprinting Service
Implements audio/video fingerprinting, enhanced perceptual hashing, and ML pattern recognition
for comprehensive content matching beyond basic face recognition.
"""

import asyncio
import hashlib
import io
import logging
import numpy as np
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms, models
from PIL import Image
import librosa
import imagehash
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest
import ffmpeg

logger = logging.getLogger(__name__)


class FingerprintType(Enum):
    """Types of content fingerprints"""
    AUDIO = "audio"
    VIDEO = "video" 
    IMAGE = "image"
    TEXT = "text"


@dataclass
class ContentFingerprint:
    """Container for content fingerprint data"""
    fingerprint_type: FingerprintType
    fingerprint_data: Dict[str, Any]
    confidence: float
    source_url: str
    content_hash: str
    created_at: datetime
    metadata: Dict[str, Any] = None


@dataclass
class FingerprintMatch:
    """Container for fingerprint matching results"""
    original_fingerprint: ContentFingerprint
    matched_fingerprint: ContentFingerprint
    similarity_score: float
    match_confidence: float
    match_metadata: Dict[str, Any] = None


class AudioFingerprinter:
    """Advanced audio fingerprinting using spectral analysis and MFCCs"""
    
    def __init__(self):
        self.sample_rate = 22050
        self.n_mfcc = 13
        self.n_fft = 2048
        self.hop_length = 512
        
    async def extract_audio_fingerprint(
        self, 
        audio_data: bytes,
        duration_limit: int = 300  # 5 minutes max
    ) -> Dict[str, Any]:
        """
        Extract comprehensive audio fingerprint including:
        - Spectral centroid
        - MFCCs (Mel-frequency cepstral coefficients)
        - Chroma features
        - Spectral contrast
        - Tonnetz (harmonic features)
        """
        try:
            # Load audio from bytes
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_file.write(audio_data)
                tmp_path = tmp_file.name
                
            try:
                # Load with librosa
                y, sr = librosa.load(tmp_path, sr=self.sample_rate, duration=duration_limit)
                
                # Extract comprehensive audio features
                features = {}
                
                # 1. Spectral features
                features['spectral_centroid'] = librosa.feature.spectral_centroid(
                    y=y, sr=sr, hop_length=self.hop_length
                ).mean(axis=1).tolist()
                
                features['spectral_bandwidth'] = librosa.feature.spectral_bandwidth(
                    y=y, sr=sr, hop_length=self.hop_length
                ).mean(axis=1).tolist()
                
                features['spectral_rolloff'] = librosa.feature.spectral_rolloff(
                    y=y, sr=sr, hop_length=self.hop_length
                ).mean(axis=1).tolist()
                
                # 2. MFCCs - crucial for audio matching
                mfccs = librosa.feature.mfcc(
                    y=y, sr=sr, n_mfcc=self.n_mfcc,
                    n_fft=self.n_fft, hop_length=self.hop_length
                )
                features['mfccs'] = mfccs.mean(axis=1).tolist()
                features['mfccs_delta'] = librosa.feature.delta(mfccs).mean(axis=1).tolist()
                
                # 3. Chroma features for harmonic content
                chroma = librosa.feature.chroma_stft(
                    y=y, sr=sr, hop_length=self.hop_length
                )
                features['chroma'] = chroma.mean(axis=1).tolist()
                
                # 4. Spectral contrast
                features['spectral_contrast'] = librosa.feature.spectral_contrast(
                    y=y, sr=sr, hop_length=self.hop_length
                ).mean(axis=1).tolist()
                
                # 5. Tonnetz (harmonic network)
                tonnetz = librosa.feature.tonnetz(
                    y=librosa.effects.harmonic(y), sr=sr
                )
                features['tonnetz'] = tonnetz.mean(axis=1).tolist()
                
                # 6. Zero crossing rate
                features['zero_crossing_rate'] = librosa.feature.zero_crossing_rate(
                    y, hop_length=self.hop_length
                ).mean()
                
                # 7. Tempo and beat features
                try:
                    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                    features['tempo'] = float(tempo)
                    features['beat_intervals'] = np.diff(beats).mean() if len(beats) > 1 else 0.0
                except:
                    features['tempo'] = 0.0
                    features['beat_intervals'] = 0.0
                
                # 8. Root Mean Square Energy
                features['rms_energy'] = librosa.feature.rms(
                    y=y, hop_length=self.hop_length
                ).mean()
                
                # 9. Create compact audio signature for quick matching
                signature_vector = np.concatenate([
                    features['mfccs'],
                    features['chroma'],
                    [features['spectral_centroid'][0]],
                    [features['tempo']],
                    [features['zero_crossing_rate']],
                    [features['rms_energy']]
                ])
                features['signature_vector'] = signature_vector.tolist()
                
                # Metadata
                features['duration'] = float(len(y)) / sr
                features['sample_rate'] = sr
                features['n_samples'] = len(y)
                
                logger.info(f"Extracted audio fingerprint: {len(features)} features")
                return features
                
            finally:
                # Cleanup temp file
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error extracting audio fingerprint: {e}")
            return {}
    
    async def compare_audio_fingerprints(
        self,
        fp1: Dict[str, Any],
        fp2: Dict[str, Any]
    ) -> float:
        """Compare two audio fingerprints and return similarity score (0-1)"""
        try:
            if not fp1.get('signature_vector') or not fp2.get('signature_vector'):
                return 0.0
                
            vec1 = np.array(fp1['signature_vector']).reshape(1, -1)
            vec2 = np.array(fp2['signature_vector']).reshape(1, -1)
            
            # Cosine similarity
            similarity = cosine_similarity(vec1, vec2)[0][0]
            
            # Additional weighted comparisons for key features
            weights = {
                'mfccs': 0.4,
                'chroma': 0.3,
                'spectral_centroid': 0.1,
                'tempo': 0.1,
                'zero_crossing_rate': 0.05,
                'rms_energy': 0.05
            }
            
            weighted_similarity = 0.0
            total_weight = 0.0
            
            for feature, weight in weights.items():
                if feature in fp1 and feature in fp2:
                    if isinstance(fp1[feature], list) and isinstance(fp2[feature], list):
                        if len(fp1[feature]) == len(fp2[feature]):
                            f1 = np.array(fp1[feature]).reshape(1, -1)
                            f2 = np.array(fp2[feature]).reshape(1, -1)
                            feat_sim = cosine_similarity(f1, f2)[0][0]
                            weighted_similarity += feat_sim * weight
                            total_weight += weight
                    else:
                        # Scalar features
                        val1, val2 = float(fp1[feature]), float(fp2[feature])
                        if val1 != 0 and val2 != 0:
                            feat_sim = 1.0 - abs(val1 - val2) / max(abs(val1), abs(val2))
                            weighted_similarity += feat_sim * weight
                            total_weight += weight
            
            if total_weight > 0:
                weighted_similarity /= total_weight
                # Combine cosine similarity with weighted feature similarity
                final_similarity = 0.6 * similarity + 0.4 * weighted_similarity
            else:
                final_similarity = similarity
                
            return max(0.0, min(1.0, final_similarity))
            
        except Exception as e:
            logger.error(f"Error comparing audio fingerprints: {e}")
            return 0.0


class VideoFingerprinter:
    """Advanced video fingerprinting using scene analysis and temporal features"""
    
    def __init__(self):
        self.max_frames = 100  # Sample every N frames
        self.frame_size = (224, 224)
        
    async def extract_video_fingerprint(
        self,
        video_data: bytes,
        duration_limit: int = 600  # 10 minutes max
    ) -> Dict[str, Any]:
        """
        Extract comprehensive video fingerprint including:
        - Scene detection and key frames
        - Optical flow patterns
        - Color histograms
        - Edge features
        - Motion vectors
        """
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_file:
                tmp_file.write(video_data)
                tmp_path = tmp_file.name
                
            try:
                # Get video info
                probe = ffmpeg.probe(tmp_path)
                video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
                
                duration = float(video_info.get('duration', 0))
                fps = eval(video_info.get('r_frame_rate', '25/1'))
                width = int(video_info.get('width', 0))
                height = int(video_info.get('height', 0))
                
                if duration > duration_limit:
                    logger.warning(f"Video duration {duration}s exceeds limit {duration_limit}s")
                    duration = duration_limit
                
                features = {
                    'duration': duration,
                    'fps': fps,
                    'width': width,
                    'height': height,
                    'aspect_ratio': width / height if height > 0 else 0
                }
                
                # Extract frames for analysis
                cap = cv2.VideoCapture(tmp_path)
                
                # Calculate frame sampling interval
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                frame_interval = max(1, total_frames // self.max_frames)
                
                frames_data = []
                frame_features = []
                prev_frame = None
                motion_vectors = []
                
                frame_count = 0
                extracted_count = 0
                
                while cap.isOpened() and extracted_count < self.max_frames:
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    if frame_count % frame_interval == 0:
                        # Resize frame for consistent processing
                        frame_resized = cv2.resize(frame, self.frame_size)
                        frames_data.append(frame_resized)
                        
                        # Extract frame features
                        frame_feat = self._extract_frame_features(frame_resized)
                        frame_features.append(frame_feat)
                        
                        # Calculate optical flow if we have previous frame
                        if prev_frame is not None:
                            flow = self._calculate_optical_flow(prev_frame, frame_resized)
                            motion_vectors.append(flow)
                            
                        prev_frame = frame_resized.copy()
                        extracted_count += 1
                        
                    frame_count += 1
                
                cap.release()
                
                # Process extracted features
                if frame_features:
                    features['frame_features'] = frame_features
                    features['avg_brightness'] = np.mean([f['brightness'] for f in frame_features])
                    features['avg_contrast'] = np.mean([f['contrast'] for f in frame_features])
                    features['dominant_colors'] = self._extract_dominant_colors(frames_data)
                
                if motion_vectors:
                    features['motion_intensity'] = np.mean([np.mean(mv) for mv in motion_vectors])
                    features['motion_variance'] = np.var([np.mean(mv) for mv in motion_vectors])
                
                # Scene change detection
                features['scene_changes'] = self._detect_scene_changes(frame_features)
                
                # Create compact video signature
                signature_components = []
                if 'avg_brightness' in features:
                    signature_components.extend([features['avg_brightness'], features['avg_contrast']])
                if 'motion_intensity' in features:
                    signature_components.append(features['motion_intensity'])
                if 'dominant_colors' in features:
                    signature_components.extend(features['dominant_colors'][:6])  # Top 6 colors
                
                features['signature_vector'] = signature_components
                features['extracted_frames'] = extracted_count
                
                logger.info(f"Extracted video fingerprint: {extracted_count} frames analyzed")
                return features
                
            finally:
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error extracting video fingerprint: {e}")
            return {}
    
    def _extract_frame_features(self, frame: np.ndarray) -> Dict[str, Any]:
        """Extract features from a single frame"""
        try:
            # Convert to different color spaces
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            features = {}
            
            # Basic statistics
            features['brightness'] = np.mean(gray)
            features['contrast'] = np.std(gray)
            
            # Color histogram
            hist_b = cv2.calcHist([frame], [0], None, [16], [0, 256])
            hist_g = cv2.calcHist([frame], [1], None, [16], [0, 256])
            hist_r = cv2.calcHist([frame], [2], None, [16], [0, 256])
            features['color_hist'] = np.concatenate([hist_b, hist_g, hist_r]).flatten().tolist()
            
            # Edge features
            edges = cv2.Canny(gray, 50, 150)
            features['edge_density'] = np.mean(edges) / 255.0
            
            # Texture features using Local Binary Patterns (simplified)
            features['texture_variance'] = np.var(gray)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting frame features: {e}")
            return {}
    
    def _calculate_optical_flow(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> float:
        """Calculate optical flow between two frames"""
        try:
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
            
            # Calculate dense optical flow
            flow = cv2.calcOpticalFlowPyrLK(
                prev_gray, curr_gray, 
                np.array([[x, y] for x in range(0, prev_gray.shape[1], 20) 
                         for y in range(0, prev_gray.shape[0], 20)], dtype=np.float32),
                None
            )[0]
            
            # Calculate average motion magnitude
            if flow is not None and len(flow) > 0:
                motion = np.linalg.norm(flow, axis=1)
                return np.mean(motion)
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating optical flow: {e}")
            return 0.0
    
    def _extract_dominant_colors(self, frames: List[np.ndarray], k: int = 6) -> List[float]:
        """Extract dominant colors across all frames"""
        try:
            if not frames:
                return []
                
            # Sample colors from frames
            all_pixels = []
            for frame in frames[::max(1, len(frames)//10)]:  # Sample every 10th frame
                resized = cv2.resize(frame, (64, 64))  # Reduce for speed
                pixels = resized.reshape(-1, 3)
                all_pixels.append(pixels)
            
            if all_pixels:
                combined_pixels = np.vstack(all_pixels)
                
                # Use K-means clustering to find dominant colors
                from sklearn.cluster import KMeans
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                kmeans.fit(combined_pixels)
                
                # Return normalized color centers
                colors = kmeans.cluster_centers_ / 255.0
                return colors.flatten().tolist()
            
            return []
            
        except Exception as e:
            logger.error(f"Error extracting dominant colors: {e}")
            return []
    
    def _detect_scene_changes(self, frame_features: List[Dict[str, Any]]) -> List[int]:
        """Detect scene changes based on frame feature differences"""
        try:
            if len(frame_features) < 2:
                return []
                
            scene_changes = []
            threshold = 0.3  # Adjust based on sensitivity needed
            
            for i in range(1, len(frame_features)):
                # Compare brightness and contrast changes
                brightness_diff = abs(
                    frame_features[i]['brightness'] - frame_features[i-1]['brightness']
                ) / 255.0
                
                contrast_diff = abs(
                    frame_features[i]['contrast'] - frame_features[i-1]['contrast']
                ) / 255.0
                
                # Color histogram difference
                hist_diff = 0.0
                if ('color_hist' in frame_features[i] and 
                    'color_hist' in frame_features[i-1]):
                    hist1 = np.array(frame_features[i]['color_hist'])
                    hist2 = np.array(frame_features[i-1]['color_hist'])
                    hist_diff = np.sum(np.abs(hist1 - hist2)) / np.sum(hist1 + hist2 + 1e-7)
                
                combined_diff = (brightness_diff + contrast_diff + hist_diff) / 3.0
                
                if combined_diff > threshold:
                    scene_changes.append(i)
            
            return scene_changes
            
        except Exception as e:
            logger.error(f"Error detecting scene changes: {e}")
            return []
    
    async def compare_video_fingerprints(
        self,
        fp1: Dict[str, Any], 
        fp2: Dict[str, Any]
    ) -> float:
        """Compare two video fingerprints and return similarity score (0-1)"""
        try:
            if not fp1.get('signature_vector') or not fp2.get('signature_vector'):
                return 0.0
            
            # Compare signature vectors
            vec1 = np.array(fp1['signature_vector'])
            vec2 = np.array(fp2['signature_vector'])
            
            if len(vec1) != len(vec2):
                # Pad shorter vector
                min_len = min(len(vec1), len(vec2))
                vec1 = vec1[:min_len]
                vec2 = vec2[:min_len]
            
            if len(vec1) == 0:
                return 0.0
            
            # Cosine similarity
            similarity = cosine_similarity(vec1.reshape(1, -1), vec2.reshape(1, -1))[0][0]
            
            # Additional comparisons
            bonus_similarity = 0.0
            comparisons = 0
            
            # Duration similarity
            if 'duration' in fp1 and 'duration' in fp2:
                dur1, dur2 = fp1['duration'], fp2['duration']
                if dur1 > 0 and dur2 > 0:
                    dur_sim = 1.0 - abs(dur1 - dur2) / max(dur1, dur2)
                    bonus_similarity += dur_sim
                    comparisons += 1
            
            # Aspect ratio similarity
            if 'aspect_ratio' in fp1 and 'aspect_ratio' in fp2:
                ar1, ar2 = fp1['aspect_ratio'], fp2['aspect_ratio']
                if ar1 > 0 and ar2 > 0:
                    ar_sim = 1.0 - abs(ar1 - ar2) / max(ar1, ar2)
                    bonus_similarity += ar_sim
                    comparisons += 1
            
            # Scene change pattern similarity
            if 'scene_changes' in fp1 and 'scene_changes' in fp2:
                sc1, sc2 = len(fp1['scene_changes']), len(fp2['scene_changes'])
                if sc1 > 0 or sc2 > 0:
                    sc_sim = 1.0 - abs(sc1 - sc2) / max(sc1 + sc2, 1)
                    bonus_similarity += sc_sim
                    comparisons += 1
            
            if comparisons > 0:
                bonus_similarity /= comparisons
                final_similarity = 0.7 * similarity + 0.3 * bonus_similarity
            else:
                final_similarity = similarity
            
            return max(0.0, min(1.0, final_similarity))
            
        except Exception as e:
            logger.error(f"Error comparing video fingerprints: {e}")
            return 0.0


class EnhancedPerceptualHasher:
    """Enhanced perceptual hashing with multiple algorithms and robustness"""
    
    def __init__(self):
        self.hash_size = 8  # Standard 8x8 for most algorithms
        
    async def extract_enhanced_hash(self, image: Image.Image) -> Dict[str, str]:
        """Extract multiple perceptual hashes for robustness"""
        try:
            hashes = {}
            
            # Standard perceptual hashes
            hashes['phash'] = str(imagehash.phash(image, hash_size=self.hash_size))
            hashes['ahash'] = str(imagehash.average_hash(image, hash_size=self.hash_size))
            hashes['dhash'] = str(imagehash.dhash(image, hash_size=self.hash_size))
            hashes['whash'] = str(imagehash.whash(image, hash_size=self.hash_size))
            
            # Color hash for color-sensitive matching
            hashes['colorhash'] = str(imagehash.colorhash(image, binbits=3))
            
            # Crop-resistant hash
            hashes['crop_resistant'] = str(imagehash.crop_resistant_hash(image))
            
            return hashes
            
        except Exception as e:
            logger.error(f"Error extracting enhanced hashes: {e}")
            return {}
    
    async def compare_enhanced_hashes(
        self,
        hashes1: Dict[str, str],
        hashes2: Dict[str, str],
        threshold: int = 10
    ) -> Dict[str, float]:
        """Compare enhanced hashes and return similarity scores"""
        try:
            similarities = {}
            
            for hash_type in hashes1:
                if hash_type in hashes2:
                    try:
                        hash1 = imagehash.hex_to_hash(hashes1[hash_type])
                        hash2 = imagehash.hex_to_hash(hashes2[hash_type])
                        
                        # Calculate Hamming distance
                        distance = hash1 - hash2
                        
                        # Convert to similarity score (0-1)
                        max_distance = len(hash1.hash.flatten()) * 4  # Max possible distance
                        similarity = 1.0 - (distance / max_distance)
                        similarities[hash_type] = max(0.0, similarity)
                        
                    except Exception as e:
                        logger.warning(f"Error comparing {hash_type} hashes: {e}")
                        similarities[hash_type] = 0.0
            
            return similarities
            
        except Exception as e:
            logger.error(f"Error comparing enhanced hashes: {e}")
            return {}


class MLPatternRecognizer:
    """Machine learning-based pattern recognition for piracy prediction"""
    
    def __init__(self):
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.clustering_model = DBSCAN(eps=0.5, min_samples=2)
        self.trained = False
        
    async def analyze_piracy_patterns(
        self,
        historical_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze historical piracy data to identify patterns"""
        try:
            if len(historical_data) < 10:
                return {'insufficient_data': True}
            
            # Extract features from historical data
            features = self._extract_pattern_features(historical_data)
            
            if len(features) == 0:
                return {'no_features_extracted': True}
            
            features_array = np.array(features)
            
            # Anomaly detection
            anomaly_scores = self.anomaly_detector.fit_predict(features_array)
            anomalies = np.where(anomaly_scores == -1)[0].tolist()
            
            # Clustering to find patterns
            clusters = self.clustering_model.fit_predict(features_array)
            unique_clusters = set(clusters)
            unique_clusters.discard(-1)  # Remove noise cluster
            
            # Pattern analysis
            patterns = {
                'total_incidents': len(historical_data),
                'anomaly_count': len(anomalies),
                'pattern_clusters': len(unique_clusters),
                'high_risk_indicators': self._identify_risk_indicators(historical_data, features_array, clusters),
                'temporal_patterns': self._analyze_temporal_patterns(historical_data),
                'platform_patterns': self._analyze_platform_patterns(historical_data)
            }
            
            self.trained = True
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing piracy patterns: {e}")
            return {'error': str(e)}
    
    def _extract_pattern_features(self, data: List[Dict[str, Any]]) -> List[List[float]]:
        """Extract numerical features from historical piracy data"""
        features = []
        
        for incident in data:
            feature_vector = []
            
            # Time-based features
            if 'timestamp' in incident:
                ts = incident['timestamp']
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts)
                    except:
                        ts = datetime.now()
                
                feature_vector.extend([
                    float(ts.hour),  # Hour of day
                    float(ts.weekday()),  # Day of week
                    float(ts.day),  # Day of month
                ])
            else:
                feature_vector.extend([0.0, 0.0, 0.0])
            
            # Platform features
            platform = incident.get('platform', 'unknown').lower()
            platform_features = [
                1.0 if 'social' in platform else 0.0,
                1.0 if 'video' in platform else 0.0,
                1.0 if 'image' in platform else 0.0,
                1.0 if 'forum' in platform else 0.0,
            ]
            feature_vector.extend(platform_features)
            
            # Content type features
            content_type = incident.get('content_type', 'unknown').lower()
            content_features = [
                1.0 if 'image' in content_type else 0.0,
                1.0 if 'video' in content_type else 0.0,
                1.0 if 'text' in content_type else 0.0,
            ]
            feature_vector.extend(content_features)
            
            # Response time feature
            response_time = incident.get('response_time_hours', 24.0)
            feature_vector.append(float(response_time))
            
            # Success feature
            success = 1.0 if incident.get('resolved', False) else 0.0
            feature_vector.append(success)
            
            features.append(feature_vector)
        
        return features
    
    def _identify_risk_indicators(
        self, 
        data: List[Dict[str, Any]], 
        features: np.ndarray, 
        clusters: np.ndarray
    ) -> List[str]:
        """Identify high-risk indicators from clustered data"""
        indicators = []
        
        try:
            # Find clusters with high incident rates
            cluster_sizes = {}
            for cluster in clusters:
                if cluster != -1:  # Ignore noise
                    cluster_sizes[cluster] = cluster_sizes.get(cluster, 0) + 1
            
            if cluster_sizes:
                avg_cluster_size = np.mean(list(cluster_sizes.values()))
                
                for cluster, size in cluster_sizes.items():
                    if size > avg_cluster_size * 1.5:  # 50% above average
                        # Analyze this cluster's characteristics
                        cluster_indices = np.where(clusters == cluster)[0]
                        cluster_data = [data[i] for i in cluster_indices]
                        
                        # Common platforms in this cluster
                        platforms = [item.get('platform', 'unknown') for item in cluster_data]
                        most_common_platform = max(set(platforms), key=platforms.count)
                        
                        indicators.append(f"High activity on {most_common_platform}")
            
            # Time-based patterns
            hours = [item.get('timestamp', datetime.now()).hour 
                    if isinstance(item.get('timestamp'), datetime) else 12 
                    for item in data]
            
            # Find peak hours
            hour_counts = {}
            for hour in hours:
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            if hour_counts:
                peak_hour = max(hour_counts, key=hour_counts.get)
                if hour_counts[peak_hour] > len(data) * 0.2:  # More than 20% of incidents
                    indicators.append(f"Peak activity around {peak_hour}:00")
                    
        except Exception as e:
            logger.error(f"Error identifying risk indicators: {e}")
        
        return indicators
    
    def _analyze_temporal_patterns(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal patterns in piracy incidents"""
        try:
            timestamps = []
            for item in data:
                ts = item.get('timestamp', datetime.now())
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts)
                    except:
                        ts = datetime.now()
                timestamps.append(ts)
            
            # Hour distribution
            hours = [ts.hour for ts in timestamps]
            hour_dist = {h: hours.count(h) for h in range(24)}
            peak_hour = max(hour_dist, key=hour_dist.get) if hour_dist else 12
            
            # Day of week distribution  
            weekdays = [ts.weekday() for ts in timestamps]
            weekday_dist = {d: weekdays.count(d) for d in range(7)}
            peak_day = max(weekday_dist, key=weekday_dist.get) if weekday_dist else 0
            
            return {
                'peak_hour': peak_hour,
                'peak_day': peak_day,
                'hour_distribution': hour_dist,
                'weekday_distribution': weekday_dist
            }
            
        except Exception as e:
            logger.error(f"Error analyzing temporal patterns: {e}")
            return {}
    
    def _analyze_platform_patterns(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze platform-specific patterns"""
        try:
            platforms = [item.get('platform', 'unknown') for item in data]
            platform_counts = {}
            platform_success_rates = {}
            
            for i, platform in enumerate(platforms):
                platform_counts[platform] = platform_counts.get(platform, 0) + 1
                
                # Track success rates by platform
                if platform not in platform_success_rates:
                    platform_success_rates[platform] = {'total': 0, 'success': 0}
                
                platform_success_rates[platform]['total'] += 1
                if data[i].get('resolved', False):
                    platform_success_rates[platform]['success'] += 1
            
            # Calculate success rates
            success_rates = {}
            for platform, stats in platform_success_rates.items():
                if stats['total'] > 0:
                    success_rates[platform] = stats['success'] / stats['total']
            
            # Identify most problematic platforms
            problematic_platforms = [
                platform for platform, rate in success_rates.items() 
                if rate < 0.5 and platform_counts[platform] > 1
            ]
            
            return {
                'platform_counts': platform_counts,
                'success_rates': success_rates,
                'most_common_platform': max(platform_counts, key=platform_counts.get) if platform_counts else 'unknown',
                'problematic_platforms': problematic_platforms
            }
            
        except Exception as e:
            logger.error(f"Error analyzing platform patterns: {e}")
            return {}


class ContentFingerprintingService:
    """Main service orchestrating all fingerprinting capabilities"""
    
    def __init__(self):
        self.audio_fingerprinter = AudioFingerprinter()
        self.video_fingerprinter = VideoFingerprinter()
        self.enhanced_hasher = EnhancedPerceptualHasher()
        self.pattern_recognizer = MLPatternRecognizer()
        
        # In-memory cache for fingerprints (in production, use Redis or database)
        self.fingerprint_cache = {}
        
    async def create_content_fingerprint(
        self,
        content_data: bytes,
        content_type: FingerprintType,
        source_url: str,
        metadata: Dict[str, Any] = None
    ) -> ContentFingerprint:
        """Create comprehensive fingerprint for content"""
        try:
            fingerprint_data = {}
            confidence = 0.0
            
            if content_type == FingerprintType.AUDIO:
                fingerprint_data = await self.audio_fingerprinter.extract_audio_fingerprint(content_data)
                confidence = 0.9 if fingerprint_data.get('signature_vector') else 0.1
                
            elif content_type == FingerprintType.VIDEO:
                fingerprint_data = await self.video_fingerprinter.extract_video_fingerprint(content_data)
                confidence = 0.9 if fingerprint_data.get('signature_vector') else 0.1
                
            elif content_type == FingerprintType.IMAGE:
                try:
                    image = Image.open(io.BytesIO(content_data))
                    fingerprint_data = await self.enhanced_hasher.extract_enhanced_hash(image)
                    confidence = 0.9 if fingerprint_data else 0.1
                except Exception as e:
                    logger.error(f"Error processing image: {e}")
                    confidence = 0.1
                    
            elif content_type == FingerprintType.TEXT:
                text = content_data.decode('utf-8', errors='ignore')
                # Simple text fingerprinting (can be enhanced with NLP)
                fingerprint_data = {
                    'text_hash': hashlib.sha256(text.encode()).hexdigest(),
                    'length': len(text),
                    'word_count': len(text.split()),
                    'char_distribution': self._analyze_char_distribution(text)
                }
                confidence = 0.8
            
            content_hash = hashlib.sha256(content_data).hexdigest()
            
            fingerprint = ContentFingerprint(
                fingerprint_type=content_type,
                fingerprint_data=fingerprint_data,
                confidence=confidence,
                source_url=source_url,
                content_hash=content_hash,
                created_at=datetime.utcnow(),
                metadata=metadata or {}
            )
            
            # Cache the fingerprint
            self.fingerprint_cache[content_hash] = fingerprint
            
            return fingerprint
            
        except Exception as e:
            logger.error(f"Error creating content fingerprint: {e}")
            raise
    
    async def find_matching_fingerprints(
        self,
        query_fingerprint: ContentFingerprint,
        similarity_threshold: float = 0.8
    ) -> List[FingerprintMatch]:
        """Find matching fingerprints in the database/cache"""
        matches = []
        
        try:
            for cached_hash, cached_fingerprint in self.fingerprint_cache.items():
                if (cached_fingerprint.fingerprint_type == query_fingerprint.fingerprint_type and
                    cached_hash != query_fingerprint.content_hash):
                    
                    similarity_score = await self._calculate_fingerprint_similarity(
                        query_fingerprint, cached_fingerprint
                    )
                    
                    if similarity_score >= similarity_threshold:
                        match_confidence = min(
                            query_fingerprint.confidence,
                            cached_fingerprint.confidence
                        ) * similarity_score
                        
                        match = FingerprintMatch(
                            original_fingerprint=query_fingerprint,
                            matched_fingerprint=cached_fingerprint,
                            similarity_score=similarity_score,
                            match_confidence=match_confidence,
                            match_metadata={
                                'comparison_method': query_fingerprint.fingerprint_type.value,
                                'threshold_used': similarity_threshold
                            }
                        )
                        matches.append(match)
            
            # Sort by confidence
            matches.sort(key=lambda x: x.match_confidence, reverse=True)
            
        except Exception as e:
            logger.error(f"Error finding matching fingerprints: {e}")
        
        return matches
    
    async def _calculate_fingerprint_similarity(
        self,
        fp1: ContentFingerprint,
        fp2: ContentFingerprint
    ) -> float:
        """Calculate similarity between two fingerprints"""
        try:
            if fp1.fingerprint_type != fp2.fingerprint_type:
                return 0.0
            
            if fp1.fingerprint_type == FingerprintType.AUDIO:
                return await self.audio_fingerprinter.compare_audio_fingerprints(
                    fp1.fingerprint_data, fp2.fingerprint_data
                )
                
            elif fp1.fingerprint_type == FingerprintType.VIDEO:
                return await self.video_fingerprinter.compare_video_fingerprints(
                    fp1.fingerprint_data, fp2.fingerprint_data
                )
                
            elif fp1.fingerprint_type == FingerprintType.IMAGE:
                similarities = await self.enhanced_hasher.compare_enhanced_hashes(
                    fp1.fingerprint_data, fp2.fingerprint_data
                )
                # Return weighted average of all hash similarities
                if similarities:
                    weights = {
                        'phash': 0.3,
                        'ahash': 0.2, 
                        'dhash': 0.2,
                        'whash': 0.15,
                        'colorhash': 0.1,
                        'crop_resistant': 0.05
                    }
                    
                    weighted_sim = 0.0
                    total_weight = 0.0
                    
                    for hash_type, similarity in similarities.items():
                        weight = weights.get(hash_type, 0.1)
                        weighted_sim += similarity * weight
                        total_weight += weight
                    
                    return weighted_sim / total_weight if total_weight > 0 else 0.0
                else:
                    return 0.0
                    
            elif fp1.fingerprint_type == FingerprintType.TEXT:
                # Simple text comparison
                if (fp1.fingerprint_data.get('text_hash') == 
                    fp2.fingerprint_data.get('text_hash')):
                    return 1.0
                    
                # Compare character distributions
                dist1 = fp1.fingerprint_data.get('char_distribution', {})
                dist2 = fp2.fingerprint_data.get('char_distribution', {})
                
                if dist1 and dist2:
                    # Calculate similarity between distributions
                    all_chars = set(dist1.keys()) | set(dist2.keys())
                    vec1 = [dist1.get(c, 0) for c in all_chars]
                    vec2 = [dist2.get(c, 0) for c in all_chars]
                    
                    if sum(vec1) > 0 and sum(vec2) > 0:
                        similarity = cosine_similarity([vec1], [vec2])[0][0]
                        return max(0.0, similarity)
                
                return 0.0
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating fingerprint similarity: {e}")
            return 0.0
    
    def _analyze_char_distribution(self, text: str) -> Dict[str, float]:
        """Analyze character distribution in text"""
        if not text:
            return {}
            
        char_count = {}
        total_chars = len(text)
        
        for char in text.lower():
            if char.isalnum():  # Only count alphanumeric characters
                char_count[char] = char_count.get(char, 0) + 1
        
        # Convert to frequencies
        return {char: count / total_chars for char, count in char_count.items()}
    
    async def analyze_content_patterns(
        self,
        historical_infringements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze patterns in historical infringement data"""
        return await self.pattern_recognizer.analyze_piracy_patterns(historical_infringements)
    
    async def predict_piracy_risk(
        self,
        content_metadata: Dict[str, Any],
        creator_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Predict piracy risk for new content based on patterns"""
        try:
            if not self.pattern_recognizer.trained:
                return {
                    'risk_score': 0.5,
                    'confidence': 0.1,
                    'message': 'Insufficient historical data for prediction'
                }
            
            # Extract features from content and creator
            risk_factors = []
            
            # Content type risk
            content_type = content_metadata.get('type', 'unknown').lower()
            if 'video' in content_type:
                risk_factors.append(0.7)  # Videos are higher risk
            elif 'image' in content_type:
                risk_factors.append(0.5)
            else:
                risk_factors.append(0.3)
            
            # Creator popularity risk
            follower_count = creator_profile.get('follower_count', 0)
            if follower_count > 100000:
                risk_factors.append(0.8)  # High-profile creators are higher risk
            elif follower_count > 10000:
                risk_factors.append(0.6)
            else:
                risk_factors.append(0.3)
            
            # Platform risk
            platform = content_metadata.get('platform', 'unknown').lower()
            platform_risk = {
                'onlyfans': 0.9,
                'instagram': 0.6,
                'twitter': 0.7,
                'tiktok': 0.8,
                'youtube': 0.5,
            }
            risk_factors.append(platform_risk.get(platform, 0.5))
            
            # Time-based risk (new content is higher risk)
            upload_time = content_metadata.get('upload_time')
            if upload_time:
                try:
                    if isinstance(upload_time, str):
                        upload_time = datetime.fromisoformat(upload_time)
                    
                    hours_since_upload = (datetime.utcnow() - upload_time).total_seconds() / 3600
                    if hours_since_upload < 24:
                        risk_factors.append(0.8)  # Very new content
                    elif hours_since_upload < 168:  # 1 week
                        risk_factors.append(0.6)
                    else:
                        risk_factors.append(0.4)
                except:
                    risk_factors.append(0.5)
            else:
                risk_factors.append(0.5)
            
            # Calculate overall risk score
            risk_score = np.mean(risk_factors)
            confidence = 0.7 if len(risk_factors) >= 4 else 0.4
            
            # Risk level categorization
            if risk_score >= 0.7:
                risk_level = 'HIGH'
            elif risk_score >= 0.5:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'
            
            return {
                'risk_score': float(risk_score),
                'risk_level': risk_level,
                'confidence': float(confidence),
                'factors': {
                    'content_type_risk': risk_factors[0] if len(risk_factors) > 0 else 0.5,
                    'creator_popularity_risk': risk_factors[1] if len(risk_factors) > 1 else 0.5,
                    'platform_risk': risk_factors[2] if len(risk_factors) > 2 else 0.5,
                    'temporal_risk': risk_factors[3] if len(risk_factors) > 3 else 0.5,
                },
                'recommendations': self._generate_risk_recommendations(risk_score, content_metadata)
            }
            
        except Exception as e:
            logger.error(f"Error predicting piracy risk: {e}")
            return {
                'risk_score': 0.5,
                'confidence': 0.1,
                'error': str(e)
            }
    
    def _generate_risk_recommendations(
        self,
        risk_score: float,
        content_metadata: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on risk score"""
        recommendations = []
        
        if risk_score >= 0.7:
            recommendations.extend([
                "Enable intensive monitoring for this content",
                "Consider adding visible watermarks",
                "Set up real-time alerts for this content",
                "Monitor social media platforms closely"
            ])
        elif risk_score >= 0.5:
            recommendations.extend([
                "Enable regular monitoring",
                "Consider adding discrete watermarks",
                "Monitor major platforms daily"
            ])
        else:
            recommendations.extend([
                "Standard monitoring should be sufficient",
                "Weekly platform checks recommended"
            ])
        
        # Content-specific recommendations
        content_type = content_metadata.get('type', '').lower()
        if 'video' in content_type:
            recommendations.append("Consider video fingerprinting for rapid detection")
        elif 'image' in content_type:
            recommendations.append("Use perceptual hashing for similar image detection")
        
        return recommendations