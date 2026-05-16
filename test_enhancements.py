#!/usr/bin/env python3
"""
Test script for the three new enhancement features.
Demonstrates movement detection, activity classification, and crowd density estimation.
"""

import numpy as np
from src.anomaly_detection.movement_detector import MovementDetector
from src.anomaly_detection.activity_classifier import ActivityClassifier
from src.anomaly_detection.crowd_estimator import CrowdDensityEstimator


def generate_synthetic_csi(activity_type: str, num_packets: int = 20) -> np.ndarray:
    """Generate synthetic CSI data for different activities."""
    
    if activity_type == "walking":
        # High energy, periodic signal (walking)
        t = np.linspace(0, 2*np.pi*3, num_packets)
        signal = 5 * np.sin(t) + 3 * np.sin(2*t) + np.random.randn(num_packets) * 0.5
    
    elif activity_type == "standing":
        # Medium energy, less regular
        t = np.linspace(0, 2*np.pi, num_packets)
        signal = 2 * np.sin(0.5*t) + np.random.randn(num_packets) * 1.5
    
    elif activity_type == "sitting":
        # Low energy, minimal movement
        signal = 0.5 * np.sin(0.2*np.linspace(0, 2*np.pi, num_packets)) + \
                 np.random.randn(num_packets) * 0.3
    
    elif activity_type == "empty":
        # Very low energy (noise only)
        signal = np.random.randn(num_packets) * 0.1
    
    else:
        signal = np.random.randn(num_packets)
    
    # Repeat to create 52 subcarriers
    csi = np.tile(signal.reshape(-1, 1), (1, 52))
    return csi


def test_movement_detector():
    """Test movement detection."""
    print("\n" + "="*70)
    print("TEST 1: MOVEMENT DETECTOR")
    print("="*70)
    
    detector = MovementDetector(buffer_size=20)
    
    activities = [
        ("empty", 5),
        ("sitting", 8),
        ("standing", 8),
        ("walking", 10),
    ]
    
    for activity, num_windows in activities:
        print(f"\n→ Simulating {activity.upper()} ({num_windows} windows)...")
        for i in range(num_windows):
            csi = generate_synthetic_csi(activity, num_packets=20)
            result = detector.add_window(csi)
            
            if i == num_windows - 1:  # Last window
                print(f"   {result['description']}")
                print(f"   Variance: {result['variance']:.4f}, Confidence: {result['confidence']:.1%}")
        
        detector.reset()


def test_activity_classifier():
    """Test activity classification."""
    print("\n" + "="*70)
    print("TEST 2: ACTIVITY CLASSIFIER")
    print("="*70)
    
    classifier = ActivityClassifier(window_size=20)
    
    activities = ["empty", "sitting", "standing", "walking"]
    
    for activity in activities:
        print(f"\n→ Classifying {activity.upper()}...")
        csi = generate_synthetic_csi(activity, num_packets=20)
        result = classifier.classify(csi)
        
        print(f"   {result['description']}")
        print(f"   Top 3: {sorted(result['scores'].items(), key=lambda x: x[1], reverse=True)[:3]}")
        print(f"   Confidence: {result['confidence']:.1%}")
        
        classifier.reset()


def test_crowd_estimator():
    """Test crowd density estimation."""
    print("\n" + "="*70)
    print("TEST 3: CROWD DENSITY ESTIMATOR")
    print("="*70)
    
    estimator = CrowdDensityEstimator(buffer_size=30)
    
    scenarios = [
        ("empty", 5),
        ("single_person", 8),
        ("multiple_people", 10),
    ]
    
    for scenario, num_windows in scenarios:
        print(f"\n→ Simulating {scenario.upper()} ({num_windows} windows)...")
        
        if scenario == "empty":
            base_activity = "empty"
        elif scenario == "single_person":
            base_activity = "standing"
        else:
            # Multiple people = mix of activities
            base_activity = "walking"
        
        for i in range(num_windows):
            csi = generate_synthetic_csi(base_activity, num_packets=20)
            
            # Add multi-person variation
            if scenario == "multiple_people":
                csi = csi + 0.5 * generate_synthetic_csi("sitting", num_packets=20)
            
            result = estimator.estimate(csi)
            
            if i == num_windows - 1:
                print(f"   {result['description']}")
                print(f"   Complexity: {result['complexity']:.2%}, "
                      f"Variance: {result['variance']:.2%}, "
                      f"Multimodality: {result['multimodality']:.2%}")
                print(f"   Confidence: {result['confidence']:.1%}")
        
        estimator.reset()


def test_combined():
    """Test all three working together."""
    print("\n" + "="*70)
    print("TEST 4: COMBINED ANALYSIS (Real Scenario)")
    print("="*70)
    
    movement = MovementDetector()
    activity = ActivityClassifier()
    crowd = CrowdDensityEstimator()
    
    print("\n→ Simulating a person walking in the room...")
    
    for i in range(15):
        csi = generate_synthetic_csi("walking", num_packets=20)
        
        m_result = movement.add_window(csi)
        a_result = activity.classify(csi)
        c_result = crowd.estimate(csi)
        
        if (i + 1) % 5 == 0:
            print(f"\n  Window {i+1}:")
            print(f"    Movement: {m_result['state']:8s} (conf: {m_result['confidence']:.1%})")
            print(f"    Activity: {a_result['activity']:10s} (conf: {a_result['confidence']:.1%})")
            print(f"    Occupancy: {c_result['count']:10s} (est: {c_result['estimated_people']} people)")


def main():
    print("\n" + "="*70)
    print("TESTING ENHANCED FEATURES")
    print("="*70)
    
    test_movement_detector()
    test_activity_classifier()
    test_crowd_estimator()
    test_combined()
    
    print("\n" + "="*70)
    print("ALL TESTS COMPLETED ✓")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
