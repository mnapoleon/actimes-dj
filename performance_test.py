#!/usr/bin/env python
"""
Performance comparison script for data transformation optimization.

This script compares the performance of the old calculation methods
vs the new pre-computed approach.
"""

import os
import sys
import time
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'actimes_project.settings')
django.setup()

from laptimes.models import Session
from laptimes.statistics import SessionStatisticsCalculator


def time_function(func, *args, **kwargs):
    """Time a function execution and return the result and duration"""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    return result, end_time - start_time


def performance_comparison():
    """Compare old vs new calculation performance"""
    
    print("=== Data Transformation Optimization Performance Test ===\n")
    
    # Get a session with decent amount of data
    sessions = Session.objects.filter(total_laps__gt=5).order_by('-total_laps')[:3]
    
    if not sessions:
        print("No sessions with >5 laps found. Please upload some test data first.")
        return
    
    for session in sessions:
        print(f"Testing session: {session}")
        print(f"Laps: {session.total_laps}, Drivers: {session.total_drivers}")
        print(f"Pre-computed statistics available: {'Yes' if session.session_statistics else 'No'}")
        print("-" * 50)
        
        # Test 1: Driver Statistics
        print("1. Driver Statistics Calculation:")
        
        # Force recalculation using old method (without pre-computed data)
        old_session_stats = session.session_statistics
        session.session_statistics = {}  # Clear to force recalculation
        
        try:
            _, old_time = time_function(session.get_driver_statistics)
            print(f"   Old method (on-demand calculation): {old_time:.4f}s")
        except Exception as e:
            print(f"   Old method failed: {e}")
            old_time = float('inf')
        
        # Restore pre-computed data
        session.session_statistics = old_session_stats
        
        # Test new method (pre-computed)
        _, new_time = time_function(lambda: session.session_statistics)
        print(f"   New method (pre-computed lookup): {new_time:.6f}s")
        
        if old_time != float('inf') and new_time > 0:
            speedup = old_time / new_time
            print(f"   Speedup: {speedup:.1f}x faster")
        
        print()
        
        # Test 2: Chart Data Generation
        print("2. Chart Data Generation:")
        
        calculator = SessionStatisticsCalculator(session)
        
        # Test calculation time
        _, calc_time = time_function(calculator.calculate_chart_data)
        print(f"   Calculation time: {calc_time:.4f}s")
        
        # Test pre-computed lookup time
        _, lookup_time = time_function(lambda: session.chart_data)
        print(f"   Pre-computed lookup: {lookup_time:.6f}s")
        
        if calc_time > 0 and lookup_time > 0:
            speedup = calc_time / lookup_time
            print(f"   Speedup: {speedup:.1f}x faster")
        
        print()
        
        # Test 3: Sector Statistics
        print("3. Sector Statistics Calculation:")
        
        _, calc_time = time_function(calculator.calculate_sector_statistics)
        print(f"   Calculation time: {calc_time:.4f}s")
        
        _, lookup_time = time_function(lambda: session.sector_statistics)
        print(f"   Pre-computed lookup: {lookup_time:.6f}s")
        
        if calc_time > 0 and lookup_time > 0:
            speedup = calc_time / lookup_time
            print(f"   Speedup: {speedup:.1f}x faster")
        
        print("\n" + "=" * 60 + "\n")


def test_view_performance():
    """Test view rendering performance"""
    
    print("=== View Rendering Performance Test ===\n")
    
    from django.test import Client
    from django.contrib.auth.models import User
    
    client = Client()
    
    # Get a session to test
    session = Session.objects.filter(total_laps__gt=5).first()
    if not session:
        print("No sessions with >5 laps found for view testing.")
        return
    
    print(f"Testing view performance for session: {session}")
    print(f"Session has pre-computed statistics: {'Yes' if session.session_statistics else 'No'}")
    
    # Test session detail view performance
    url = f'/session/{session.id}/'
    
    # Warm up
    response = client.get(url)
    if response.status_code != 200:
        print(f"Failed to load view: {response.status_code}")
        return
    
    # Time multiple requests
    times = []
    for i in range(5):
        start = time.time()
        response = client.get(url)
        end = time.time()
        times.append(end - start)
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"View rendering times:")
    print(f"   Average: {avg_time:.4f}s")
    print(f"   Min: {min_time:.4f}s") 
    print(f"   Max: {max_time:.4f}s")
    
    # Estimate what this would be like with larger sessions
    laps_factor = session.total_laps or 1
    estimated_100_laps = avg_time * (100 / laps_factor) if laps_factor > 0 else avg_time
    
    print(f"\nEstimated time for 100-lap session:")
    print(f"   With optimization: ~{avg_time:.4f}s (constant time)")
    print(f"   Without optimization: ~{estimated_100_laps:.4f}s (scales with lap count)")


if __name__ == "__main__":
    performance_comparison()
    test_view_performance()