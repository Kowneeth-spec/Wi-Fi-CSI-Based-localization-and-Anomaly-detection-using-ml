# src/anomaly_detection/zscore.py
"""
Z-score based anomaly detection for CSI feature vectors.

A sample is flagged as anomalous if ANY of its features exceeds
*threshold* standard deviations from the training mean.

Fit on training data, then apply to train/test/live streams.
"""

from __future__ import annotations

import numpy as np

from src.utils.helper import get_logger

logger = get_logger(__name__)


class ZScoreDetector:
    """
    Univariate Z-score anomaly detector applied feature-wise.

    Parameters
    ----------
    threshold : float
        Number of standard deviations beyond which a sample is anomalous.
    strategy  : "any" | "mean"
        "any"  – flag if ANY feature exceeds threshold  (strict)
        "mean" – flag if MEAN z-score exceeds threshold (lenient)
    """

    def __init__(self, threshold: float = 3.0, strategy: str = "any"):
        self.threshold = threshold
        self.strategy  = strategy
        self.mean_: np.ndarray | None = None
        self.std_:  np.ndarray | None = None

    # ── Fit ───────────────────────────────────────────────────────────────────
    def fit(self, X: np.ndarray) -> "ZScoreDetector":
        """Compute per-feature mean and std from training data."""
        self.mean_ = X.mean(axis=0)
        self.std_  = X.std(axis=0)
        self.std_  = np.where(self.std_ == 0, 1e-9, self.std_)   # avoid /0
        logger.info(f"ZScoreDetector fitted on {X.shape[0]} samples.")
        return self

    # ── Score ─────────────────────────────────────────────────────────────────
    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """
        Return per-sample anomaly score (max absolute z-score across features).

        Higher score → more anomalous.
        """
        self._check_fitted()
        z = np.abs((X - self.mean_) / self.std_)   # (N, F)
        if self.strategy == "any":
            return z.max(axis=1)
        return z.mean(axis=1)

    # ── Predict ───────────────────────────────────────────────────────────────
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Return boolean mask: True = anomaly.
        """
        scores = self.score_samples(X)
        return scores > self.threshold

    def filter_anomalies(
        self, X: np.ndarray, *arrays: np.ndarray
    ) -> tuple[np.ndarray, ...]:
        """
        Remove anomalous rows from X and any aligned label arrays.

        Returns
        -------
        Tuple of cleaned arrays (X_clean, *arrays_clean).
        """
        mask = ~self.predict(X)
        n_removed = (~mask).sum()
        logger.info(
            f"Z-score anomaly filter: removed {n_removed}/{len(X)} samples "
            f"({n_removed/len(X)*100:.1f}%)"
        )
        return (X[mask],) + tuple(a[mask] for a in arrays)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _check_fitted(self):
        if self.mean_ is None:
            raise RuntimeError("ZScoreDetector not fitted. Call fit() first.")

    def get_params(self) -> dict:
        return {"threshold": self.threshold, "strategy": self.strategy}
