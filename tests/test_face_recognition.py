"""
Tests for face recognition processor.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile
import os

from scanning.processors.face_recognition_processor import (
    FaceRecognitionProcessor,
    FaceEncoding,
    FaceMatch,
    FaceProcessingResult
)


class TestFaceRecognitionProcessor:
    """Test face recognition processor functionality."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, test_settings):
        """Test processor initialization."""
        processor = FaceRecognitionProcessor(test_settings)
        
        # Mock face_recognition and cv2 imports
        with patch('scanning.processors.face_recognition_processor.face_recognition'), \
             patch('scanning.processors.face_recognition_processor.cv2'):
            await processor.initialize()
            
            assert processor._models_loaded
            assert processor.session is not None
    
    @pytest.mark.asyncio
    async def test_add_person_success(self, test_settings, sample_face_image):
        """Test adding a person with reference images."""
        processor = FaceRecognitionProcessor(test_settings)
        
        # Mock face recognition functions
        mock_face_locations = [(0, 100, 100, 0)]  # Mock face location
        mock_face_encodings = [np.random.random(128)]  # Mock 128-dim encoding
        
        with patch('scanning.processors.face_recognition_processor.face_recognition') as mock_fr, \
             patch('scanning.processors.face_recognition_processor.cv2'):
            
            mock_fr.face_locations.return_value = mock_face_locations
            mock_fr.face_encodings.return_value = mock_face_encodings
            
            await processor.initialize()
            
            # Add person
            encodings_added = await processor.add_person(
                person_id="test_person",
                reference_images=[sample_face_image]
            )
            
            assert encodings_added == 1
            assert "test_person" in processor.known_encodings
            assert len(processor.known_encodings["test_person"]) == 1
    
    @pytest.mark.asyncio
    async def test_add_person_no_faces(self, test_settings, sample_image):
        """Test adding person with image containing no faces."""
        processor = FaceRecognitionProcessor(test_settings)
        
        with patch('scanning.processors.face_recognition_processor.face_recognition') as mock_fr, \
             patch('scanning.processors.face_recognition_processor.cv2'):
            
            # No faces detected
            mock_fr.face_locations.return_value = []
            
            await processor.initialize()
            
            encodings_added = await processor.add_person(
                person_id="test_person",
                reference_images=[sample_image]
            )
            
            assert encodings_added == 0
            assert "test_person" not in processor.known_encodings
    
    @pytest.mark.asyncio
    async def test_process_image_with_match(self, test_settings, sample_face_image):
        """Test processing image that matches known person."""
        processor = FaceRecognitionProcessor(test_settings)
        
        # Mock face recognition
        mock_face_locations = [(0, 100, 100, 0)]
        mock_face_encodings = [np.random.random(128)]
        
        with patch('scanning.processors.face_recognition_processor.face_recognition') as mock_fr, \
             patch('scanning.processors.face_recognition_processor.cv2'):
            
            mock_fr.face_locations.return_value = mock_face_locations
            mock_fr.face_encodings.return_value = mock_face_encodings
            mock_fr.face_distance.return_value = [0.3]  # Good match
            
            await processor.initialize()
            
            # Add known person
            await processor.add_person(
                person_id="test_person",
                reference_images=[sample_face_image]
            )
            
            # Process test image
            result = await processor.process_image(
                sample_face_image,
                person_ids=["test_person"]
            )
            
            assert isinstance(result, FaceProcessingResult)
            assert result.faces_found == 1
            assert result.has_matches
            assert result.best_match is not None
            assert result.best_match.person_id == "test_person"
    
    @pytest.mark.asyncio
    async def test_process_image_no_match(self, test_settings, sample_face_image):
        """Test processing image with no matching faces."""
        processor = FaceRecognitionProcessor(test_settings)
        
        mock_face_locations = [(0, 100, 100, 0)]
        mock_face_encodings = [np.random.random(128)]
        
        with patch('scanning.processors.face_recognition_processor.face_recognition') as mock_fr, \
             patch('scanning.processors.face_recognition_processor.cv2'):
            
            mock_fr.face_locations.return_value = mock_face_locations
            mock_fr.face_encodings.return_value = mock_face_encodings
            mock_fr.face_distance.return_value = [0.8]  # Poor match
            
            await processor.initialize()
            
            # Add known person
            await processor.add_person(
                person_id="test_person",
                reference_images=[sample_face_image]
            )
            
            # Process different image
            result = await processor.process_image(
                sample_face_image,
                person_ids=["test_person"]
            )
            
            assert result.faces_found == 1
            assert not result.has_matches or result.best_match.distance > 0.6
    
    @pytest.mark.asyncio
    async def test_process_image_from_url(self, test_settings):
        """Test processing image from URL."""
        processor = FaceRecognitionProcessor(test_settings)
        
        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read.return_value = b"fake_image_data"
        
        with patch('scanning.processors.face_recognition_processor.face_recognition') as mock_fr, \
             patch('scanning.processors.face_recognition_processor.cv2') as mock_cv2:
            
            mock_fr.face_locations.return_value = []
            mock_cv2.imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
            mock_cv2.cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
            
            await processor.initialize()
            
            # Mock session.get
            processor.session.get.return_value.__aenter__.return_value = mock_response
            
            result = await processor.process_image("https://example.com/image.jpg")
            
            assert isinstance(result, FaceProcessingResult)
            assert result.image_url == "https://example.com/image.jpg"
    
    @pytest.mark.asyncio
    async def test_bulk_process_images(self, test_settings, sample_face_image):
        """Test bulk image processing."""
        processor = FaceRecognitionProcessor(test_settings)
        
        with patch('scanning.processors.face_recognition_processor.face_recognition') as mock_fr, \
             patch('scanning.processors.face_recognition_processor.cv2'):
            
            mock_fr.face_locations.return_value = [(0, 100, 100, 0)]
            mock_fr.face_encodings.return_value = [np.random.random(128)]
            
            await processor.initialize()
            
            # Add person
            await processor.add_person(
                person_id="test_person",
                reference_images=[sample_face_image]
            )
            
            # Process multiple images
            image_urls = ["image1.jpg", "image2.jpg"]
            results = await processor.bulk_process_images(
                image_urls,
                person_ids=["test_person"],
                max_concurrent=2
            )
            
            assert len(results) == 2
            assert "image1.jpg" in results
            assert "image2.jpg" in results
    
    @pytest.mark.asyncio
    async def test_remove_person(self, test_settings, sample_face_image):
        """Test removing a person from the database."""
        processor = FaceRecognitionProcessor(test_settings)
        
        with patch('scanning.processors.face_recognition_processor.face_recognition') as mock_fr, \
             patch('scanning.processors.face_recognition_processor.cv2'):
            
            mock_fr.face_locations.return_value = [(0, 100, 100, 0)]
            mock_fr.face_encodings.return_value = [np.random.random(128)]
            
            await processor.initialize()
            
            # Add person
            await processor.add_person(
                person_id="test_person",
                reference_images=[sample_face_image]
            )
            
            assert "test_person" in processor.known_encodings
            
            # Remove person
            success = await processor.remove_person("test_person")
            
            assert success
            assert "test_person" not in processor.known_encodings
    
    @pytest.mark.asyncio
    async def test_save_load_encodings(self, test_settings, sample_face_image, temp_dir):
        """Test saving and loading face encodings."""
        processor = FaceRecognitionProcessor(test_settings)
        
        with patch('scanning.processors.face_recognition_processor.face_recognition') as mock_fr, \
             patch('scanning.processors.face_recognition_processor.cv2'):
            
            mock_fr.face_locations.return_value = [(0, 100, 100, 0)]
            mock_fr.face_encodings.return_value = [np.random.random(128)]
            
            await processor.initialize()
            
            # Add person
            await processor.add_person(
                person_id="test_person", 
                reference_images=[sample_face_image]
            )
            
            # Save encodings
            save_path = temp_dir / "encodings.pkl"
            success = await processor.save_encodings(str(save_path))
            assert success
            assert save_path.exists()
            
            # Clear encodings
            processor.known_encodings.clear()
            assert len(processor.known_encodings) == 0
            
            # Load encodings
            success = await processor.load_encodings(str(save_path))
            assert success
            assert "test_person" in processor.known_encodings
            assert len(processor.known_encodings["test_person"]) == 1


class TestFaceEncoding:
    """Test FaceEncoding dataclass."""
    
    def test_face_encoding_creation(self):
        """Test creating FaceEncoding object."""
        encoding = np.random.random(128)
        face_encoding = FaceEncoding(
            encoding=encoding,
            person_id="test_person",
            confidence=0.95
        )
        
        assert np.array_equal(face_encoding.encoding, encoding)
        assert face_encoding.person_id == "test_person"
        assert face_encoding.confidence == 0.95
    
    def test_face_encoding_with_list(self):
        """Test FaceEncoding with list input (should convert to numpy)."""
        encoding_list = [0.1, 0.2, 0.3, 0.4]
        face_encoding = FaceEncoding(
            encoding=encoding_list,
            person_id="test_person"
        )
        
        assert isinstance(face_encoding.encoding, np.ndarray)
        assert np.array_equal(face_encoding.encoding, np.array(encoding_list))


class TestFaceMatch:
    """Test FaceMatch dataclass."""
    
    def test_face_match_creation(self):
        """Test creating FaceMatch object."""
        match = FaceMatch(
            person_id="test_person",
            confidence=0.85,
            distance=0.25
        )
        
        assert match.person_id == "test_person"
        assert match.confidence == 0.85
        assert match.distance == 0.25
    
    def test_is_match_property(self):
        """Test is_match property logic."""
        # Good match
        good_match = FaceMatch(
            person_id="test_person",
            confidence=0.8,
            distance=0.3
        )
        assert good_match.is_match
        
        # Poor match (high distance)
        poor_match = FaceMatch(
            person_id="test_person",
            confidence=0.8,
            distance=0.7
        )
        assert not poor_match.is_match
        
        # Poor match (low confidence)
        low_confidence_match = FaceMatch(
            person_id="test_person",
            confidence=0.3,
            distance=0.4
        )
        assert not low_confidence_match.is_match


class TestFaceProcessingResult:
    """Test FaceProcessingResult dataclass."""
    
    def test_processing_result_creation(self):
        """Test creating FaceProcessingResult."""
        matches = [
            FaceMatch(person_id="person1", confidence=0.8, distance=0.2),
            FaceMatch(person_id="person2", confidence=0.6, distance=0.4)
        ]
        
        result = FaceProcessingResult(
            image_url="test.jpg",
            faces_found=2,
            matches=matches,
            processing_time=0.5
        )
        
        assert result.image_url == "test.jpg"
        assert result.faces_found == 2
        assert len(result.matches) == 2
        assert result.processing_time == 0.5
    
    def test_has_matches_property(self):
        """Test has_matches property."""
        # With good matches
        good_matches = [FaceMatch(person_id="test", confidence=0.8, distance=0.2)]
        result_with_matches = FaceProcessingResult(
            image_url="test.jpg",
            faces_found=1,
            matches=good_matches
        )
        assert result_with_matches.has_matches
        
        # With poor matches
        poor_matches = [FaceMatch(person_id="test", confidence=0.2, distance=0.8)]
        result_no_matches = FaceProcessingResult(
            image_url="test.jpg",
            faces_found=1, 
            matches=poor_matches
        )
        assert not result_no_matches.has_matches
    
    def test_best_match_property(self):
        """Test best_match property."""
        matches = [
            FaceMatch(person_id="person1", confidence=0.8, distance=0.3),
            FaceMatch(person_id="person2", confidence=0.9, distance=0.2),  # Best
            FaceMatch(person_id="person3", confidence=0.1, distance=0.9)   # Poor
        ]
        
        result = FaceProcessingResult(
            image_url="test.jpg",
            faces_found=3,
            matches=matches
        )
        
        best = result.best_match
        assert best is not None
        assert best.person_id == "person2"
        assert best.distance == 0.2