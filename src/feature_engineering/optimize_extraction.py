"""
Optimized feature extraction with parallel processing.

Provides both the original sequential extraction and a parallel variant
that uses joblib to speed up processing on multi-core systems.
"""

from __future__ import annotations

import numpy as np
from pathlib import Path
import joblib
from tqdm import tqdm

from src.utils.config import (
    FEATURE_STEP,
    FEATURE_WINDOW_SIZE,
    NUM_SUBCARRIERS,
)
from src.utils.helper import get_logger, sliding_windows
from src.feature_engineering.feature_extraction import (
    extract_window_features,
)

logger = get_logger(__name__)


def extract_features_parallel(
    amplitude: np.ndarray,
    phase: np.ndarray,
    labels: np.ndarray,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    window_size: int = None,
    step: int = None,
    n_jobs: int = -1,
    verbose: bool = True,
) -> dict:
    """
    Extract features with parallel window processing.
    
    This is a drop-in replacement for extract_features() with parallel
    processing support via joblib.
    
    Parameters
    ----------
    amplitude  : ndarray, shape (T, N_sub)
    phase      : ndarray, shape (T, N_sub)
    labels     : ndarray, shape (T,)
    x_coords   : ndarray, shape (T,)
    y_coords   : ndarray, shape (T,)
    window_size: int (default: config.FEATURE_WINDOW_SIZE)
    step       : int (default: config.FEATURE_STEP)
    n_jobs     : int, jobs for parallel processing (-1 = all CPUs)
    verbose    : bool, show progress
    
    Returns
    -------
    dict with keys: X, y_label, y_x, y_y
    """
    W = window_size or FEATURE_WINDOW_SIZE
    S = step or FEATURE_STEP
    
    # Create sliding windows
    amp_windows = sliding_windows(amplitude, W, S)  # (N, W, N_sub)
    phase_windows = sliding_windows(phase, W, S)
    label_windows = sliding_windows(labels.reshape(-1, 1), W, S)[:, :, 0]
    x_windows = sliding_windows(x_coords.reshape(-1, 1), W, S)[:, :, 0]
    y_windows = sliding_windows(y_coords.reshape(-1, 1), W, S)[:, :, 0]
    
    N = amp_windows.shape[0]
    logger.info(f"Extracting {N} features in parallel (W={W}, step={S}, n_jobs={n_jobs})")
    
    # Parallel feature extraction
    with joblib.Parallel(n_jobs=n_jobs, backend='loky') as parallel:
        feature_list = parallel(
            joblib.delayed(extract_window_features)(
                amp_windows[i], phase_windows[i]
            )
            for i in tqdm(
                range(N),
                desc="[PARALLEL] Extracting features",
                disable=not verbose
            )
        )
    
    X = np.vstack(feature_list)
    
    # Label aggregation (single-threaded for small overhead)
    from scipy.stats import mode as _mode
    y_label = np.array([int(_mode(label_windows[i], keepdims=False).mode) for i in range(N)])
    y_x = x_windows.mean(axis=1)
    y_y = y_windows.mean(axis=1)
    
    logger.info(f"Parallel feature extraction complete: {X.shape}")
    return dict(X=X, y_label=y_label, y_x=y_x, y_y=y_y)


# Speedup benchmark
def benchmark_parallel_extraction():
    """Compare sequential vs parallel feature extraction."""
    import time
    from src.feature_engineering.feature_extraction import extract_features
    
    # Create synthetic data
    T, N_sub = 1000, 52
    amplitude = np.random.randn(T, N_sub).astype(np.float32)
    phase = np.random.uniform(-np.pi, np.pi, (T, N_sub)).astype(np.float32)
    labels = np.random.randint(0, 5, T).astype(int)
    x_coords = np.random.uniform(0, 10, T).astype(np.float32)
    y_coords = np.random.uniform(0, 8, T).astype(np.float32)
    
    print("\n" + "="*60)
    print("BENCHMARK: Sequential vs Parallel Feature Extraction")
    print("="*60)
    print(f"Data shape: amplitude {amplitude.shape}, {len(labels)} labels")
    
    # Sequential
    print("\n[SEQ] Sequential extraction...")
    start = time.time()
    result_seq = extract_features(amplitude, phase, labels, x_coords, y_coords)
    seq_time = time.time() - start
    print(f"  Time: {seq_time:.3f}s")
    print(f"  Features: {result_seq['X'].shape}")
    
    # Parallel
    print("\n[PAR] Parallel extraction (n_jobs=-1)...")
    start = time.time()
    result_par = extract_features_parallel(
        amplitude, phase, labels, x_coords, y_coords,
        n_jobs=-1, verbose=False
    )
    par_time = time.time() - start
    print(f"  Time: {par_time:.3f}s")
    print(f"  Speedup: {seq_time/par_time:.1f}x")
    print(f"  Features: {result_par['X'].shape}")
    
    # Verify same output
    assert result_par['X'].shape == result_seq['X'].shape
    assert np.allclose(result_par['X'], result_seq['X'])
    print("\n  ✓ Output verified (identical)")
    print("="*60 + "\n")
