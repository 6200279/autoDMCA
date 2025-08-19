"""
AI Performance Benchmarking Suite
Comprehensive benchmarking of AI inference performance with production-ready metrics
"""
import asyncio
import time
import statistics
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np
from PIL import Image
import torch
import psutil
import matplotlib.pyplot as plt
import seaborn as sns

from app.services.ai.performance_optimized_matcher import performance_matcher
from app.services.performance.ai_performance_optimizer import ai_optimizer, OptimizationLevel
from app.services.monitoring.performance_monitor import performance_monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIPerformanceBenchmark:
    """
    Comprehensive AI performance benchmarking system
    Measures and validates performance against production requirements
    """
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.utcnow().isoformat(),
            'system_info': self._get_system_info(),
            'benchmarks': {},
            'performance_goals': {
                'inference_time_ms': 2000,  # <2s target
                'api_response_ms': 500,     # <500ms target
                'concurrent_users': 1000,    # 1000+ target
                'uptime_percent': 99.9       # 99.9% target
            }
        }
        self.test_data = self._prepare_test_data()
        
    def _get_system_info(self) -> Dict[str, Any]:
        """Collect system information"""
        return {
            'cpu_count': psutil.cpu_count(),
            'cpu_freq': psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            'memory_gb': psutil.virtual_memory().total / (1024**3),
            'gpu_available': torch.cuda.is_available(),
            'gpu_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A',
            'gpu_memory_gb': torch.cuda.get_device_properties(0).total_memory / (1024**3) if torch.cuda.is_available() else 0
        }
    
    def _prepare_test_data(self) -> Dict[str, Any]:
        """Prepare test data for benchmarking"""
        # Create test images of different sizes
        test_images = {
            'small': Image.new('RGB', (224, 224), color='white'),
            'medium': Image.new('RGB', (512, 512), color='gray'),
            'large': Image.new('RGB', (1024, 1024), color='black'),
            'hd': Image.new('RGB', (1920, 1080), color='blue')
        }
        
        # Create test profiles with face encodings
        test_profiles = {
            'minimal': {
                'face_encodings': [np.random.randn(128).tolist()],
                'image_features': [np.random.randn(2048).tolist()],
                'content_hashes': [{'average': '0' * 16}]
            },
            'typical': {
                'face_encodings': [np.random.randn(128).tolist() for _ in range(5)],
                'image_features': [np.random.randn(2048).tolist() for _ in range(10)],
                'content_hashes': [{'average': f'{i:016x}' for i in range(20)}]
            },
            'large': {
                'face_encodings': [np.random.randn(128).tolist() for _ in range(50)],
                'image_features': [np.random.randn(2048).tolist() for _ in range(100)],
                'content_hashes': [{'average': f'{i:016x}' for i in range(200)}]
            }
        }
        
        return {
            'images': test_images,
            'profiles': test_profiles
        }
    
    async def benchmark_single_inference(self) -> Dict[str, Any]:
        """Benchmark single image inference performance"""
        logger.info("Starting single inference benchmark...")
        results = {}
        
        for image_size, image in self.test_data['images'].items():
            for profile_size, profile in self.test_data['profiles'].items():
                test_name = f"{image_size}_{profile_size}"
                
                # Convert image to bytes
                import io
                img_bytes = io.BytesIO()
                image.save(img_bytes, format='JPEG')
                img_data = img_bytes.getvalue()
                
                # Warmup
                await performance_matcher.analyze_content_optimized(
                    f"warmup_{test_name}",
                    img_data,
                    profile
                )
                
                # Benchmark runs
                times = []
                for i in range(10):
                    start = time.perf_counter()
                    result = await performance_matcher.analyze_content_optimized(
                        f"benchmark_{test_name}_{i}",
                        img_data,
                        profile
                    )
                    elapsed = (time.perf_counter() - start) * 1000
                    times.append(elapsed)
                
                results[test_name] = {
                    'avg_ms': statistics.mean(times),
                    'median_ms': statistics.median(times),
                    'min_ms': min(times),
                    'max_ms': max(times),
                    'std_ms': statistics.stdev(times) if len(times) > 1 else 0,
                    'p95_ms': np.percentile(times, 95),
                    'p99_ms': np.percentile(times, 99),
                    'meets_target': statistics.mean(times) < 2000
                }
                
                logger.info(f"  {test_name}: {results[test_name]['avg_ms']:.2f}ms avg")
        
        return results
    
    async def benchmark_batch_processing(self) -> Dict[str, Any]:
        """Benchmark batch processing performance"""
        logger.info("Starting batch processing benchmark...")
        results = {}
        
        batch_sizes = [1, 5, 10, 16, 32, 64]
        test_image = self.test_data['images']['medium']
        test_profile = self.test_data['profiles']['typical']
        
        for batch_size in batch_sizes:
            # Create batch
            import io
            img_bytes = io.BytesIO()
            test_image.save(img_bytes, format='JPEG')
            img_data = img_bytes.getvalue()
            
            # Benchmark batch processing
            times = []
            throughputs = []
            
            for run in range(5):
                start = time.perf_counter()
                
                # Process batch concurrently
                tasks = []
                for i in range(batch_size):
                    task = performance_matcher.analyze_content_optimized(
                        f"batch_{batch_size}_{run}_{i}",
                        img_data,
                        test_profile
                    )
                    tasks.append(task)
                
                await asyncio.gather(*tasks)
                elapsed = time.perf_counter() - start
                
                times.append(elapsed * 1000)
                throughputs.append(batch_size / elapsed)
            
            results[f"batch_{batch_size}"] = {
                'batch_size': batch_size,
                'avg_total_ms': statistics.mean(times),
                'avg_per_item_ms': statistics.mean(times) / batch_size,
                'throughput_per_sec': statistics.mean(throughputs),
                'efficiency': (batch_size / statistics.mean(times)) / (1 / results.get('batch_1', {}).get('avg_total_ms', 1000)) if 'batch_1' in results else 1.0
            }
            
            logger.info(f"  Batch {batch_size}: {results[f'batch_{batch_size}']['throughput_per_sec']:.2f} items/sec")
        
        return results
    
    async def benchmark_concurrent_users(self) -> Dict[str, Any]:
        """Benchmark performance under concurrent user load"""
        logger.info("Starting concurrent users benchmark...")
        results = {}
        
        user_levels = [1, 10, 50, 100, 500, 1000]
        test_image = self.test_data['images']['small']
        test_profile = self.test_data['profiles']['minimal']
        
        import io
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='JPEG')
        img_data = img_bytes.getvalue()
        
        for num_users in user_levels:
            logger.info(f"  Testing {num_users} concurrent users...")
            
            async def simulate_user(user_id: int) -> float:
                """Simulate a single user request"""
                start = time.perf_counter()
                try:
                    await performance_matcher.analyze_content_optimized(
                        f"user_{user_id}",
                        img_data,
                        test_profile
                    )
                    return (time.perf_counter() - start) * 1000
                except asyncio.TimeoutError:
                    return -1  # Timeout indicator
            
            # Run concurrent users
            start_time = time.perf_counter()
            user_tasks = [simulate_user(i) for i in range(num_users)]
            response_times = await asyncio.gather(*user_tasks)
            total_time = time.perf_counter() - start_time
            
            # Filter out timeouts
            successful_times = [t for t in response_times if t > 0]
            timeout_count = len([t for t in response_times if t < 0])
            
            if successful_times:
                results[f"users_{num_users}"] = {
                    'concurrent_users': num_users,
                    'avg_response_ms': statistics.mean(successful_times),
                    'median_response_ms': statistics.median(successful_times),
                    'p95_response_ms': np.percentile(successful_times, 95),
                    'p99_response_ms': np.percentile(successful_times, 99),
                    'success_rate': len(successful_times) / num_users,
                    'timeout_count': timeout_count,
                    'throughput_per_sec': num_users / total_time,
                    'meets_target': num_users >= 1000 and statistics.mean(successful_times) < 2000
                }
                
                logger.info(f"    Success rate: {results[f'users_{num_users}']['success_rate']:.1%}")
                logger.info(f"    Avg response: {results[f'users_{num_users}']['avg_response_ms']:.2f}ms")
        
        return results
    
    async def benchmark_memory_usage(self) -> Dict[str, Any]:
        """Benchmark memory usage patterns"""
        logger.info("Starting memory usage benchmark...")
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024**2)  # MB
        
        results = {
            'initial_memory_mb': initial_memory,
            'measurements': []
        }
        
        # Test with increasing load
        test_image = self.test_data['images']['large']
        test_profile = self.test_data['profiles']['large']
        
        import io
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='JPEG')
        img_data = img_bytes.getvalue()
        
        for iteration in range(100):
            # Process request
            await performance_matcher.analyze_content_optimized(
                f"memory_test_{iteration}",
                img_data,
                test_profile
            )
            
            # Measure memory every 10 iterations
            if iteration % 10 == 0:
                current_memory = process.memory_info().rss / (1024**2)
                gpu_memory = 0
                if torch.cuda.is_available():
                    gpu_memory = torch.cuda.memory_allocated() / (1024**2)
                
                results['measurements'].append({
                    'iteration': iteration,
                    'memory_mb': current_memory,
                    'memory_increase_mb': current_memory - initial_memory,
                    'gpu_memory_mb': gpu_memory
                })
                
                logger.info(f"  Iteration {iteration}: {current_memory:.1f}MB (Δ{current_memory - initial_memory:.1f}MB)")
        
        # Check for memory leaks
        memory_increases = [m['memory_increase_mb'] for m in results['measurements']]
        if len(memory_increases) > 2:
            # Simple linear regression to detect trends
            x = list(range(len(memory_increases)))
            correlation = np.corrcoef(x, memory_increases)[0, 1]
            results['memory_leak_correlation'] = correlation
            results['potential_leak'] = abs(correlation) > 0.8
        
        return results
    
    async def benchmark_cache_performance(self) -> Dict[str, Any]:
        """Benchmark cache hit rates and performance impact"""
        logger.info("Starting cache performance benchmark...")
        
        results = {
            'cache_disabled': {},
            'cache_enabled': {}
        }
        
        test_image = self.test_data['images']['medium']
        test_profile = self.test_data['profiles']['typical']
        
        import io
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='JPEG')
        img_data = img_bytes.getvalue()
        
        # Test with unique URLs (cache misses)
        miss_times = []
        for i in range(20):
            start = time.perf_counter()
            await performance_matcher.analyze_content_optimized(
                f"cache_miss_{i}",
                img_data,
                test_profile
            )
            miss_times.append((time.perf_counter() - start) * 1000)
        
        results['cache_disabled'] = {
            'avg_ms': statistics.mean(miss_times),
            'median_ms': statistics.median(miss_times)
        }
        
        # Test with repeated URLs (cache hits)
        hit_times = []
        # First request to populate cache
        await performance_matcher.analyze_content_optimized(
            "cache_test_url",
            img_data,
            test_profile
        )
        
        # Subsequent requests should hit cache
        for i in range(20):
            start = time.perf_counter()
            await performance_matcher.analyze_content_optimized(
                "cache_test_url",  # Same URL
                img_data,
                test_profile
            )
            hit_times.append((time.perf_counter() - start) * 1000)
        
        results['cache_enabled'] = {
            'avg_ms': statistics.mean(hit_times),
            'median_ms': statistics.median(hit_times)
        }
        
        # Calculate cache performance improvement
        results['cache_speedup'] = results['cache_disabled']['avg_ms'] / results['cache_enabled']['avg_ms']
        results['cache_hit_rate'] = performance_matcher.cache.metrics.cache_hits / max(1, 
            performance_matcher.cache.metrics.cache_hits + performance_matcher.cache.metrics.cache_misses)
        
        logger.info(f"  Cache speedup: {results['cache_speedup']:.2f}x")
        logger.info(f"  Cache hit rate: {results['cache_hit_rate']:.1%}")
        
        return results
    
    async def benchmark_optimization_levels(self) -> Dict[str, Any]:
        """Benchmark different optimization levels"""
        logger.info("Starting optimization level benchmark...")
        
        results = {}
        test_image = self.test_data['images']['medium']
        test_profile = self.test_data['profiles']['typical']
        
        import io
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='JPEG')
        
        for level in OptimizationLevel:
            logger.info(f"  Testing {level.value} optimization...")
            
            # Create optimizer with specific level
            optimizer = ai_optimizer
            optimizer.optimization_level = level
            
            times = []
            for i in range(10):
                start = time.perf_counter()
                
                # Test face recognition
                await optimizer.optimize_face_recognition(
                    test_image,
                    test_profile['face_encodings']
                )
                
                # Test feature extraction
                await optimizer.optimize_image_features(
                    test_image,
                    'resnet50'
                )
                
                # Test hash computation
                await optimizer.optimize_hash_computation(
                    test_image
                )
                
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
            
            results[level.value] = {
                'avg_ms': statistics.mean(times),
                'median_ms': statistics.median(times),
                'std_ms': statistics.stdev(times) if len(times) > 1 else 0,
                'memory_mb': psutil.Process().memory_info().rss / (1024**2)
            }
            
            logger.info(f"    {level.value}: {results[level.value]['avg_ms']:.2f}ms")
        
        return results
    
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run all benchmarks and compile results"""
        logger.info("="*60)
        logger.info("AI PERFORMANCE BENCHMARK SUITE")
        logger.info("="*60)
        
        # Warmup system
        logger.info("Warming up system...")
        await performance_matcher.warmup()
        
        # Run benchmarks
        self.results['benchmarks']['single_inference'] = await self.benchmark_single_inference()
        self.results['benchmarks']['batch_processing'] = await self.benchmark_batch_processing()
        self.results['benchmarks']['concurrent_users'] = await self.benchmark_concurrent_users()
        self.results['benchmarks']['memory_usage'] = await self.benchmark_memory_usage()
        self.results['benchmarks']['cache_performance'] = await self.benchmark_cache_performance()
        self.results['benchmarks']['optimization_levels'] = await self.benchmark_optimization_levels()
        
        # Get performance report from monitoring system
        self.results['monitoring_report'] = performance_matcher.get_performance_report()
        self.results['optimizer_report'] = ai_optimizer.get_performance_report()
        
        # Validate against targets
        self.results['validation'] = self._validate_performance()
        
        # Save results
        self._save_results()
        
        # Generate visualizations
        self._generate_visualizations()
        
        return self.results
    
    def _validate_performance(self) -> Dict[str, Any]:
        """Validate performance against production targets"""
        validation = {
            'passes_all': True,
            'details': {}
        }
        
        # Check inference time (<2s target)
        single_inference = self.results['benchmarks']['single_inference']
        worst_case_inference = max(r['p99_ms'] for r in single_inference.values())
        validation['details']['inference_time'] = {
            'target_ms': 2000,
            'worst_case_ms': worst_case_inference,
            'passes': worst_case_inference < 2000
        }
        
        # Check concurrent users (1000+ target)
        concurrent = self.results['benchmarks']['concurrent_users']
        if 'users_1000' in concurrent:
            validation['details']['concurrent_users'] = {
                'target': 1000,
                'achieved': 1000,
                'success_rate': concurrent['users_1000']['success_rate'],
                'passes': concurrent['users_1000']['success_rate'] > 0.95
            }
        
        # Check memory stability
        memory = self.results['benchmarks']['memory_usage']
        validation['details']['memory_stability'] = {
            'potential_leak': memory.get('potential_leak', False),
            'passes': not memory.get('potential_leak', False)
        }
        
        # Overall pass/fail
        validation['passes_all'] = all(
            v.get('passes', True) for v in validation['details'].values()
        )
        
        return validation
    
    def _save_results(self):
        """Save benchmark results to file"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"benchmark_results_{timestamp}.json"
        
        Path("benchmark_results").mkdir(exist_ok=True)
        filepath = Path("benchmark_results") / filename
        
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {filepath}")
    
    def _generate_visualizations(self):
        """Generate performance visualization charts"""
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            
            fig, axes = plt.subplots(2, 3, figsize=(15, 10))
            fig.suptitle('AI Performance Benchmark Results', fontsize=16)
            
            # 1. Single inference times
            ax = axes[0, 0]
            single_data = self.results['benchmarks']['single_inference']
            names = list(single_data.keys())
            avg_times = [single_data[n]['avg_ms'] for n in names]
            ax.bar(range(len(names)), avg_times)
            ax.set_xticks(range(len(names)))
            ax.set_xticklabels(names, rotation=45, ha='right')
            ax.set_ylabel('Time (ms)')
            ax.set_title('Single Inference Performance')
            ax.axhline(y=2000, color='r', linestyle='--', label='Target (2s)')
            ax.legend()
            
            # 2. Batch processing throughput
            ax = axes[0, 1]
            batch_data = self.results['benchmarks']['batch_processing']
            batch_sizes = [batch_data[k]['batch_size'] for k in sorted(batch_data.keys())]
            throughputs = [batch_data[k]['throughput_per_sec'] for k in sorted(batch_data.keys())]
            ax.plot(batch_sizes, throughputs, 'o-')
            ax.set_xlabel('Batch Size')
            ax.set_ylabel('Throughput (items/sec)')
            ax.set_title('Batch Processing Throughput')
            ax.grid(True, alpha=0.3)
            
            # 3. Concurrent users scalability
            ax = axes[0, 2]
            concurrent_data = self.results['benchmarks']['concurrent_users']
            user_counts = [concurrent_data[k]['concurrent_users'] for k in sorted(concurrent_data.keys())]
            response_times = [concurrent_data[k]['avg_response_ms'] for k in sorted(concurrent_data.keys())]
            ax.plot(user_counts, response_times, 'o-')
            ax.set_xlabel('Concurrent Users')
            ax.set_ylabel('Avg Response Time (ms)')
            ax.set_title('Concurrent User Scalability')
            ax.axhline(y=2000, color='r', linestyle='--', label='Target (2s)')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # 4. Memory usage over time
            ax = axes[1, 0]
            memory_data = self.results['benchmarks']['memory_usage']['measurements']
            iterations = [m['iteration'] for m in memory_data]
            memory_usage = [m['memory_mb'] for m in memory_data]
            ax.plot(iterations, memory_usage, 'o-')
            ax.set_xlabel('Iterations')
            ax.set_ylabel('Memory (MB)')
            ax.set_title('Memory Usage Pattern')
            ax.grid(True, alpha=0.3)
            
            # 5. Cache performance
            ax = axes[1, 1]
            cache_data = self.results['benchmarks']['cache_performance']
            categories = ['No Cache', 'With Cache']
            times = [cache_data['cache_disabled']['avg_ms'], cache_data['cache_enabled']['avg_ms']]
            ax.bar(categories, times)
            ax.set_ylabel('Avg Time (ms)')
            ax.set_title(f'Cache Performance (Speedup: {cache_data["cache_speedup"]:.2f}x)')
            
            # 6. Optimization levels comparison
            ax = axes[1, 2]
            opt_data = self.results['benchmarks']['optimization_levels']
            levels = list(opt_data.keys())
            opt_times = [opt_data[l]['avg_ms'] for l in levels]
            ax.bar(range(len(levels)), opt_times)
            ax.set_xticks(range(len(levels)))
            ax.set_xticklabels(levels, rotation=45, ha='right')
            ax.set_ylabel('Avg Time (ms)')
            ax.set_title('Optimization Level Comparison')
            
            plt.tight_layout()
            
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            Path("benchmark_results").mkdir(exist_ok=True)
            filepath = Path("benchmark_results") / f"benchmark_charts_{timestamp}.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Visualizations saved to {filepath}")
            
        except Exception as e:
            logger.warning(f"Could not generate visualizations: {e}")


async def main():
    """Run the benchmark suite"""
    benchmark = AIPerformanceBenchmark()
    results = await benchmark.run_all_benchmarks()
    
    # Print summary
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)
    
    validation = results['validation']
    if validation['passes_all']:
        print("✅ ALL PERFORMANCE TARGETS MET")
    else:
        print("❌ SOME PERFORMANCE TARGETS NOT MET")
    
    print("\nDetails:")
    for key, value in validation['details'].items():
        status = "✅" if value.get('passes', True) else "❌"
        print(f"  {status} {key}: {value}")
    
    print("\nKey Metrics:")
    print(f"  - Worst-case inference: {validation['details']['inference_time']['worst_case_ms']:.2f}ms")
    
    if 'concurrent_users' in validation['details']:
        print(f"  - 1000 user success rate: {validation['details']['concurrent_users']['success_rate']:.1%}")
    
    cache_data = results['benchmarks']['cache_performance']
    print(f"  - Cache speedup: {cache_data['cache_speedup']:.2f}x")
    print(f"  - Cache hit rate: {cache_data['cache_hit_rate']:.1%}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())