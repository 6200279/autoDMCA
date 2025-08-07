"""
Tests for task manager and scheduling system.
"""

import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock

from scanning.scheduler.task_manager import TaskManager
from scanning.scheduler.scan_scheduler import ScanTask, TaskStatus, TaskPriority


class TestTaskManager:
    """Test TaskManager functionality."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, test_config):
        """Test task manager initialization."""
        task_manager = TaskManager(test_config)
        
        # Mock all component initializations
        with patch.object(task_manager.scheduler, 'initialize', new_callable=AsyncMock), \
             patch.object(task_manager.piracy_crawler, 'initialize', new_callable=AsyncMock), \
             patch.object(task_manager.content_matcher, 'initialize', new_callable=AsyncMock), \
             patch.object(task_manager.dmca_queue, 'initialize', new_callable=AsyncMock), \
             patch.object(task_manager.notification_sender, 'initialize', new_callable=AsyncMock):
            
            await task_manager.initialize()
            
            assert task_manager._initialized
            
            # Verify all components were initialized
            task_manager.scheduler.initialize.assert_called_once()
            task_manager.piracy_crawler.initialize.assert_called_once()
            task_manager.content_matcher.initialize.assert_called_once()
            task_manager.dmca_queue.initialize.assert_called_once()
            task_manager.notification_sender.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_person_profile_success(self, test_config):
        """Test adding person profile successfully."""
        task_manager = TaskManager(test_config)
        
        with patch.object(task_manager.content_matcher, 'add_person_profile', new_callable=AsyncMock, return_value=True), \
             patch.object(task_manager, '_schedule_person_tasks', new_callable=AsyncMock):
            
            success = await task_manager.add_person_profile(
                person_id="test_user",
                reference_images=["image1.jpg", "image2.jpg"],
                usernames=["testuser", "test_user"],
                additional_keywords=["leaked", "premium"]
            )
            
            assert success
            task_manager.content_matcher.add_person_profile.assert_called_once()
            task_manager._schedule_person_tasks.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_schedule_person_tasks(self, test_config):
        """Test scheduling tasks for a person."""
        task_manager = TaskManager(test_config)
        task_manager.scheduler = AsyncMock()
        
        await task_manager._schedule_person_tasks(
            person_id="test_user",
            scan_interval_hours=12,
            priority_scan=True
        )
        
        # Should schedule multiple task types
        assert task_manager.scheduler.schedule_task.call_count >= 2
        
        # Check that priority tasks are scheduled with HIGH priority
        calls = task_manager.scheduler.schedule_task.call_args_list
        priority_calls = [call for call in calls if call.kwargs.get('priority') == TaskPriority.HIGH]
        assert len(priority_calls) > 0
    
    @pytest.mark.asyncio
    async def test_handle_full_scan(self, test_config, sample_infringing_content):
        """Test handling full scan task."""
        task_manager = TaskManager(test_config)
        
        # Create test task
        task = ScanTask(
            task_id="test_task",
            task_type="full_scan",
            person_id="test_user",
            parameters={"comprehensive": True}
        )
        
        # Mock methods
        with patch.object(task_manager, '_get_search_terms_for_person', return_value=["test_user"]), \
             patch.object(task_manager, '_perform_search_engine_scan', new_callable=AsyncMock, return_value=sample_infringing_content[:1]), \
             patch.object(task_manager, '_perform_piracy_site_scan', new_callable=AsyncMock, return_value=sample_infringing_content[1:]), \
             patch.object(task_manager.content_matcher, 'bulk_match_content', new_callable=AsyncMock) as mock_match, \
             patch.object(task_manager, '_create_dmca_requests', new_callable=AsyncMock, return_value=2), \
             patch.object(task_manager, '_send_match_notifications', new_callable=AsyncMock):
            
            # Mock positive matches
            mock_matches = {
                'url1': [MagicMock(is_positive_match=True)],
                'url2': [MagicMock(is_positive_match=True)]
            }
            mock_match.return_value = mock_matches
            
            result = await task_manager._handle_full_scan(task)
            
            assert result['person_id'] == "test_user"
            assert result['scan_type'] == "full"
            assert len(result['search_results']) == 1
            assert len(result['piracy_results']) == 1
            assert result['content_matches'] == 2
            assert result['dmca_requests_created'] == 2
            assert 'processing_time' in result
    
    @pytest.mark.asyncio
    async def test_handle_search_engine_scan(self, test_config, sample_infringing_content):
        """Test handling search engine scan task."""
        task_manager = TaskManager(test_config)
        
        task = ScanTask(
            task_id="test_task",
            task_type="search_engine_scan",
            person_id="test_user",
            parameters={"quick_scan": True}
        )
        
        with patch.object(task_manager, '_get_search_terms_for_person', return_value=["test_user"]), \
             patch.object(task_manager, '_perform_search_engine_scan', new_callable=AsyncMock, return_value=sample_infringing_content), \
             patch.object(task_manager.content_matcher, 'bulk_match_content', new_callable=AsyncMock) as mock_match:
            
            # Mock high confidence matches
            mock_matches = {
                'url1': [MagicMock(is_high_confidence=True, is_positive_match=True)]
            }
            mock_match.return_value = mock_matches
            
            result = await task_manager._handle_search_engine_scan(task)
            
            assert result['person_id'] == "test_user"
            assert result['scan_type'] == "search_engine"
            assert len(result['results']) == 2
    
    @pytest.mark.asyncio
    async def test_handle_process_dmca_queue(self, test_config):
        """Test handling DMCA queue processing task."""
        task_manager = TaskManager(test_config)
        task_manager.dmca_queue = AsyncMock()
        task_manager.dmca_queue.process_pending_requests = AsyncMock(return_value=5)
        
        task = ScanTask(
            task_id="test_task",
            task_type="process_dmca_queue",
            person_id="system",
            parameters={"max_requests": 10}
        )
        
        result = await task_manager._handle_process_dmca_queue(task)
        
        assert result['task_type'] == "process_dmca_queue"
        assert result['processed_count'] == 5
        task_manager.dmca_queue.process_pending_requests.assert_called_once_with(max_requests=10)
    
    @pytest.mark.asyncio
    async def test_handle_send_notifications(self, test_config):
        """Test handling notification sending task."""
        task_manager = TaskManager(test_config)
        task_manager.notification_sender = AsyncMock()
        task_manager.notification_sender.process_notification_queue = AsyncMock(return_value=3)
        
        task = ScanTask(
            task_id="test_task",
            task_type="send_notifications",
            person_id="system",
            parameters={"batch_size": 5}
        )
        
        result = await task_manager._handle_send_notifications(task)
        
        assert result['task_type'] == "send_notifications"
        assert result['sent_count'] == 3
        task_manager.notification_sender.process_notification_queue.assert_called_once_with(batch_size=5)
    
    @pytest.mark.asyncio
    async def test_handle_maintenance(self, test_config):
        """Test handling maintenance task."""
        task_manager = TaskManager(test_config)
        
        # Mock cleanup methods
        task_manager.scheduler = AsyncMock()
        task_manager.dmca_queue = AsyncMock()
        task_manager.notification_sender = AsyncMock()
        
        task_manager.scheduler.cleanup_old_tasks = AsyncMock(return_value=5)
        task_manager.dmca_queue.cleanup_old_requests = AsyncMock(return_value=3)
        task_manager.notification_sender.cleanup_old_notifications = AsyncMock(return_value=7)
        
        task = ScanTask(
            task_id="test_task",
            task_type="maintenance",
            person_id="system",
            parameters={"days_old": 30}
        )
        
        result = await task_manager._handle_maintenance(task)
        
        assert result['task_type'] == "maintenance"
        assert result['tasks_cleaned'] == 5
        assert result['dmca_cleaned'] == 3
        assert result['notifications_cleaned'] == 7
    
    @pytest.mark.asyncio
    async def test_perform_search_engine_scan(self, test_config, mock_search_results):
        """Test performing search engine scan."""
        task_manager = TaskManager(test_config)
        task_manager.search_manager = AsyncMock()
        task_manager.search_manager.search_all = AsyncMock(return_value=mock_search_results)
        
        results = await task_manager._perform_search_engine_scan(
            person_id="test_user",
            search_terms=["test_user", "test_user leaked"],
            quick_scan=True
        )
        
        assert len(results) == 4  # 2 terms × 2 results each
        assert all(hasattr(result, 'title') for result in results)
        assert all(hasattr(result, 'url') for result in results)
    
    @pytest.mark.asyncio
    async def test_perform_piracy_site_scan(self, test_config, sample_infringing_content):
        """Test performing piracy site scan."""
        task_manager = TaskManager(test_config)
        task_manager.piracy_crawler = AsyncMock()
        
        # Mock crawl sessions
        mock_sessions = {
            'site1': MagicMock(results=sample_infringing_content[:1]),
            'site2': MagicMock(results=sample_infringing_content[1:])
        }
        task_manager.piracy_crawler.bulk_crawl = AsyncMock(return_value=mock_sessions)
        
        results = await task_manager._perform_piracy_site_scan(
            person_id="test_user",
            search_terms=["test_user"],
            comprehensive=True
        )
        
        assert len(results) == 2
        task_manager.piracy_crawler.bulk_crawl.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_dmca_requests(self, test_config):
        """Test creating DMCA requests from matches."""
        task_manager = TaskManager(test_config)
        task_manager.dmca_queue = AsyncMock()
        task_manager.dmca_queue.enqueue_request = AsyncMock(return_value=True)
        
        # Mock content matches
        mock_matches = [
            MagicMock(
                person_id="test_user",
                content=MagicMock(url="https://example.com/leak1")
            ),
            MagicMock(
                person_id="test_user",
                content=MagicMock(url="https://example.com/leak2")
            )
        ]
        
        created_count = await task_manager._create_dmca_requests(mock_matches, priority=True)
        
        assert created_count == 2
        assert task_manager.dmca_queue.enqueue_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_schedule_system_tasks(self, test_config):
        """Test scheduling system tasks."""
        task_manager = TaskManager(test_config)
        task_manager.scheduler = AsyncMock()
        
        await task_manager.schedule_system_tasks()
        
        # Should schedule multiple system tasks
        assert task_manager.scheduler.schedule_task.call_count >= 3
        
        # Check that different task types are scheduled
        calls = task_manager.scheduler.schedule_task.call_args_list
        task_types = {call.kwargs['task_type'] for call in calls}
        
        expected_types = {'process_dmca_queue', 'send_notifications', 'maintenance'}
        assert expected_types.issubset(task_types)
    
    @pytest.mark.asyncio
    async def test_get_system_status(self, test_config):
        """Test getting system status."""
        task_manager = TaskManager(test_config)
        
        # Mock component status methods
        task_manager.scheduler = AsyncMock()
        task_manager.dmca_queue = AsyncMock()
        task_manager.notification_sender = AsyncMock()
        
        task_manager.scheduler.get_scheduler_stats = AsyncMock(return_value={'total_tasks': 10})
        task_manager.dmca_queue.get_queue_status = AsyncMock(return_value={'pending': 5})
        task_manager.notification_sender.get_queue_stats = AsyncMock(return_value={'queued': 3})
        task_manager.scheduler.health_check = AsyncMock(return_value={'healthy': True})
        
        status = await task_manager.get_system_status()
        
        assert status['system_status'] == 'operational'
        assert 'scheduler' in status
        assert 'dmca_queue' in status
        assert 'notifications' in status
        assert 'health' in status
        assert 'timestamp' in status


class TestTaskManagerErrorHandling:
    """Test error handling in TaskManager."""
    
    @pytest.mark.asyncio
    async def test_handle_full_scan_exception(self, test_config):
        """Test exception handling in full scan."""
        task_manager = TaskManager(test_config)
        
        task = ScanTask(
            task_id="test_task",
            task_type="full_scan",
            person_id="test_user"
        )
        
        with patch.object(task_manager, '_get_search_terms_for_person', side_effect=Exception("Search failed")):
            
            with pytest.raises(Exception, match="Search failed"):
                await task_manager._handle_full_scan(task)
    
    @pytest.mark.asyncio
    async def test_create_dmca_requests_partial_failure(self, test_config):
        """Test DMCA request creation with partial failures."""
        task_manager = TaskManager(test_config)
        task_manager.dmca_queue = AsyncMock()
        
        # Mock some successes and some failures
        task_manager.dmca_queue.enqueue_request = AsyncMock(side_effect=[True, False, True])
        
        mock_matches = [MagicMock() for _ in range(3)]
        
        created_count = await task_manager._create_dmca_requests(mock_matches)
        
        assert created_count == 2  # Only 2 succeeded
    
    @pytest.mark.asyncio
    async def test_get_system_status_exception(self, test_config):
        """Test system status with component failure."""
        task_manager = TaskManager(test_config)
        task_manager.scheduler = AsyncMock()
        task_manager.scheduler.get_scheduler_stats = AsyncMock(side_effect=Exception("Scheduler error"))
        
        status = await task_manager.get_system_status()
        
        assert status['system_status'] == 'error'
        assert 'error' in status


class TestTaskManagerIntegration:
    """Integration tests for TaskManager."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, test_config, sample_infringing_content):
        """Test complete workflow from person addition to DMCA creation."""
        task_manager = TaskManager(test_config)
        
        # Mock all dependencies
        with patch.object(task_manager.content_matcher, 'add_person_profile', new_callable=AsyncMock, return_value=True), \
             patch.object(task_manager, '_schedule_person_tasks', new_callable=AsyncMock), \
             patch.object(task_manager, '_get_search_terms_for_person', return_value=["test_user"]), \
             patch.object(task_manager, '_perform_search_engine_scan', new_callable=AsyncMock, return_value=sample_infringing_content), \
             patch.object(task_manager, '_perform_piracy_site_scan', new_callable=AsyncMock, return_value=[]), \
             patch.object(task_manager.content_matcher, 'bulk_match_content', new_callable=AsyncMock) as mock_match, \
             patch.object(task_manager.dmca_queue, 'enqueue_request', new_callable=AsyncMock, return_value=True), \
             patch.object(task_manager.notification_sender, 'send_content_match_alert', new_callable=AsyncMock):
            
            # Setup mock matches
            positive_matches = [MagicMock(is_positive_match=True, person_id="test_user")]
            mock_match.return_value = {'url1': positive_matches}
            
            # 1. Add person
            success = await task_manager.add_person_profile(
                person_id="test_user",
                reference_images=["image1.jpg"],
                usernames=["testuser"]
            )
            assert success
            
            # 2. Simulate full scan task execution
            task = ScanTask(
                task_type="full_scan",
                person_id="test_user",
                parameters={"comprehensive": False}
            )
            
            result = await task_manager._handle_full_scan(task)
            
            # Verify workflow completed
            assert result['person_id'] == "test_user"
            assert result['dmca_requests_created'] == 1
            
            # Verify DMCA request was created
            task_manager.dmca_queue.enqueue_request.assert_called_once()
            
            # Verify notification was sent
            task_manager.notification_sender.send_content_match_alert.assert_called_once()