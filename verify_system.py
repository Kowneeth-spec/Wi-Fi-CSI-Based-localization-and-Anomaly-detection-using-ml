#!/usr/bin/env python3
"""
CSI Indoor Localization - Installation Verification Script

Checks that all dependencies are installed and system is ready.
"""

import sys
import importlib
from pathlib import Path

def check_python_version():
    """Verify Python 3.8+"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print(f"✓ Python {sys.version.split()[0]}")
    return True


def check_dependencies():
    """Verify all required packages are installed"""
    required = {
        'numpy': 'NumPy',
        'pandas': 'Pandas',
        'scipy': 'SciPy',
        'sklearn': 'Scikit-Learn',
        'xgboost': 'XGBoost',
        'matplotlib': 'Matplotlib',
        'serial': 'PySerial',
        'tqdm': 'tqdm',
    }
    
    missing = []
    
    for module, name in required.items():
        try:
            importlib.import_module(module)
            print(f"✓ {name}")
        except ImportError:
            print(f"❌ {name}")
            missing.append(module)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    return True


def check_directories():
    """Verify project structure"""
    dirs = [
        'data/raw',
        'data/processed',
        'data/test',
        'models',
        'results/graphs',
        'results/outputs',
        'src',
    ]
    
    missing = []
    for d in dirs:
        if not Path(d).exists():
            print(f"❌ Missing: {d}/")
            missing.append(d)
        else:
            print(f"✓ {d}/")
    
    if missing:
        print(f"\n⚠ Creating missing directories...")
        for d in missing:
            Path(d).mkdir(parents=True, exist_ok=True)
        return True
    
    return True


def check_config():
    """Check configuration files"""
    if Path('setup_config.json').exists():
        print("✓ setup_config.json (device configuration)")
        return True
    else:
        print("⚠ setup_config.json (not yet configured)")
        print("  Run: python quick_start.py setup")
        return False


def check_models():
    """Check if models are trained"""
    model_files = [
        'models/room_classifier.pkl',
        'models/coord_regressor_x.pkl',
        'models/coord_regressor_y.pkl',
    ]
    
    found = []
    for f in model_files:
        if Path(f).exists():
            print(f"✓ {f}")
            found.append(f)
        else:
            print(f"⚠ {f} (not yet trained)")
    
    if len(found) == len(model_files):
        return True
    else:
        print("\n  Models not found. Run:")
        print("    python quick_start.py collect --duration 120 --parse")
        print("    python quick_start.py train")
        return False


def main():
    """Run all checks"""
    print("\n" + "="*70)
    print(" CSI INDOOR LOCALIZATION - SYSTEM VERIFICATION")
    print("="*70 + "\n")
    
    print("[1/5] Python Version")
    py_ok = check_python_version()
    
    print("\n[2/5] Dependencies")
    deps_ok = check_dependencies()
    
    print("\n[3/5] Project Structure")
    dirs_ok = check_directories()
    
    print("\n[4/5] Configuration")
    config_ok = check_config()
    
    print("\n[5/5] Trained Models")
    models_ok = check_models()
    
    print("\n" + "="*70)
    
    if py_ok and deps_ok and dirs_ok:
        print("✓ SYSTEM READY FOR DEPLOYMENT")
        
        if not config_ok:
            print("\nNext: python quick_start.py setup")
        elif not models_ok:
            print("\nNext: python quick_start.py collect --duration 120 --parse")
            print("      python quick_start.py train")
        else:
            print("\n✓ All systems go!")
            print("Ready: python quick_start.py run")
        
        return 0
    else:
        print("❌ System not ready")
        return 1


if __name__ == "__main__":
    sys.exit(main())
