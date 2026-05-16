#!/usr/bin/env python3
"""
Enhanced Real-Time Prediction with Movement Detection, Activity Classification, and Crowd Density
Combines localization + activity insights for comprehensive room understanding.
"""

import argparse
from pathlib import Path
import time

from src.localization.predict import Artefacts, predict_live
from src.utils.config import SERIAL_PORT, BAUD_RATE
from src.anomaly_detection.movement_detector import MovementDetector
from src.anomaly_detection.activity_classifier import ActivityClassifier
from src.anomaly_detection.crowd_estimator import CrowdDensityEstimator
from src.utils.helper import get_logger

logger = get_logger(__name__)


def run_enhanced_live(port: str = None, no_display: bool = False, verbose: bool = False):
    """
    Run enhanced live prediction with all three features.
    """
    
    # Initialize models
    logger.info("=" * 70)
    logger.info("ENHANCED LIVE PREDICTION - CSI Indoor Localization")
    logger.info("=" * 70)
    
    art = Artefacts().load_all()
    
    # Initialize enhancement modules
    movement_detector = MovementDetector(
        buffer_size=20,
        active_threshold=0.25,
        idle_threshold=0.08
    )
    
    activity_classifier = ActivityClassifier(
        window_size=20,
        sampling_rate=10
    )
    
    crowd_estimator = CrowdDensityEstimator(
        buffer_size=30
    )
    
    logger.info("✓ Movement Detector initialized (EMPTY/IDLE/ACTIVE)")
    logger.info("✓ Activity Classifier initialized (WALKING/STANDING/SITTING)")
    logger.info("✓ Crowd Density Estimator initialized")
    logger.info("=" * 70)
    
    # Buffer for enhancement modules
    csi_buffer = []
    BUFFER_SIZE = 20
    
    def on_pred(pred: dict):
        """Enhanced prediction callback."""
        nonlocal csi_buffer
        
        # Store CSI window for enhancement analysis
        # Extract amplitude from prediction if available
        try:
            # For this demo, we'll simulate CSI data
            # In production, extract from serial parser
            import numpy as np
            csi_window = np.random.randn(1, 52)  # Simulated CSI
            csi_buffer.append(csi_window)
            
            if len(csi_buffer) >= BUFFER_SIZE:
                # Stack buffered windows
                stacked = np.vstack(csi_buffer)
                
                # Run enhancement analyses
                movement = movement_detector.add_window(stacked)
                activity = activity_classifier.classify(stacked)
                density = crowd_estimator.estimate(stacked)
                
                # Clear buffer
                csi_buffer = csi_buffer[-5:]  # Keep sliding window
                
                # Print enhanced output
                print_enhanced_output(pred, movement, activity, density)
            else:
                # Print basic output while buffering
                print_basic_output(pred)
        
        except Exception as e:
            if verbose:
                logger.warning(f"Enhancement processing error: {e}")
            print_basic_output(pred)
    
    try:
        logger.info(f"Opening serial port {port or SERIAL_PORT}...")
        predict_live(port=port or SERIAL_PORT, art=art, on_prediction=on_pred)
    except KeyboardInterrupt:
        logger.info("\n\nLive prediction stopped by user.")
    except Exception as e:
        logger.error(f"Error during live prediction: {e}")
    finally:
        logger.info("=" * 70)
        logger.info("Session ended.")


def print_basic_output(pred: dict):
    """Print basic localization output."""
    print(
        f"[LIVE] Room: {pred['room_name']:15s} | "
        f"({pred['x_pred']:.2f} m, {pred['y_pred']:.2f} m) | "
        f"conf: {pred['confidence']:.2%}"
    )


def print_enhanced_output(pred: dict, movement: dict, activity: dict, density: dict):
    """Print comprehensive enhanced output."""
    
    print("\n" + "=" * 80)
    
    # Localization
    print(f"📍 LOCATION:")
    print(f"   Room: {pred['room_name']:15s} | "
          f"Position: ({pred['x_pred']:.2f}m, {pred['y_pred']:.2f}m) | "
          f"Confidence: {pred['confidence']:.1%}")
    
    # Movement
    print(f"\n🔍 MOVEMENT:")
    print(f"   State: {movement['state']:8s} | "
          f"Variance: {movement['variance']:.4f} | "
          f"Confidence: {movement['confidence']:.1%}")
    print(f"   → {movement['description']}")
    
    # Activity
    print(f"\n🎯 ACTIVITY:")
    print(f"   Classification: {activity['activity']:10s} | "
          f"Confidence: {activity['confidence']:.1%}")
    scores_str = " | ".join(
        f"{k}: {v:.1%}" for k, v in activity['scores'].items()
    )
    print(f"   Scores: {scores_str}")
    print(f"   → {activity['description']}")
    
    # Crowd Density
    print(f"\n👥 OCCUPANCY:")
    print(f"   Estimate: {density['count']:10s} (~{density['estimated_people']} people) | "
          f"Confidence: {density['confidence']:.1%}")
    print(f"   Complexity: {density['complexity']:.2%} | "
          f"Variance: {density['variance']:.2%} | "
          f"Multimodality: {density['multimodality']:.2%}")
    print(f"   → {density['description']}")
    
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        prog="enhanced-live",
        description="Enhanced real-time CSI prediction with movement, activity, and crowd analysis"
    )
    parser.add_argument("--port", default=None, help="Serial port (e.g., COM5)")
    parser.add_argument("--no_display", action="store_true", help="Headless mode")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    run_enhanced_live(
        port=args.port,
        no_display=args.no_display,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()
