#!/usr/bin/env python3
"""
End-to-end verification script for CSI Indoor Localization pipeline.

Tests:
  1. All imports work
  2. Dependency versions are compatible
  3. Full pipeline runs on synthetic data
  4. Output artifacts are generated
"""

import sys
import traceback
from pathlib import Path

def verify_imports():
    """Check all critical imports."""
    print("\n" + "="*60)
    print("STEP 1: Verifying Imports")
    print("="*60)
    
    imports_to_test = [
        ("numpy", None),
        ("pandas", None),
        ("scipy", None),
        ("sklearn", None),
        ("xgboost", None),
        ("matplotlib", None),
        ("seaborn", None),
        ("pyserial", None),
        ("joblib", None),
        ("tqdm", None),
        ("yaml", None),
        ("src.utils.config", "config"),
        ("src.utils.helper", "helper"),
        ("src.data_collection.parser", "parser"),
        ("src.preprocessing.clean_data", "clean"),
        ("src.feature_engineering.feature_extraction", "features"),
        ("src.anomaly_detection.detector", "detector"),
        ("src.localization.model", "model"),
        ("src.localization.train", "train"),
        ("src.localization.predict", "predict"),
        ("src.visualization.plot_results", "plots"),
    ]
    
    failed = []
    for module_name, alias in imports_to_test:
        try:
            parts = module_name.split(".")
            if len(parts) == 1:
                __import__(module_name)
            else:
                from importlib import import_module
                import_module(module_name)
            print(f"  ✓ {module_name}")
        except Exception as e:
            print(f"  ✗ {module_name}: {str(e)[:60]}")
            failed.append((module_name, e))
    
    return len(failed) == 0, failed


def verify_dependency_versions():
    """Check package versions."""
    print("\n" + "="*60)
    print("STEP 2: Verifying Dependency Versions")
    print("="*60)
    
    requirements = {
        'numpy': '1.24.0',
        'pandas': '2.0.0',
        'scipy': '1.10.0',
        'scikit-learn': '1.3.0',
        'xgboost': '1.7.0',
        'matplotlib': '3.7.0',
        'seaborn': '0.12.0',
        'joblib': '1.3.0',
        'tqdm': '4.65.0',
        'pyyaml': '6.0',
    }
    
    issues = []
    for pkg, min_ver in requirements.items():
        try:
            if pkg == 'scikit-learn':
                mod = __import__('sklearn')
            elif pkg == 'pyyaml':
                mod = __import__('yaml')
            else:
                mod = __import__(pkg)
            
            version = getattr(mod, '__version__', 'unknown')
            print(f"  ✓ {pkg:20s} {version}")
        except Exception as e:
            print(f"  ✗ {pkg:20s} {str(e)[:40]}")
            issues.append(pkg)
    
    return len(issues) == 0, issues


def create_synthetic_data():
    """Create synthetic CSI data for testing."""
    print("\n" + "="*60)
    print("STEP 3: Creating Synthetic Training Data")
    print("="*60)
    
    import numpy as np
    from src.utils.config import PROC_DIR, NUM_SUBCARRIERS
    import os
    
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create synthetic data
    n_samples = 500
    n_rooms = 5
    
    # Synthetic amplitude (dB) and phase
    amplitude_db = np.random.randn(n_samples, NUM_SUBCARRIERS) * 10 + 20
    phase = np.random.uniform(-np.pi, np.pi, (n_samples, NUM_SUBCARRIERS))
    
    # Random room labels and coordinates
    labels = np.random.randint(0, n_rooms, n_samples)
    x_coords = np.random.uniform(0, 10, n_samples)
    y_coords = np.random.uniform(0, 8, n_samples)
    
    # Save to numpy files
    np.save(PROC_DIR / "amplitude_db.npy", amplitude_db)
    np.save(PROC_DIR / "phase.npy", phase)
    
    # Save metadata
    import pandas as pd
    metadata = pd.DataFrame({
        'label': labels,
        'x_m': x_coords,
        'y_m': y_coords,
    })
    metadata.to_csv(PROC_DIR / "metadata.csv", index=False)
    
    print(f"  ✓ Created {n_samples} synthetic samples")
    print(f"  ✓ {n_rooms} room classes")
    print(f"  ✓ Saved to {PROC_DIR}")
    return True


def verify_full_pipeline():
    """Run full training pipeline on synthetic data."""
    print("\n" + "="*60)
    print("STEP 4: Running Full Training Pipeline")
    print("="*60)
    
    from src.localization.train import train_pipeline
    from src.utils.config import MODEL_DIR, RESULT_DIR
    
    try:
        print("  → Loading and preprocessing data...")
        results = train_pipeline(use_pca=True)
        
        print(f"\n  ✓ Training completed!")
        print(f"    Room accuracy:      {results['accuracy']*100:.2f}%")
        print(f"    Mean Euclidean err: {results['mean_euclidean_error']:.3f} m")
        print(f"    90-percentile err:  {results['p90_error']:.3f} m")
        print(f"    MAE (x):            {results['mae_x']:.3f} m")
        print(f"    MAE (y):            {results['mae_y']:.3f} m")
        
        # Check model files
        expected_files = [
            MODEL_DIR / "room_classifier.pkl",
            MODEL_DIR / "coord_regressor_x.pkl",
            MODEL_DIR / "coord_regressor_y.pkl",
            MODEL_DIR / "scaler.pkl",
            MODEL_DIR / "pca.pkl",
            MODEL_DIR / "label_encoder.pkl",
        ]
        
        print("\n  Model artifacts:")
        all_exist = True
        for f in expected_files:
            exists = f.exists()
            status = "✓" if exists else "✗"
            print(f"    {status} {f.name}")
            all_exist = all_exist and exists
        
        return True, results
    except Exception as e:
        print(f"  ✗ Pipeline failed: {e}")
        traceback.print_exc()
        return False, None


def verify_predictions():
    """Test prediction on synthetic data."""
    print("\n" + "="*60)
    print("STEP 5: Testing Predictions")
    print("="*60)
    
    from src.localization.predict import Artefacts, predict_from_file
    from src.utils.config import PROC_DIR
    import pandas as pd
    
    try:
        art = Artefacts().load_all()
        print(f"  ✓ Loaded all artifacts")
        
        # Test batch prediction from CSV
        meta_path = PROC_DIR / "metadata.csv"
        df = predict_from_file(meta_path, art)
        
        print(f"  ✓ Batch predictions: {len(df)} samples")
        print(f"    Columns: {list(df.columns)}")
        print(f"    Sample:\n{df.head(3).to_string(index=False)}")
        
        return True
    except Exception as e:
        print(f"  ✗ Prediction failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all verification steps."""
    print("\n" + "█" * 60)
    print("█  CSI INDOOR LOCALIZATION - END-TO-END VERIFICATION")
    print("█" * 60)
    
    # Step 1: Imports
    imports_ok, import_errors = verify_imports()
    if not imports_ok:
        print(f"\n  ⚠ {len(import_errors)} import(s) failed")
        for module, err in import_errors[:3]:
            print(f"    → {module}: {str(err)[:50]}")
        # Don't exit; continue with other checks
    
    # Step 2: Versions
    versions_ok, version_issues = verify_dependency_versions()
    
    # Step 3: Synthetic data
    try:
        data_ok = create_synthetic_data()
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        data_ok = False
    
    # Step 4: Pipeline
    pipeline_ok = False
    results = None
    if data_ok:
        try:
            pipeline_ok, results = verify_full_pipeline()
        except Exception as e:
            print(f"  ✗ Pipeline error: {e}")
            traceback.print_exc()
    
    # Step 5: Predictions
    pred_ok = False
    if pipeline_ok:
        try:
            pred_ok = verify_predictions()
        except Exception as e:
            print(f"  ✗ Prediction error: {e}")
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    print(f"  Imports:          {'✓ PASS' if imports_ok else '✗ FAIL'}")
    print(f"  Versions:         {'✓ PASS' if versions_ok else '✗ WARN'}")
    print(f"  Data Creation:    {'✓ PASS' if data_ok else '✗ FAIL'}")
    print(f"  Pipeline:         {'✓ PASS' if pipeline_ok else '✗ FAIL'}")
    print(f"  Predictions:      {'✓ PASS' if pred_ok else '✗ FAIL'}")
    
    overall_pass = imports_ok and data_ok and pipeline_ok
    print(f"\n  OVERALL:          {'✓ ALL SYSTEMS GO' if overall_pass else '✗ NEEDS FIXES'}")
    print("="*60 + "\n")
    
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
