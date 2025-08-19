#!/usr/bin/env python3
"""
Load Testing Script
Quick way to run load tests using Locust
"""
import subprocess
import sys
import os
import time

def run_load_test(users=100, spawn_rate=5, run_time="5m", host="http://localhost:8000"):
    """Run load test with specified parameters"""
    
    print(f"🎯 Starting Load Test")
    print(f"   Users: {users}")
    print(f"   Spawn Rate: {spawn_rate} users/sec")
    print(f"   Duration: {run_time}")
    print(f"   Host: {host}")
    print()
    
    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    
    # Build locust command
    cmd = [
        'locust',
        '-f', 'app/benchmarks/locustfile.py',
        '--host', host,
        '--users', str(users),
        '--spawn-rate', str(spawn_rate),
        '--run-time', run_time,
        '--headless',
        '--html', 'locust_report.html'
    ]
    
    try:
        # Run locust
        result = subprocess.run(cmd, cwd=backend_dir, capture_output=False)
        
        if result.returncode == 0:
            print("\n✅ Load test completed successfully!")
            print(f"Report saved to: {os.path.join(backend_dir, 'locust_report.html')}")
            print(f"SLA compliance report: {os.path.join(backend_dir, 'locust_sla_report.json')}")
        else:
            print(f"\n❌ Load test failed with return code: {result.returncode}")
            return False
            
    except FileNotFoundError:
        print("❌ Locust not found. Install it with: pip install locust")
        return False
    except KeyboardInterrupt:
        print("\n⚠️ Load test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Load test failed: {e}")
        return False
    
    return True

def main():
    """Main function with different test scenarios"""
    print("🏋️ Load Testing Suite for Content Protection Platform")
    print("=" * 60)
    
    scenarios = [
        {
            "name": "Quick Test (Low Load)",
            "users": 10,
            "spawn_rate": 2,
            "run_time": "2m",
            "description": "Basic functionality test with low load"
        },
        {
            "name": "Standard Test (Medium Load)",
            "users": 100,
            "spawn_rate": 5,
            "run_time": "5m",
            "description": "Standard load test simulating normal usage"
        },
        {
            "name": "Stress Test (High Load)",
            "users": 500,
            "spawn_rate": 10,
            "run_time": "10m",
            "description": "High load test to find limits"
        },
        {
            "name": "Production Test (Target Load)",
            "users": 1000,
            "spawn_rate": 20,
            "run_time": "15m",
            "description": "Production target test with 1000 users"
        }
    ]
    
    print("\nAvailable test scenarios:")
    for i, scenario in enumerate(scenarios, 1):
        print(f"  {i}. {scenario['name']}")
        print(f"     {scenario['description']}")
        print(f"     Users: {scenario['users']}, Duration: {scenario['run_time']}")
        print()
    
    try:
        choice = input("Select scenario (1-4) or press Enter for Standard Test: ").strip()
        
        if not choice:
            choice = "2"  # Default to standard test
        
        scenario_idx = int(choice) - 1
        if scenario_idx < 0 or scenario_idx >= len(scenarios):
            print("Invalid choice, using Standard Test")
            scenario_idx = 1
        
        scenario = scenarios[scenario_idx]
        print(f"\n🚀 Running: {scenario['name']}")
        
        # Ask for host
        host = input(f"Enter host URL (default: http://localhost:8000): ").strip()
        if not host:
            host = "http://localhost:8000"
        
        # Run the test
        success = run_load_test(
            users=scenario['users'],
            spawn_rate=scenario['spawn_rate'],
            run_time=scenario['run_time'],
            host=host
        )
        
        if success:
            print("\n📊 Load test completed! Check the following files:")
            print("   - locust_report.html: Detailed HTML report")
            print("   - locust_sla_report.json: SLA compliance report")
            print("\n💡 Tips for analyzing results:")
            print("   - Response times should be <2000ms for 95th percentile")
            print("   - Error rate should be <1%")
            print("   - RPS should scale linearly with users (up to limits)")
        
    except ValueError:
        print("Invalid input. Please enter a number 1-4.")
    except KeyboardInterrupt:
        print("\n⚠️ Test selection interrupted by user")

if __name__ == "__main__":
    main()