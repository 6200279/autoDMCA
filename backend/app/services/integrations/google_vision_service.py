"""
Google Vision API Service Integration

Provides advanced image analysis capabilities for content protection:
- Text detection and OCR
- Object and scene detection  
- Explicit content detection
- Face detection and landmark recognition
- Label detection for content categorization
"""

import logging
import asyncio
import base64
import io
from typing import Dict, List, Optional, Any, Tuple, Union
from PIL import Image
import json
from datetime import datetime

try:
    from google.cloud import vision
    from google.oauth2 import service_account
    import google.auth.exceptions
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleVisionError(Exception):
    """Google Vision API specific errors"""
    pass


class GoogleVisionService:
    """
    Google Vision API service providing comprehensive image analysis:
    - Safe search detection (explicit content)
    - Text detection and OCR
    - Object and scene detection
    - Face detection and analysis
    - Label detection and categorization
    - Logo detection
    - Landmark detection
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_VISION_API_KEY', None)
        self.credentials_path = getattr(settings, 'GOOGLE_VISION_CREDENTIALS_PATH', None)
        self.credentials_json = getattr(settings, 'GOOGLE_VISION_CREDENTIALS_JSON', None)
        
        self.client = None
        self.available = False
        
        if not VISION_AVAILABLE:
            logger.warning("Google Vision API library not available")
            return
        
        try:
            # Initialize client with different credential methods
            if self.credentials_path:
                # Service account key file
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path
                )
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
            elif self.credentials_json:
                # Service account key as JSON string
                credentials_info = json.loads(self.credentials_json)
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_info
                )
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
            elif self.api_key:
                # API key authentication (limited functionality)
                from google.auth.credentials import AnonymousCredentials
                self.client = vision.ImageAnnotatorClient(
                    client_options={"api_key": self.api_key}
                )
            else:
                # Use default credentials (environment variables, etc.)
                self.client = vision.ImageAnnotatorClient()
            
            self.available = True
            logger.info("Google Vision API service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Vision API: {e}")
            self.client = None
            self.available = False
    
    def _prepare_image(self, image_data: Union[bytes, str]) -> vision.Image:
        """Prepare image data for Vision API."""
        if isinstance(image_data, str):
            # Base64 encoded image
            image_content = base64.b64decode(image_data)
        else:
            # Raw bytes
            image_content = image_data
        
        return vision.Image(content=image_content)
    
    async def detect_explicit_content(
        self,
        image_data: Union[bytes, str],
        include_details: bool = False
    ) -> Dict[str, Any]:
        """
        Detect explicit or inappropriate content in images.
        
        Args:
            image_data: Image as bytes or base64 string
            include_details: Include detailed probability scores
            
        Returns:
            Dict with explicit content analysis results
        """
        if not self.available:
            return {
                'error': 'Google Vision API not available',
                'safe': True,  # Default to safe when unavailable
                'confidence': 0.0
            }
        
        try:
            image = self._prepare_image(image_data)
            
            # Perform safe search detection
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.safe_search_detection(image=image)
            )
            
            safe_search = response.safe_search_annotation
            
            # Convert likelihood enum to scores
            likelihood_scores = {
                vision.Likelihood.UNKNOWN: 0,
                vision.Likelihood.VERY_UNLIKELY: 1,
                vision.Likelihood.UNLIKELY: 2,
                vision.Likelihood.POSSIBLE: 3,
                vision.Likelihood.LIKELY: 4,
                vision.Likelihood.VERY_LIKELY: 5
            }
            
            # Analyze different types of explicit content
            adult_score = likelihood_scores.get(safe_search.adult, 0)
            spoof_score = likelihood_scores.get(safe_search.spoof, 0)
            medical_score = likelihood_scores.get(safe_search.medical, 0)
            violence_score = likelihood_scores.get(safe_search.violence, 0)
            racy_score = likelihood_scores.get(safe_search.racy, 0)
            
            # Calculate overall risk score (0-5 scale)
            max_score = max(adult_score, violence_score, racy_score)
            
            # Determine if content is safe (threshold can be configured)
            safety_threshold = 3  # POSSIBLE or higher is flagged
            is_safe = max_score < safety_threshold
            
            result = {
                'safe': is_safe,
                'risk_level': 'high' if max_score >= 4 else 'medium' if max_score >= 3 else 'low',
                'confidence': max_score / 5.0,  # Convert to 0-1 scale
                'detected_at': datetime.utcnow().isoformat()
            }
            
            if include_details:
                result['details'] = {
                    'adult_content': {
                        'likelihood': safe_search.adult.name,
                        'score': adult_score
                    },
                    'violent_content': {
                        'likelihood': safe_search.violence.name,
                        'score': violence_score
                    },
                    'racy_content': {
                        'likelihood': safe_search.racy.name,
                        'score': racy_score
                    },
                    'medical_content': {
                        'likelihood': safe_search.medical.name,
                        'score': medical_score
                    },
                    'spoof_content': {
                        'likelihood': safe_search.spoof.name,
                        'score': spoof_score
                    }
                }
            
            logger.info(f"Explicit content detection completed. Safe: {is_safe}, Risk: {result['risk_level']}")
            return result
            
        except Exception as e:
            logger.error(f"Google Vision explicit content detection error: {e}")
            return {
                'error': str(e),
                'safe': True,  # Default to safe on error
                'confidence': 0.0
            }
    
    async def detect_text(
        self,
        image_data: Union[bytes, str],
        language_hints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect and extract text from images using OCR.
        
        Args:
            image_data: Image as bytes or base64 string
            language_hints: List of language codes to improve detection
            
        Returns:
            Dict with detected text and metadata
        """
        if not self.available:
            return {
                'error': 'Google Vision API not available',
                'text': '',
                'confidence': 0.0
            }
        
        try:
            image = self._prepare_image(image_data)
            
            # Configure image context if language hints provided
            image_context = None
            if language_hints:
                image_context = vision.ImageContext(language_hints=language_hints)
            
            # Perform text detection
            if image_context:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.text_detection(image=image, image_context=image_context)
                )
            else:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.text_detection(image=image)
                )
            
            texts = response.text_annotations
            
            if not texts:
                return {
                    'text': '',
                    'confidence': 0.0,
                    'word_count': 0,
                    'blocks': []
                }
            
            # First annotation contains the entire detected text
            full_text = texts[0].description
            
            # Extract individual words/blocks with positions
            text_blocks = []
            for text in texts[1:]:  # Skip the first one (full text)
                vertices = [(vertex.x, vertex.y) for vertex in text.bounding_poly.vertices]
                text_blocks.append({
                    'text': text.description,
                    'bounding_box': vertices,
                    'confidence': getattr(text, 'confidence', 0.9)  # Vision API doesn't always provide confidence
                })
            
            # Calculate average confidence
            avg_confidence = sum(block.get('confidence', 0.9) for block in text_blocks) / len(text_blocks) if text_blocks else 0.9
            
            result = {
                'text': full_text,
                'confidence': avg_confidence,
                'word_count': len(full_text.split()) if full_text else 0,
                'character_count': len(full_text) if full_text else 0,
                'blocks': text_blocks,
                'detected_at': datetime.utcnow().isoformat()
            }
            
            # Add text analysis
            if full_text:
                result['analysis'] = self._analyze_detected_text(full_text)
            
            logger.info(f"Text detection completed. Found {len(text_blocks)} text blocks")
            return result
            
        except Exception as e:
            logger.error(f"Google Vision text detection error: {e}")
            return {
                'error': str(e),
                'text': '',
                'confidence': 0.0
            }
    
    async def detect_objects(
        self,
        image_data: Union[bytes, str],
        max_results: int = 50
    ) -> Dict[str, Any]:
        """
        Detect objects and scenes in images.
        
        Args:
            image_data: Image as bytes or base64 string
            max_results: Maximum number of objects to detect
            
        Returns:
            Dict with detected objects and their properties
        """
        if not self.available:
            return {
                'error': 'Google Vision API not available',
                'objects': [],
                'labels': []
            }
        
        try:
            image = self._prepare_image(image_data)
            
            # Perform object localization and label detection
            objects_response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.object_localization(image=image)
            )
            
            labels_response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.label_detection(image=image, max_results=max_results)
            )
            
            # Process detected objects
            objects = []
            for obj in objects_response.localized_object_annotations:
                vertices = [(vertex.x, vertex.y) for vertex in obj.bounding_poly.normalized_vertices]
                objects.append({
                    'name': obj.name,
                    'confidence': obj.score,
                    'bounding_box': vertices,
                    'mid': obj.mid  # Machine-generated identifier
                })
            
            # Process detected labels
            labels = []
            for label in labels_response.label_annotations:
                labels.append({
                    'description': label.description,
                    'confidence': label.score,
                    'topicality': getattr(label, 'topicality', 0.0),
                    'mid': label.mid
                })
            
            result = {
                'objects': objects,
                'labels': labels,
                'object_count': len(objects),
                'label_count': len(labels),
                'detected_at': datetime.utcnow().isoformat(),
                'analysis': {
                    'primary_subjects': [obj['name'] for obj in objects[:3]],
                    'main_categories': [label['description'] for label in labels[:5]],
                    'scene_confidence': max([label['confidence'] for label in labels]) if labels else 0.0
                }
            }
            
            logger.info(f"Object detection completed. Found {len(objects)} objects and {len(labels)} labels")
            return result
            
        except Exception as e:
            logger.error(f"Google Vision object detection error: {e}")
            return {
                'error': str(e),
                'objects': [],
                'labels': []
            }
    
    async def detect_faces(
        self,
        image_data: Union[bytes, str],
        include_landmarks: bool = True,
        include_attributes: bool = True
    ) -> Dict[str, Any]:
        """
        Detect faces and analyze facial features.
        
        Args:
            image_data: Image as bytes or base64 string
            include_landmarks: Include facial landmark detection
            include_attributes: Include face attributes (emotions, etc.)
            
        Returns:
            Dict with detected faces and their properties
        """
        if not self.available:
            return {
                'error': 'Google Vision API not available',
                'faces': [],
                'face_count': 0
            }
        
        try:
            image = self._prepare_image(image_data)
            
            # Perform face detection
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.face_detection(image=image)
            )
            
            faces = response.face_annotations
            
            if not faces:
                return {
                    'faces': [],
                    'face_count': 0,
                    'detected_at': datetime.utcnow().isoformat()
                }
            
            detected_faces = []
            for face in faces:
                face_data = {
                    'detection_confidence': face.detection_confidence,
                    'landmarking_confidence': face.landmarking_confidence if include_landmarks else None,
                    'bounding_box': [
                        (vertex.x, vertex.y) for vertex in face.bounding_poly.vertices
                    ],
                    'fd_bounding_box': {
                        'center': (face.fd_bounding_poly.vertices[0].x, face.fd_bounding_poly.vertices[0].y),
                        'width': face.fd_bounding_poly.vertices[2].x - face.fd_bounding_poly.vertices[0].x,
                        'height': face.fd_bounding_poly.vertices[2].y - face.fd_bounding_poly.vertices[0].y
                    }
                }
                
                if include_attributes:
                    # Convert likelihood enums to readable strings
                    def likelihood_to_string(likelihood):
                        return likelihood.name.lower().replace('_', ' ')
                    
                    face_data['attributes'] = {
                        'joy_likelihood': likelihood_to_string(face.joy_likelihood),
                        'sorrow_likelihood': likelihood_to_string(face.sorrow_likelihood),
                        'anger_likelihood': likelihood_to_string(face.anger_likelihood),
                        'surprise_likelihood': likelihood_to_string(face.surprise_likelihood),
                        'under_exposed_likelihood': likelihood_to_string(face.under_exposed_likelihood),
                        'blurred_likelihood': likelihood_to_string(face.blurred_likelihood),
                        'headwear_likelihood': likelihood_to_string(face.headwear_likelihood),
                        'tilt_angles': {
                            'roll': face.roll_angle,
                            'pan': face.pan_angle,
                            'tilt': face.tilt_angle
                        }
                    }
                
                if include_landmarks and face.landmarks:
                    landmarks = {}
                    for landmark in face.landmarks:
                        landmark_type = landmark.type_.name.lower()
                        landmarks[landmark_type] = {
                            'x': landmark.position.x,
                            'y': landmark.position.y,
                            'z': landmark.position.z
                        }
                    face_data['landmarks'] = landmarks
                
                detected_faces.append(face_data)
            
            # Analyze face detection results
            avg_confidence = sum(face['detection_confidence'] for face in detected_faces) / len(detected_faces)
            
            result = {
                'faces': detected_faces,
                'face_count': len(detected_faces),
                'average_confidence': avg_confidence,
                'detected_at': datetime.utcnow().isoformat(),
                'analysis': {
                    'multiple_faces': len(detected_faces) > 1,
                    'high_quality_faces': len([f for f in detected_faces if f['detection_confidence'] > 0.8]),
                    'dominant_emotion': self._analyze_dominant_emotion(detected_faces) if include_attributes else None
                }
            }
            
            logger.info(f"Face detection completed. Found {len(detected_faces)} faces")
            return result
            
        except Exception as e:
            logger.error(f"Google Vision face detection error: {e}")
            return {
                'error': str(e),
                'faces': [],
                'face_count': 0
            }
    
    async def detect_logos(
        self,
        image_data: Union[bytes, str],
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Detect logos and brands in images.
        
        Args:
            image_data: Image as bytes or base64 string
            max_results: Maximum number of logos to detect
            
        Returns:
            Dict with detected logos and their properties
        """
        if not self.available:
            return {
                'error': 'Google Vision API not available',
                'logos': []
            }
        
        try:
            image = self._prepare_image(image_data)
            
            # Perform logo detection
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.logo_detection(image=image, max_results=max_results)
            )
            
            logos = response.logo_annotations
            
            detected_logos = []
            for logo in logos:
                vertices = [(vertex.x, vertex.y) for vertex in logo.bounding_poly.vertices]
                detected_logos.append({
                    'description': logo.description,
                    'confidence': logo.score,
                    'bounding_box': vertices,
                    'mid': logo.mid
                })
            
            result = {
                'logos': detected_logos,
                'logo_count': len(detected_logos),
                'detected_at': datetime.utcnow().isoformat(),
                'brands_detected': [logo['description'] for logo in detected_logos]
            }
            
            logger.info(f"Logo detection completed. Found {len(detected_logos)} logos")
            return result
            
        except Exception as e:
            logger.error(f"Google Vision logo detection error: {e}")
            return {
                'error': str(e),
                'logos': []
            }
    
    async def analyze_image_comprehensive(
        self,
        image_data: Union[bytes, str],
        include_text: bool = True,
        include_objects: bool = True,
        include_faces: bool = True,
        include_logos: bool = True,
        include_explicit_check: bool = True
    ) -> Dict[str, Any]:
        """
        Perform comprehensive image analysis using multiple Vision API features.
        
        Args:
            image_data: Image as bytes or base64 string
            include_text: Include text detection
            include_objects: Include object detection
            include_faces: Include face detection
            include_logos: Include logo detection
            include_explicit_check: Include explicit content detection
            
        Returns:
            Dict with comprehensive analysis results
        """
        if not self.available:
            return {
                'error': 'Google Vision API not available',
                'analysis_complete': False
            }
        
        try:
            # Perform all requested analyses concurrently
            tasks = []
            
            if include_explicit_check:
                tasks.append(self.detect_explicit_content(image_data, include_details=True))
            
            if include_text:
                tasks.append(self.detect_text(image_data))
            
            if include_objects:
                tasks.append(self.detect_objects(image_data))
            
            if include_faces:
                tasks.append(self.detect_faces(image_data))
            
            if include_logos:
                tasks.append(self.detect_logos(image_data))
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            comprehensive_analysis = {
                'analyzed_at': datetime.utcnow().isoformat(),
                'analysis_complete': True,
                'features_analyzed': []
            }
            
            result_index = 0
            
            if include_explicit_check:
                explicit_result = results[result_index] if not isinstance(results[result_index], Exception) else {'error': str(results[result_index])}
                comprehensive_analysis['explicit_content'] = explicit_result
                comprehensive_analysis['features_analyzed'].append('explicit_content')
                result_index += 1
            
            if include_text:
                text_result = results[result_index] if not isinstance(results[result_index], Exception) else {'error': str(results[result_index])}
                comprehensive_analysis['text_detection'] = text_result
                comprehensive_analysis['features_analyzed'].append('text_detection')
                result_index += 1
            
            if include_objects:
                objects_result = results[result_index] if not isinstance(results[result_index], Exception) else {'error': str(results[result_index])}
                comprehensive_analysis['object_detection'] = objects_result
                comprehensive_analysis['features_analyzed'].append('object_detection')
                result_index += 1
            
            if include_faces:
                faces_result = results[result_index] if not isinstance(results[result_index], Exception) else {'error': str(results[result_index])}
                comprehensive_analysis['face_detection'] = faces_result
                comprehensive_analysis['features_analyzed'].append('face_detection')
                result_index += 1
            
            if include_logos:
                logos_result = results[result_index] if not isinstance(results[result_index], Exception) else {'error': str(results[result_index])}
                comprehensive_analysis['logo_detection'] = logos_result
                comprehensive_analysis['features_analyzed'].append('logo_detection')
            
            # Generate summary insights
            comprehensive_analysis['insights'] = self._generate_analysis_insights(comprehensive_analysis)
            
            logger.info(f"Comprehensive image analysis completed with {len(comprehensive_analysis['features_analyzed'])} features")
            return comprehensive_analysis
            
        except Exception as e:
            logger.error(f"Google Vision comprehensive analysis error: {e}")
            return {
                'error': str(e),
                'analysis_complete': False
            }
    
    def _analyze_detected_text(self, text: str) -> Dict[str, Any]:
        """Analyze detected text for insights."""
        words = text.split()
        
        # Basic text analysis
        analysis = {
            'word_count': len(words),
            'character_count': len(text),
            'sentence_count': text.count('.') + text.count('!') + text.count('?'),
            'contains_urls': 'http' in text.lower() or 'www.' in text.lower(),
            'contains_email': '@' in text and '.' in text,
            'contains_phone': any(word.replace('-', '').replace('(', '').replace(')', '').replace(' ', '').isdigit() and len(word.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')) >= 10 for word in words),
            'language_detected': 'english',  # Simplified - could use language detection
            'readability': 'medium'  # Simplified assessment
        }
        
        return analysis
    
    def _analyze_dominant_emotion(self, faces: List[Dict[str, Any]]) -> Optional[str]:
        """Analyze dominant emotion across detected faces."""
        if not faces:
            return None
        
        emotion_scores = {
            'joy': 0,
            'sorrow': 0,
            'anger': 0,
            'surprise': 0
        }
        
        likelihood_values = {
            'unknown': 0,
            'very unlikely': 1,
            'unlikely': 2,
            'possible': 3,
            'likely': 4,
            'very likely': 5
        }
        
        for face in faces:
            if 'attributes' in face:
                attrs = face['attributes']
                emotion_scores['joy'] += likelihood_values.get(attrs.get('joy_likelihood', 'unknown'), 0)
                emotion_scores['sorrow'] += likelihood_values.get(attrs.get('sorrow_likelihood', 'unknown'), 0)
                emotion_scores['anger'] += likelihood_values.get(attrs.get('anger_likelihood', 'unknown'), 0)
                emotion_scores['surprise'] += likelihood_values.get(attrs.get('surprise_likelihood', 'unknown'), 0)
        
        if max(emotion_scores.values()) > 0:
            return max(emotion_scores, key=emotion_scores.get)
        
        return None
    
    def _generate_analysis_insights(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from comprehensive analysis."""
        insights = {
            'content_type': 'unknown',
            'risk_level': 'low',
            'contains_people': False,
            'contains_text': False,
            'contains_brands': False,
            'potential_issues': [],
            'recommendations': []
        }
        
        # Analyze explicit content
        if 'explicit_content' in analysis and 'error' not in analysis['explicit_content']:
            explicit = analysis['explicit_content']
            if not explicit.get('safe', True):
                insights['risk_level'] = explicit.get('risk_level', 'medium')
                insights['potential_issues'].append('Explicit content detected')
                insights['recommendations'].append('Review content before publishing')
        
        # Analyze text content
        if 'text_detection' in analysis and 'error' not in analysis['text_detection']:
            text_data = analysis['text_detection']
            if text_data.get('text'):
                insights['contains_text'] = True
                insights['content_type'] = 'text_image'
                
                if text_data.get('analysis', {}).get('contains_urls'):
                    insights['potential_issues'].append('Contains URLs')
                if text_data.get('analysis', {}).get('contains_email'):
                    insights['potential_issues'].append('Contains email addresses')
        
        # Analyze faces
        if 'face_detection' in analysis and 'error' not in analysis['face_detection']:
            face_data = analysis['face_detection']
            if face_data.get('face_count', 0) > 0:
                insights['contains_people'] = True
                insights['content_type'] = 'portrait' if face_data['face_count'] == 1 else 'group_photo'
                
                if face_data.get('analysis', {}).get('multiple_faces'):
                    insights['recommendations'].append('Multiple faces detected - verify all subjects consent')
        
        # Analyze logos/brands
        if 'logo_detection' in analysis and 'error' not in analysis['logo_detection']:
            logo_data = analysis['logo_detection']
            if logo_data.get('logo_count', 0) > 0:
                insights['contains_brands'] = True
                insights['potential_issues'].append('Brand logos detected')
                insights['recommendations'].append('Verify trademark usage rights')
        
        # Analyze objects for content type refinement
        if 'object_detection' in analysis and 'error' not in analysis['object_detection']:
            object_data = analysis['object_detection']
            if object_data.get('labels'):
                top_labels = [label['description'].lower() for label in object_data['labels'][:5]]
                
                if any(label in ['vehicle', 'car', 'motorcycle', 'truck'] for label in top_labels):
                    insights['content_type'] = 'automotive'
                elif any(label in ['food', 'meal', 'restaurant'] for label in top_labels):
                    insights['content_type'] = 'food'
                elif any(label in ['clothing', 'fashion', 'apparel'] for label in top_labels):
                    insights['content_type'] = 'fashion'
                elif any(label in ['nature', 'landscape', 'outdoor'] for label in top_labels):
                    insights['content_type'] = 'nature'
        
        return insights
    
    async def batch_analyze_images(
        self,
        image_list: List[Dict[str, Union[bytes, str]]],
        analysis_config: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """
        Analyze multiple images in batch for efficiency.
        
        Args:
            image_list: List of dicts with 'image_data' and optional 'id'
            analysis_config: Configuration for which analyses to perform
            
        Returns:
            Dict with batch analysis results
        """
        if not self.available:
            return {
                'error': 'Google Vision API not available',
                'results': []
            }
        
        config = analysis_config or {
            'include_text': True,
            'include_objects': True,
            'include_faces': True,
            'include_logos': False,
            'include_explicit_check': True
        }
        
        try:
            # Analyze images concurrently (with reasonable batch size limit)
            batch_size = 10  # Adjust based on API limits
            all_results = []
            
            for i in range(0, len(image_list), batch_size):
                batch = image_list[i:i + batch_size]
                
                # Create tasks for this batch
                tasks = []
                for item in batch:
                    image_data = item['image_data']
                    task = self.analyze_image_comprehensive(
                        image_data,
                        **config
                    )
                    tasks.append(task)
                
                # Execute batch
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Add results with IDs
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        result = {'error': str(result)}
                    
                    result['image_id'] = batch[j].get('id', f'image_{i + j}')
                    all_results.append(result)
            
            # Generate batch summary
            successful_analyses = [r for r in all_results if 'error' not in r]
            failed_analyses = [r for r in all_results if 'error' in r]
            
            batch_summary = {
                'total_images': len(image_list),
                'successful_analyses': len(successful_analyses),
                'failed_analyses': len(failed_analyses),
                'success_rate': len(successful_analyses) / len(image_list) if image_list else 0,
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
            return {
                'summary': batch_summary,
                'results': all_results,
                'config_used': config
            }
            
        except Exception as e:
            logger.error(f"Google Vision batch analysis error: {e}")
            return {
                'error': str(e),
                'results': []
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Check Google Vision API service health."""
        try:
            if not self.available:
                return {
                    'service': 'google_vision',
                    'status': 'unavailable',
                    'message': 'Google Vision API not configured or library unavailable'
                }
            
            # Try a simple operation to verify API connectivity
            # Note: This would make an actual API call in production
            return {
                'service': 'google_vision',
                'status': 'healthy',
                'client_initialized': self.client is not None,
                'credentials_configured': bool(self.credentials_path or self.credentials_json or self.api_key),
                'features_available': [
                    'text_detection',
                    'object_detection',
                    'face_detection',
                    'logo_detection',
                    'explicit_content_detection'
                ]
            }
            
        except Exception as e:
            return {
                'service': 'google_vision',
                'status': 'unhealthy',
                'error': str(e)
            }


# Create singleton instance
google_vision_service = GoogleVisionService()


# Convenience functions for common operations
async def analyze_content_safety(image_data: Union[bytes, str]) -> Dict[str, Any]:
    """Quick safety analysis for content moderation."""
    return await google_vision_service.detect_explicit_content(image_data, include_details=True)


async def extract_image_text(image_data: Union[bytes, str], languages: Optional[List[str]] = None) -> str:
    """Extract text from image and return as string."""
    result = await google_vision_service.detect_text(image_data, language_hints=languages)
    return result.get('text', '') if 'error' not in result else ''


async def detect_faces_in_image(image_data: Union[bytes, str]) -> List[Dict[str, Any]]:
    """Detect faces and return simplified face data."""
    result = await google_vision_service.detect_faces(image_data, include_attributes=True)
    return result.get('faces', []) if 'error' not in result else []


async def analyze_image_for_piracy_detection(image_data: Union[bytes, str]) -> Dict[str, Any]:
    """Analyze image specifically for piracy detection purposes."""
    analysis = await google_vision_service.analyze_image_comprehensive(
        image_data,
        include_text=True,
        include_faces=True,
        include_logos=True,
        include_explicit_check=True,
        include_objects=False  # Skip objects for faster processing
    )
    
    if 'error' in analysis:
        return analysis
    
    # Extract relevant information for piracy detection
    piracy_indicators = {
        'has_faces': analysis.get('face_detection', {}).get('face_count', 0) > 0,
        'has_text': bool(analysis.get('text_detection', {}).get('text', '')),
        'has_brands': analysis.get('logo_detection', {}).get('logo_count', 0) > 0,
        'is_explicit': not analysis.get('explicit_content', {}).get('safe', True),
        'risk_score': 0.0
    }
    
    # Calculate risk score based on detected elements
    risk_factors = 0
    if piracy_indicators['has_faces']:
        risk_factors += 3  # Faces are high priority for piracy detection
    if piracy_indicators['has_text']:
        risk_factors += 1
    if piracy_indicators['has_brands']:
        risk_factors += 2
    if piracy_indicators['is_explicit']:
        risk_factors += 4
    
    piracy_indicators['risk_score'] = min(risk_factors / 10.0, 1.0)  # Normalize to 0-1
    piracy_indicators['priority'] = 'high' if risk_factors >= 7 else 'medium' if risk_factors >= 4 else 'low'
    
    return piracy_indicators