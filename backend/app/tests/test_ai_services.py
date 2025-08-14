"""
Comprehensive tests for AI/ML services including content matching,
face recognition, and image processing capabilities.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock
from PIL import Image
import io
import base64

from app.services.ai.content_matcher import ContentMatcher, MatchType, MatchResult
from app.services.social_media.face_matcher import ProfileImageAnalyzer, FaceMatch
from app.services.content.watermarking import WatermarkService


@pytest.mark.ai
@pytest.mark.unit
class TestContentMatcher:
    """Test AI content matching service."""

    @pytest.fixture
    def content_matcher(self):
        """Create content matcher instance."""
        return ContentMatcher()

    @pytest.fixture
    def sample_image_data(self):
        """Create sample image data for testing."""
        # Create a simple test image
        img = Image.new('RGB', (300, 300), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        return img_bytes.getvalue()

    @pytest.fixture
    def sample_face_image_data(self):
        """Create sample face image data."""
        # Create a more complex image that could contain face-like patterns
        img = Image.new('RGB', (400, 400), color='white')
        # Add some patterns that might be detected as features
        pixels = img.load()
        for i in range(150, 250):
            for j in range(150, 250):
                pixels[i, j] = (200, 180, 160)  # Skin-like color
        
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        return img_bytes.getvalue()

    @pytest.mark.asyncio
    async def test_analyze_content_image_hash(self, content_matcher, sample_image_data):
        """Test content analysis using image hashing."""
        # Mock the image hash processing
        with patch.object(content_matcher, '_generate_image_hash') as mock_hash:
            mock_hash.return_value = "abc123def456"
            
            with patch.object(content_matcher, '_compare_image_hashes') as mock_compare:
                mock_compare.return_value = {"similarity": 0.85, "is_match": True}
                
                result = await content_matcher.analyze_content(
                    content_data=sample_image_data,
                    content_type="image",
                    reference_id="test_ref_123"
                )
                
                assert result["similarity_score"] >= 0.8
                assert result["is_match"] is True
                assert "image_hash" in result["features_matched"]

    @pytest.mark.asyncio
    async def test_analyze_content_face_recognition(self, content_matcher, sample_face_image_data):
        """Test content analysis using face recognition."""
        # Mock face recognition
        with patch('face_recognition.face_encodings') as mock_encodings:
            mock_encodings.return_value = [np.array([0.1, 0.2, 0.3, 0.4])]
            
            with patch.object(content_matcher, '_compare_face_encodings') as mock_compare:
                mock_compare.return_value = {"similarity": 0.92, "is_match": True, "confidence": "high"}
                
                result = await content_matcher.analyze_content(
                    content_data=sample_face_image_data,
                    content_type="image",
                    reference_id="test_face_ref"
                )
                
                assert result["similarity_score"] >= 0.9
                assert result["is_match"] is True
                assert result["confidence"] == "high"
                assert "face_recognition" in result["features_matched"]

    @pytest.mark.asyncio
    async def test_analyze_content_no_match(self, content_matcher, sample_image_data):
        """Test content analysis when no match is found."""
        with patch.object(content_matcher, '_generate_image_hash') as mock_hash:
            mock_hash.return_value = "xyz789abc123"
            
            with patch.object(content_matcher, '_compare_image_hashes') as mock_compare:
                mock_compare.return_value = {"similarity": 0.3, "is_match": False}
                
                with patch('face_recognition.face_encodings') as mock_encodings:
                    mock_encodings.return_value = []  # No faces detected
                    
                    result = await content_matcher.analyze_content(
                        content_data=sample_image_data,
                        content_type="image",
                        reference_id="no_match_ref"
                    )
                    
                    assert result["similarity_score"] < 0.5
                    assert result["is_match"] is False
                    assert result["confidence"] == "low"

    @pytest.mark.asyncio
    async def test_add_reference_content(self, content_matcher, sample_image_data):
        """Test adding reference content for future matching."""
        with patch.object(content_matcher, '_store_reference_data') as mock_store:
            mock_store.return_value = True
            
            result = await content_matcher.add_reference_content(
                content_id="ref_123",
                content_data=sample_image_data,
                content_type="image",
                metadata={"creator": "test_user", "title": "Test Image"}
            )
            
            assert result is True
            mock_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_reference_content(self, content_matcher):
        """Test removing reference content."""
        with patch.object(content_matcher, '_remove_reference_data') as mock_remove:
            mock_remove.return_value = True
            
            result = await content_matcher.remove_reference_content("ref_123")
            
            assert result is True
            mock_remove.assert_called_once_with("ref_123")

    @pytest.mark.asyncio
    async def test_batch_analyze_content(self, content_matcher, sample_image_data):
        """Test batch content analysis."""
        content_batch = [
            {"id": "batch_1", "data": sample_image_data, "type": "image"},
            {"id": "batch_2", "data": sample_image_data, "type": "image"},
        ]
        
        with patch.object(content_matcher, 'analyze_content') as mock_analyze:
            mock_analyze.return_value = {
                "similarity_score": 0.8,
                "is_match": True,
                "confidence": "high"
            }
            
            results = await content_matcher.batch_analyze_content(
                content_batch,
                reference_id="batch_ref"
            )
            
            assert len(results) == 2
            assert all(r["is_match"] for r in results.values())

    def test_generate_image_hash(self, content_matcher, sample_image_data):
        """Test image hash generation."""
        with patch('imagehash.phash') as mock_phash:
            mock_phash.return_value = MagicMock()
            mock_phash.return_value.__str__ = MagicMock(return_value="abc123def456")
            
            hash_result = content_matcher._generate_image_hash(sample_image_data)
            
            assert hash_result is not None
            assert len(hash_result) > 0

    def test_compare_image_hashes(self, content_matcher):
        """Test image hash comparison."""
        hash1 = "abc123def456"
        hash2 = "abc123def789"  # Similar hash
        hash3 = "xyz987uvw321"  # Different hash
        
        # Test similar hashes
        result1 = content_matcher._compare_image_hashes(hash1, hash2)
        assert result1["similarity"] > 0.5
        
        # Test different hashes
        result2 = content_matcher._compare_image_hashes(hash1, hash3)
        assert result2["similarity"] < 0.5

    def test_compare_face_encodings(self, content_matcher):
        """Test face encoding comparison."""
        encoding1 = np.array([0.1, 0.2, 0.3, 0.4])
        encoding2 = np.array([0.1, 0.2, 0.3, 0.4])  # Identical
        encoding3 = np.array([0.8, 0.9, 0.7, 0.6])  # Different
        
        # Test identical encodings
        result1 = content_matcher._compare_face_encodings([encoding1], [encoding2])
        assert result1["similarity"] > 0.9
        assert result1["is_match"] is True
        
        # Test different encodings
        result2 = content_matcher._compare_face_encodings([encoding1], [encoding3])
        assert result2["similarity"] < 0.7


@pytest.mark.ai
@pytest.mark.unit
class TestProfileImageAnalyzer:
    """Test social media profile image analysis."""

    @pytest.fixture
    def image_analyzer(self):
        """Create profile image analyzer instance."""
        from app.services.social_media.config import SocialMediaSettings
        settings = SocialMediaSettings()
        return ProfileImageAnalyzer(settings)

    @pytest.fixture
    def mock_profile_data(self):
        """Create mock profile data."""
        return {
            "original": {
                "username": "original_user",
                "display_name": "Original User",
                "profile_image_url": "https://example.com/original.jpg"
            },
            "candidate": {
                "username": "fake_user",
                "display_name": "Fake User",
                "profile_image_url": "https://example.com/fake.jpg"
            }
        }

    @pytest.mark.asyncio
    async def test_analyze_profile_similarity_high_match(self, image_analyzer, mock_profile_data):
        """Test profile similarity analysis with high match."""
        with patch.object(image_analyzer, '_download_image') as mock_download:
            mock_download.return_value = b"fake image data"
            
            with patch.object(image_analyzer, '_analyze_images') as mock_analyze:
                mock_analyze.return_value = {
                    "face_match": FaceMatch(
                        similarity_score=0.92,
                        confidence_level="high",
                        face_detected=True
                    ),
                    "image_similarity": 0.88,
                    "metadata_match": True
                }
                
                result = await image_analyzer.analyze_profile_similarity(
                    mock_profile_data["original"],
                    mock_profile_data["candidate"]
                )
                
                assert result["overall_similarity"] > 0.85
                assert result["confidence_level"] == "high"
                assert "face_recognition" in result["analysis_methods"]

    @pytest.mark.asyncio
    async def test_analyze_profile_similarity_low_match(self, image_analyzer, mock_profile_data):
        """Test profile similarity analysis with low match."""
        with patch.object(image_analyzer, '_download_image') as mock_download:
            mock_download.return_value = b"fake image data"
            
            with patch.object(image_analyzer, '_analyze_images') as mock_analyze:
                mock_analyze.return_value = {
                    "face_match": FaceMatch(
                        similarity_score=0.3,
                        confidence_level="low",
                        face_detected=True
                    ),
                    "image_similarity": 0.25,
                    "metadata_match": False
                }
                
                result = await image_analyzer.analyze_profile_similarity(
                    mock_profile_data["original"],
                    mock_profile_data["candidate"]
                )
                
                assert result["overall_similarity"] < 0.5
                assert result["confidence_level"] == "low"

    @pytest.mark.asyncio
    async def test_batch_analyze_candidates(self, image_analyzer, mock_profile_data):
        """Test batch analysis of candidate profiles."""
        candidates = [
            {"username": "candidate1", "profile_image_url": "https://example.com/c1.jpg"},
            {"username": "candidate2", "profile_image_url": "https://example.com/c2.jpg"},
            {"username": "candidate3", "profile_image_url": "https://example.com/c3.jpg"},
        ]
        
        with patch.object(image_analyzer, 'analyze_profile_similarity') as mock_analyze:
            # Return different similarity scores for sorting test
            mock_analyze.side_effect = [
                {"overall_similarity": 0.9, "confidence_level": "high"},
                {"overall_similarity": 0.6, "confidence_level": "medium"},
                {"overall_similarity": 0.3, "confidence_level": "low"},
            ]
            
            results = await image_analyzer.batch_analyze_candidates(
                mock_profile_data["original"],
                candidates
            )
            
            assert len(results) == 3
            # Results should be sorted by similarity (highest first)
            usernames = list(results.keys())
            similarities = [results[u]["overall_similarity"] for u in usernames]
            assert similarities == sorted(similarities, reverse=True)

    @pytest.mark.asyncio
    async def test_download_image_success(self, image_analyzer):
        """Test successful image download."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.read.return_value = b"image data"
            mock_response.status = 200
            mock_response.headers = {"content-type": "image/jpeg"}
            
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await image_analyzer._download_image("https://example.com/image.jpg")
            
            assert result == b"image data"

    @pytest.mark.asyncio
    async def test_download_image_failure(self, image_analyzer):
        """Test image download failure handling."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 404
            
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await image_analyzer._download_image("https://example.com/nonexistent.jpg")
            
            assert result is None


@pytest.mark.ai
@pytest.mark.unit
class TestWatermarkService:
    """Test watermarking service functionality."""

    @pytest.fixture
    def watermark_service(self):
        """Create watermark service instance."""
        return WatermarkService()

    @pytest.fixture
    def sample_image(self):
        """Create sample image for watermarking."""
        img = Image.new('RGB', (500, 500), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        return img_bytes.getvalue()

    @pytest.mark.asyncio
    async def test_add_visible_watermark(self, watermark_service, sample_image):
        """Test adding visible watermark to image."""
        watermark_text = "© Test Creator 2024"
        
        result = await watermark_service.add_visible_watermark(
            image_data=sample_image,
            watermark_text=watermark_text,
            position="bottom_right",
            opacity=0.7
        )
        
        assert result is not None
        assert len(result) > 0
        assert len(result) != len(sample_image)  # Should be different due to watermark

    @pytest.mark.asyncio
    async def test_add_invisible_watermark(self, watermark_service, sample_image):
        """Test adding invisible watermark to image."""
        watermark_data = "creator_id:123|timestamp:2024-01-01"
        
        result = await watermark_service.add_invisible_watermark(
            image_data=sample_image,
            watermark_data=watermark_data
        )
        
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_extract_invisible_watermark(self, watermark_service, sample_image):
        """Test extracting invisible watermark from image."""
        watermark_data = "creator_id:123|timestamp:2024-01-01"
        
        # First add invisible watermark
        watermarked_image = await watermark_service.add_invisible_watermark(
            image_data=sample_image,
            watermark_data=watermark_data
        )
        
        # Then extract it
        with patch.object(watermark_service, '_extract_steganographic_data') as mock_extract:
            mock_extract.return_value = watermark_data
            
            extracted_data = await watermark_service.extract_invisible_watermark(watermarked_image)
            
            assert extracted_data == watermark_data

    @pytest.mark.asyncio
    async def test_verify_watermark_integrity(self, watermark_service, sample_image):
        """Test watermark integrity verification."""
        original_signature = "abc123def456"
        
        with patch.object(watermark_service, '_calculate_image_signature') as mock_signature:
            mock_signature.return_value = original_signature
            
            # Test with matching signature
            is_valid = await watermark_service.verify_watermark_integrity(
                image_data=sample_image,
                expected_signature=original_signature
            )
            
            assert is_valid is True
            
            # Test with non-matching signature
            is_valid = await watermark_service.verify_watermark_integrity(
                image_data=sample_image,
                expected_signature="different_signature"
            )
            
            assert is_valid is False

    @pytest.mark.asyncio
    async def test_batch_watermark_images(self, watermark_service, sample_image):
        """Test batch watermarking of multiple images."""
        images = [
            {"id": "img1", "data": sample_image, "text": "© Creator 1"},
            {"id": "img2", "data": sample_image, "text": "© Creator 2"},
        ]
        
        with patch.object(watermark_service, 'add_visible_watermark') as mock_watermark:
            mock_watermark.return_value = sample_image  # Return watermarked image
            
            results = await watermark_service.batch_watermark_images(
                images,
                position="center",
                opacity=0.5
            )
            
            assert len(results) == 2
            assert "img1" in results
            assert "img2" in results
            assert mock_watermark.call_count == 2


@pytest.mark.ai
@pytest.mark.integration
class TestAIServicesIntegration:
    """Integration tests for AI services working together."""

    @pytest.mark.asyncio
    async def test_content_matching_with_face_recognition_pipeline(self, sample_face_image_data):
        """Test complete pipeline from content upload to face recognition match."""
        content_matcher = ContentMatcher()
        
        # Step 1: Add reference content
        with patch.object(content_matcher, '_store_reference_data') as mock_store:
            mock_store.return_value = True
            
            reference_added = await content_matcher.add_reference_content(
                content_id="ref_face_123",
                content_data=sample_face_image_data,
                content_type="image",
                metadata={"creator": "test_creator"}
            )
            assert reference_added is True
        
        # Step 2: Analyze potentially infringing content
        with patch('face_recognition.face_encodings') as mock_encodings:
            mock_encodings.return_value = [np.array([0.1, 0.2, 0.3, 0.4])]
            
            with patch.object(content_matcher, '_compare_face_encodings') as mock_compare:
                mock_compare.return_value = {
                    "similarity": 0.95,
                    "is_match": True,
                    "confidence": "high"
                }
                
                match_result = await content_matcher.analyze_content(
                    content_data=sample_face_image_data,
                    content_type="image",
                    reference_id="ref_face_123"
                )
                
                assert match_result["is_match"] is True
                assert match_result["similarity_score"] >= 0.9
                assert match_result["confidence"] == "high"

    @pytest.mark.asyncio
    async def test_watermark_and_content_matching_integration(self, sample_image_data):
        """Test watermarking followed by content matching."""
        watermark_service = WatermarkService()
        content_matcher = ContentMatcher()
        
        # Step 1: Add watermark to original content
        watermark_data = "creator_id:test_123|timestamp:2024-01-01"
        
        with patch.object(watermark_service, 'add_invisible_watermark') as mock_watermark:
            mock_watermark.return_value = sample_image_data  # Return watermarked image
            
            watermarked_image = await watermark_service.add_invisible_watermark(
                image_data=sample_image_data,
                watermark_data=watermark_data
            )
            
            assert watermarked_image is not None
        
        # Step 2: Add watermarked content as reference
        with patch.object(content_matcher, '_store_reference_data') as mock_store:
            mock_store.return_value = True
            
            await content_matcher.add_reference_content(
                content_id="watermarked_ref",
                content_data=watermarked_image,
                content_type="image"
            )
        
        # Step 3: Check if potentially stolen content matches
        with patch.object(content_matcher, '_generate_image_hash') as mock_hash:
            mock_hash.return_value = "watermarked_hash_123"
            
            with patch.object(content_matcher, '_compare_image_hashes') as mock_compare:
                mock_compare.return_value = {"similarity": 0.9, "is_match": True}
                
                match_result = await content_matcher.analyze_content(
                    content_data=sample_image_data,  # Potentially stolen content
                    content_type="image",
                    reference_id="watermarked_ref"
                )
                
                assert match_result["is_match"] is True
                assert match_result["similarity_score"] >= 0.8


@pytest.mark.ai
@pytest.mark.performance
class TestAIServicesPerformance:
    """Performance tests for AI services."""

    @pytest.mark.asyncio
    async def test_batch_content_analysis_performance(self, sample_image_data):
        """Test performance of batch content analysis."""
        import time
        
        content_matcher = ContentMatcher()
        
        # Create batch of 10 images
        content_batch = [
            {"id": f"perf_test_{i}", "data": sample_image_data, "type": "image"}
            for i in range(10)
        ]
        
        with patch.object(content_matcher, 'analyze_content') as mock_analyze:
            mock_analyze.return_value = {
                "similarity_score": 0.7,
                "is_match": True,
                "confidence": "medium"
            }
            
            start_time = time.time()
            results = await content_matcher.batch_analyze_content(
                content_batch,
                reference_id="perf_ref"
            )
            end_time = time.time()
            
            assert len(results) == 10
            assert (end_time - start_time) < 5.0  # Should complete within 5 seconds

    @pytest.mark.asyncio
    async def test_face_recognition_memory_efficiency(self, sample_face_image_data):
        """Test memory efficiency of face recognition processing."""
        import psutil
        import os
        
        content_matcher = ContentMatcher()
        process = psutil.Process(os.getpid())
        
        # Get initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with patch('face_recognition.face_encodings') as mock_encodings:
            mock_encodings.return_value = [np.random.random(128) for _ in range(5)]  # Multiple faces
            
            # Process multiple images
            for i in range(20):
                await content_matcher.analyze_content(
                    content_data=sample_face_image_data,
                    content_type="image",
                    reference_id=f"memory_test_{i}"
                )
        
        # Check final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 500MB)
        assert memory_increase < 500


@pytest.mark.ai
@pytest.mark.security
class TestAIServicesSecurity:
    """Security tests for AI services."""

    @pytest.mark.asyncio
    async def test_malicious_image_handling(self, content_matcher):
        """Test handling of potentially malicious image data."""
        # Test with various malicious payloads
        malicious_payloads = [
            b"\x89PNG\r\n\x1a\n" + b"A" * 10000,  # Oversized PNG header
            b"\xFF\xD8\xFF" + b"B" * 10000,        # Oversized JPEG header
            b"GIF89a" + b"C" * 10000,              # Oversized GIF header
            b"<script>alert('xss')</script>",      # Script injection attempt
        ]
        
        for payload in malicious_payloads:
            try:
                result = await content_matcher.analyze_content(
                    content_data=payload,
                    content_type="image",
                    reference_id="security_test"
                )
                
                # Should either handle gracefully or return safe error
                assert result is None or isinstance(result, dict)
                
            except Exception as e:
                # Exceptions should be controlled, not system crashes
                assert "system" not in str(e).lower()
                assert "critical" not in str(e).lower()

    @pytest.mark.asyncio
    async def test_input_sanitization(self, watermark_service, sample_image_data):
        """Test input sanitization in watermark service."""
        # Test XSS in watermark text
        malicious_texts = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "../../../etc/passwd",
        ]
        
        for malicious_text in malicious_texts:
            result = await watermark_service.add_visible_watermark(
                image_data=sample_image_data,
                watermark_text=malicious_text,
                position="center"
            )
            
            # Should either sanitize or safely reject
            assert result is not None
            # Verify dangerous content is not included
            if isinstance(result, bytes):
                result_str = str(result)
                assert "<script>" not in result_str
                assert "javascript:" not in result_str

    @pytest.mark.asyncio
    async def test_resource_exhaustion_protection(self, content_matcher):
        """Test protection against resource exhaustion attacks."""
        # Test with extremely large image dimensions (metadata only)
        large_image_metadata = {
            "width": 100000,
            "height": 100000,
            "format": "JPEG",
            "size": 1000000000  # 1GB
        }
        
        with patch.object(content_matcher, '_validate_image_size') as mock_validate:
            mock_validate.return_value = False  # Should reject oversized images
            
            result = await content_matcher.analyze_content(
                content_data=b"fake_large_image_data",
                content_type="image",
                reference_id="resource_test",
                metadata=large_image_metadata
            )
            
            # Should reject or handle safely
            assert result is None or result.get("error") is not None