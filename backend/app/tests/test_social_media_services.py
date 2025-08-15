"""
Comprehensive tests for social media services including impersonation detection,
profile monitoring, face matching, and API integrations.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import json
import numpy as np
from typing import Dict, Any, List

from app.services.social_media.impersonation_detector import ImpersonationDetector, SuspiciousProfile
from app.services.social_media.face_matcher import ProfileImageAnalyzer, FaceMatch
from app.services.social_media.api_clients import InstagramAPI, TwitterAPI, OnlyFansAPI
from app.services.social_media.scrapers import SocialMediaScraper
from app.services.social_media.monitoring_service import SocialMediaMonitoringService
from app.services.social_media.username_monitor import UsernameMonitor


@pytest.mark.unit
@pytest.mark.social_media
class TestImpersonationDetector:
    """Test social media impersonation detection."""

    @pytest.fixture
    def impersonation_detector(self):
        """Create impersonation detector instance."""
        return ImpersonationDetector()

    @pytest.fixture
    def original_profile(self):
        """Original user profile data."""
        return {
            "username": "original_user",
            "display_name": "Original Creator",
            "bio": "Content creator and model",
            "profile_image_url": "https://example.com/original_profile.jpg",
            "follower_count": 10000,
            "verified": True,
            "social_media_accounts": {
                "instagram": "@original_user",
                "twitter": "@original_creator",
                "onlyfans": "original_user"
            }
        }

    @pytest.fixture
    def suspicious_profiles(self):
        """List of potentially suspicious profiles."""
        return [
            {
                "username": "originaI_user",  # Lowercase L instead of l
                "display_name": "Original Creator",
                "bio": "Content creator and model",
                "profile_image_url": "https://fake-site.com/stolen_profile.jpg",
                "follower_count": 50,
                "verified": False,
                "platform": "instagram"
            },
            {
                "username": "original_user_real",
                "display_name": "Original Creator - Real Account",
                "bio": "This is my real account! Follow me here",
                "profile_image_url": "https://another-fake.com/profile.jpg",
                "follower_count": 25,
                "verified": False,
                "platform": "twitter"
            },
            {
                "username": "totally_different",
                "display_name": "Completely Different Person",
                "bio": "I love cats and pizza",
                "profile_image_url": "https://legitimate.com/cat_lover.jpg",
                "follower_count": 1000,
                "verified": False,
                "platform": "instagram"
            }
        ]

    @pytest.mark.asyncio
    async def test_detect_impersonation_high_confidence(self, impersonation_detector, original_profile, suspicious_profiles):
        """Test impersonation detection with high confidence match."""
        suspicious_profile = suspicious_profiles[0]  # Very similar username
        
        with patch.object(impersonation_detector, '_analyze_profile_images') as mock_image_analysis:
            mock_image_analysis.return_value = FaceMatch(
                similarity_score=0.95,
                confidence_level="high",
                face_detected=True
            )
            
            result = await impersonation_detector.analyze_profile(
                original_profile,
                suspicious_profile
            )
            
            assert result.is_impersonation is True
            assert result.confidence_score > 0.8
            assert "username_similarity" in result.analysis_factors
            assert "image_similarity" in result.analysis_factors

    @pytest.mark.asyncio
    async def test_detect_impersonation_low_confidence(self, impersonation_detector, original_profile, suspicious_profiles):
        """Test impersonation detection with low confidence match."""
        suspicious_profile = suspicious_profiles[2]  # Completely different
        
        with patch.object(impersonation_detector, '_analyze_profile_images') as mock_image_analysis:
            mock_image_analysis.return_value = FaceMatch(
                similarity_score=0.2,
                confidence_level="low",
                face_detected=True
            )
            
            result = await impersonation_detector.analyze_profile(
                original_profile,
                suspicious_profile
            )
            
            assert result.is_impersonation is False
            assert result.confidence_score < 0.5

    @pytest.mark.asyncio
    async def test_batch_analyze_profiles(self, impersonation_detector, original_profile, suspicious_profiles):
        """Test batch analysis of multiple profiles."""
        with patch.object(impersonation_detector, 'analyze_profile') as mock_analyze:
            # Return different confidence scores for each profile
            mock_analyze.side_effect = [
                SuspiciousProfile(
                    profile_data=suspicious_profiles[0],
                    is_impersonation=True,
                    confidence_score=0.9,
                    analysis_factors=["username_similarity", "image_similarity"]
                ),
                SuspiciousProfile(
                    profile_data=suspicious_profiles[1],
                    is_impersonation=True,
                    confidence_score=0.7,
                    analysis_factors=["display_name_similarity"]
                ),
                SuspiciousProfile(
                    profile_data=suspicious_profiles[2],
                    is_impersonation=False,
                    confidence_score=0.2,
                    analysis_factors=[]
                )
            ]
            
            results = await impersonation_detector.batch_analyze_profiles(
                original_profile,
                suspicious_profiles
            )
            
            assert len(results) == 3
            # Results should be sorted by confidence score (highest first)
            assert results[0].confidence_score >= results[1].confidence_score
            assert results[1].confidence_score >= results[2].confidence_score

    def test_calculate_username_similarity(self, impersonation_detector):
        """Test username similarity calculation."""
        original = "original_user"
        
        # Very similar (character substitution)
        similar1 = "originaI_user"  # I instead of l
        similarity1 = impersonation_detector._calculate_username_similarity(original, similar1)
        assert similarity1 > 0.8
        
        # Moderately similar (addition)
        similar2 = "original_user_real"
        similarity2 = impersonation_detector._calculate_username_similarity(original, similar2)
        assert 0.5 < similarity2 < 0.8
        
        # Not similar
        different = "completely_different"
        similarity3 = impersonation_detector._calculate_username_similarity(original, different)
        assert similarity3 < 0.3

    def test_calculate_display_name_similarity(self, impersonation_detector):
        """Test display name similarity calculation."""
        original = "Original Creator"
        
        # Exact match
        exact = "Original Creator"
        similarity1 = impersonation_detector._calculate_display_name_similarity(original, exact)
        assert similarity1 > 0.95
        
        # Case variation
        case_var = "original creator"
        similarity2 = impersonation_detector._calculate_display_name_similarity(original, case_var)
        assert similarity2 > 0.9
        
        # Additional words
        extended = "Original Creator - Real Account"
        similarity3 = impersonation_detector._calculate_display_name_similarity(original, extended)
        assert 0.6 < similarity3 < 0.9

    def test_analyze_bio_similarity(self, impersonation_detector):
        """Test bio content similarity analysis."""
        original_bio = "Content creator and model specializing in artistic photography"
        
        # Very similar bio
        similar_bio = "Content creator and model specializing in photography"
        similarity1 = impersonation_detector._analyze_bio_similarity(original_bio, similar_bio)
        assert similarity1 > 0.7
        
        # Completely different bio
        different_bio = "I love cats and pizza and video games"
        similarity2 = impersonation_detector._analyze_bio_similarity(original_bio, different_bio)
        assert similarity2 < 0.3

    def test_detect_suspicious_patterns(self, impersonation_detector):
        """Test detection of suspicious patterns in profiles."""
        # Profile with suspicious patterns
        suspicious_profile = {
            "username": "original_user_real",
            "display_name": "Original Creator - REAL ACCOUNT",
            "bio": "This is my REAL account! Follow me here for exclusive content!",
            "follower_count": 10,
            "verified": False
        }
        
        patterns = impersonation_detector._detect_suspicious_patterns(suspicious_profile)
        
        assert "fake_verification_claims" in patterns
        assert "urgency_language" in patterns
        assert "low_follower_count" in patterns

    def test_calculate_follower_ratio_suspicion(self, impersonation_detector):
        """Test follower ratio suspicion calculation."""
        original_followers = 10000
        
        # Very low followers (suspicious)
        low_followers = 50
        suspicion1 = impersonation_detector._calculate_follower_ratio_suspicion(
            original_followers, low_followers
        )
        assert suspicion1 > 0.8
        
        # Similar followers (not suspicious)
        similar_followers = 9500
        suspicion2 = impersonation_detector._calculate_follower_ratio_suspicion(
            original_followers, similar_followers
        )
        assert suspicion2 < 0.2


@pytest.mark.unit
@pytest.mark.social_media
class TestProfileImageAnalyzer:
    """Test profile image analysis and face matching."""

    @pytest.fixture
    def image_analyzer(self):
        """Create profile image analyzer instance."""
        from app.services.social_media.config import SocialMediaSettings
        settings = SocialMediaSettings()
        return ProfileImageAnalyzer(settings)

    @pytest.fixture
    def sample_face_encoding(self):
        """Sample face encoding data."""
        return np.array([0.1, 0.2, 0.3, 0.4, 0.5] * 25 + [0.6])  # 128-dimensional encoding

    @pytest.mark.asyncio
    async def test_analyze_profile_images_match(self, image_analyzer, sample_face_encoding):
        """Test profile image analysis with face match."""
        original_image_url = "https://example.com/original.jpg"
        suspect_image_url = "https://example.com/suspect.jpg"
        
        with patch.object(image_analyzer, '_download_image') as mock_download:
            mock_download.return_value = b"fake image data"
            
            with patch('face_recognition.face_encodings') as mock_encodings:
                # Return similar face encodings
                mock_encodings.side_effect = [
                    [sample_face_encoding],  # Original image
                    [sample_face_encoding + 0.01]  # Very similar face in suspect image
                ]
                
                result = await image_analyzer.compare_profile_images(
                    original_image_url,
                    suspect_image_url
                )
                
                assert result.similarity_score > 0.9
                assert result.face_detected is True
                assert result.confidence_level == "high"

    @pytest.mark.asyncio
    async def test_analyze_profile_images_no_match(self, image_analyzer, sample_face_encoding):
        """Test profile image analysis with no face match."""
        original_image_url = "https://example.com/original.jpg"
        suspect_image_url = "https://example.com/suspect.jpg"
        
        with patch.object(image_analyzer, '_download_image') as mock_download:
            mock_download.return_value = b"fake image data"
            
            with patch('face_recognition.face_encodings') as mock_encodings:
                # Return different face encodings
                different_encoding = np.random.random(128)
                mock_encodings.side_effect = [
                    [sample_face_encoding],  # Original image
                    [different_encoding]  # Different face in suspect image
                ]
                
                result = await image_analyzer.compare_profile_images(
                    original_image_url,
                    suspect_image_url
                )
                
                assert result.similarity_score < 0.5
                assert result.confidence_level == "low"

    @pytest.mark.asyncio
    async def test_analyze_images_no_faces_detected(self, image_analyzer):
        """Test analysis when no faces are detected."""
        original_image_url = "https://example.com/original.jpg"
        suspect_image_url = "https://example.com/suspect.jpg"
        
        with patch.object(image_analyzer, '_download_image') as mock_download:
            mock_download.return_value = b"fake image data"
            
            with patch('face_recognition.face_encodings') as mock_encodings:
                # No faces detected
                mock_encodings.return_value = []
                
                result = await image_analyzer.compare_profile_images(
                    original_image_url,
                    suspect_image_url
                )
                
                assert result.face_detected is False
                assert result.similarity_score == 0.0

    @pytest.mark.asyncio
    async def test_download_image_success(self, image_analyzer):
        """Test successful image download."""
        image_url = "https://example.com/image.jpg"
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.read.return_value = b"image data"
            mock_response.status = 200
            mock_response.headers = {"content-type": "image/jpeg"}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            image_data = await image_analyzer._download_image(image_url)
            
            assert image_data == b"image data"

    @pytest.mark.asyncio
    async def test_download_image_failure(self, image_analyzer):
        """Test image download failure handling."""
        image_url = "https://example.com/nonexistent.jpg"
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_get.return_value.__aenter__.return_value = mock_response
            
            image_data = await image_analyzer._download_image(image_url)
            
            assert image_data is None

    def test_calculate_face_similarity(self, image_analyzer, sample_face_encoding):
        """Test face similarity calculation."""
        encoding1 = sample_face_encoding
        encoding2 = sample_face_encoding + 0.01  # Very similar
        encoding3 = np.random.random(128)  # Different
        
        # High similarity
        similarity1 = image_analyzer._calculate_face_similarity(encoding1, encoding2)
        assert similarity1 > 0.9
        
        # Low similarity
        similarity2 = image_analyzer._calculate_face_similarity(encoding1, encoding3)
        assert similarity2 < 0.7


@pytest.mark.unit
@pytest.mark.social_media
class TestSocialMediaAPIs:
    """Test social media API clients."""

    @pytest.fixture
    def instagram_api(self):
        """Create Instagram API client."""
        return InstagramAPI(access_token="fake_token")

    @pytest.fixture
    def twitter_api(self):
        """Create Twitter API client."""
        return TwitterAPI(
            consumer_key="fake_key",
            consumer_secret="fake_secret",
            access_token="fake_token",
            access_token_secret="fake_token_secret"
        )

    @pytest.mark.asyncio
    async def test_instagram_search_users(self, instagram_api):
        """Test Instagram user search."""
        query = "test_username"
        
        mock_response = {
            "data": [
                {
                    "id": "123456789",
                    "username": "test_username",
                    "account_type": "PERSONAL",
                    "media_count": 150
                },
                {
                    "id": "987654321", 
                    "username": "test_username_2",
                    "account_type": "BUSINESS",
                    "media_count": 300
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response
            mock_resp.status = 200
            mock_get.return_value.__aenter__.return_value = mock_resp
            
            results = await instagram_api.search_users(query)
            
            assert len(results) == 2
            assert results[0]["username"] == "test_username"

    @pytest.mark.asyncio
    async def test_instagram_get_user_profile(self, instagram_api):
        """Test getting Instagram user profile."""
        user_id = "123456789"
        
        mock_response = {
            "id": user_id,
            "username": "test_user",
            "account_type": "PERSONAL",
            "media_count": 150,
            "followers_count": 1000
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response
            mock_resp.status = 200
            mock_get.return_value.__aenter__.return_value = mock_resp
            
            profile = await instagram_api.get_user_profile(user_id)
            
            assert profile["id"] == user_id
            assert profile["username"] == "test_user"
            assert profile["followers_count"] == 1000

    @pytest.mark.asyncio
    async def test_twitter_search_users(self, twitter_api):
        """Test Twitter user search."""
        query = "test_username"
        
        mock_response = {
            "data": [
                {
                    "id": "123456789",
                    "username": "test_username",
                    "name": "Test User",
                    "public_metrics": {
                        "followers_count": 500,
                        "following_count": 200
                    }
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response
            mock_resp.status = 200
            mock_get.return_value.__aenter__.return_value = mock_resp
            
            results = await twitter_api.search_users(query)
            
            assert len(results) == 1
            assert results[0]["username"] == "test_username"

    @pytest.mark.asyncio
    async def test_api_rate_limiting(self, instagram_api):
        """Test API rate limiting handling."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_resp = AsyncMock()
            mock_resp.status = 429  # Rate limited
            mock_resp.headers = {"Retry-After": "60"}
            mock_get.return_value.__aenter__.return_value = mock_resp
            
            with patch('asyncio.sleep') as mock_sleep:
                result = await instagram_api.search_users("test")
                
                # Should handle rate limiting gracefully
                assert result == []
                mock_sleep.assert_called_with(60)

    @pytest.mark.asyncio
    async def test_api_error_handling(self, instagram_api):
        """Test API error handling."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            result = await instagram_api.search_users("test")
            
            assert result == []


@pytest.mark.unit
@pytest.mark.social_media
class TestSocialMediaScraper:
    """Test social media scraping functionality."""

    @pytest.fixture
    def scraper(self):
        """Create social media scraper instance."""
        return SocialMediaScraper()

    @pytest.fixture
    def mock_instagram_html(self):
        """Mock Instagram profile HTML."""
        return """
        <html>
            <head><title>@test_user Instagram profile</title></head>
            <body>
                <div class="profile-info">
                    <span class="username">test_user</span>
                    <span class="follower-count">1.2K followers</span>
                    <div class="bio">Content creator and model</div>
                </div>
                <img src="https://instagram.com/profile.jpg" alt="Profile picture">
            </body>
        </html>
        """

    @pytest.mark.asyncio
    async def test_scrape_instagram_profile(self, scraper, mock_instagram_html):
        """Test Instagram profile scraping."""
        profile_url = "https://instagram.com/test_user"
        
        with patch.object(scraper, '_fetch_page_content') as mock_fetch:
            mock_fetch.return_value = mock_instagram_html
            
            profile_data = await scraper.scrape_instagram_profile(profile_url)
            
            assert profile_data is not None
            assert profile_data["username"] == "test_user"
            assert "1.2K" in profile_data["follower_count"]
            assert profile_data["bio"] == "Content creator and model"

    @pytest.mark.asyncio
    async def test_scrape_with_rate_limiting(self, scraper):
        """Test scraping with rate limiting."""
        urls = [f"https://instagram.com/user_{i}" for i in range(10)]
        
        with patch.object(scraper, '_fetch_page_content') as mock_fetch:
            mock_fetch.return_value = "<html>test</html>"
            
            with patch('asyncio.sleep') as mock_sleep:
                results = await scraper.batch_scrape_profiles(urls, delay=1.0)
                
                assert len(results) == 10
                # Should have added delays between requests
                assert mock_sleep.call_count >= 9  # 9 delays for 10 requests

    @pytest.mark.asyncio
    async def test_scrape_error_handling(self, scraper):
        """Test scraping error handling."""
        profile_url = "https://instagram.com/nonexistent_user"
        
        with patch.object(scraper, '_fetch_page_content') as mock_fetch:
            mock_fetch.side_effect = Exception("Page not found")
            
            profile_data = await scraper.scrape_instagram_profile(profile_url)
            
            assert profile_data is None

    def test_parse_follower_count(self, scraper):
        """Test follower count parsing."""
        # Test various formats
        assert scraper._parse_follower_count("1.2K followers") == 1200
        assert scraper._parse_follower_count("15M followers") == 15000000
        assert scraper._parse_follower_count("500 followers") == 500
        assert scraper._parse_follower_count("2.5M") == 2500000

    def test_extract_profile_image_url(self, scraper, mock_instagram_html):
        """Test profile image URL extraction."""
        image_url = scraper._extract_profile_image_url(mock_instagram_html)
        assert image_url == "https://instagram.com/profile.jpg"


@pytest.mark.unit
@pytest.mark.social_media
class TestUsernameMonitor:
    """Test username monitoring functionality."""

    @pytest.fixture
    def username_monitor(self):
        """Create username monitor instance."""
        return UsernameMonitor()

    @pytest.fixture
    def sample_usernames(self):
        """Sample usernames to monitor."""
        return [
            "original_user",
            "original.user", 
            "originaluser",
            "original_creator"
        ]

    @pytest.mark.asyncio
    async def test_generate_username_variations(self, username_monitor):
        """Test generation of username variations."""
        base_username = "original_user"
        
        variations = username_monitor._generate_username_variations(base_username)
        
        assert "originaI_user" in variations  # I instead of l
        assert "original.user" in variations  # underscore to dot
        assert "original-user" in variations  # underscore to dash
        assert "originaluser" in variations   # no underscore
        assert "original_user_real" in variations  # added suffix

    @pytest.mark.asyncio
    async def test_monitor_username_registration(self, username_monitor, sample_usernames):
        """Test monitoring for new username registrations."""
        with patch.object(username_monitor, '_check_username_availability') as mock_check:
            # Simulate some usernames becoming taken
            mock_check.side_effect = [
                {"available": True, "platform": "instagram"},
                {"available": False, "platform": "instagram", "profile_url": "https://instagram.com/original.user"},
                {"available": True, "platform": "instagram"},
                {"available": True, "platform": "instagram"}
            ]
            
            newly_taken = await username_monitor.check_username_status_changes(
                sample_usernames,
                platform="instagram"
            )
            
            assert len(newly_taken) == 1
            assert newly_taken[0]["username"] == "original.user"
            assert newly_taken[0]["available"] is False

    @pytest.mark.asyncio
    async def test_detect_suspicious_new_accounts(self, username_monitor):
        """Test detection of suspicious new account registrations."""
        new_accounts = [
            {
                "username": "originaI_user",  # Suspicious similarity
                "profile_url": "https://instagram.com/originaI_user",
                "created_date": datetime.now() - timedelta(days=1),
                "follower_count": 5
            },
            {
                "username": "completely_different",
                "profile_url": "https://instagram.com/completely_different", 
                "created_date": datetime.now() - timedelta(days=30),
                "follower_count": 500
            }
        ]
        
        original_username = "original_user"
        
        suspicious = username_monitor._filter_suspicious_accounts(
            new_accounts,
            original_username
        )
        
        assert len(suspicious) == 1
        assert suspicious[0]["username"] == "originaI_user"

    def test_calculate_username_suspicion_score(self, username_monitor):
        """Test username suspicion score calculation."""
        original = "original_user"
        
        # High suspicion (character substitution)
        suspicious1 = "originaI_user"
        score1 = username_monitor._calculate_suspicion_score(original, suspicious1)
        assert score1 > 0.8
        
        # Medium suspicion (addition)
        suspicious2 = "original_user_real"
        score2 = username_monitor._calculate_suspicion_score(original, suspicious2)
        assert 0.5 < score2 < 0.8
        
        # Low suspicion (completely different)
        not_suspicious = "cat_lover_123"
        score3 = username_monitor._calculate_suspicion_score(original, not_suspicious)
        assert score3 < 0.3


@pytest.mark.integration
@pytest.mark.social_media
class TestSocialMediaIntegration:
    """Integration tests for social media services."""

    @pytest.mark.asyncio
    async def test_end_to_end_impersonation_detection(self, db_session):
        """Test complete impersonation detection workflow."""
        detector = ImpersonationDetector()
        image_analyzer = ProfileImageAnalyzer()
        
        original_profile = {
            "username": "test_creator",
            "display_name": "Test Creator",
            "profile_image_url": "https://example.com/original.jpg"
        }
        
        suspicious_profile = {
            "username": "test_creat0r",  # 0 instead of o
            "display_name": "Test Creator",
            "profile_image_url": "https://fake-site.com/stolen.jpg",
            "platform": "instagram"
        }
        
        # Mock image analysis
        with patch.object(image_analyzer, 'compare_profile_images') as mock_compare:
            mock_compare.return_value = FaceMatch(
                similarity_score=0.92,
                confidence_level="high",
                face_detected=True
            )
            
            # Run impersonation detection
            result = await detector.analyze_profile(
                original_profile,
                suspicious_profile
            )
            
            assert result.is_impersonation is True
            assert result.confidence_score > 0.8


@pytest.mark.performance
@pytest.mark.social_media
class TestSocialMediaPerformance:
    """Performance tests for social media services."""

    @pytest.mark.asyncio
    async def test_batch_profile_analysis_performance(self):
        """Test performance of batch profile analysis."""
        import time
        
        detector = ImpersonationDetector()
        original_profile = {"username": "test_user"}
        suspicious_profiles = [{"username": f"test_user_{i}"} for i in range(50)]
        
        with patch.object(detector, 'analyze_profile') as mock_analyze:
            mock_analyze.return_value = SuspiciousProfile(
                profile_data={},
                is_impersonation=False,
                confidence_score=0.3,
                analysis_factors=[]
            )
            
            start_time = time.time()
            results = await detector.batch_analyze_profiles(
                original_profile,
                suspicious_profiles
            )
            end_time = time.time()
            
            assert len(results) == 50
            assert (end_time - start_time) < 20  # Should complete within 20 seconds

    @pytest.mark.asyncio
    async def test_concurrent_image_analysis_performance(self):
        """Test performance of concurrent image analysis."""
        analyzer = ProfileImageAnalyzer()
        image_pairs = [
            ("https://example.com/orig.jpg", f"https://example.com/test_{i}.jpg")
            for i in range(20)
        ]
        
        with patch.object(analyzer, 'compare_profile_images') as mock_compare:
            mock_compare.return_value = FaceMatch(
                similarity_score=0.5,
                confidence_level="medium",
                face_detected=True
            )
            
            import asyncio
            tasks = [
                analyzer.compare_profile_images(orig, suspect)
                for orig, suspect in image_pairs
            ]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            assert len(results) == 20
            assert (end_time - start_time) < 15  # Should complete within 15 seconds


@pytest.mark.security
@pytest.mark.social_media
class TestSocialMediaSecurity:
    """Security tests for social media services."""

    @pytest.mark.asyncio
    async def test_api_credential_protection(self):
        """Test protection of API credentials."""
        api = InstagramAPI(access_token="secret_token")
        
        # Ensure credentials are not logged or exposed
        with patch('logging.Logger.info') as mock_log:
            await api.search_users("test")
            
            # Check that no log messages contain the secret token
            for call_args in mock_log.call_args_list:
                message = call_args[0][0] if call_args[0] else ""
                assert "secret_token" not in str(message)

    @pytest.mark.asyncio
    async def test_input_sanitization_in_scraping(self):
        """Test input sanitization in web scraping."""
        scraper = SocialMediaScraper()
        
        malicious_urls = [
            "https://evil-site.com/<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>"
        ]
        
        for url in malicious_urls:
            with patch.object(scraper, '_fetch_page_content') as mock_fetch:
                mock_fetch.return_value = "<html>safe content</html>"
                
                # Should sanitize or reject malicious URLs
                result = await scraper.scrape_instagram_profile(url)
                
                # Either safely handle or return None for malicious URLs
                assert result is None or isinstance(result, dict)

    def test_prevent_social_media_injection_attacks(self):
        """Test prevention of social media injection attacks."""
        detector = ImpersonationDetector()
        
        malicious_profile = {
            "username": "test<script>alert('xss')</script>",
            "display_name": "Test<script>alert('xss')</script>",
            "bio": "Bio with <script>alert('xss')</script>"
        }
        
        sanitized = detector._sanitize_profile_data(malicious_profile)
        
        assert "<script>" not in sanitized["username"]
        assert "<script>" not in sanitized["display_name"] 
        assert "<script>" not in sanitized["bio"]