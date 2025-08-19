#!/usr/bin/env python3
"""
Quick Performance Benchmark Runner
Run this to validate the AI inference performance optimization is working
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.benchmarks.ai_performance_benchmark import main

if __name__ == "__main__":
    print("🚀 Starting AI Performance Benchmark Suite")
    print("This will validate that the optimizations achieve production targets:")
    print("  - <2s AI inference time")
    print("  - <500ms API response time") 
    print("  - 1000+ concurrent user support")
    print("  - 99.9% uptime SLA")
    print()
    
    try:
        asyncio.run(main())
        print("\n✅ Benchmark completed successfully!")
        print("Check the benchmark_results/ directory for detailed reports and visualizations.")
    except KeyboardInterrupt:
        print("\n⚠️ Benchmark interrupted by user")
    except Exception as e:
        print(f"\n❌ Benchmark failed with error: {e}")
        sys.exit(1)