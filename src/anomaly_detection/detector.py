# src/anomaly_detection/detector.py
"""
Unified anomaly detection interface.

Selects Z-score or Isolation Forest based on config.ANOMALY_STRATEGY,
exposes a single API:  fit → filter_anomalies → predict
"""

from __future__ import annotations

import numpy as np

from src.utils.config import ANOMALY_STRATEGY, ZSCORE_THRESHOLD, ISOLATION_CONTAMINATION
from src.utils.helper import get_logger
from src.anomaly_detection.zscore import ZScoreDetector
from src.anomaly_detection.isolation_forest import IFDetector

logger = get_logger(__name__)


class AnomalyDetector:
    """
    Facade that wraps ZScoreDetector or IFDetector.

    Parameters
    ----------
    strategy : "zscore" | "isolation_forest"
               Defaults to config.ANOMALY_STRATEGY.
    **kwargs : forwarded to the underlying detector constructor.
    """

    def __init__(self, strategy: str = None, **kwargs):
        self.strategy = (strategy or ANOMALY_STRATEGY).lower()
        self._detector = self._build(self.strategy, **kwargs)
        logger.info(f"AnomalyDetector using strategy: '{self.strategy}'")

    # ── Internal factory ──────────────────────────────────────────────────────
    @staticmethod
    def _build(strategy: str, **kwargs):
        if strategy == "zscore":
            return ZScoreDetector(
                threshold=kwargs.get("threshold", ZSCORE_THRESHOLD),
                strategy=kwargs.get("zscore_strategy", "any"),
            )
        elif strategy == "isolation_forest":
            return IFDetector(
                contamination=kwargs.get("contamination", ISOLATION_CONTAMINATION),
                n_estimators=kwargs.get("n_estimators", 100),
            )
        else:
            raise ValueError(
                f"Unknown anomaly strategy '{strategy}'. "
                "Choose 'zscore' or 'isolation_forest'."
            )

    # ── Public API ────────────────────────────────────────────────────────────
    def fit(self, X: np.ndarray) -> "AnomalyDetector":
        """Fit the detector on training feature matrix X."""
        self._detector.fit(X)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return boolean mask: True = anomaly."""
        return self._detector.predict(X)

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        """Return per-sample anomaly scores (higher = more anomalous)."""
        return self._detector.score_samples(X)

    def filter_anomalies(
        self, X: np.ndarray, *arrays: np.ndarray
    ) -> tuple[np.ndarray, ...]:
        """
        Remove detected anomalies from X and any aligned arrays.

        Example
        -------
        X_clean, y_label_clean, y_x_clean, y_y_clean = detector.filter_anomalies(
            X, y_label, y_x, y_y
        )
        """
        return self._detector.filter_anomalies(X, *arrays)

    # ── Convenience ───────────────────────────────────────────────────────────
    def anomaly_rate(self, X: np.ndarray) -> float:
        """Fraction of anomalous samples in X."""
        return float(self.predict(X).mean())

    def summary(self, X: np.ndarray) -> dict:
        """Return a summary dict for logging / reporting."""
        mask = self.predict(X)
        return {
            "strategy":      self.strategy,
            "total_samples": len(X),
            "n_anomalies":   int(mask.sum()),
            "anomaly_rate":  float(mask.mean()),
        }
