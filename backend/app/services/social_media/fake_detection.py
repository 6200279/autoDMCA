"""
Fake account detection algorithms for social media monitoring.
"""

import asyncio
import re
import math
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import Counter
import statistics

import structlog
import numpy as np
from textblob import TextBlob

from app.db.models.social_media import SocialMediaPlatform
from .config import SocialMediaSettings
from .api_clients import ProfileData
from .face_matcher import ProfileImageAnalyzer


logger = structlog.get_logger(__name__)


@dataclass
class DetectionFeature:
    """Represents a feature used in fake account detection."""
    name: str
    value: float
    weight: float
    description: str
    category: str  # profile, content, behavior, network


@dataclass
class FakeAccountScore:
    """Represents the fake account detection score and analysis."""
    overall_score: float  # 0-1, higher = more likely fake
    confidence_level: str  # low, medium, high
    risk_category: str  # legitimate, suspicious, likely_fake, definitely_fake
    features: List[DetectionFeature]
    reasons: List[str]
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if not self.metadata:
            self.metadata = {}


class ProfileAnalyzer:
    """Analyzes profile characteristics for fake account detection."""
    
    def __init__(self, settings: SocialMediaSettings):
        self.settings = settings
        self.suspicious_patterns = self._load_suspicious_patterns()
        
    def _load_suspicious_patterns(self) -> Dict[str, List[str]]:
        """Load patterns commonly associated with fake accounts."""
        return {
            'username_patterns': [
                r'.*\d{4,}$',  # Ends with 4+ digits
                r'^[a-z]+\d{1,3}$',  # Simple name + 1-3 digits
                r'^[a-z]{1,3}\d{4,}$',  # 1-3 letters + 4+ digits
                r'.*(_|\.).*(_|\.).*',  # Multiple underscores/dots
                r'^(real|official|verified).*',  # Starts with legitimacy claims
            ],
            'bio_spam_keywords': [
                'click here', 'visit my', 'check out', 'dm me', 'follow me',
                'make money', 'earn cash', 'free followers', 'grow your',
                'hot singles', 'dating app', 'hookup', 'sugar daddy',
                'crypto', 'bitcoin', 'investment', 'forex', 'trading',
                'weight loss', 'diet pills', 'miracle cure'
            ],
            'suspicious_domains': [
                'bit.ly', 'tinyurl.com', 'goo.gl', 't.co',  # URL shorteners
                'blogspot.com', 'wordpress.com',  # Free hosting
            ],
        }
    
    def analyze_profile_features(self, profile: ProfileData, platform: SocialMediaPlatform) -> List[DetectionFeature]:
        """Analyze profile-based features for fake account detection."""
        features = []
        
        # Username analysis
        features.extend(self._analyze_username(profile.username))
        
        # Display name analysis
        if profile.display_name:
            features.extend(self._analyze_display_name(profile.username, profile.display_name))
        
        # Bio analysis
        if profile.bio:
            features.extend(self._analyze_bio(profile.bio))
        
        # Profile image analysis
        features.extend(self._analyze_profile_image(profile))
        
        # Account metrics analysis
        features.extend(self._analyze_account_metrics(profile, platform))
        
        # Verification status
        features.append(DetectionFeature(
            name="is_verified",
            value=0.0 if profile.is_verified else 1.0,
            weight=0.3,
            description="Account verification status",
            category="profile"
        ))
        
        return features
    
    def _analyze_username(self, username: str) -> List[DetectionFeature]:
        """Analyze username for suspicious patterns."""
        features = []
        
        # Check for suspicious patterns
        suspicious_score = 0.0
        matched_patterns = 0
        
        for pattern in self.suspicious_patterns['username_patterns']:
            if re.match(pattern, username.lower()):
                suspicious_score += 0.2
                matched_patterns += 1
        
        features.append(DetectionFeature(
            name="username_pattern_suspicious",
            value=min(suspicious_score, 1.0),
            weight=0.4,
            description=f"Username matches {matched_patterns} suspicious patterns",
            category="profile"
        ))
        
        # Length analysis
        length_score = 0.0
        if len(username) < 4:
            length_score = 0.8  # Very short usernames are suspicious
        elif len(username) > 20:
            length_score = 0.3  # Very long usernames are slightly suspicious
        
        features.append(DetectionFeature(
            name="username_length_suspicious",
            value=length_score,
            weight=0.2,
            description=f"Username length: {len(username)} characters",
            category="profile"
        ))
        
        # Character composition
        digit_ratio = sum(1 for c in username if c.isdigit()) / len(username)
        features.append(DetectionFeature(
            name="username_digit_ratio",
            value=min(digit_ratio * 2, 1.0),  # High digit ratio is suspicious
            weight=0.3,
            description=f"Digit ratio in username: {digit_ratio:.2f}",
            category="profile"
        ))
        
        return features
    
    def _analyze_display_name(self, username: str, display_name: str) -> List[DetectionFeature]:
        """Analyze display name vs username consistency."""
        features = []
        
        # Check if display name is very different from username
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, username.lower(), display_name.lower()).ratio()
        
        # Very different display name and username can be suspicious
        dissimilarity_score = 1.0 - similarity if similarity < 0.3 else 0.0
        
        features.append(DetectionFeature(
            name="display_name_dissimilarity",
            value=dissimilarity_score,
            weight=0.2,
            description=f"Display name similarity to username: {similarity:.2f}",
            category="profile"
        ))
        
        # Check for legitimacy claims in display name
        legitimacy_claims = ['official', 'real', 'verified', 'authentic', 'genuine']
        claim_score = 0.0
        for claim in legitimacy_claims:
            if claim in display_name.lower():
                claim_score = 0.7  # Suspicious unless actually verified
                break
        
        features.append(DetectionFeature(
            name="display_name_legitimacy_claims",
            value=claim_score,
            weight=0.4,
            description="Display name contains legitimacy claims",
            category="profile"
        ))
        
        return features
    
    def _analyze_bio(self, bio: str) -> List[DetectionFeature]:
        """Analyze bio content for spam and suspicious content."""
        features = []
        bio_lower = bio.lower()
        
        # Check for spam keywords
        spam_score = 0.0
        spam_keywords_found = 0
        
        for keyword in self.suspicious_patterns['bio_spam_keywords']:
            if keyword in bio_lower:
                spam_score += 0.1
                spam_keywords_found += 1
        
        features.append(DetectionFeature(
            name="bio_spam_content",
            value=min(spam_score, 1.0),
            weight=0.5,
            description=f"Bio contains {spam_keywords_found} spam keywords",
            category="content"
        ))
        
        # URL analysis
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        urls = url_pattern.findall(bio)
        
        suspicious_url_score = 0.0
        for url in urls:
            for domain in self.suspicious_patterns['suspicious_domains']:
                if domain in url:
                    suspicious_url_score += 0.3
                    break
        
        features.append(DetectionFeature(
            name="bio_suspicious_urls",
            value=min(suspicious_url_score, 1.0),
            weight=0.4,
            description=f"Bio contains {len(urls)} URLs, {suspicious_url_score:.1f} suspicious",
            category="content"
        ))
        
        # Text quality analysis
        try:
            blob = TextBlob(bio)
            polarity = abs(blob.sentiment.polarity)  # Extreme sentiment can be suspicious
            
            features.append(DetectionFeature(
                name="bio_sentiment_extremity",
                value=polarity if polarity > 0.7 else 0.0,
                weight=0.2,
                description=f"Bio sentiment polarity: {blob.sentiment.polarity:.2f}",
                category="content"
            ))
        except:
            pass  # Skip if text analysis fails
        
        # Length analysis
        bio_length_score = 0.0
        if len(bio) < 10:
            bio_length_score = 0.3  # Very short bio is slightly suspicious
        elif len(bio) > 500:
            bio_length_score = 0.2  # Very long bio can be suspicious
        
        features.append(DetectionFeature(
            name="bio_length_suspicious",
            value=bio_length_score,
            weight=0.1,
            description=f"Bio length: {len(bio)} characters",
            category="content"
        ))
        
        return features
    
    def _analyze_profile_image(self, profile: ProfileData) -> List[DetectionFeature]:
        """Analyze profile image characteristics."""
        features = []
        
        # Missing profile image
        if not profile.profile_image_url:
            features.append(DetectionFeature(
                name="missing_profile_image",
                value=0.6,
                weight=0.3,
                description="No profile image",
                category="profile"
            ))
        else:
            # Default/generic profile image detection would go here
            # For now, we'll check URL patterns
            generic_patterns = ['default', 'avatar', 'placeholder']
            generic_score = 0.0
            
            for pattern in generic_patterns:
                if pattern in profile.profile_image_url.lower():
                    generic_score = 0.5
                    break
            
            features.append(DetectionFeature(
                name="generic_profile_image",
                value=generic_score,
                weight=0.2,
                description="Profile image appears generic",
                category="profile"
            ))
        
        return features
    
    def _analyze_account_metrics(self, profile: ProfileData, platform: SocialMediaPlatform) -> List[DetectionFeature]:
        """Analyze account metrics like follower/following ratios."""
        features = []
        
        if profile.follower_count is not None and profile.following_count is not None:
            # Follower to following ratio analysis
            if profile.following_count > 0:
                ratio = profile.follower_count / profile.following_count
                
                # Very low follower to following ratio is suspicious
                low_ratio_score = 0.0
                if ratio < 0.1 and profile.following_count > 100:
                    low_ratio_score = 0.7
                elif ratio < 0.3 and profile.following_count > 50:
                    low_ratio_score = 0.4
                
                features.append(DetectionFeature(
                    name="low_follower_ratio",
                    value=low_ratio_score,
                    weight=0.4,
                    description=f"Follower/following ratio: {ratio:.2f}",
                    category="behavior"
                ))
                
                # Extremely high following count
                high_following_score = 0.0
                if profile.following_count > 5000:
                    high_following_score = 0.6
                elif profile.following_count > 2000:
                    high_following_score = 0.3
                
                features.append(DetectionFeature(
                    name="excessive_following",
                    value=high_following_score,
                    weight=0.3,
                    description=f"Following {profile.following_count} accounts",
                    category="behavior"
                ))
        
        # Post count analysis
        if profile.post_count is not None:
            post_activity_score = 0.0
            
            # No posts but has followers (suspicious)
            if profile.post_count == 0 and profile.follower_count and profile.follower_count > 100:
                post_activity_score = 0.8
            # Very few posts but many followers
            elif profile.post_count < 10 and profile.follower_count and profile.follower_count > 1000:
                post_activity_score = 0.5
            
            features.append(DetectionFeature(
                name="suspicious_post_activity",
                value=post_activity_score,
                weight=0.3,
                description=f"Post count: {profile.post_count}",
                category="behavior"
            ))
        
        return features


class BehaviorAnalyzer:
    """Analyzes account behavior patterns for fake detection."""
    
    def __init__(self, settings: SocialMediaSettings):
        self.settings = settings
        
    def analyze_temporal_patterns(self, profile_data: Dict[str, Any]) -> List[DetectionFeature]:
        """Analyze temporal patterns in account activity."""
        features = []
        
        # This would analyze posting patterns, activity times, etc.
        # For now, we'll implement basic account age analysis
        
        if 'created_date' in profile_data and profile_data['created_date']:
            try:
                created_date = datetime.fromisoformat(profile_data['created_date'].replace('Z', '+00:00'))
                account_age_days = (datetime.now().replace(tzinfo=created_date.tzinfo) - created_date).days
                
                # Very new accounts are more suspicious
                new_account_score = 0.0
                if account_age_days < 7:
                    new_account_score = 0.8
                elif account_age_days < 30:
                    new_account_score = 0.4
                elif account_age_days < 90:
                    new_account_score = 0.2
                
                features.append(DetectionFeature(
                    name="new_account",
                    value=new_account_score,
                    weight=0.4,
                    description=f"Account age: {account_age_days} days",
                    category="behavior"
                ))
                
            except Exception as e:
                logger.debug("Failed to parse account creation date", error=str(e))
        
        return features
    
    def analyze_network_patterns(self, profile_data: Dict[str, Any]) -> List[DetectionFeature]:
        """Analyze network and connection patterns."""
        features = []
        
        # This would analyze follower/following patterns, mutual connections, etc.
        # Implementation would require additional data collection
        
        return features


class MLFakeDetector:
    """Machine learning-based fake account detection."""
    
    def __init__(self, settings: SocialMediaSettings):
        self.settings = settings
        # In a real implementation, this would load a trained ML model
        
    def predict_fake_probability(self, features: List[DetectionFeature]) -> float:
        """Predict probability that account is fake using ML model."""
        # Simplified rule-based approach for now
        # In production, this would use a trained classifier
        
        if not features:
            return 0.5  # Unknown
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for feature in features:
            weighted_sum += feature.value * feature.weight
            total_weight += feature.weight
        
        if total_weight == 0:
            return 0.5
        
        probability = weighted_sum / total_weight
        return min(max(probability, 0.0), 1.0)  # Clamp to [0, 1]


class FakeAccountDetector:
    """Main fake account detection service."""
    
    def __init__(self, settings: SocialMediaSettings):
        self.settings = settings
        self.profile_analyzer = ProfileAnalyzer(settings)
        self.behavior_analyzer = BehaviorAnalyzer(settings)
        self.ml_detector = MLFakeDetector(settings)
        self.image_analyzer = ProfileImageAnalyzer(settings)
        
    async def analyze_account(self, profile: ProfileData, platform: SocialMediaPlatform) -> FakeAccountScore:
        """Comprehensive fake account analysis."""
        all_features = []
        reasons = []
        
        # Profile-based analysis
        profile_features = self.profile_analyzer.analyze_profile_features(profile, platform)
        all_features.extend(profile_features)
        
        # Behavior analysis
        behavior_features = self.behavior_analyzer.analyze_temporal_patterns(profile.metadata or {})
        all_features.extend(behavior_features)
        
        network_features = self.behavior_analyzer.analyze_network_patterns(profile.metadata or {})
        all_features.extend(network_features)
        
        # ML prediction
        fake_probability = self.ml_detector.predict_fake_probability(all_features)
        
        # Determine confidence and risk category
        confidence_level = self._determine_confidence(all_features, fake_probability)
        risk_category = self._determine_risk_category(fake_probability, all_features)
        
        # Generate human-readable reasons
        reasons = self._generate_reasons(all_features, fake_probability)
        
        # Compile metadata
        metadata = {
            'feature_count': len(all_features),
            'high_risk_features': len([f for f in all_features if f.value > 0.7]),
            'analysis_timestamp': datetime.now().isoformat(),
            'platform': platform.value,
            'ml_probability': fake_probability
        }
        
        return FakeAccountScore(
            overall_score=fake_probability,
            confidence_level=confidence_level,
            risk_category=risk_category,
            features=all_features,
            reasons=reasons,
            metadata=metadata
        )
    
    def _determine_confidence(self, features: List[DetectionFeature], probability: float) -> str:
        """Determine confidence level in the fake account prediction."""
        high_confidence_features = len([f for f in features if f.value > 0.8 and f.weight > 0.3])
        feature_agreement = statistics.stdev([f.value for f in features]) if len(features) > 1 else 0
        
        # High confidence if multiple strong indicators and low variance
        if high_confidence_features >= 3 and feature_agreement < 0.3:
            return "high"
        elif high_confidence_features >= 2 or (probability > 0.8 or probability < 0.2):
            return "medium"
        else:
            return "low"
    
    def _determine_risk_category(self, probability: float, features: List[DetectionFeature]) -> str:
        """Determine risk category based on probability and features."""
        if probability >= 0.9:
            return "definitely_fake"
        elif probability >= 0.7:
            return "likely_fake"
        elif probability >= 0.4:
            return "suspicious"
        else:
            return "legitimate"
    
    def _generate_reasons(self, features: List[DetectionFeature], probability: float) -> List[str]:
        """Generate human-readable reasons for the fake account assessment."""
        reasons = []
        
        # Sort features by suspiciousness (value * weight)
        suspicious_features = sorted(
            [f for f in features if f.value > 0.3],
            key=lambda x: x.value * x.weight,
            reverse=True
        )[:5]  # Top 5 suspicious features
        
        for feature in suspicious_features:
            if feature.name == "username_pattern_suspicious" and feature.value > 0.5:
                reasons.append("Username follows patterns commonly used by fake accounts")
            elif feature.name == "bio_spam_content" and feature.value > 0.5:
                reasons.append("Profile bio contains spam-like content")
            elif feature.name == "low_follower_ratio" and feature.value > 0.5:
                reasons.append("Suspiciously low follower-to-following ratio")
            elif feature.name == "new_account" and feature.value > 0.5:
                reasons.append("Account is very new")
            elif feature.name == "missing_profile_image" and feature.value > 0.5:
                reasons.append("No profile image")
            elif feature.name == "excessive_following" and feature.value > 0.5:
                reasons.append("Following an unusually high number of accounts")
            elif feature.name == "display_name_legitimacy_claims" and feature.value > 0.5:
                reasons.append("Display name contains unverified legitimacy claims")
            elif feature.value > 0.7:
                reasons.append(f"Suspicious {feature.category} characteristic: {feature.description}")
        
        if probability > 0.8:
            reasons.append("Multiple indicators suggest this is likely a fake account")
        elif probability > 0.6:
            reasons.append("Several suspicious characteristics detected")
        
        if not reasons:
            reasons.append("Account appears legitimate based on available information")
        
        return reasons[:7]  # Limit to 7 reasons for readability
    
    async def batch_analyze_accounts(
        self,
        profiles: List[ProfileData],
        platform: SocialMediaPlatform
    ) -> Dict[str, FakeAccountScore]:
        """Analyze multiple accounts for fake detection."""
        results = {}
        
        for profile in profiles:
            try:
                score = await self.analyze_account(profile, platform)
                results[profile.username] = score
            except Exception as e:
                logger.error("Failed to analyze account", username=profile.username, error=str(e))
                # Create minimal score for failed analysis
                results[profile.username] = FakeAccountScore(
                    overall_score=0.5,
                    confidence_level="low",
                    risk_category="unknown",
                    features=[],
                    reasons=["Analysis failed due to technical error"],
                    metadata={"error": str(e)}
                )
        
        return results
    
    def rank_accounts_by_suspicion(self, analysis_results: Dict[str, FakeAccountScore]) -> List[Tuple[str, FakeAccountScore]]:
        """Rank accounts by suspicion level."""
        # Sort by overall score (descending) and confidence level
        confidence_weights = {"high": 3, "medium": 2, "low": 1}
        
        ranked = sorted(
            analysis_results.items(),
            key=lambda x: (
                x[1].overall_score,
                confidence_weights.get(x[1].confidence_level, 0)
            ),
            reverse=True
        )
        
        return ranked
    
    def generate_summary_report(self, analysis_results: Dict[str, FakeAccountScore]) -> Dict[str, Any]:
        """Generate summary report of fake account analysis."""
        if not analysis_results:
            return {
                "total_accounts": 0,
                "risk_distribution": {},
                "high_priority_alerts": [],
                "summary": "No accounts analyzed"
            }
        
        # Count by risk category
        risk_distribution = {}
        for score in analysis_results.values():
            risk_distribution[score.risk_category] = risk_distribution.get(score.risk_category, 0) + 1
        
        # High priority alerts (definitely fake or likely fake with high confidence)
        high_priority = []
        for username, score in analysis_results.items():
            if (score.risk_category in ["definitely_fake", "likely_fake"] and 
                score.confidence_level in ["high", "medium"]):
                high_priority.append({
                    "username": username,
                    "risk_category": score.risk_category,
                    "confidence": score.confidence_level,
                    "score": score.overall_score,
                    "top_reasons": score.reasons[:3]
                })
        
        # Sort high priority by score
        high_priority.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "total_accounts": len(analysis_results),
            "risk_distribution": risk_distribution,
            "high_priority_alerts": high_priority[:10],  # Top 10
            "average_fake_score": statistics.mean([s.overall_score for s in analysis_results.values()]),
            "summary": f"Analyzed {len(analysis_results)} accounts. "
                      f"{len(high_priority)} high-priority threats identified."
        }