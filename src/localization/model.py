# src/localization/model.py
"""
ML model factory for dual-task localization:

  Task A – Room-level classification  (Random Forest | XGBoost)
  Task B – (x, y) coordinate regression (Random Forest | XGBoost)

Each task uses a separate model object; x and y coordinates are
regressed independently for simplicity and are combined at prediction time.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

from src.utils.config import (
    CLASSIFIER,
    REGRESSOR,
    RF_CLASSIFIER_PARAMS,
    RF_REGRESSOR_PARAMS,
    XGB_CLASSIFIER_PARAMS,
    XGB_REGRESSOR_PARAMS,
    XGB_REGRESSOR_X_PARAMS,
    XGB_REGRESSOR_Y_PARAMS,
)
from src.utils.helper import get_logger

logger = get_logger(__name__)


# ── Factory functions ─────────────────────────────────────────────────────────
def build_classifier(model_type: str = None):
    """
    Build the room-level classifier.

    Parameters
    ----------
    model_type : "random_forest" | "xgboost" (default: config.CLASSIFIER)

    Returns
    -------
    Unfitted sklearn-compatible classifier.
    """
    mt = (model_type or CLASSIFIER).lower()
    logger.info(f"Building classifier: {mt}")

    if mt == "random_forest":
        return RandomForestClassifier(**RF_CLASSIFIER_PARAMS)

    elif mt == "xgboost":
        try:
            from xgboost import XGBClassifier
        except ImportError:
            raise ImportError("xgboost not installed. Run: pip install xgboost")
        return XGBClassifier(**XGB_CLASSIFIER_PARAMS)

    else:
        raise ValueError(f"Unknown classifier type '{mt}'. Use 'random_forest' or 'xgboost'.")


def build_regressor(model_type: str = None, coordinate: str = None):
    """
    Build a coordinate regressor (used separately for x and y).

    Parameters
    ----------
    model_type : "random_forest" | "xgboost" (default: config.REGRESSOR)
    coordinate : "x" | "y" (for optimized XGBoost params; default: None)

    Returns
    -------
    Unfitted sklearn-compatible regressor.
    """
    mt = (model_type or REGRESSOR).lower()
    logger.info(f"Building regressor: {mt}")

    if mt == "random_forest":
        return RandomForestRegressor(**RF_REGRESSOR_PARAMS)

    elif mt == "xgboost":
        try:
            from xgboost import XGBRegressor
        except ImportError:
            raise ImportError("xgboost not installed. Run: pip install xgboost")
        
        # Use coordinate-specific parameters if available
        if coordinate and coordinate.lower() == "x":
            params = XGB_REGRESSOR_X_PARAMS.copy()
        elif coordinate and coordinate.lower() == "y":
            params = XGB_REGRESSOR_Y_PARAMS.copy()
        else:
            params = XGB_REGRESSOR_PARAMS.copy()
        
        return XGBRegressor(**params)

    else:
        raise ValueError(f"Unknown regressor type '{mt}'. Use 'random_forest' or 'xgboost'.")


# ── Unified localization model container ──────────────────────────────────────
class LocalizationModel:
    """
    Container holding all three models needed for dual-task localization:

        classifier  – predicts room label
        regressor_x – predicts x coordinate (metres)
        regressor_y – predicts y coordinate (metres)

    Parameters
    ----------
    clf_type : "random_forest" | "xgboost"
    reg_type : "random_forest" | "xgboost"
    """

    def __init__(self, clf_type: str = None, reg_type: str = None):
        self.classifier  = build_classifier(clf_type)
        self.regressor_x = build_regressor(reg_type, coordinate="x")
        self.regressor_y = build_regressor(reg_type, coordinate="y")
        self._fitted = False

    def fit(
        self,
        X: np.ndarray,
        y_label: np.ndarray,
        y_x: np.ndarray,
        y_y: np.ndarray,
    ) -> "LocalizationModel":
        """
        Fit classifier and both regressors.

        Parameters
        ----------
        X       : feature matrix, shape (N, F)
        y_label : room labels, shape (N,)
        y_x     : x coordinates, shape (N,)
        y_y     : y coordinates, shape (N,)
        """
        logger.info("Fitting classifier …")
        self.classifier.fit(X, y_label)

        logger.info("Fitting x-regressor …")
        self.regressor_x.fit(X, y_x)

        logger.info("Fitting y-regressor …")
        self.regressor_y.fit(X, y_y)

        self._fitted = True
        logger.info("LocalizationModel fully fitted.")
        return self

    def predict(self, X: np.ndarray) -> dict:
        """
        Predict room labels and (x, y) coordinates.

        Returns
        -------
        dict with keys:
            room_label  – ndarray int, shape (N,)
            x_pred      – ndarray float, shape (N,)
            y_pred      – ndarray float, shape (N,)
            xy_pred     – ndarray float, shape (N, 2)
        """
        self._check_fitted()
        room_label = self.classifier.predict(X)
        x_pred     = self.regressor_x.predict(X)
        y_pred     = self.regressor_y.predict(X)
        return dict(
            room_label = room_label,
            x_pred     = x_pred,
            y_pred     = y_pred,
            xy_pred    = np.stack([x_pred, y_pred], axis=1),
        )

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return room-classification probability matrix (N, n_classes)."""
        self._check_fitted()
        if hasattr(self.classifier, "predict_proba"):
            return self.classifier.predict_proba(X)
        raise NotImplementedError("Classifier does not support predict_proba.")

    def feature_importances(self) -> dict:
        """Return feature importances for all three models (if available)."""
        self._check_fitted()
        out = {}
        for name, mdl in [
            ("classifier",  self.classifier),
            ("regressor_x", self.regressor_x),
            ("regressor_y", self.regressor_y),
        ]:
            if hasattr(mdl, "feature_importances_"):
                out[name] = mdl.feature_importances_
        return out

    def _check_fitted(self):
        if not self._fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
