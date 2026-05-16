# src/anomaly_detection/isolation_forest.py
"""
Isolation Forest anomaly detection for CSI feature vectors.

Better than Z-score for high-dimensional, non-Gaussian data.
Uses scikit-learn's IsolationForest internally.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from src.utils.config import ISOLATION_CONTAMINATION, MODEL_DIR
from src.utils.helper import get_logger

logger = get_logger(__name__)

_IF_SAVE_PATH = MODEL_DIR / "isolation_forest.pkl"


class IFDetector:
    """
    Thin wrapper around sklearn IsolationForest with save/load support.

    Parameters
    ----------
    contamination : float
        Expected proportion of anomalies in training set (0 < c < 0.5).
    n_estimators  : int
        Number of isolation trees.
    random_state  : int
    """

    def __init__(
        self,
        contamination: float = None,
        n_estimators: int = 100,
        random_state: int = 42,
    ):
        self.contamination = contamination or ISOLATION_CONTAMINATION
        self.n_estimators  = n_estimators
        self.random_state  = random_state
        self._model: IsolationForest | None = None

    # ── Fit ───────────────────────────────────────────────────────────────────
    def fit(self, X: np.ndarray, save_path: Path = None) -> "IFDetector":
        """
        Fit the Isolation Forest on training features.

        Parameters
        ----------
        X         : ndarray, shape (N, F) – scaled feature matrix
        save_path : where to save the fitted model
        """
        self._model = IsolationForest(
            n_estimators  = self.n_estimators,
            contamination = self.contamination,
            random_state  = self.random_state,
            n_jobs        = -1,
        )
        self._model.fit(X)

        n_anomaly = (self._model.predict(X) == -1).sum()
        logger.info(
            f"IsolationForest fitted on {X.shape[0]} samples. "
            f"Training anomalies detected: {n_anomaly} ({n_anomaly/len(X)*100:.1f}%)"
        )

        path = Path(save_path or _IF_SAVE_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._model, path)
        logger.info(f"IsolationForest saved → {path}")
        return self

    # ── Score ─────────────────────────────────────────────────────────────────
    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """
        Return anomaly scores: lower (more negative) → more anomalous.
        Negated so higher = more anomalous (consistent with ZScoreDetector).
        """
        self._check_fitted()
        return -self._model.score_samples(X)

    # ── Predict ───────────────────────────────────────────────────────────────
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Return boolean mask: True = anomaly.
        sklearn uses -1 for anomaly, 1 for inlier.
        """
        self._check_fitted()
        return self._model.predict(X) == -1

    def filter_anomalies(
        self, X: np.ndarray, *arrays: np.ndarray
    ) -> tuple[np.ndarray, ...]:
        """Remove anomalous rows from X and any aligned arrays."""
        mask      = ~self.predict(X)
        n_removed = (~mask).sum()
        logger.info(
            f"IsolationForest filter: removed {n_removed}/{len(X)} anomalies "
            f"({n_removed/len(X)*100:.1f}%)"
        )
        return (X[mask],) + tuple(a[mask] for a in arrays)

    # ── Load ──────────────────────────────────────────────────────────────────
    @classmethod
    def load(cls, path: Path = None) -> "IFDetector":
        path = Path(path or _IF_SAVE_PATH)
        if not path.exists():
            raise FileNotFoundError(f"IsolationForest model not found at {path}")
        obj = cls.__new__(cls)
        obj._model = joblib.load(path)
        logger.info(f"IsolationForest loaded from {path}")
        return obj

    def _check_fitted(self):
        if self._model is None:
            raise RuntimeError("IFDetector not fitted. Call fit() first.")
