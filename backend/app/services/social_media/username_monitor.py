"""
Username and handle monitoring system for detecting impersonations and variations.
"""

import asyncio
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from difflib import SequenceMatcher
from collections import defaultdict
import unicodedata

import structlog
from fuzzywuzzy import fuzz, process

from app.db.models.social_media import SocialMediaPlatform
from .config import SocialMediaSettings, MonitoringConfig
from .api_clients import ProfileData, SearchResult, create_api_client
from .scrapers import create_scraper


logger = structlog.get_logger(__name__)


@dataclass
class UsernameVariation:
    """Represents a username variation to monitor."""
    original: str
    variation: str
    similarity_score: float
    variation_type: str  # substitution, addition, omission, transposition, etc.
    risk_level: str  # low, medium, high
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class UsernameMatch:
    """Represents a found username that matches monitoring criteria."""
    found_username: str
    original_username: str
    platform: SocialMediaPlatform
    similarity_score: float
    match_type: str
    profile_data: Optional[ProfileData] = None
    risk_assessment: str = "medium"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class UsernameGenerator:
    """Generates username variations for monitoring."""
    
    def __init__(self, settings: SocialMediaSettings):
        self.settings = settings
        self.common_substitutions = self._load_common_substitutions()
        self.common_additions = self._load_common_additions()
        self.leet_speak_map = self._load_leet_speak_mapping()
        
    def _load_common_substitutions(self) -> Dict[str, List[str]]:
        """Load common character substitutions used in impersonations."""
        return {
            'a': ['@', '4', 'α', 'а'],  # Latin a, Cyrillic а
            'e': ['3', 'ë', 'é', 'е'],  # Latin e, Cyrillic е
            'i': ['1', 'l', '!', 'í', 'ï', 'і'],  # Latin i, Cyrillic і
            'o': ['0', 'ö', 'ó', 'о'],  # Latin o, Cyrillic о
            'u': ['ü', 'ú', 'υ'],
            's': ['$', '5', 'ѕ'],  # Latin s, Cyrillic ѕ
            'l': ['1', 'I', '|'],
            't': ['7', '+'],
            'g': ['9', 'q'],
            'b': ['6'],
            'z': ['2'],
            'c': ['(', 'ç', 'с'],  # Latin c, Cyrillic с
            'p': ['р'],  # Cyrillic р
            'h': ['н'],  # Cyrillic н
            'x': ['х'],  # Cyrillic х
            'y': ['у'],  # Cyrillic у
            'k': ['κ'],  # Greek κ
        }
    
    def _load_common_additions(self) -> List[str]:
        """Load common additions to usernames."""
        return [
            '', '_', '.', '-', '2023', '2024', '2025',
            'official', 'real', 'verified', 'vip', 'premium',
            '1', '2', '3', '11', '22', '33', '69', '420',
            'x', 'xx', 'xxx', 'o', 'oo', 'ooo',
        ]
    
    def _load_leet_speak_mapping(self) -> Dict[str, str]:
        """Load leet speak character mappings."""
        return {
            '@': 'a', '4': 'a', '3': 'e', '1': 'i', '0': 'o',
            '5': 's', '7': 't', '6': 'b', '9': 'g', '2': 'z',
            '!': 'i', '$': 's', '+': 't', '|': 'l', '(': 'c'
        }
    
    def generate_variations(self, username: str, max_variations: int = 100) -> List[UsernameVariation]:
        """Generate comprehensive username variations."""
        variations = set()
        username_lower = username.lower()
        
        # 1. Character substitutions
        variations.update(self._generate_substitution_variations(username_lower))
        
        # 2. Character additions/prefixes/suffixes
        variations.update(self._generate_addition_variations(username_lower))
        
        # 3. Character omissions
        variations.update(self._generate_omission_variations(username_lower))
        
        # 4. Transpositions (adjacent character swaps)
        variations.update(self._generate_transposition_variations(username_lower))
        
        # 5. Unicode homoglyphs
        variations.update(self._generate_homoglyph_variations(username_lower))
        
        # 6. Common misspellings
        variations.update(self._generate_misspelling_variations(username_lower))
        
        # 7. Keyboard proximity variations
        variations.update(self._generate_keyboard_variations(username_lower))
        
        # Convert to UsernameVariation objects and calculate similarity
        variation_objects = []
        for var, var_type in variations:
            if var != username_lower and len(var) > 2:  # Exclude original and very short variations
                similarity = self._calculate_similarity(username_lower, var)
                risk_level = self._assess_risk_level(username_lower, var, similarity)
                
                variation_obj = UsernameVariation(
                    original=username,
                    variation=var,
                    similarity_score=similarity,
                    variation_type=var_type,
                    risk_level=risk_level,
                    metadata={'length_diff': len(var) - len(username_lower)}
                )
                variation_objects.append(variation_obj)
        
        # Sort by risk level and similarity
        variation_objects.sort(key=lambda x: (x.risk_level == 'high', x.similarity_score), reverse=True)
        
        return variation_objects[:max_variations]
    
    def _generate_substitution_variations(self, username: str) -> Set[Tuple[str, str]]:
        """Generate variations using character substitutions."""
        variations = set()
        
        for i, char in enumerate(username):
            if char in self.common_substitutions:
                for substitute in self.common_substitutions[char]:
                    variation = username[:i] + substitute + username[i+1:]
                    variations.add((variation, 'substitution'))
        
        return variations
    
    def _generate_addition_variations(self, username: str) -> Set[Tuple[str, str]]:
        """Generate variations with additions."""
        variations = set()
        
        for addition in self.common_additions:
            if addition:  # Skip empty string
                variations.add((username + addition, 'suffix'))
                variations.add((addition + username, 'prefix'))
                
                # Add in middle for longer usernames
                if len(username) > 4:
                    mid = len(username) // 2
                    variation = username[:mid] + addition + username[mid:]
                    variations.add((variation, 'insertion'))
        
        return variations
    
    def _generate_omission_variations(self, username: str) -> Set[Tuple[str, str]]:
        """Generate variations by omitting characters."""
        variations = set()
        
        if len(username) > 3:  # Don't make username too short
            for i in range(len(username)):
                variation = username[:i] + username[i+1:]
                if len(variation) > 2:
                    variations.add((variation, 'omission'))
        
        return variations
    
    def _generate_transposition_variations(self, username: str) -> Set[Tuple[str, str]]:
        """Generate variations by swapping adjacent characters."""
        variations = set()
        
        for i in range(len(username) - 1):
            chars = list(username)
            chars[i], chars[i+1] = chars[i+1], chars[i]
            variation = ''.join(chars)
            variations.add((variation, 'transposition'))
        
        return variations
    
    def _generate_homoglyph_variations(self, username: str) -> Set[Tuple[str, str]]:
        """Generate variations using Unicode homoglyphs (visually similar characters)."""
        variations = set()
        
        # This is a simplified version - a full implementation would have extensive homoglyph mappings
        homoglyphs = {
            'a': ['а'],  # Cyrillic a
            'e': ['е'],  # Cyrillic e
            'o': ['о'],  # Cyrillic o
            'p': ['р'],  # Cyrillic p
            'c': ['с'],  # Cyrillic c
            'x': ['х'],  # Cyrillic x
            'y': ['у'],  # Cyrillic y
        }
        
        for i, char in enumerate(username):
            if char in homoglyphs:
                for homoglyph in homoglyphs[char]:
                    variation = username[:i] + homoglyph + username[i+1:]
                    variations.add((variation, 'homoglyph'))
        
        return variations
    
    def _generate_misspelling_variations(self, username: str) -> Set[Tuple[str, str]]:
        """Generate common misspelling variations."""
        variations = set()
        
        # Double characters
        for i in range(len(username)):
            variation = username[:i+1] + username[i] + username[i+1:]
            variations.add((variation, 'double_char'))
        
        # Common letter swaps
        common_swaps = [('ei', 'ie'), ('ou', 'uo'), ('er', 're')]
        for old, new in common_swaps:
            if old in username:
                variation = username.replace(old, new)
                variations.add((variation, 'letter_swap'))
        
        return variations
    
    def _generate_keyboard_variations(self, username: str) -> Set[Tuple[str, str]]:
        """Generate variations based on keyboard proximity."""
        variations = set()
        
        # QWERTY keyboard layout proximity
        keyboard_proximity = {
            'q': ['w', 'a'], 'w': ['q', 'e', 's'], 'e': ['w', 'r', 'd'],
            'r': ['e', 't', 'f'], 't': ['r', 'y', 'g'], 'y': ['t', 'u', 'h'],
            'u': ['y', 'i', 'j'], 'i': ['u', 'o', 'k'], 'o': ['i', 'p', 'l'],
            'p': ['o'], 'a': ['q', 's', 'z'], 's': ['w', 'a', 'd', 'z', 'x'],
            'd': ['e', 's', 'f', 'x', 'c'], 'f': ['r', 'd', 'g', 'c', 'v'],
            'g': ['t', 'f', 'h', 'v', 'b'], 'h': ['y', 'g', 'j', 'b', 'n'],
            'j': ['u', 'h', 'k', 'n', 'm'], 'k': ['i', 'j', 'l', 'm'],
            'l': ['o', 'k'], 'z': ['a', 's', 'x'], 'x': ['s', 'd', 'z', 'c'],
            'c': ['d', 'f', 'x', 'v'], 'v': ['f', 'g', 'c', 'b'],
            'b': ['g', 'h', 'v', 'n'], 'n': ['h', 'j', 'b', 'm'],
            'm': ['j', 'k', 'n']
        }
        
        for i, char in enumerate(username):
            if char in keyboard_proximity:
                for adjacent in keyboard_proximity[char]:
                    variation = username[:i] + adjacent + username[i+1:]
                    variations.add((variation, 'keyboard_proximity'))
        
        return variations
    
    def _calculate_similarity(self, original: str, variation: str) -> float:
        """Calculate similarity score between original and variation."""
        # Use multiple similarity metrics and combine them
        ratio = SequenceMatcher(None, original, variation).ratio()
        partial_ratio = fuzz.partial_ratio(original, variation) / 100.0
        token_sort_ratio = fuzz.token_sort_ratio(original, variation) / 100.0
        
        # Weighted average
        similarity = (ratio * 0.5 + partial_ratio * 0.3 + token_sort_ratio * 0.2)
        return similarity
    
    def _assess_risk_level(self, original: str, variation: str, similarity: float) -> str:
        """Assess risk level of username variation."""
        # High risk: very similar usernames that could easily fool users
        if similarity >= 0.9:
            return 'high'
        
        # High risk: single character substitutions with visually similar characters
        if len(original) == len(variation):
            diff_count = sum(1 for a, b in zip(original, variation) if a != b)
            if diff_count == 1:
                return 'high'
        
        # High risk: common impersonation patterns
        high_risk_patterns = ['official', 'real', 'verified', 'vip']
        for pattern in high_risk_patterns:
            if pattern in variation and pattern not in original:
                return 'high'
        
        # Medium risk
        if similarity >= 0.75:
            return 'medium'
        
        return 'low'


class UsernameMonitor:
    """Main username monitoring service."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.settings = config.settings
        self.generator = UsernameGenerator(self.settings)
        self.logger = logger.bind(service="username_monitor")
        
    async def monitor_username(
        self,
        username: str,
        platforms: List[SocialMediaPlatform],
        stage_name: Optional[str] = None
    ) -> Dict[SocialMediaPlatform, List[UsernameMatch]]:
        """Monitor username across specified platforms."""
        # Generate variations to monitor
        variations = self.generator.generate_variations(username)
        
        # Add stage name variations if provided
        if stage_name:
            stage_variations = self.generator.generate_variations(stage_name)
            variations.extend(stage_variations)
        
        # Filter to high and medium risk variations to avoid overwhelming searches
        priority_variations = [
            v for v in variations 
            if v.risk_level in ['high', 'medium']
        ][:50]  # Limit to top 50 variations
        
        results = {}
        
        for platform in platforms:
            self.logger.info("Monitoring platform", platform=platform.value, username=username)
            platform_matches = await self._monitor_platform(username, priority_variations, platform)
            results[platform] = platform_matches
        
        return results
    
    async def _monitor_platform(
        self,
        original_username: str,
        variations: List[UsernameVariation],
        platform: SocialMediaPlatform
    ) -> List[UsernameMatch]:
        """Monitor a specific platform for username variations."""
        matches = []
        platform_config = self.config.get_platform_config(platform)
        
        if not platform_config:
            self.logger.warning("No configuration for platform", platform=platform.value)
            return matches
        
        # Try API-based search first
        api_matches = await self._search_via_api(original_username, variations, platform, platform_config)
        matches.extend(api_matches)
        
        # Fallback to scraping if API is limited
        if not api_matches or len(api_matches) < 5:
            scraping_matches = await self._search_via_scraping(original_username, variations, platform, platform_config)
            matches.extend(scraping_matches)
        
        # Remove duplicates
        seen_usernames = set()
        unique_matches = []
        for match in matches:
            if match.found_username not in seen_usernames:
                unique_matches.append(match)
                seen_usernames.add(match.found_username)
        
        # Sort by similarity score
        unique_matches.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return unique_matches
    
    async def _search_via_api(
        self,
        original_username: str,
        variations: List[UsernameVariation],
        platform: SocialMediaPlatform,
        platform_config
    ) -> List[UsernameMatch]:
        """Search for username variations using platform API."""
        matches = []
        
        try:
            async with create_api_client(platform, platform_config, self.settings) as client:
                # Search for exact matches first
                for variation in variations[:20]:  # Limit API calls
                    try:
                        profile = await client.get_profile(variation.variation)
                        if profile:
                            match = UsernameMatch(
                                found_username=profile.username,
                                original_username=original_username,
                                platform=platform,
                                similarity_score=variation.similarity_score,
                                match_type='exact',
                                profile_data=profile,
                                risk_assessment=variation.risk_level,
                                metadata={
                                    'detection_method': 'api_exact',
                                    'variation_type': variation.variation_type
                                }
                            )
                            matches.append(match)
                    
                    except Exception as e:
                        self.logger.debug("API profile lookup failed", username=variation.variation, error=str(e))
                        continue
                
                # Try search functionality if available
                if hasattr(client, 'search_profiles'):
                    try:
                        search_result = await client.search_profiles(original_username, limit=20)
                        for profile in search_result.profiles:
                            similarity = self.generator._calculate_similarity(original_username, profile.username)
                            if similarity >= 0.7:  # Only include reasonably similar matches
                                match = UsernameMatch(
                                    found_username=profile.username,
                                    original_username=original_username,
                                    platform=platform,
                                    similarity_score=similarity,
                                    match_type='search',
                                    profile_data=profile,
                                    risk_assessment='medium',
                                    metadata={
                                        'detection_method': 'api_search'
                                    }
                                )
                                matches.append(match)
                    except Exception as e:
                        self.logger.debug("API search failed", error=str(e))
        
        except Exception as e:
            self.logger.error("API client creation failed", platform=platform.value, error=str(e))
        
        return matches
    
    async def _search_via_scraping(
        self,
        original_username: str,
        variations: List[UsernameVariation],
        platform: SocialMediaPlatform,
        platform_config
    ) -> List[UsernameMatch]:
        """Search for username variations using web scraping."""
        matches = []
        
        try:
            scraper = create_scraper(platform, platform_config, self.settings)
            
            # Check high-priority variations
            high_priority = [v for v in variations if v.risk_level == 'high'][:10]
            
            for variation in high_priority:
                try:
                    profile = await scraper.scrape_profile(variation.variation)
                    if profile:
                        match = UsernameMatch(
                            found_username=profile.username,
                            original_username=original_username,
                            platform=platform,
                            similarity_score=variation.similarity_score,
                            match_type='scraping',
                            profile_data=profile,
                            risk_assessment=variation.risk_level,
                            metadata={
                                'detection_method': 'scraping',
                                'variation_type': variation.variation_type
                            }
                        )
                        matches.append(match)
                
                except Exception as e:
                    self.logger.debug("Scraping failed", username=variation.variation, error=str(e))
                    continue
        
        except Exception as e:
            self.logger.error("Scraper creation failed", platform=platform.value, error=str(e))
        
        return matches
    
    async def continuous_monitoring(
        self,
        username: str,
        platforms: List[SocialMediaPlatform],
        check_interval_hours: int = 24,
        stage_name: Optional[str] = None
    ) -> None:
        """Continuously monitor username variations."""
        self.logger.info(
            "Starting continuous monitoring",
            username=username,
            platforms=[p.value for p in platforms],
            check_interval=check_interval_hours
        )
        
        while True:
            try:
                results = await self.monitor_username(username, platforms, stage_name)
                
                # Process results
                total_matches = sum(len(matches) for matches in results.values())
                high_risk_matches = sum(
                    len([m for m in matches if m.risk_assessment == 'high'])
                    for matches in results.values()
                )
                
                self.logger.info(
                    "Monitoring cycle completed",
                    username=username,
                    total_matches=total_matches,
                    high_risk_matches=high_risk_matches
                )
                
                # Here you would typically save results to database
                # and trigger alerts for high-risk matches
                
                # Wait for next check
                await asyncio.sleep(check_interval_hours * 3600)
                
            except Exception as e:
                self.logger.error("Monitoring cycle failed", username=username, error=str(e))
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    def analyze_username_risks(self, matches: List[UsernameMatch]) -> Dict[str, Any]:
        """Analyze risks from found username matches."""
        if not matches:
            return {
                'total_matches': 0,
                'risk_distribution': {'low': 0, 'medium': 0, 'high': 0},
                'top_risks': [],
                'recommendations': ['No suspicious usernames found']
            }
        
        risk_distribution = {'low': 0, 'medium': 0, 'high': 0}
        for match in matches:
            risk_distribution[match.risk_assessment] += 1
        
        # Sort by risk and similarity
        sorted_matches = sorted(
            matches,
            key=lambda x: (x.risk_assessment == 'high', x.similarity_score),
            reverse=True
        )
        
        top_risks = sorted_matches[:10]  # Top 10 highest risk matches
        
        recommendations = []
        if risk_distribution['high'] > 0:
            recommendations.append(f"URGENT: {risk_distribution['high']} high-risk impersonation(s) detected")
        if risk_distribution['medium'] > 5:
            recommendations.append(f"Consider investigating {risk_distribution['medium']} medium-risk accounts")
        if len(matches) > 20:
            recommendations.append("High number of similar usernames detected - consider trademark protection")
        
        return {
            'total_matches': len(matches),
            'risk_distribution': risk_distribution,
            'top_risks': [
                {
                    'username': match.found_username,
                    'platform': match.platform.value,
                    'similarity_score': match.similarity_score,
                    'risk_level': match.risk_assessment
                }
                for match in top_risks
            ],
            'recommendations': recommendations
        }