# src/feature_engineering/feature_extraction.py
"""
Extract handcrafted statistical and spectral features from CSI windows.

Input
-----
Each window is a 2-D array of shape (window_size, NUM_SUBCARRIERS) for
either amplitude or phase.  The extractor processes both and concatenates.

Features extracted (per subcarrier + global)
--------------------------------------------
Statistical  : mean, std, variance, min, max, range, skewness, kurtosis
Temporal     : mean absolute difference, root-mean-square
Spectral     : dominant frequency, spectral entropy (via FFT)
Cross-carrier: mean pairwise correlation, correlation matrix upper triangle

The final feature vector is 1-D and suitable for scikit-learn / XGBoost.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import kurtosis, skew

from src.utils.config import (
    FEATURE_STEP,
    FEATURE_WINDOW_SIZE,
    NUM_SUBCARRIERS,
)
from src.utils.helper import get_logger, sliding_windows

logger = get_logger(__name__)


# ── Per-window feature functions ──────────────────────────────────────────────
def _statistical_features(window: np.ndarray) -> np.ndarray:
    """
    Shape : (window_size, N_sub) → 1-D feature vector.

    Per-subcarrier: mean, std, var, min, max, range, skewness, kurtosis (8 × N)
    """
    mean_  = window.mean(axis=0)
    std_   = window.std(axis=0)
    var_   = window.var(axis=0)
    min_   = window.min(axis=0)
    max_   = window.max(axis=0)
    range_ = max_ - min_
    skew_  = skew(window, axis=0)
    kurt_  = kurtosis(window, axis=0)
    
    # Replace NaN/inf from numerical instability with safe values
    skew_  = np.nan_to_num(skew_, nan=0.0, posinf=0.0, neginf=0.0)
    kurt_  = np.nan_to_num(kurt_, nan=0.0, posinf=0.0, neginf=0.0)

    return np.concatenate([mean_, std_, var_, min_, max_, range_, skew_, kurt_])


def _temporal_features(window: np.ndarray) -> np.ndarray:
    """
    MAD  = mean(|x[t] - x[t-1]|)  per subcarrier  → N features
    RMS  = sqrt(mean(x²))          per subcarrier  → N features
    """
    diff = np.abs(np.diff(window, axis=0))
    mad  = diff.mean(axis=0)
    rms  = np.sqrt((window ** 2).mean(axis=0))
    return np.concatenate([mad, rms])


def _spectral_features(window: np.ndarray, n_dominant: int = 3) -> np.ndarray:
    """
    FFT-based features per subcarrier.

    dominant_freq_idx (n_dominant strongest bins)  → N × n_dominant
    spectral_entropy                               → N
    """
    fft_mag  = np.abs(np.fft.rfft(window, axis=0))   # (freq_bins, N_sub)
    fft_mag += 1e-9                                    # avoid log(0)

    # Dominant frequency bins (top-3)
    n_freqs  = fft_mag.shape[0]
    dom_freq = np.argsort(-fft_mag, axis=0)[:n_dominant, :].T.flatten().astype(float)

    # Spectral entropy per subcarrier
    p        = fft_mag / fft_mag.sum(axis=0, keepdims=True)
    sp_ent   = -np.sum(p * np.log2(p + 1e-9), axis=0) / np.log2(n_freqs)

    return np.concatenate([dom_freq, sp_ent])


def _correlation_features(window: np.ndarray, max_sub: int = 16) -> np.ndarray:
    """
    Upper-triangle of correlation matrix across first *max_sub* subcarriers.
    Using all 52 would produce 52*51/2 = 1326 features; truncate to keep size
    manageable.
    """
    sub = window[:, :max_sub]
    corr_mat = np.corrcoef(sub.T)                  # (max_sub, max_sub)
    idx  = np.triu_indices(max_sub, k=1)
    return corr_mat[idx]


# ── Single-window extractor ───────────────────────────────────────────────────
def extract_window_features(
    amp_window: np.ndarray,
    phase_window: np.ndarray,
) -> np.ndarray:
    """
    Compute the full feature vector for one (amplitude, phase) window pair.
    Uses enhanced features if available for better position accuracy.

    Parameters
    ----------
    amp_window   : ndarray, shape (W, N_sub)
    phase_window : ndarray, shape (W, N_sub)

    Returns
    -------
    1-D feature vector.
    """
    from src.utils.config import USE_ENHANCED_FEATURES
    
    if USE_ENHANCED_FEATURES:
        try:
            from src.feature_engineering.enhanced_extraction import extract_enhanced_features
            return extract_enhanced_features(amp_window, phase_window)
        except ImportError:
            logger.warning("Enhanced features unavailable, using standard extraction")
    
    # Fallback to standard features
    feats = []
    for sig in (amp_window, phase_window):
        feats.extend([
            _statistical_features(sig),
            _temporal_features(sig),
            _spectral_features(sig),
            _correlation_features(sig),
        ])
    return np.concatenate(feats)


# ── Full dataset feature extraction ──────────────────────────────────────────
def extract_features(
    amplitude: np.ndarray,
    phase: np.ndarray,
    labels: np.ndarray,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    window_size: int = None,
    step: int = None,
) -> dict:
    """
    Extract features for the entire dataset using a sliding window.

    Parameters
    ----------
    amplitude  : ndarray, shape (T, N_sub)
    phase      : ndarray, shape (T, N_sub)
    labels     : ndarray, shape (T,)  – room labels (int)
    x_coords   : ndarray, shape (T,)  – x in metres
    y_coords   : ndarray, shape (T,)  – y in metres
    window_size: int (defaults to config.FEATURE_WINDOW_SIZE)
    step       : int (defaults to config.FEATURE_STEP)

    Returns
    -------
    dict with keys:
        X       – ndarray (N_windows, n_features)
        y_label – ndarray (N_windows,)  – majority label per window
        y_x     – ndarray (N_windows,)  – mean x per window
        y_y     – ndarray (N_windows,)  – mean y per window
    """
    W = window_size or FEATURE_WINDOW_SIZE
    S = step        or FEATURE_STEP

    amp_windows   = sliding_windows(amplitude, W, S)   # (N, W, N_sub)
    phase_windows = sliding_windows(phase,     W, S)
    label_windows = sliding_windows(labels.reshape(-1, 1), W, S)[:, :, 0]
    x_windows     = sliding_windows(x_coords.reshape(-1, 1), W, S)[:, :, 0]
    y_windows     = sliding_windows(y_coords.reshape(-1, 1), W, S)[:, :, 0]

    N = amp_windows.shape[0]
    logger.info(f"Extracting features from {N} windows (W={W}, step={S})")

    feature_list = []
    for i in range(N):
        fv = extract_window_features(amp_windows[i], phase_windows[i])
        feature_list.append(fv)

    X = np.vstack(feature_list)

    # Majority label per window; mean (x, y)
    from scipy.stats import mode as _mode
    y_label = np.array([int(_mode(label_windows[i], keepdims=False).mode) for i in range(N)])
    y_x     = x_windows.mean(axis=1)
    y_y     = y_windows.mean(axis=1)

    logger.info(f"Feature matrix shape: {X.shape}")
    return dict(X=X, y_label=y_label, y_x=y_x, y_y=y_y)
