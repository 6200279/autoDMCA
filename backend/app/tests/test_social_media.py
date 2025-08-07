"""
Comprehensive tests for social media monitoring system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from app.services.social_media.config import MonitoringConfig, SocialMediaSettings
from app.services.social_media.api_clients import ProfileData, SearchResult, create_api_client
from app.services.social_media.scrapers import SocialMediaScraper
from app.services.social_media.username_monitor import UsernameMonitor, UsernameGenerator, UsernameMatch
from app.services.social_media.face_matcher import ProfileImageAnalyzer, FaceMatch, ImageMatch
from app.services.social_media.fake_detection import FakeAccountDetector, FakeAccountScore
from app.services.social_media.reporting import AutomatedReportingService, ReportSubmission
from app.services.social_media.monitoring_service import SocialMediaMonitoringService, MonitoringResult
from app.services.social_media.scheduler import MonitoringScheduler, ScheduledTask, TaskQueue
from app.db.models.social_media import SocialMediaPlatform, ImpersonationType


class TestSocialMediaConfig:
    """Test social media configuration."""
    
    def test_settings_initialization(self):
        """Test settings initialization with defaults."""
        settings = SocialMediaSettings()
        
        assert settings.face_recognition_tolerance == 0.6
        assert settings.image_similarity_threshold == 0.85
        assert settings.auto_reporting_enabled == False
        assert settings.supported_image_formats == {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".avif"}
    
    def test_monitoring_config_initialization(self):
        """Test monitoring config initialization."""
        config = MonitoringConfig()
        
        assert len(config.platform_configs) > 0
        assert SocialMediaPlatform.INSTAGRAM in config.platform_configs
        assert SocialMediaPlatform.TWITTER in config.platform_configs
    
    def test_platform_config_retrieval(self):
        """Test platform configuration retrieval."""
        config = MonitoringConfig()
        
        instagram_config = config.get_platform_config(SocialMediaPlatform.INSTAGRAM)
        assert instagram_config is not None
        assert instagram_config.platform == SocialMediaPlatform.INSTAGRAM
        assert instagram_config.base_url == "https://www.instagram.com"
    
    def test_search_terms_generation(self):
        """Test search terms generation."""
        config = MonitoringConfig()
        
        terms = config.get_search_terms("testuser", "TestStage")
        assert "testuser" in terms
        assert "testuser_leaked" in terms
        assert "TestStage" in terms
        assert "TestStage leaked" in terms
    
    def test_username_variations_generation(self):
        """Test username variations generation."""
        config = MonitoringConfig()
        
        variations = config.get_username_variations("testuser")
        assert "testuser" in variations
        assert "testuser_" in variations
        assert "testuser2024" in variations
        assert "testuserofficial" in variations


class TestUsernameMonitor:
    """Test username monitoring functionality."""
    
    @pytest.fixture
    def config(self):
        return MonitoringConfig()
    
    @pytest.fixture
    def username_monitor(self, config):
        return UsernameMonitor(config)
    
    def test_username_generator_initialization(self):
        """Test username generator initialization."""
        settings = SocialMediaSettings()
        generator = UsernameGenerator(settings)
        
        assert len(generator.common_substitutions) > 0
        assert len(generator.common_additions) > 0
        assert 'a' in generator.common_substitutions
        assert '@' in generator.common_substitutions['a']
    
    def test_username_variations_generation(self):
        """Test generation of username variations."""
        settings = SocialMediaSettings()
        generator = UsernameGenerator(settings)
        
        variations = generator.generate_variations("testuser", max_variations=50)
        
        assert len(variations) > 0
        assert len(variations) <= 50
        assert all(v.original == "testuser" for v in variations)
        assert all(v.similarity_score >= 0.0 and v.similarity_score <= 1.0 for v in variations)
        
        # Check for high-risk variations
        high_risk = [v for v in variations if v.risk_level == 'high']
        assert len(high_risk) > 0
    
    def test_character_substitutions(self):
        """Test character substitution variations."""
        settings = SocialMediaSettings()
        generator = UsernameGenerator(settings)
        
        variations = generator._generate_substitution_variations("test")
        variation_strings = {v[0] for v in variations}
        
        # Should include substitutions like 't3st', 'test' with '@'
        assert any('@' in var for var in variation_strings)
        assert any('3' in var for var in variation_strings)
    
    def test_similarity_calculation(self):
        """Test similarity calculation between usernames."""
        settings = SocialMediaSettings()
        generator = UsernameGenerator(settings)
        
        # Very similar usernames
        similarity = generator._calculate_similarity("testuser", "testuser1")
        assert similarity > 0.8
        
        # Less similar usernames
        similarity = generator._calculate_similarity("testuser", "completely_different")
        assert similarity < 0.5
        
        # Identical usernames
        similarity = generator._calculate_similarity("testuser", "testuser")
        assert similarity == 1.0
    
    def test_risk_assessment(self):
        """Test risk level assessment."""
        settings = SocialMediaSettings()
        generator = UsernameGenerator(settings)
        
        # High similarity should be high risk
        risk = generator._assess_risk_level("testuser", "testuser1", 0.95)
        assert risk == 'high'
        
        # Medium similarity should be medium risk
        risk = generator._assess_risk_level("testuser", "testuser123", 0.75)
        assert risk == 'medium'
        
        # Low similarity should be low risk
        risk = generator._assess_risk_level("testuser", "completely_different", 0.3)
        assert risk == 'low'
    
    @pytest.mark.asyncio
    async def test_username_monitoring_workflow(self, username_monitor):
        """Test complete username monitoring workflow."""
        # Mock the API clients and scrapers
        with patch('app.services.social_media.username_monitor.create_api_client') as mock_api, \
             patch('app.services.social_media.username_monitor.create_scraper') as mock_scraper:
            
            # Mock API client
            mock_client = AsyncMock()
            mock_client.get_profile.return_value = ProfileData(
                username="testuser1",
                display_name="Test User",
                bio="Test bio",
                follower_count=1000,
                url="https://instagram.com/testuser1"
            )
            mock_api.return_value.__aenter__.return_value = mock_client
            
            # Mock scraper
            mock_scraper_instance = AsyncMock()
            mock_scraper_instance.scrape_profile.return_value = ProfileData(
                username="testuser2",
                display_name="Test User 2",
                bio="Another test bio", 
                follower_count=500,
                url="https://twitter.com/testuser2"
            )
            mock_scraper.return_value = mock_scraper_instance
            
            # Run monitoring
            results = await username_monitor.monitor_username(
                "testuser",
                [SocialMediaPlatform.INSTAGRAM, SocialMediaPlatform.TWITTER]
            )
            
            assert SocialMediaPlatform.INSTAGRAM in results
            assert SocialMediaPlatform.TWITTER in results
            
            # Should have found some matches
            instagram_matches = results[SocialMediaPlatform.INSTAGRAM]
            twitter_matches = results[SocialMediaPlatform.TWITTER]
            
            assert isinstance(instagram_matches, list)
            assert isinstance(twitter_matches, list)


class TestFaceMatching:
    """Test face matching functionality."""
    
    @pytest.fixture
    def settings(self):
        return SocialMediaSettings()
    
    @pytest.fixture
    def face_matcher(self, settings):
        return ProfileImageAnalyzer(settings)
    
    @pytest.mark.asyncio
    async def test_profile_similarity_analysis(self, face_matcher):
        """Test profile similarity analysis."""
        original_profile = ProfileData(
            username="original",
            display_name="Original User",
            profile_image_url="https://example.com/original.jpg"
        )
        
        candidate_profile = ProfileData(
            username="fake",
            display_name="Fake User", 
            profile_image_url="https://example.com/fake.jpg"
        )
        
        # Mock image downloading and analysis
        with patch.object(face_matcher.face_matcher.image_processor, 'download_image') as mock_download:
            mock_download.return_value = b"fake image data"
            
            with patch.object(face_matcher.image_matcher, 'compare_images') as mock_compare:
                mock_compare.return_value = ImageMatch(
                    similarity_score=0.85,
                    hash_similarity=0.9,
                    confidence_level="high"
                )
                
                analysis = await face_matcher.analyze_profile_similarity(
                    original_profile,
                    candidate_profile
                )
                
                assert analysis['overall_similarity'] > 0.0
                assert 'image_similarity' in analysis['analysis_methods']
                assert analysis['image_match'] is not None
    
    @pytest.mark.asyncio
    async def test_batch_candidate_analysis(self, face_matcher):
        """Test batch analysis of candidate profiles."""
        original_profile = ProfileData(
            username="original",
            profile_image_url="https://example.com/original.jpg"
        )
        
        candidates = [
            ProfileData(username="candidate1", profile_image_url="https://example.com/c1.jpg"),
            ProfileData(username="candidate2", profile_image_url="https://example.com/c2.jpg"),
        ]
        
        # Mock the analysis
        with patch.object(face_matcher, 'analyze_profile_similarity') as mock_analyze:
            mock_analyze.return_value = {
                'overall_similarity': 0.75,
                'confidence_level': 'medium',
                'analysis_methods': ['image_similarity']
            }
            
            results = await face_matcher.batch_analyze_candidates(
                original_profile,
                candidates
            )
            
            assert len(results) == 2
            assert 'candidate1' in results
            assert 'candidate2' in results
            
            # Results should be sorted by similarity
            usernames = list(results.keys())
            similarities = [results[u]['overall_similarity'] for u in usernames]
            assert similarities == sorted(similarities, reverse=True)


class TestFakeDetection:
    """Test fake account detection."""
    
    @pytest.fixture
    def settings(self):
        return SocialMediaSettings()
    
    @pytest.fixture
    def fake_detector(self, settings):
        return FakeAccountDetector(settings)
    
    @pytest.mark.asyncio
    async def test_fake_account_analysis(self, fake_detector):
        """Test fake account analysis."""
        # Create a suspicious profile
        suspicious_profile = ProfileData(
            username="user123456789",  # Long numeric suffix
            display_name="Real User Official",  # Legitimacy claims
            bio="Click here for free content!",  # Spam content
            follower_count=10,
            following_count=5000,  # Suspicious ratio
            post_count=0,  # No posts but followers
            is_verified=False
        )
        
        result = await fake_detector.analyze_account(suspicious_profile, SocialMediaPlatform.INSTAGRAM)
        
        assert isinstance(result, FakeAccountScore)
        assert result.overall_score > 0.5  # Should be suspicious
        assert len(result.features) > 0
        assert len(result.reasons) > 0
        
        # Check for specific suspicious features
        feature_names = [f.name for f in result.features]
        assert "username_pattern_suspicious" in feature_names
        assert "low_follower_ratio" in feature_names
        assert "bio_spam_content" in feature_names
    
    @pytest.mark.asyncio
    async def test_batch_fake_analysis(self, fake_detector):
        """Test batch fake account analysis."""
        profiles = [
            ProfileData(username="normal_user", display_name="Normal User", follower_count=500, following_count=300),
            ProfileData(username="user12345678", display_name="Official Real", follower_count=10, following_count=2000),
        ]
        
        results = await fake_detector.batch_analyze_accounts(profiles, SocialMediaPlatform.TWITTER)
        
        assert len(results) == 2
        assert "normal_user" in results
        assert "user12345678" in results
        
        # Suspicious account should have higher score
        assert results["user12345678"].overall_score > results["normal_user"].overall_score
    
    def test_ranking_by_suspicion(self, fake_detector):
        """Test ranking accounts by suspicion level."""
        analysis_results = {
            "user1": FakeAccountScore(0.3, "low", "legitimate", [], []),
            "user2": FakeAccountScore(0.8, "high", "likely_fake", [], []),
            "user3": FakeAccountScore(0.6, "medium", "suspicious", [], []),
        }
        
        ranked = fake_detector.rank_accounts_by_suspicion(analysis_results)
        
        # Should be sorted by score (highest first)
        assert ranked[0][0] == "user2"  # Highest score
        assert ranked[1][0] == "user3"  # Medium score
        assert ranked[2][0] == "user1"  # Lowest score
    
    def test_summary_report_generation(self, fake_detector):
        """Test summary report generation."""
        analysis_results = {
            "user1": FakeAccountScore(0.3, "low", "legitimate", [], []),
            "user2": FakeAccountScore(0.9, "high", "definitely_fake", [], ["High confidence fake"]),
            "user3": FakeAccountScore(0.7, "high", "likely_fake", [], ["Likely fake account"]),
        }
        
        summary = fake_detector.generate_summary_report(analysis_results)
        
        assert summary["total_accounts"] == 3
        assert summary["risk_distribution"]["legitimate"] == 1
        assert summary["risk_distribution"]["definitely_fake"] == 1
        assert summary["risk_distribution"]["likely_fake"] == 1
        assert len(summary["high_priority_alerts"]) == 2  # user2 and user3


class TestReporting:
    """Test automated reporting system."""
    
    @pytest.fixture
    def config(self):
        return MonitoringConfig()
    
    @pytest.fixture
    def reporting_service(self, config):
        return AutomatedReportingService(config)
    
    @pytest.mark.asyncio
    async def test_report_creation(self, reporting_service):
        """Test report creation."""
        impersonation_data = {
            "platform": "instagram",
            "fake_username": "fake_user",
            "fake_url": "https://instagram.com/fake_user",
            "original_username": "real_user",
            "original_url": "https://instagram.com/real_user",
            "reporter_name": "John Doe",
            "contact_email": "john@example.com",
            "similarity_score": 0.9,
            "confidence_score": 0.85
        }
        
        with patch.object(reporting_service.evidence_manager, 'prepare_evidence_package') as mock_evidence:
            mock_evidence.return_value = []
            
            report = await reporting_service.create_report(impersonation_data)
            
            assert isinstance(report, ReportSubmission)
            assert report.platform == SocialMediaPlatform.INSTAGRAM
            assert report.target_username == "fake_user"
            assert report.target_url == "https://instagram.com/fake_user"
            assert "subject" in report.report_content
            assert "body" in report.report_content
    
    @pytest.mark.asyncio
    async def test_batch_report_creation(self, reporting_service):
        """Test batch report creation."""
        impersonations = [
            {
                "platform": "instagram",
                "fake_username": "fake1",
                "fake_url": "https://instagram.com/fake1",
                "original_username": "real",
                "original_url": "https://instagram.com/real",
                "reporter_name": "Reporter",
                "contact_email": "reporter@example.com"
            },
            {
                "platform": "twitter", 
                "fake_username": "fake2",
                "fake_url": "https://twitter.com/fake2",
                "original_username": "real",
                "original_url": "https://twitter.com/real",
                "reporter_name": "Reporter",
                "contact_email": "reporter@example.com"
            }
        ]
        
        with patch.object(reporting_service.evidence_manager, 'prepare_evidence_package') as mock_evidence:
            mock_evidence.return_value = []
            
            reports = await reporting_service.batch_create_reports(impersonations)
            
            assert len(reports) == 2
            assert reports[0].platform == SocialMediaPlatform.INSTAGRAM
            assert reports[1].platform == SocialMediaPlatform.TWITTER
    
    def test_report_summary(self, reporting_service):
        """Test reporting summary generation."""
        from app.services.social_media.reporting import ReportStatus
        
        submissions = [
            ReportSubmission(
                report_id="1",
                platform=SocialMediaPlatform.INSTAGRAM,
                report_type="impersonation",
                target_username="fake1",
                target_url="https://instagram.com/fake1",
                reporter_info={},
                report_content={},
                evidence=[],
                status=ReportStatus.SUBMITTED
            ),
            ReportSubmission(
                report_id="2",
                platform=SocialMediaPlatform.TWITTER,
                report_type="impersonation", 
                target_username="fake2",
                target_url="https://twitter.com/fake2",
                reporter_info={},
                report_content={},
                evidence=[],
                status=ReportStatus.ACCEPTED
            )
        ]
        
        summary = reporting_service.generate_reporting_summary(submissions)
        
        assert summary["total_reports"] == 2
        assert summary["platform_distribution"]["instagram"] == 1
        assert summary["platform_distribution"]["twitter"] == 1
        assert summary["status_distribution"]["submitted"] == 1
        assert summary["status_distribution"]["accepted"] == 1
        assert summary["success_rate"] == 100.0  # Both submitted/accepted are successful


class TestTaskQueue:
    """Test task queue functionality."""
    
    @pytest.fixture
    def task_queue(self):
        return TaskQueue(max_size=100)
    
    @pytest.mark.asyncio
    async def test_task_queue_operations(self, task_queue):
        """Test basic task queue operations."""
        from app.services.social_media.scheduler import ScheduledTask, TaskPriority
        
        # Create test tasks
        high_priority_task = ScheduledTask(
            task_id="high_task",
            profile_id=1,
            platforms=[SocialMediaPlatform.INSTAGRAM],
            task_type="one_time",
            priority=TaskPriority.HIGH,
            next_run=datetime.now()
        )
        
        low_priority_task = ScheduledTask(
            task_id="low_task",
            profile_id=1,
            platforms=[SocialMediaPlatform.TWITTER],
            task_type="periodic",
            priority=TaskPriority.LOW,
            next_run=datetime.now()
        )
        
        # Add tasks
        assert await task_queue.put(low_priority_task) == True
        assert await task_queue.put(high_priority_task) == True
        assert await task_queue.size() == 2
        
        # Higher priority task should come first
        next_task = await task_queue.get()
        assert next_task.task_id == "high_task"
        
        # Lower priority task should come second
        next_task = await task_queue.get()
        assert next_task.task_id == "low_task"
        
        # Queue should be empty
        assert await task_queue.size() == 0
    
    @pytest.mark.asyncio
    async def test_task_queue_capacity(self, task_queue):
        """Test task queue capacity limits."""
        from app.services.social_media.scheduler import ScheduledTask, TaskPriority
        
        # Fill queue to capacity
        task_queue.max_size = 2
        
        task1 = ScheduledTask("task1", 1, [SocialMediaPlatform.INSTAGRAM], "test")
        task2 = ScheduledTask("task2", 1, [SocialMediaPlatform.TWITTER], "test")
        task3 = ScheduledTask("task3", 1, [SocialMediaPlatform.FACEBOOK], "test")
        
        assert await task_queue.put(task1) == True
        assert await task_queue.put(task2) == True
        assert await task_queue.put(task3) == False  # Should fail due to capacity


class TestMonitoringService:
    """Test main monitoring service."""
    
    @pytest.fixture
    def config(self):
        return MonitoringConfig()
    
    @pytest.fixture
    def monitoring_service(self, config):
        return SocialMediaMonitoringService(config)
    
    @pytest.mark.asyncio
    async def test_monitoring_job_creation(self, monitoring_service):
        """Test monitoring job creation."""
        job_id = await monitoring_service.start_monitoring(
            profile_id=1,
            platforms=[SocialMediaPlatform.INSTAGRAM, SocialMediaPlatform.TWITTER],
            monitoring_type="comprehensive"
        )
        
        assert job_id is not None
        assert len(monitoring_service.pending_jobs) == 1
        
        job = monitoring_service.pending_jobs[0]
        assert job.profile_id == 1
        assert len(job.platforms) == 2
        assert job.monitoring_type == "comprehensive"
    
    def test_statistics_tracking(self, monitoring_service):
        """Test statistics tracking."""
        stats = monitoring_service.get_monitoring_statistics()
        
        assert "jobs_completed" in stats
        assert "impersonations_found" in stats
        assert "reports_submitted" in stats
        assert "platforms_monitored" in stats
        assert "last_activity" in stats
    
    def test_job_status_tracking(self, monitoring_service):
        """Test job status tracking."""
        # Initially no jobs
        status = monitoring_service.get_job_status("nonexistent")
        assert status["status"] == "not_found"
        
        # Add a pending job
        from app.services.social_media.monitoring_service import MonitoringJob
        job = MonitoringJob(
            job_id="test_job",
            profile_id=1,
            platforms=[SocialMediaPlatform.INSTAGRAM],
            monitoring_type="test"
        )
        monitoring_service.pending_jobs.append(job)
        
        status = monitoring_service.get_job_status("test_job")
        assert status["status"] == "pending"
        assert status["job_id"] == "test_job"


class TestScheduler:
    """Test monitoring scheduler."""
    
    @pytest.fixture
    def config(self):
        return MonitoringConfig()
    
    @pytest.fixture 
    def monitoring_service(self, config):
        return SocialMediaMonitoringService(config)
    
    @pytest.fixture
    def scheduler(self, config, monitoring_service):
        return MonitoringScheduler(config, monitoring_service)
    
    @pytest.mark.asyncio
    async def test_scheduled_task_creation(self, scheduler):
        """Test creation of scheduled tasks."""
        task_id = await scheduler.schedule_profile_monitoring(
            profile_id=1,
            platforms=[SocialMediaPlatform.INSTAGRAM],
            schedule_type="daily"
        )
        
        assert task_id is not None
        assert task_id in scheduler.scheduled_tasks
        
        task = scheduler.scheduled_tasks[task_id]
        assert task.profile_id == 1
        assert task.task_type == "periodic"
        assert task.schedule_expression == "0 9 * * *"  # Daily at 9 AM
    
    @pytest.mark.asyncio
    async def test_one_time_task_creation(self, scheduler):
        """Test creation of one-time tasks."""
        run_time = datetime.now() + timedelta(minutes=5)
        
        task_id = await scheduler.schedule_one_time_monitoring(
            profile_id=1,
            platforms=[SocialMediaPlatform.TWITTER],
            run_at=run_time
        )
        
        assert task_id is not None
        task = scheduler.scheduled_tasks[task_id]
        assert task.task_type == "one_time"
        assert task.next_run == run_time
    
    @pytest.mark.asyncio
    async def test_emergency_monitoring(self, scheduler):
        """Test emergency monitoring scheduling."""
        from app.services.social_media.scheduler import TaskPriority
        
        task_id = await scheduler.schedule_emergency_monitoring(
            profile_id=1,
            platforms=[SocialMediaPlatform.INSTAGRAM, SocialMediaPlatform.TWITTER],
            reason="Urgent impersonation detected"
        )
        
        assert task_id is not None
        task = scheduler.scheduled_tasks[task_id]
        assert task.task_type == "emergency"
        assert task.priority == TaskPriority.EMERGENCY
        assert "Urgent impersonation detected" in task.metadata["reason"]
    
    @pytest.mark.asyncio
    async def test_task_cancellation(self, scheduler):
        """Test task cancellation."""
        task_id = await scheduler.schedule_profile_monitoring(
            profile_id=1,
            platforms=[SocialMediaPlatform.INSTAGRAM],
            schedule_type="daily"
        )
        
        # Cancel the task
        success = await scheduler.cancel_task(task_id)
        assert success == True
        
        # Task should be marked as cancelled
        task = scheduler.scheduled_tasks[task_id]
        assert task.enabled == False
    
    @pytest.mark.asyncio
    async def test_profile_monitoring_pause_resume(self, scheduler):
        """Test pausing and resuming profile monitoring."""
        # Create multiple tasks for a profile
        task1_id = await scheduler.schedule_profile_monitoring(
            profile_id=1,
            platforms=[SocialMediaPlatform.INSTAGRAM],
            schedule_type="daily"
        )
        task2_id = await scheduler.schedule_profile_monitoring(
            profile_id=1,
            platforms=[SocialMediaPlatform.TWITTER],
            schedule_type="hourly"
        )
        
        # Pause monitoring
        paused_count = await scheduler.pause_profile_monitoring(1)
        assert paused_count == 2
        
        # Tasks should be disabled
        assert scheduler.scheduled_tasks[task1_id].enabled == False
        assert scheduler.scheduled_tasks[task2_id].enabled == False
        
        # Resume monitoring
        resumed_count = await scheduler.resume_profile_monitoring(1)
        assert resumed_count == 2
        
        # Tasks should be re-enabled
        assert scheduler.scheduled_tasks[task1_id].enabled == True
        assert scheduler.scheduled_tasks[task2_id].enabled == True
    
    def test_scheduler_statistics(self, scheduler):
        """Test scheduler statistics."""
        stats = scheduler.get_scheduler_statistics()
        
        assert "total_tasks" in stats
        assert "active_profiles" in stats
        assert "task_status_distribution" in stats
        assert "task_type_distribution" in stats
        assert "scheduler_running" in stats


class TestIntegration:
    """Integration tests for the complete social media monitoring system."""
    
    @pytest.fixture
    def config(self):
        return MonitoringConfig()
    
    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_workflow(self, config):
        """Test complete end-to-end monitoring workflow."""
        # This is a simplified integration test
        # In reality, this would involve actual database operations
        
        monitoring_service = SocialMediaMonitoringService(config)
        scheduler = MonitoringScheduler(config, monitoring_service)
        
        # Schedule monitoring
        task_id = await scheduler.schedule_profile_monitoring(
            profile_id=1,
            platforms=[SocialMediaPlatform.INSTAGRAM],
            schedule_type="daily"
        )
        
        assert task_id is not None
        
        # Verify task is scheduled
        task_details = await scheduler.get_task_details(task_id)
        assert task_details is not None
        assert task_details["profile_id"] == 1
        
        # Get monitoring statistics
        stats = monitoring_service.get_monitoring_statistics()
        assert stats is not None
    
    @pytest.mark.asyncio
    async def test_error_handling_and_resilience(self, config):
        """Test error handling and system resilience."""
        monitoring_service = SocialMediaMonitoringService(config)
        
        # Test handling of invalid profile ID
        try:
            await monitoring_service.monitor_profile(-1, [SocialMediaPlatform.INSTAGRAM])
            # Should handle gracefully and not crash
        except Exception:
            pass  # Expected in this test setup
        
        # Service should still be functional
        stats = monitoring_service.get_monitoring_statistics()
        assert stats is not None


# Test execution helper
if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])