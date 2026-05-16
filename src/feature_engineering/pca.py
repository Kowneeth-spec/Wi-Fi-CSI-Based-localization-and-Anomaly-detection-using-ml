# src/feature_engineering/pca.py
"""
PCA-based dimensionality reduction for CSI feature vectors.

Wraps scikit-learn PCA with:
- automatic component selection by explained variance ratio
- fit / transform / fit_transform modes
- save/load of fitted PCA object to disk
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.decomposition import PCA

from src.utils.config import PCA_FILE, PCA_VARIANCE_RATIO
from src.utils.helper import get_logger

logger = get_logger(__name__)


def fit_pca(
    X: np.ndarray,
    variance_ratio: float = None,
    n_components: int = None,
    save_path: Path = None,
) -> tuple[np.ndarray, PCA]:
    """
    Fit PCA on training features and transform them.

    Parameters
    ----------
    X              : ndarray, shape (N, F) – already scaled
    variance_ratio : keep components explaining this fraction of variance
                     (ignored if n_components is set explicitly)
    n_components   : exact number of components (overrides variance_ratio)
    save_path      : where to persist the PCA object

    Returns
    -------
    (X_pca, fitted_pca)
    """
    save_path      = Path(save_path or PCA_FILE)
    variance_ratio = variance_ratio or PCA_VARIANCE_RATIO

    n_comp = n_components if n_components else variance_ratio
    pca    = PCA(n_components=n_comp, random_state=42)
    X_pca  = pca.fit_transform(X)

    explained = pca.explained_variance_ratio_.cumsum()[-1]
    logger.info(
        f"PCA: {X.shape[1]} → {X_pca.shape[1]} dims "
        f"({explained*100:.1f}% variance explained)"
    )

    save_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pca, save_path)
    logger.info(f"PCA saved → {save_path}")

    return X_pca, pca


def apply_pca(
    X: np.ndarray,
    pca: PCA = None,
    load_path: Path = None,
) -> np.ndarray:
    """
    Apply a fitted PCA transform to new data.

    Parameters
    ----------
    X         : ndarray, shape (N, F)
    pca       : fitted PCA object (takes priority)
    load_path : path to saved PCA if pca is None

    Returns
    -------
    ndarray, shape (N, n_components)
    """
    if pca is None:
        load_path = Path(load_path or PCA_FILE)
        if not load_path.exists():
            raise FileNotFoundError(f"PCA model not found at {load_path}")
        pca = joblib.load(load_path)
        logger.info(f"PCA loaded from {load_path}")

    return pca.transform(X)


def load_pca(path: Path = None) -> PCA:
    """Load and return a saved PCA object."""
    path = Path(path or PCA_FILE)
    if not path.exists():
        raise FileNotFoundError(f"PCA not found at {path}")
    return joblib.load(path)


def plot_variance_explained(pca: PCA, save_path: Path = None) -> None:
    """
    Quick diagnostic plot: cumulative explained variance vs. n_components.
    """
    import matplotlib.pyplot as plt
    from src.utils.config import GRAPH_DIR, PLOT_DPI

    cumvar = np.cumsum(pca.explained_variance_ratio_) * 100
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(range(1, len(cumvar) + 1), cumvar, marker="o", ms=3)
    ax.axhline(95, color="r", linestyle="--", label="95% threshold")
    ax.set_xlabel("Number of components")
    ax.set_ylabel("Cumulative explained variance (%)")
    ax.set_title("PCA – Explained Variance")
    ax.legend()
    plt.tight_layout()

    out = save_path or (GRAPH_DIR / "pca_variance.png")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=PLOT_DPI)
    plt.close(fig)
    logger.info(f"PCA variance plot saved → {out}")
