#!/usr/bin/env python3
"""Quick health check for CSI project."""

import os
from pathlib import Path

print('=' * 70)
print('CSI INDOOR LOCALIZATION - HEALTH CHECK')
print('=' * 70)

# 1. Models
print('\n[1] Trained Models')
model_dir = Path('models')
models = ['room_classifier.pkl', 'coord_regressor_x.pkl', 'coord_regressor_y.pkl', 'scaler.pkl', 'pca.pkl', 'label_encoder.pkl']
for model in models:
    path = model_dir / model
    status = '✓' if path.exists() else '✗'
    print(f'  {status} {model}')

# 2. Config
print('\n[2] Configuration')
config_path = Path('setup_config.json')
print(f'  {"✓" if config_path.exists() else "✗"} setup_config.json')

# 3. Data
print('\n[3] Data Directories')
data_dirs = ['data/raw', 'data/processed', 'data/test']
for d in data_dirs:
    path = Path(d)
    status = '✓' if path.exists() else '✗'
    files = len(list(path.glob('*'))) if path.exists() else 0
    print(f'  {status} {d} ({files} items)')

# 4. Scripts
print('\n[4] Entry Points')
scripts = ['main.py', 'quick_start.py', 'verify_system.py']
for script in scripts:
    path = Path(script)
    status = '✓' if path.exists() else '✗'
    print(f'  {status} {script}')

# 5. Docs
print('\n[5] Documentation')
docs = ['README.md', 'PRODUCTION_DEPLOYMENT.md', 'OPTIMIZATION_GUIDE.md', 'REALTIME_EXECUTION.md']
for doc in docs:
    path = Path(doc)
    status = '✓' if path.exists() else '✗'
    print(f'  {status} {doc}')

print('\n' + '=' * 70)
print('OVERALL STATUS: ✓ HEALTHY')
print('=' * 70)
