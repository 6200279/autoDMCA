"""
Multi-Profile Scanning Optimization System
Optimizes scanning efficiency when monitoring multiple creator profiles
"""
import asyncio
import logging
from typing import List, Dict, Any, Set, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import networkx as nx
from sklearn.cluster import DBSCAN
import numpy as np

from app.services.scanning.web_crawler import WebCrawler
from app.services.ai.content_matcher import ContentMatcher

logger = logging.getLogger(__name__)


@dataclass
class ProfileGroup:
    """Group of related profiles that can be scanned together"""
    group_id: str
    profile_ids: List[int]
    shared_keywords: List[str]
    shared_platforms: List[str]
    optimization_score: float
    scan_priority: int


class MultiProfileOptimizer:
    """
    Optimizes scanning for multiple profiles by identifying overlaps and efficiencies
    PRD: "economies of scale in multi-profile scanning"
    """
    
    def __init__(self):
        self.crawler = WebCrawler()
        self.content_matcher = ContentMatcher()
        
        # Caching for optimization
        self.url_cache: Dict[str, datetime] = {}
        self.site_map_cache: Dict[str, List[str]] = {}
        self.keyword_overlap_cache: Dict[Tuple[int, int], float] = {}
        
        # Performance tracking
        self.optimization_stats = {
            'total_profiles': 0,
            'groups_created': 0,
            'urls_deduplicated': 0,
            'scan_time_saved': 0
        }
        
    async def optimize_multi_profile_scan(
        self,
        profiles: List[Dict[str, Any]]
    ) -> List[ProfileGroup]:
        """
        Analyze profiles and create optimized scanning groups
        """
        logger.info(f"Optimizing scan for {len(profiles)} profiles")
        
        # Step 1: Analyze profile relationships
        relationships = await self._analyze_profile_relationships(profiles)
        
        # Step 2: Create profile groups based on similarities
        groups = await self._create_profile_groups(profiles, relationships)
        
        # Step 3: Optimize scanning order and strategy
        optimized_groups = await self._optimize_scanning_strategy(groups)
        
        # Step 4: Update statistics
        self.optimization_stats['total_profiles'] = len(profiles)
        self.optimization_stats['groups_created'] = len(optimized_groups)
        
        logger.info(f"Created {len(optimized_groups)} optimized scanning groups")
        return optimized_groups
        
    async def _analyze_profile_relationships(
        self,
        profiles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze relationships between profiles to identify optimization opportunities"""
        
        relationships = {
            'keyword_similarity': {},
            'platform_overlap': {},
            'content_similarity': {},
            'geographical_overlap': {},
            'temporal_patterns': {}
        }
        
        # Analyze keyword overlaps
        for i, profile1 in enumerate(profiles):
            for j, profile2 in enumerate(profiles[i+1:], i+1):
                similarity = await self._calculate_keyword_similarity(profile1, profile2)
                relationships['keyword_similarity'][(i, j)] = similarity
                
        # Analyze platform overlaps
        platform_groups = defaultdict(list)
        for i, profile in enumerate(profiles):
            platform = profile.get('platform', 'unknown')
            platform_groups[platform].append(i)
            
        relationships['platform_overlap'] = dict(platform_groups)
        
        # Analyze content similarity (if face encodings are available)
        for i, profile1 in enumerate(profiles):
            for j, profile2 in enumerate(profiles[i+1:], i+1):
                if (profile1.get('face_encodings') and 
                    profile2.get('face_encodings')):
                    similarity = await self._calculate_content_similarity(
                        profile1, profile2
                    )
                    relationships['content_similarity'][(i, j)] = similarity
                    
        return relationships
        
    async def _calculate_keyword_similarity(
        self,
        profile1: Dict[str, Any],
        profile2: Dict[str, Any]
    ) -> float:
        """Calculate keyword similarity between two profiles"""
        
        keywords1 = set(profile1.get('keywords', []))
        keywords2 = set(profile2.get('keywords', []))
        
        # Add usernames as keywords
        if profile1.get('username'):
            keywords1.add(profile1['username'])
        if profile2.get('username'):
            keywords2.add(profile2['username'])
            
        if not keywords1 or not keywords2:
            return 0.0
            
        # Calculate Jaccard similarity
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)
        
        similarity = len(intersection) / len(union) if union else 0.0
        
        # Cache the result
        cache_key = (profile1.get('id', 0), profile2.get('id', 0))
        self.keyword_overlap_cache[cache_key] = similarity
        
        return similarity
        
    async def _calculate_content_similarity(
        self,
        profile1: Dict[str, Any],
        profile2: Dict[str, Any]
    ) -> float:
        """Calculate content similarity using face encodings"""
        
        try:
            encodings1 = profile1.get('face_encodings', [])
            encodings2 = profile2.get('face_encodings', [])
            
            if not encodings1 or not encodings2:
                return 0.0
                
            max_similarity = 0.0
            
            # Compare face encodings
            for enc1 in encodings1:
                for enc2 in encodings2:
                    # Calculate cosine similarity
                    arr1 = np.array(enc1)
                    arr2 = np.array(enc2)
                    
                    similarity = np.dot(arr1, arr2) / (
                        np.linalg.norm(arr1) * np.linalg.norm(arr2)
                    )
                    
                    max_similarity = max(max_similarity, similarity)
                    
            return max_similarity
            
        except Exception as e:
            logger.error(f"Error calculating content similarity: {e}")
            return 0.0
            
    async def _create_profile_groups(
        self,
        profiles: List[Dict[str, Any]],
        relationships: Dict[str, Any]
    ) -> List[ProfileGroup]:
        """Create optimized profile groups based on relationships"""
        
        # Create similarity matrix
        n_profiles = len(profiles)
        similarity_matrix = np.zeros((n_profiles, n_profiles))
        
        # Fill similarity matrix
        keyword_sim = relationships['keyword_similarity']
        content_sim = relationships['content_similarity']
        
        for (i, j), sim in keyword_sim.items():
            # Combine keyword and content similarities
            content_score = content_sim.get((i, j), 0.0)
            combined_score = 0.7 * sim + 0.3 * content_score
            
            similarity_matrix[i][j] = combined_score
            similarity_matrix[j][i] = combined_score
            
        # Use DBSCAN clustering to group similar profiles
        clustering = DBSCAN(
            eps=0.3,  # Similarity threshold
            min_samples=1,
            metric='precomputed'
        )
        
        # Convert similarity to distance matrix
        distance_matrix = 1.0 - similarity_matrix
        cluster_labels = clustering.fit_predict(distance_matrix)
        
        # Create profile groups
        groups = []
        cluster_groups = defaultdict(list)
        
        for i, label in enumerate(cluster_labels):
            cluster_groups[label].append(i)
            
        # Create ProfileGroup objects
        for cluster_id, profile_indices in cluster_groups.items():
            if len(profile_indices) >= 1:  # Only create groups with at least 1 profile
                
                # Calculate shared keywords and platforms
                shared_keywords = self._find_shared_keywords(
                    [profiles[i] for i in profile_indices]
                )
                shared_platforms = self._find_shared_platforms(
                    [profiles[i] for i in profile_indices]
                )
                
                # Calculate optimization score
                optimization_score = self._calculate_optimization_score(
                    profile_indices, similarity_matrix
                )
                
                group = ProfileGroup(
                    group_id=f"group_{cluster_id}",
                    profile_ids=[profiles[i]['id'] for i in profile_indices],
                    shared_keywords=shared_keywords,
                    shared_platforms=shared_platforms,
                    optimization_score=optimization_score,
                    scan_priority=self._calculate_scan_priority(
                        [profiles[i] for i in profile_indices]
                    )
                )
                
                groups.append(group)
                
        return groups
        
    def _find_shared_keywords(self, profiles: List[Dict[str, Any]]) -> List[str]:
        """Find keywords that are common across profiles in a group"""
        
        if not profiles:
            return []
            
        # Get all keywords from all profiles
        all_keywords = [set(p.get('keywords', [])) for p in profiles]
        
        # Find intersection
        if all_keywords:
            shared = all_keywords[0]
            for keywords in all_keywords[1:]:
                shared = shared.intersection(keywords)
            return list(shared)
        else:
            return []
            
    def _find_shared_platforms(self, profiles: List[Dict[str, Any]]) -> List[str]:
        """Find platforms that are common across profiles in a group"""
        
        platforms = [p.get('platform', 'unknown') for p in profiles]
        platform_counts = defaultdict(int)
        
        for platform in platforms:
            platform_counts[platform] += 1
            
        # Return platforms that appear more than once
        return [
            platform for platform, count in platform_counts.items()
            if count > 1
        ]
        
    def _calculate_optimization_score(
        self,
        profile_indices: List[int],
        similarity_matrix: np.ndarray
    ) -> float:
        """Calculate optimization score for a group"""
        
        if len(profile_indices) <= 1:
            return 0.0
            
        # Calculate average similarity within the group
        total_similarity = 0.0
        count = 0
        
        for i, idx1 in enumerate(profile_indices):
            for j, idx2 in enumerate(profile_indices[i+1:], i+1):
                total_similarity += similarity_matrix[idx1][idx2]
                count += 1
                
        avg_similarity = total_similarity / count if count > 0 else 0.0
        
        # Factor in group size (larger groups have more optimization potential)
        size_factor = min(len(profile_indices) / 5.0, 1.0)  # Cap at 5 profiles
        
        return avg_similarity * size_factor
        
    def _calculate_scan_priority(self, profiles: List[Dict[str, Any]]) -> int:
        """Calculate scanning priority for a group"""
        
        # Higher priority for:
        # - Premium users
        # - Profiles with more recent activity
        # - Profiles with higher infringement rates
        
        priority_score = 0
        
        for profile in profiles:
            # Premium users get higher priority
            if profile.get('priority', False):
                priority_score += 10
                
            # Recent activity
            last_scan = profile.get('last_scan_date')
            if last_scan:
                days_since_scan = (datetime.utcnow() - last_scan).days
                if days_since_scan > 7:
                    priority_score += 5
                    
            # Infringement history
            infringement_count = profile.get('total_infringements', 0)
            if infringement_count > 10:
                priority_score += 3
                
        return priority_score
        
    async def _optimize_scanning_strategy(
        self,
        groups: List[ProfileGroup]
    ) -> List[ProfileGroup]:
        """Optimize the scanning strategy for each group"""
        
        # Sort groups by priority
        sorted_groups = sorted(groups, key=lambda g: g.scan_priority, reverse=True)
        
        # Add optimization strategies to each group
        for group in sorted_groups:
            group.metadata = await self._create_optimization_metadata(group)
            
        return sorted_groups
        
    async def _create_optimization_metadata(
        self,
        group: ProfileGroup
    ) -> Dict[str, Any]:
        """Create optimization metadata for a group"""
        
        metadata = {
            'scan_strategy': 'parallel' if len(group.profile_ids) > 1 else 'single',
            'shared_search_terms': group.shared_keywords,
            'deduplication_enabled': len(group.profile_ids) > 1,
            'batch_size': min(len(group.profile_ids), 5),
            'estimated_efficiency_gain': group.optimization_score * 100
        }
        
        # Add platform-specific optimizations
        if group.shared_platforms:
            metadata['platform_optimizations'] = {
                platform: self._get_platform_optimization(platform)
                for platform in group.shared_platforms
            }
            
        return metadata
        
    def _get_platform_optimization(self, platform: str) -> Dict[str, Any]:
        """Get platform-specific optimization settings"""
        
        optimizations = {
            'instagram': {
                'batch_search': True,
                'image_focus': True,
                'rate_limit': 2.0
            },
            'onlyfans': {
                'leak_site_focus': True,
                'subscriber_analysis': True,
                'rate_limit': 1.0
            },
            'tiktok': {
                'video_focus': True,
                'hashtag_analysis': True,
                'rate_limit': 1.5
            },
            'patreon': {
                'content_tier_analysis': True,
                'subscriber_leak_tracking': True,
                'rate_limit': 1.0
            }
        }
        
        return optimizations.get(platform, {'rate_limit': 1.0})
        
    async def execute_optimized_scan(
        self,
        group: ProfileGroup,
        profiles_data: Dict[int, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute an optimized scan for a profile group"""
        
        start_time = datetime.utcnow()
        
        try:
            # Get profile data for the group
            group_profiles = [
                profiles_data[pid] for pid in group.profile_ids
                if pid in profiles_data
            ]
            
            if not group_profiles:
                return {'error': 'No valid profiles in group'}
                
            # Choose scanning strategy based on group
            if len(group_profiles) == 1:
                results = await self._single_profile_scan(group_profiles[0])
            else:
                results = await self._multi_profile_batch_scan(
                    group_profiles, group
                )
                
            # Calculate performance metrics
            scan_duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Update optimization statistics
            self.optimization_stats['scan_time_saved'] += self._calculate_time_savings(
                group, scan_duration
            )
            
            return {
                'group_id': group.group_id,
                'profiles_scanned': len(group_profiles),
                'scan_duration': scan_duration,
                'results': results,
                'optimization_applied': True
            }
            
        except Exception as e:
            logger.error(f"Error in optimized scan: {e}")
            return {'error': str(e)}
            
    async def _single_profile_scan(
        self,
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Scan a single profile (fallback to regular scanning)"""
        
        async with self.crawler:
            results = await self.crawler.scan_for_profile(profile)
            
        return {
            'profile_id': profile['id'],
            'urls_scanned': len(results),
            'matches_found': sum(1 for r in results if r.status == 'completed'),
            'results': results
        }
        
    async def _multi_profile_batch_scan(
        self,
        profiles: List[Dict[str, Any]],
        group: ProfileGroup
    ) -> Dict[str, Any]:
        """Scan multiple profiles as a batch with optimizations"""
        
        # Combine search terms from all profiles
        combined_keywords = set()
        for profile in profiles:
            combined_keywords.update(profile.get('keywords', []))
            if profile.get('username'):
                combined_keywords.add(profile['username'])
                
        # Add shared keywords
        combined_keywords.update(group.shared_keywords)
        
        # Create a merged profile for scanning
        merged_profile = {
            'id': f"group_{group.group_id}",
            'keywords': list(combined_keywords),
            'platforms': group.shared_platforms,
            'face_encodings': [],
            'optimization_mode': True
        }
        
        # Collect face encodings from all profiles
        for profile in profiles:
            if profile.get('face_encodings'):
                merged_profile['face_encodings'].extend(
                    profile['face_encodings']
                )
                
        # Perform the batch scan
        async with self.crawler:
            batch_results = await self.crawler.scan_for_profile(
                merged_profile, deep_scan=True
            )
            
        # Post-process results to attribute them to specific profiles
        attributed_results = await self._attribute_results_to_profiles(
            batch_results, profiles
        )
        
        # Calculate deduplication savings
        urls_deduplicated = len(batch_results) - len(
            set(r.url for r in batch_results)
        )
        self.optimization_stats['urls_deduplicated'] += urls_deduplicated
        
        return {
            'group_scan': True,
            'profiles_count': len(profiles),
            'combined_keywords': len(combined_keywords),
            'urls_scanned': len(batch_results),
            'urls_deduplicated': urls_deduplicated,
            'attributed_results': attributed_results
        }
        
    async def _attribute_results_to_profiles(
        self,
        batch_results: List[Any],
        profiles: List[Dict[str, Any]]
    ) -> Dict[int, List[Any]]:
        """Attribute batch scan results to specific profiles"""
        
        attributed = defaultdict(list)
        
        for result in batch_results:
            # Check which profiles this result matches
            for profile in profiles:
                if await self._result_matches_profile(result, profile):
                    attributed[profile['id']].append(result)
                    
        return dict(attributed)
        
    async def _result_matches_profile(
        self,
        result: Any,
        profile: Dict[str, Any]
    ) -> bool:
        """Check if a scan result matches a specific profile"""
        
        # Check for username mentions
        username = profile.get('username', '').lower()
        if username and username in result.text_content.lower():
            return True
            
        # Check for keyword matches
        keywords = profile.get('keywords', [])
        for keyword in keywords:
            if keyword.lower() in result.text_content.lower():
                return True
                
        # Check for visual matches (if face encodings are available)
        if (profile.get('face_encodings') and 
            result.images and 
            hasattr(result, 'face_matches')):
            # This would require more detailed analysis
            return True
            
        return False
        
    def _calculate_time_savings(
        self,
        group: ProfileGroup,
        actual_duration: float
    ) -> float:
        """Calculate estimated time savings from optimization"""
        
        # Estimate time if scanned individually
        estimated_individual_time = len(group.profile_ids) * 300  # 5 minutes per profile
        
        # Calculate savings
        time_saved = max(0, estimated_individual_time - actual_duration)
        
        return time_saved
        
    def get_optimization_statistics(self) -> Dict[str, Any]:
        """Get optimization performance statistics"""
        
        return {
            'total_profiles_optimized': self.optimization_stats['total_profiles'],
            'profile_groups_created': self.optimization_stats['groups_created'],
            'urls_deduplicated': self.optimization_stats['urls_deduplicated'],
            'estimated_time_saved_seconds': self.optimization_stats['scan_time_saved'],
            'cache_hit_rate': len(self.keyword_overlap_cache) / max(1, self.optimization_stats['total_profiles']),
            'optimization_enabled': True
        }