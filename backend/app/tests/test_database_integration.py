"""
Comprehensive database integration tests covering all models,
relationships, complex queries, and data integrity.
"""

import pytest
from sqlalchemy import text, func, and_, or_
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import uuid
from typing import List

from app.db.models.user import User
from app.db.models.profile import Profile
from app.db.models.takedown import TakedownRequest
from app.db.models.infringement import Infringement
from app.db.models.social_media import SocialMediaAccount, ImpersonationReport
from app.db.models.subscription import Subscription, BillingHistory
from app.core.security import get_password_hash


@pytest.mark.database
@pytest.mark.integration
class TestUserModel:
    """Test User model and related operations."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session):
        """Test creating a new user."""
        user = User(
            email="testuser@example.com",
            username="testuser",
            full_name="Test User",
            hashed_password=get_password_hash("testpassword"),
            is_active=True,
            is_superuser=False
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "testuser@example.com"
        assert user.created_at is not None

    @pytest.mark.asyncio
    async def test_user_unique_email_constraint(self, db_session):
        """Test unique email constraint."""
        user1 = User(
            email="duplicate@example.com",
            username="user1",
            full_name="User 1",
            hashed_password=get_password_hash("password1")
        )
        
        user2 = User(
            email="duplicate@example.com",  # Same email
            username="user2",
            full_name="User 2",
            hashed_password=get_password_hash("password2")
        )
        
        db_session.add(user1)
        await db_session.commit()
        
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_user_unique_username_constraint(self, db_session):
        """Test unique username constraint."""
        user1 = User(
            email="user1@example.com",
            username="duplicate_username",
            full_name="User 1",
            hashed_password=get_password_hash("password1")
        )
        
        user2 = User(
            email="user2@example.com",
            username="duplicate_username",  # Same username
            full_name="User 2",
            hashed_password=get_password_hash("password2")
        )
        
        db_session.add(user1)
        await db_session.commit()
        
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_user_profiles_relationship(self, db_session):
        """Test User-Profile relationship."""
        user = User(
            email="creator@example.com",
            username="creator",
            full_name="Content Creator",
            hashed_password=get_password_hash("password")
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create profiles for the user
        profile1 = Profile(
            user_id=user.id,
            stage_name="Creator Profile 1",
            bio="First profile",
            monitoring_enabled=True
        )
        
        profile2 = Profile(
            user_id=user.id,
            stage_name="Creator Profile 2",
            bio="Second profile",
            monitoring_enabled=False
        )
        
        db_session.add_all([profile1, profile2])
        await db_session.commit()
        
        # Refresh to load relationships
        await db_session.refresh(user)
        
        assert len(user.profiles) == 2
        assert profile1 in user.profiles
        assert profile2 in user.profiles

    @pytest.mark.asyncio
    async def test_user_soft_delete(self, db_session):
        """Test user soft delete functionality."""
        user = User(
            email="todelete@example.com",
            username="todelete",
            full_name="To Delete",
            hashed_password=get_password_hash("password"),
            is_active=True
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Soft delete
        user.is_active = False
        user.deleted_at = datetime.utcnow()
        await db_session.commit()
        
        # User should still exist in database but marked as inactive
        result = await db_session.get(User, user.id)
        assert result is not None
        assert result.is_active is False
        assert result.deleted_at is not None


@pytest.mark.database
@pytest.mark.integration
class TestProfileModel:
    """Test Profile model and operations."""

    @pytest.mark.asyncio
    async def test_create_profile(self, db_session, test_user):
        """Test creating a profile."""
        profile = Profile(
            user_id=test_user.id,
            stage_name="Test Creator",
            real_name="Real Name",
            bio="Content creator and model",
            social_media_accounts={
                "instagram": "@testcreator",
                "twitter": "@testcreator",
                "onlyfans": "testcreator"
            },
            content_categories=["photos", "videos"],
            monitoring_keywords=["testcreator", "test creator"],
            protection_level="premium",
            monitoring_enabled=True
        )
        
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        assert profile.id is not None
        assert profile.stage_name == "Test Creator"
        assert profile.user_id == test_user.id
        assert "instagram" in profile.social_media_accounts

    @pytest.mark.asyncio
    async def test_profile_json_fields(self, db_session, test_user):
        """Test JSON field storage and retrieval."""
        complex_data = {
            "instagram": "@testcreator",
            "twitter": "@testcreator_official",
            "onlyfans": "testcreator_premium",
            "custom_platform": "https://custom-site.com/testcreator"
        }
        
        keywords = ["keyword1", "keyword2", "keyword with spaces", "unicode_키워드"]
        categories = ["photos", "videos", "live_streams"]
        
        profile = Profile(
            user_id=test_user.id,
            stage_name="JSON Test",
            social_media_accounts=complex_data,
            monitoring_keywords=keywords,
            content_categories=categories
        )
        
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        # Verify JSON data integrity
        assert profile.social_media_accounts == complex_data
        assert profile.monitoring_keywords == keywords
        assert profile.content_categories == categories

    @pytest.mark.asyncio
    async def test_profile_cascade_delete(self, db_session):
        """Test cascade delete behavior."""
        user = User(
            email="cascade@example.com",
            username="cascade_user",
            full_name="Cascade Test",
            hashed_password=get_password_hash("password")
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        profile = Profile(
            user_id=user.id,
            stage_name="Test Profile"
        )
        
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        profile_id = profile.id
        
        # Delete user
        await db_session.delete(user)
        await db_session.commit()
        
        # Profile should be cascade deleted
        result = await db_session.get(Profile, profile_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_profile_search_functionality(self, db_session, test_user):
        """Test profile search capabilities."""
        profiles = [
            Profile(
                user_id=test_user.id,
                stage_name="Photography Creator",
                bio="Professional photographer specializing in portraits",
                content_categories=["photos", "art"]
            ),
            Profile(
                user_id=test_user.id,
                stage_name="Video Content Creator",
                bio="Video content creator and influencer",
                content_categories=["videos", "streaming"]
            ),
            Profile(
                user_id=test_user.id,
                stage_name="Art and Photography",
                bio="Digital artist and photographer",
                content_categories=["photos", "art", "digital"]
            )
        ]
        
        db_session.add_all(profiles)
        await db_session.commit()
        
        # Search by stage name
        result = await db_session.execute(
            text("SELECT * FROM profiles WHERE stage_name ILIKE :search"),
            {"search": "%photo%"}
        )
        found_profiles = result.fetchall()
        assert len(found_profiles) == 2
        
        # Search by content categories (JSON array contains)
        result = await db_session.execute(
            text("SELECT * FROM profiles WHERE content_categories @> :category"),
            {"category": '["photos"]'}
        )
        found_profiles = result.fetchall()
        assert len(found_profiles) == 2


@pytest.mark.database
@pytest.mark.integration
class TestTakedownModel:
    """Test TakedownRequest model and operations."""

    @pytest.mark.asyncio
    async def test_create_takedown_request(self, db_session, test_user):
        """Test creating a takedown request."""
        # First create a profile
        profile = Profile(
            user_id=test_user.id,
            stage_name="Test Creator"
        )
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        takedown = TakedownRequest(
            profile_id=profile.id,
            infringing_url="https://piracy-site.com/stolen-content",
            original_work_title="My Original Content",
            copyright_owner="Test Creator",
            contact_email="creator@example.com",
            infringement_description="My content was stolen and posted without permission",
            good_faith_statement=True,
            accuracy_statement=True,
            signature="Test Creator",
            status="pending",
            evidence_urls=["https://original-site.com/proof"],
            additional_information="Originally published on my OnlyFans"
        )
        
        db_session.add(takedown)
        await db_session.commit()
        await db_session.refresh(takedown)
        
        assert takedown.id is not None
        assert takedown.profile_id == profile.id
        assert takedown.status == "pending"
        assert len(takedown.evidence_urls) == 1

    @pytest.mark.asyncio
    async def test_takedown_status_transitions(self, db_session, test_user):
        """Test takedown status transitions and tracking."""
        profile = Profile(user_id=test_user.id, stage_name="Creator")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        takedown = TakedownRequest(
            profile_id=profile.id,
            infringing_url="https://example.com/stolen",
            original_work_title="Test Content",
            copyright_owner="Creator",
            contact_email="creator@example.com",
            infringement_description="Stolen content",
            good_faith_statement=True,
            accuracy_statement=True,
            signature="Creator",
            status="pending"
        )
        
        db_session.add(takedown)
        await db_session.commit()
        
        # Simulate status transitions
        statuses = ["pending", "submitted", "acknowledged", "successful"]
        
        for status in statuses:
            takedown.status = status
            takedown.status_updated_at = datetime.utcnow()
            
            if status == "submitted":
                takedown.submitted_at = datetime.utcnow()
            elif status == "successful":
                takedown.completed_at = datetime.utcnow()
                takedown.success = True
            
            await db_session.commit()
            
            # Verify status update
            await db_session.refresh(takedown)
            assert takedown.status == status

    @pytest.mark.asyncio
    async def test_takedown_metrics_queries(self, db_session, test_user):
        """Test complex queries for takedown metrics."""
        profile = Profile(user_id=test_user.id, stage_name="Creator")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        # Create multiple takedown requests with different statuses
        takedowns = []
        statuses = ["pending", "submitted", "successful", "failed", "successful"]
        
        for i, status in enumerate(statuses):
            takedown = TakedownRequest(
                profile_id=profile.id,
                infringing_url=f"https://example{i}.com/stolen",
                original_work_title=f"Content {i}",
                copyright_owner="Creator",
                contact_email="creator@example.com",
                infringement_description="Stolen content",
                good_faith_statement=True,
                accuracy_statement=True,
                signature="Creator",
                status=status,
                created_at=datetime.utcnow() - timedelta(days=i),
                success=(status == "successful")
            )
            takedowns.append(takedown)
        
        db_session.add_all(takedowns)
        await db_session.commit()
        
        # Query: Count by status
        result = await db_session.execute(
            text("""
                SELECT status, COUNT(*) as count 
                FROM takedown_requests 
                WHERE profile_id = :profile_id 
                GROUP BY status
            """),
            {"profile_id": profile.id}
        )
        status_counts = dict(result.fetchall())
        
        assert status_counts["successful"] == 2
        assert status_counts["pending"] == 1
        assert status_counts["submitted"] == 1
        assert status_counts["failed"] == 1
        
        # Query: Success rate
        result = await db_session.execute(
            text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as successful
                FROM takedown_requests 
                WHERE profile_id = :profile_id
            """),
            {"profile_id": profile.id}
        )
        metrics = result.fetchone()
        
        assert metrics.total == 5
        assert metrics.successful == 2
        success_rate = metrics.successful / metrics.total
        assert success_rate == 0.4

    @pytest.mark.asyncio
    async def test_takedown_foreign_key_constraints(self, db_session):
        """Test foreign key constraints."""
        # Try to create takedown with non-existent profile
        takedown = TakedownRequest(
            profile_id=99999,  # Non-existent profile
            infringing_url="https://example.com/stolen",
            original_work_title="Test Content",
            copyright_owner="Creator",
            contact_email="creator@example.com",
            infringement_description="Stolen content",
            good_faith_statement=True,
            accuracy_statement=True,
            signature="Creator"
        )
        
        db_session.add(takedown)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()


@pytest.mark.database
@pytest.mark.integration
class TestInfringementModel:
    """Test Infringement model and operations."""

    @pytest.mark.asyncio
    async def test_create_infringement(self, db_session, test_user):
        """Test creating an infringement record."""
        profile = Profile(user_id=test_user.id, stage_name="Creator")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        infringement = Infringement(
            profile_id=profile.id,
            url="https://piracy-site.com/stolen-photo",
            title="Stolen Photo",
            description="My photo was stolen and posted here",
            platform="instagram",
            confidence_score=0.95,
            status="detected",
            match_details={
                "similarity_score": 0.95,
                "match_type": "face_recognition",
                "analysis_method": "AI"
            },
            evidence_urls=["https://original-site.com/original-photo"]
        )
        
        db_session.add(infringement)
        await db_session.commit()
        await db_session.refresh(infringement)
        
        assert infringement.id is not None
        assert infringement.confidence_score == 0.95
        assert infringement.match_details["match_type"] == "face_recognition"

    @pytest.mark.asyncio
    async def test_infringement_platform_filtering(self, db_session, test_user):
        """Test filtering infringements by platform."""
        profile = Profile(user_id=test_user.id, stage_name="Creator")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        platforms = ["instagram", "twitter", "onlyfans", "reddit", "instagram"]
        infringements = []
        
        for i, platform in enumerate(platforms):
            infringement = Infringement(
                profile_id=profile.id,
                url=f"https://{platform}.com/stolen{i}",
                title=f"Stolen Content {i}",
                description="Stolen content",
                platform=platform,
                confidence_score=0.8,
                status="detected"
            )
            infringements.append(infringement)
        
        db_session.add_all(infringements)
        await db_session.commit()
        
        # Count by platform
        result = await db_session.execute(
            text("""
                SELECT platform, COUNT(*) as count 
                FROM infringements 
                WHERE profile_id = :profile_id 
                GROUP BY platform
                ORDER BY count DESC
            """),
            {"profile_id": profile.id}
        )
        platform_counts = result.fetchall()
        
        assert platform_counts[0].platform == "instagram"
        assert platform_counts[0].count == 2

    @pytest.mark.asyncio
    async def test_infringement_confidence_scoring(self, db_session, test_user):
        """Test confidence score analysis."""
        profile = Profile(user_id=test_user.id, stage_name="Creator")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        confidence_scores = [0.95, 0.87, 0.72, 0.91, 0.65, 0.88]
        infringements = []
        
        for i, score in enumerate(confidence_scores):
            infringement = Infringement(
                profile_id=profile.id,
                url=f"https://example{i}.com/stolen",
                title=f"Content {i}",
                description="Content",
                platform="instagram",
                confidence_score=score,
                status="detected"
            )
            infringements.append(infringement)
        
        db_session.add_all(infringements)
        await db_session.commit()
        
        # Query: High confidence infringements (>= 0.8)
        result = await db_session.execute(
            text("""
                SELECT COUNT(*) as high_confidence_count
                FROM infringements 
                WHERE profile_id = :profile_id AND confidence_score >= 0.8
            """),
            {"profile_id": profile.id}
        )
        high_confidence = result.fetchone().high_confidence_count
        assert high_confidence == 4
        
        # Query: Average confidence score
        result = await db_session.execute(
            text("""
                SELECT AVG(confidence_score) as avg_confidence
                FROM infringements 
                WHERE profile_id = :profile_id
            """),
            {"profile_id": profile.id}
        )
        avg_confidence = result.fetchone().avg_confidence
        assert 0.8 <= avg_confidence <= 0.85


@pytest.mark.database
@pytest.mark.integration
class TestSocialMediaModel:
    """Test social media related models."""

    @pytest.mark.asyncio
    async def test_social_media_account_tracking(self, db_session, test_user):
        """Test social media account tracking."""
        profile = Profile(user_id=test_user.id, stage_name="Creator")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        accounts = [
            SocialMediaAccount(
                profile_id=profile.id,
                platform="instagram",
                username="testcreator",
                url="https://instagram.com/testcreator",
                verified=True,
                follower_count=10000,
                monitoring_enabled=True
            ),
            SocialMediaAccount(
                profile_id=profile.id,
                platform="twitter",
                username="testcreator_official",
                url="https://twitter.com/testcreator_official",
                verified=False,
                follower_count=5000,
                monitoring_enabled=True
            )
        ]
        
        db_session.add_all(accounts)
        await db_session.commit()
        
        # Query monitored accounts
        result = await db_session.execute(
            text("""
                SELECT platform, username, follower_count
                FROM social_media_accounts 
                WHERE profile_id = :profile_id AND monitoring_enabled = true
                ORDER BY follower_count DESC
            """),
            {"profile_id": profile.id}
        )
        monitored = result.fetchall()
        
        assert len(monitored) == 2
        assert monitored[0].platform == "instagram"  # Highest followers first
        assert monitored[0].follower_count == 10000

    @pytest.mark.asyncio
    async def test_impersonation_report_creation(self, db_session, test_user):
        """Test creating impersonation reports."""
        profile = Profile(user_id=test_user.id, stage_name="Creator")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        report = ImpersonationReport(
            profile_id=profile.id,
            platform="instagram",
            impersonator_username="fake_testcreator",
            impersonator_url="https://instagram.com/fake_testcreator",
            confidence_score=0.92,
            analysis_details={
                "username_similarity": 0.95,
                "profile_image_similarity": 0.89,
                "bio_similarity": 0.87,
                "suspicious_patterns": ["fake_verification_claims"]
            },
            status="pending",
            evidence_screenshots=["screenshot1.jpg", "screenshot2.jpg"]
        )
        
        db_session.add(report)
        await db_session.commit()
        await db_session.refresh(report)
        
        assert report.id is not None
        assert report.confidence_score == 0.92
        assert "username_similarity" in report.analysis_details

    @pytest.mark.asyncio
    async def test_impersonation_report_statistics(self, db_session, test_user):
        """Test impersonation report statistics."""
        profile = Profile(user_id=test_user.id, stage_name="Creator")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        # Create reports with different statuses
        statuses = ["pending", "confirmed", "false_positive", "confirmed", "resolved"]
        platforms = ["instagram", "twitter", "instagram", "onlyfans", "instagram"]
        
        for i, (status, platform) in enumerate(zip(statuses, platforms)):
            report = ImpersonationReport(
                profile_id=profile.id,
                platform=platform,
                impersonator_username=f"fake_user_{i}",
                impersonator_url=f"https://{platform}.com/fake_user_{i}",
                confidence_score=0.8 + (i * 0.02),
                status=status,
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            db_session.add(report)
        
        await db_session.commit()
        
        # Platform distribution
        result = await db_session.execute(
            text("""
                SELECT platform, COUNT(*) as count
                FROM impersonation_reports 
                WHERE profile_id = :profile_id
                GROUP BY platform
                ORDER BY count DESC
            """),
            {"profile_id": profile.id}
        )
        platform_stats = result.fetchall()
        
        assert platform_stats[0].platform == "instagram"
        assert platform_stats[0].count == 3
        
        # Status distribution
        result = await db_session.execute(
            text("""
                SELECT status, COUNT(*) as count
                FROM impersonation_reports 
                WHERE profile_id = :profile_id
                GROUP BY status
            """),
            {"profile_id": profile.id}
        )
        status_stats = dict(result.fetchall())
        
        assert status_stats["confirmed"] == 2
        assert status_stats["pending"] == 1


@pytest.mark.database
@pytest.mark.integration
class TestSubscriptionModel:
    """Test subscription and billing models."""

    @pytest.mark.asyncio
    async def test_subscription_management(self, db_session, test_user):
        """Test subscription creation and management."""
        subscription = Subscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_123456789",
            plan="premium",
            status="active",
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
            cancel_at_period_end=False,
            metadata={
                "features": ["unlimited_scans", "priority_support"],
                "limits": {
                    "monthly_scans": 1000,
                    "profiles": 10
                }
            }
        )
        
        db_session.add(subscription)
        await db_session.commit()
        await db_session.refresh(subscription)
        
        assert subscription.id is not None
        assert subscription.plan == "premium"
        assert subscription.status == "active"

    @pytest.mark.asyncio
    async def test_billing_history_tracking(self, db_session, test_user):
        """Test billing history tracking."""
        subscription = Subscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_123",
            plan="premium",
            status="active"
        )
        
        db_session.add(subscription)
        await db_session.commit()
        await db_session.refresh(subscription)
        
        # Create billing history records
        billing_records = [
            BillingHistory(
                user_id=test_user.id,
                subscription_id=subscription.id,
                stripe_invoice_id="inv_001",
                amount=2999,  # $29.99
                currency="usd",
                status="paid",
                billing_period_start=datetime.utcnow() - timedelta(days=30),
                billing_period_end=datetime.utcnow(),
                paid_at=datetime.utcnow() - timedelta(days=25)
            ),
            BillingHistory(
                user_id=test_user.id,
                subscription_id=subscription.id,
                stripe_invoice_id="inv_002",
                amount=2999,
                currency="usd",
                status="paid",
                billing_period_start=datetime.utcnow() - timedelta(days=60),
                billing_period_end=datetime.utcnow() - timedelta(days=30),
                paid_at=datetime.utcnow() - timedelta(days=55)
            )
        ]
        
        db_session.add_all(billing_records)
        await db_session.commit()
        
        # Query billing history
        result = await db_session.execute(
            text("""
                SELECT COUNT(*) as payment_count, SUM(amount) as total_paid
                FROM billing_history 
                WHERE user_id = :user_id AND status = 'paid'
            """),
            {"user_id": test_user.id}
        )
        billing_stats = result.fetchone()
        
        assert billing_stats.payment_count == 2
        assert billing_stats.total_paid == 5998  # $59.98


@pytest.mark.database
@pytest.mark.integration
class TestComplexQueries:
    """Test complex database queries and analytics."""

    @pytest.mark.asyncio
    async def test_user_activity_analytics(self, db_session, seed_test_data):
        """Test complex user activity analytics."""
        users = seed_test_data["users"]
        profiles = seed_test_data["profiles"]
        
        # Create various activities for users
        for i, profile in enumerate(profiles):
            # Create takedown requests
            for j in range(i + 1):  # User 0: 1 takedown, User 1: 2 takedowns, etc.
                takedown = TakedownRequest(
                    profile_id=profile.id,
                    infringing_url=f"https://example{i}_{j}.com/stolen",
                    original_work_title=f"Content {i}_{j}",
                    copyright_owner=f"Creator {i}",
                    contact_email=f"creator{i}@example.com",
                    infringement_description="Stolen content",
                    good_faith_statement=True,
                    accuracy_statement=True,
                    signature=f"Creator {i}",
                    status="successful" if j % 2 == 0 else "pending",
                    created_at=datetime.utcnow() - timedelta(days=j * 5)
                )
                db_session.add(takedown)
            
            # Create infringements
            for k in range((i + 1) * 2):  # More infringements per user
                infringement = Infringement(
                    profile_id=profile.id,
                    url=f"https://infringement{i}_{k}.com/stolen",
                    title=f"Infringement {i}_{k}",
                    description="Detected infringement",
                    platform="instagram" if k % 2 == 0 else "twitter",
                    confidence_score=0.7 + (k * 0.05),
                    status="detected",
                    created_at=datetime.utcnow() - timedelta(days=k * 2)
                )
                db_session.add(infringement)
        
        await db_session.commit()
        
        # Complex analytics query: User activity summary
        result = await db_session.execute(text("""
            WITH user_stats AS (
                SELECT 
                    u.id as user_id,
                    u.email,
                    COUNT(DISTINCT p.id) as profile_count,
                    COUNT(DISTINCT t.id) as takedown_count,
                    COUNT(DISTINCT i.id) as infringement_count,
                    AVG(i.confidence_score) as avg_confidence
                FROM users u
                LEFT JOIN profiles p ON u.id = p.user_id
                LEFT JOIN takedown_requests t ON p.id = t.profile_id
                LEFT JOIN infringements i ON p.id = i.profile_id
                GROUP BY u.id, u.email
            )
            SELECT 
                user_id,
                email,
                profile_count,
                takedown_count,
                infringement_count,
                ROUND(avg_confidence::numeric, 2) as avg_confidence,
                CASE 
                    WHEN takedown_count > 3 THEN 'high_activity'
                    WHEN takedown_count > 1 THEN 'medium_activity'
                    ELSE 'low_activity'
                END as activity_level
            FROM user_stats
            ORDER BY takedown_count DESC
        """))
        
        stats = result.fetchall()
        assert len(stats) >= 5  # We created 5 users
        
        # Verify analytics make sense
        highest_activity = stats[0]
        assert highest_activity.takedown_count >= 4  # User 4 should have 5 takedowns
        assert highest_activity.activity_level == 'high_activity'

    @pytest.mark.asyncio
    async def test_platform_performance_metrics(self, db_session, seed_test_data):
        """Test platform performance analytics."""
        profiles = seed_test_data["profiles"]
        
        # Create platform-specific data
        platforms = ["instagram", "twitter", "onlyfans", "reddit"]
        
        for profile in profiles:
            for platform in platforms:
                # Create infringements per platform
                for i in range(3):
                    infringement = Infringement(
                        profile_id=profile.id,
                        url=f"https://{platform}.com/content_{i}",
                        title=f"Content on {platform}",
                        description="Platform content",
                        platform=platform,
                        confidence_score=0.8 if platform == "instagram" else 0.6,
                        status="detected",
                        created_at=datetime.utcnow() - timedelta(days=i)
                    )
                    db_session.add(infringement)
                
                # Create takedown for each platform
                takedown = TakedownRequest(
                    profile_id=profile.id,
                    infringing_url=f"https://{platform}.com/takedown",
                    original_work_title=f"Original on {platform}",
                    copyright_owner="Creator",
                    contact_email="creator@example.com",
                    infringement_description="Platform infringement",
                    good_faith_statement=True,
                    accuracy_statement=True,
                    signature="Creator",
                    status="successful" if platform in ["instagram", "twitter"] else "pending"
                )
                db_session.add(takedown)
        
        await db_session.commit()
        
        # Platform performance query
        result = await db_session.execute(text("""
            SELECT 
                i.platform,
                COUNT(DISTINCT i.id) as infringement_count,
                AVG(i.confidence_score) as avg_confidence,
                COUNT(DISTINCT t.id) as takedown_count,
                COUNT(DISTINCT CASE WHEN t.status = 'successful' THEN t.id END) as successful_takedowns,
                ROUND(
                    COUNT(DISTINCT CASE WHEN t.status = 'successful' THEN t.id END)::numeric / 
                    NULLIF(COUNT(DISTINCT t.id), 0) * 100, 
                    2
                ) as success_rate
            FROM infringements i
            LEFT JOIN takedown_requests t ON i.platform = 
                CASE 
                    WHEN t.infringing_url LIKE '%instagram%' THEN 'instagram'
                    WHEN t.infringing_url LIKE '%twitter%' THEN 'twitter'
                    WHEN t.infringing_url LIKE '%onlyfans%' THEN 'onlyfans'
                    WHEN t.infringing_url LIKE '%reddit%' THEN 'reddit'
                END
            GROUP BY i.platform
            ORDER BY avg_confidence DESC, success_rate DESC
        """))
        
        platform_metrics = result.fetchall()
        assert len(platform_metrics) == 4
        
        # Instagram should have highest confidence
        instagram_metrics = next(m for m in platform_metrics if m.platform == "instagram")
        assert instagram_metrics.avg_confidence == 0.8

    @pytest.mark.asyncio
    async def test_time_series_analytics(self, db_session, test_user):
        """Test time-series analytics for trends."""
        profile = Profile(user_id=test_user.id, stage_name="Creator")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        # Create data points over time (last 30 days)
        base_date = datetime.utcnow() - timedelta(days=30)
        
        for day in range(30):
            current_date = base_date + timedelta(days=day)
            
            # Create 1-3 infringements per day (random pattern)
            infringement_count = (day % 3) + 1
            
            for i in range(infringement_count):
                infringement = Infringement(
                    profile_id=profile.id,
                    url=f"https://example.com/day_{day}_item_{i}",
                    title=f"Daily infringement {day}_{i}",
                    description="Daily content",
                    platform="instagram",
                    confidence_score=0.7 + (day * 0.01),  # Gradual increase
                    status="detected",
                    created_at=current_date + timedelta(hours=i)
                )
                db_session.add(infringement)
        
        await db_session.commit()
        
        # Time-series query: Daily infringement counts
        result = await db_session.execute(text("""
            SELECT 
                DATE(created_at) as detection_date,
                COUNT(*) as daily_count,
                AVG(confidence_score) as daily_avg_confidence
            FROM infringements
            WHERE profile_id = :profile_id
                AND created_at >= :start_date
            GROUP BY DATE(created_at)
            ORDER BY detection_date
        """), {
            "profile_id": profile.id,
            "start_date": base_date
        })
        
        daily_stats = result.fetchall()
        assert len(daily_stats) == 30
        
        # Verify trend (confidence should increase over time)
        first_day_confidence = daily_stats[0].daily_avg_confidence
        last_day_confidence = daily_stats[-1].daily_avg_confidence
        assert last_day_confidence > first_day_confidence


@pytest.mark.database
@pytest.mark.performance
class TestDatabasePerformance:
    """Test database performance and optimization."""

    @pytest.mark.asyncio
    async def test_large_dataset_query_performance(self, db_session, test_user):
        """Test query performance with large datasets."""
        import time
        
        profile = Profile(user_id=test_user.id, stage_name="Performance Test")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        # Create large dataset (1000 records)
        infringements = []
        for i in range(1000):
            infringement = Infringement(
                profile_id=profile.id,
                url=f"https://performance-test-{i}.com/content",
                title=f"Performance Test Content {i}",
                description="Performance test data",
                platform="instagram" if i % 2 == 0 else "twitter",
                confidence_score=0.5 + (i % 50) * 0.01,
                status="detected",
                created_at=datetime.utcnow() - timedelta(days=i % 365)
            )
            infringements.append(infringement)
        
        # Batch insert
        start_time = time.time()
        db_session.add_all(infringements)
        await db_session.commit()
        insert_time = time.time() - start_time
        
        assert insert_time < 10.0  # Should insert 1000 records in under 10 seconds
        
        # Test query performance
        start_time = time.time()
        result = await db_session.execute(text("""
            SELECT platform, AVG(confidence_score), COUNT(*)
            FROM infringements 
            WHERE profile_id = :profile_id 
                AND confidence_score > 0.8
            GROUP BY platform
        """), {"profile_id": profile.id})
        query_time = time.time() - start_time
        
        assert query_time < 1.0  # Should query in under 1 second
        
        platform_stats = result.fetchall()
        assert len(platform_stats) <= 2  # instagram and twitter

    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self, db_session, test_user):
        """Test concurrent database operations."""
        import asyncio
        
        profile = Profile(user_id=test_user.id, stage_name="Concurrency Test")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        async def create_infringement(session, index):
            """Create a single infringement."""
            infringement = Infringement(
                profile_id=profile.id,
                url=f"https://concurrent-test-{index}.com/content",
                title=f"Concurrent Test {index}",
                description="Concurrent test data",
                platform="instagram",
                confidence_score=0.8,
                status="detected"
            )
            session.add(infringement)
            await session.commit()
            return index
        
        # Create 50 concurrent operations
        tasks = []
        for i in range(50):
            # Each task needs its own session for true concurrency
            task = create_infringement(db_session, i)
            tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        concurrent_time = time.time() - start_time
        
        # Should complete reasonably quickly
        assert concurrent_time < 30.0
        
        # Verify all operations succeeded
        successful_operations = [r for r in results if isinstance(r, int)]
        assert len(successful_operations) == 50


@pytest.mark.database
@pytest.mark.data_integrity
class TestDataIntegrity:
    """Test data integrity and constraints."""

    @pytest.mark.asyncio
    async def test_cascade_delete_integrity(self, db_session):
        """Test cascade delete maintains data integrity."""
        # Create user with complete data hierarchy
        user = User(
            email="integrity@example.com",
            username="integrity_user",
            full_name="Integrity Test",
            hashed_password=get_password_hash("password")
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        profile = Profile(user_id=user.id, stage_name="Test Profile")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        # Create related records
        takedown = TakedownRequest(
            profile_id=profile.id,
            infringing_url="https://example.com/test",
            original_work_title="Test",
            copyright_owner="Test",
            contact_email="test@example.com",
            infringement_description="Test",
            good_faith_statement=True,
            accuracy_statement=True,
            signature="Test"
        )
        
        infringement = Infringement(
            profile_id=profile.id,
            url="https://example.com/infringement",
            title="Test Infringement",
            description="Test",
            platform="instagram",
            confidence_score=0.8,
            status="detected"
        )
        
        db_session.add_all([takedown, infringement])
        await db_session.commit()
        
        # Store IDs for verification
        profile_id = profile.id
        takedown_id = takedown.id
        infringement_id = infringement.id
        
        # Delete user (should cascade)
        await db_session.delete(user)
        await db_session.commit()
        
        # Verify cascade deletion
        assert await db_session.get(Profile, profile_id) is None
        assert await db_session.get(TakedownRequest, takedown_id) is None
        assert await db_session.get(Infringement, infringement_id) is None

    @pytest.mark.asyncio
    async def test_data_validation_constraints(self, db_session, test_user):
        """Test data validation constraints."""
        # Test invalid email format (should be handled at application level)
        profile = Profile(user_id=test_user.id, stage_name="Validation Test")
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        # Test invalid confidence score (outside 0-1 range)
        invalid_infringement = Infringement(
            profile_id=profile.id,
            url="https://example.com/invalid",
            title="Invalid Test",
            description="Test",
            platform="instagram",
            confidence_score=1.5,  # Invalid (> 1.0)
            status="detected"
        )
        
        db_session.add(invalid_infringement)
        
        # This should be caught by application validation, but test DB constraint
        with pytest.raises((IntegrityError, ValueError)):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_json_field_integrity(self, db_session, test_user):
        """Test JSON field data integrity."""
        profile = Profile(
            user_id=test_user.id,
            stage_name="JSON Test",
            social_media_accounts={
                "instagram": "@test",
                "twitter": "@test",
                "nested": {
                    "complex": "data",
                    "array": [1, 2, 3]
                }
            },
            monitoring_keywords=["keyword1", "keyword2", "unicode_测试"],
            content_categories=["photos", "videos"]
        )
        
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        
        # Verify JSON data integrity after round-trip
        assert profile.social_media_accounts["nested"]["complex"] == "data"
        assert profile.social_media_accounts["nested"]["array"] == [1, 2, 3]
        assert "unicode_测试" in profile.monitoring_keywords
        
        # Test JSON query operations
        result = await db_session.execute(
            text("SELECT * FROM profiles WHERE social_media_accounts @> :search"),
            {"search": '{"instagram": "@test"}'}
        )
        found = result.fetchone()
        assert found is not None