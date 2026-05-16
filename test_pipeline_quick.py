#!/usr/bin/env python3
from src.localization.train import train_pipeline
r = train_pipeline(use_pca=True)
print(f"✓ Pipeline Success!")
print(f"  Accuracy: {r['accuracy']*100:.1f}%")
print(f"  MAE (x,y): {r['mae_x']:.3f}, {r['mae_y']:.3f} m")
print(f"  Mean Euclidean error: {r['mean_euclidean_error']:.3f} m")
