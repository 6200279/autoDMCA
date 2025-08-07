"""
Integration tests for the main ContentScanner.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from scanning.scanner import ContentScanner
from scanning.config import ScannerConfig


class TestContentScanner:
    """Test main ContentScanner functionality."""
    
    @pytest.mark.asyncio
    async def test_scanner_initialization(self, test_config):
        """Test scanner initialization."""
        scanner = ContentScanner(test_config)
        
        # Mock all the components
        with patch.object(scanner.task_manager, 'initialize', new_callable=AsyncMock), \
             patch.object(scanner.task_manager, 'schedule_system_tasks', new_callable=AsyncMock):
            
            await scanner.initialize()
            
            assert scanner._running
            scanner.task_manager.initialize.assert_called_once()
            scanner.task_manager.schedule_system_tasks.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scanner_close(self, test_config):
        """Test scanner shutdown."""
        scanner = ContentScanner(test_config)
        
        with patch.object(scanner.task_manager, 'close', new_callable=AsyncMock):
            scanner._running = True
            
            await scanner.close()
            
            assert not scanner._running
            scanner.task_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_person_success(self, test_config):
        """Test adding a person for monitoring."""
        scanner = ContentScanner(test_config)
        
        with patch.object(
            scanner.task_manager, 
            'add_person_profile', 
            new_callable=AsyncMock,
            return_value=True
        ):
            
            success = await scanner.add_person(
                person_id="test_user",
                reference_images=["https://example.com/image1.jpg"],
                usernames=["testuser", "test_user"],
                email="test@example.com"
            )
            
            assert success
            scanner.task_manager.add_person_profile.assert_called_once()
            
            # Verify call arguments
            call_args = scanner.task_manager.add_person_profile.call_args
            assert call_args.kwargs['person_id'] == "test_user"
            assert call_args.kwargs['usernames'] == ["testuser", "test_user"]
    
    @pytest.mark.asyncio
    async def test_add_person_failure(self, test_config):
        """Test adding person when task manager fails."""
        scanner = ContentScanner(test_config)
        
        with patch.object(
            scanner.task_manager,
            'add_person_profile',
            new_callable=AsyncMock,
            return_value=False
        ):
            
            success = await scanner.add_person(
                person_id="test_user",
                reference_images=["https://example.com/image1.jpg"],
                usernames=["testuser"],
                email="test@example.com"
            )
            
            assert not success
    
    @pytest.mark.asyncio
    async def test_remove_person(self, test_config):
        """Test removing a person from monitoring."""
        scanner = ContentScanner(test_config)
        
        # Mock scheduler and content matcher
        mock_tasks = [
            MagicMock(task_id="task1"),
            MagicMock(task_id="task2")
        ]
        
        with patch.object(
            scanner.task_manager.scheduler,
            'get_tasks_for_person',
            new_callable=AsyncMock,
            return_value=mock_tasks
        ), patch.object(
            scanner.task_manager.scheduler,
            'cancel_task',
            new_callable=AsyncMock,
            return_value=True
        ), patch.object(
            scanner.task_manager.content_matcher,
            'remove_person',
            new_callable=AsyncMock,
            return_value=True
        ):
            
            success = await scanner.remove_person("test_user")
            
            assert success
            # Should cancel all person's tasks
            assert scanner.task_manager.scheduler.cancel_task.call_count == 2
            scanner.task_manager.content_matcher.remove_person.assert_called_once_with("test_user")
    
    @pytest.mark.asyncio
    async def test_trigger_immediate_scan(self, test_config):
        """Test triggering immediate scan."""
        scanner = ContentScanner(test_config)
        
        with patch.object(
            scanner.task_manager.scheduler,
            'schedule_task',
            new_callable=AsyncMock,
            return_value="task_123"
        ):
            
            task_id = await scanner.trigger_immediate_scan(
                person_id="test_user",
                scan_type="full",
                priority=True
            )
            
            assert task_id == "task_123"
            scanner.task_manager.scheduler.schedule_task.assert_called_once()
            
            # Check call arguments
            call_args = scanner.task_manager.scheduler.schedule_task.call_args
            assert call_args.kwargs['task_type'] == "full_scan"
            assert call_args.kwargs['person_id'] == "test_user"
            assert call_args.kwargs['parameters']['priority'] is True
    
    @pytest.mark.asyncio
    async def test_get_person_status(self, test_config):
        """Test getting person status."""
        scanner = ContentScanner(test_config)
        
        # Mock data
        mock_stats = {
            'face_encodings': 3,
            'image_hashes': 5,
            'keywords': 10
        }
        
        mock_tasks = [
            MagicMock(
                task_id="task1",
                task_type="full_scan",
                status=MagicMock(value="running"),
                last_run_at=1234567890,
                next_run_at=1234567900,
                run_count=5,
                success_count=4
            )
        ]
        
        with patch.object(
            scanner.task_manager.content_matcher,
            'get_person_statistics',
            new_callable=AsyncMock,
            return_value=mock_stats
        ), patch.object(
            scanner.task_manager.scheduler,
            'get_tasks_for_person',
            new_callable=AsyncMock,
            return_value=mock_tasks
        ):
            
            status = await scanner.get_person_status("test_user")
            
            assert status['person_id'] == "test_user"
            assert status['profile_stats'] == mock_stats
            assert status['active_tasks'] == 1
            assert len(status['task_details']) == 1
            assert status['protection_active'] is True
    
    @pytest.mark.asyncio
    async def test_get_dmca_status(self, test_config):
        """Test getting DMCA status."""
        scanner = ContentScanner(test_config)
        
        mock_queue_status = {
            'pending': 5,
            'processing': 2,
            'completed': 15,
            'failed': 1
        }
        
        with patch.object(
            scanner.task_manager.dmca_queue,
            'get_queue_status',
            new_callable=AsyncMock,
            return_value=mock_queue_status
        ):
            
            status = await scanner.get_dmca_status()
            
            assert status['queue_status'] == mock_queue_status
            assert status['total_pending'] == 7  # pending + processing
            assert status['total_completed'] == 15
            assert status['total_failed'] == 1
    
    @pytest.mark.asyncio
    async def test_get_system_health(self, test_config):
        """Test getting system health."""
        scanner = ContentScanner(test_config)
        
        mock_health = {
            'system_status': 'operational',
            'scheduler': {'total_tasks': 10},
            'dmca_queue': {'pending': 5},
            'healthy': True
        }
        
        with patch.object(
            scanner.task_manager,
            'get_system_status',
            new_callable=AsyncMock,
            return_value=mock_health
        ):
            
            health = await scanner.get_system_health()
            
            assert health == mock_health
    
    @pytest.mark.asyncio
    async def test_manual_scan_url_success(self, test_config):
        """Test manual URL scanning."""
        scanner = ContentScanner(test_config)
        
        # Mock crawl result
        mock_crawl_result = MagicMock()
        mock_crawl_result.is_success = True
        mock_crawl_result.title = "Test Page"
        mock_crawl_result.url = "https://example.com/test"
        mock_crawl_result.text_content = "Some test content"
        mock_crawl_result.images = ["https://example.com/image1.jpg"]
        
        # Mock content matches
        mock_matches = [
            MagicMock(is_positive_match=True, person_id="test_user", confidence_score=0.9)
        ]
        
        with patch('scanning.scanner.WebCrawler') as MockWebCrawler, \
             patch.object(
                 scanner.task_manager.content_matcher,
                 'match_content',
                 new_callable=AsyncMock,
                 return_value=mock_matches
             ):
            
            mock_crawler = MockWebCrawler.return_value
            mock_crawler.initialize = AsyncMock()
            mock_crawler.close = AsyncMock()
            mock_crawler.crawl = AsyncMock(return_value=mock_crawl_result)
            
            matches = await scanner.manual_scan_url("https://example.com/test")
            
            assert len(matches) == 1
            assert matches[0].is_positive_match
            
            mock_crawler.crawl.assert_called_once_with("https://example.com/test")
    
    @pytest.mark.asyncio
    async def test_manual_scan_url_failure(self, test_config):
        """Test manual URL scanning with crawl failure."""
        scanner = ContentScanner(test_config)
        
        mock_crawl_result = MagicMock()
        mock_crawl_result.is_success = False
        mock_crawl_result.error = "Connection failed"
        
        with patch('scanning.scanner.WebCrawler') as MockWebCrawler:
            mock_crawler = MockWebCrawler.return_value
            mock_crawler.initialize = AsyncMock()
            mock_crawler.close = AsyncMock()
            mock_crawler.crawl = AsyncMock(return_value=mock_crawl_result)
            
            matches = await scanner.manual_scan_url("https://example.com/test")
            
            assert len(matches) == 0
    
    @pytest.mark.asyncio
    async def test_export_person_data(self, test_config):
        """Test exporting person data."""
        scanner = ContentScanner(test_config)
        
        mock_stats = {
            'face_encodings': 3,
            'image_hashes': 5,
            'keywords': 10
        }
        
        mock_tasks = [
            MagicMock(to_dict=MagicMock(return_value={'task_id': 'task1'}))
        ]
        
        with patch.object(
            scanner.task_manager.content_matcher,
            'get_person_statistics',
            new_callable=AsyncMock,
            return_value=mock_stats
        ), patch.object(
            scanner.task_manager.scheduler,
            'get_tasks_for_person',
            new_callable=AsyncMock,
            return_value=mock_tasks
        ):
            
            export_data = await scanner.export_person_data("test_user")
            
            assert export_data['person_id'] == "test_user"
            assert 'export_timestamp' in export_data
            assert export_data['profile_statistics'] == mock_stats
            assert len(export_data['active_tasks']) == 1


class TestContentScannerErrorHandling:
    """Test error handling in ContentScanner."""
    
    @pytest.mark.asyncio
    async def test_add_person_exception(self, test_config):
        """Test exception handling in add_person."""
        scanner = ContentScanner(test_config)
        
        with patch.object(
            scanner.task_manager,
            'add_person_profile',
            new_callable=AsyncMock,
            side_effect=Exception("Database error")
        ):
            
            success = await scanner.add_person(
                person_id="test_user",
                reference_images=["https://example.com/image1.jpg"],
                usernames=["testuser"],
                email="test@example.com"
            )
            
            assert not success
    
    @pytest.mark.asyncio
    async def test_get_person_status_exception(self, test_config):
        """Test exception handling in get_person_status."""
        scanner = ContentScanner(test_config)
        
        with patch.object(
            scanner.task_manager.content_matcher,
            'get_person_statistics',
            new_callable=AsyncMock,
            side_effect=Exception("Service unavailable")
        ):
            
            status = await scanner.get_person_status("test_user")
            
            assert 'error' in status
            assert "Service unavailable" in status['error']
    
    @pytest.mark.asyncio
    async def test_get_system_health_exception(self, test_config):
        """Test exception handling in get_system_health."""
        scanner = ContentScanner(test_config)
        
        with patch.object(
            scanner.task_manager,
            'get_system_status',
            new_callable=AsyncMock,
            side_effect=Exception("Health check failed")
        ):
            
            health = await scanner.get_system_health()
            
            assert health['system_status'] == 'error'
            assert 'Health check failed' in health['error']


class TestScannerConfiguration:
    """Test scanner configuration handling."""
    
    def test_scanner_with_default_config(self):
        """Test scanner with default configuration."""
        scanner = ContentScanner()
        
        assert scanner.config is not None
        assert isinstance(scanner.config, ScannerConfig)
    
    def test_scanner_with_custom_config(self, test_config):
        """Test scanner with custom configuration."""
        scanner = ContentScanner(test_config)
        
        assert scanner.config == test_config
        assert scanner.config.settings.face_recognition_tolerance == 0.6