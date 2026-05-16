# src/localization/optimize_regressors.py
"""
Optimize regressor hyperparameters using GridSearchCV/RandomizedSearchCV
to minimize position error (MAE).

This script performs cross-validation hyperparameter search to find
optimal settings for coordinate regressors, targeting <0.4m error.
"""

import numpy as np
from pathlib import Path
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import RandomizedSearchCV, cross_val_score
from xgboost import XGBRegressor
from src.utils.config import (
    PROC_DIR, TEST_SPLIT, RANDOM_STATE, CV_FOLDS,
    SCALER_FILE, PCA_FILE,
)
from src.utils.helper import get_logger
from src.localization.train import (
    load_processed_data, run_preprocessing, run_feature_extraction,
    run_anomaly_detection,
)
from src.preprocessing.normalization import transform
from src.feature_engineering.pca import apply_pca
from sklearn.model_selection import train_test_split

logger = get_logger(__name__)


def optimize_xgb_regressor(X_train, y_train, n_iter=20):
    """
    Randomized search for best XGBoost regressor parameters.
    Targets position MAE < 0.4m.
    """
    param_dist = {
        'n_estimators': [150, 200, 250, 300, 350],
        'max_depth': [4, 5, 6, 7, 8],
        'learning_rate': [0.02, 0.04, 0.06, 0.08, 0.1],
        'subsample': [0.6, 0.7, 0.8, 0.9],
        'colsample_bytree': [0.6, 0.7, 0.8, 0.9],
        'min_child_weight': [0.5, 1, 2, 3],
        'gamma': [0, 0.1, 0.2, 0.5],
        'reg_alpha': [0, 0.001, 0.01, 0.1],
        'reg_lambda': [0.1, 0.5, 1.0, 2.0],
    }
    
    xgb = XGBRegressor(
        objective='reg:squarederror',
        tree_method='hist',
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    
    search = RandomizedSearchCV(
        xgb,
        param_dist,
        n_iter=n_iter,
        cv=min(CV_FOLDS, 3),  # use 3-fold for speed
        scoring='neg_mean_absolute_error',
        n_jobs=-1,
        verbose=2,
        random_state=RANDOM_STATE,
    )
    
    search.fit(X_train, y_train)
    
    logger.info(f"Best XGBoost MAE: {-search.best_score_:.4f} m")
    logger.info(f"Best params: {search.best_params_}")
    
    return search.best_estimator_, search.best_params_


def optimize_rf_regressor(X_train, y_train, n_iter=10):
    """
    Randomized search for best Random Forest regressor parameters.
    """
    param_dist = {
        'n_estimators': [100, 150, 200, 300],
        'max_depth': [6, 8, 10, None],
        'min_samples_split': [2, 3, 4, 5],
        'min_samples_leaf': [1, 2, 3, 4],
        'max_features': ['sqrt', 'log2', None],
    }
    
    rf = RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=-1)
    
    search = RandomizedSearchCV(
        rf,
        param_dist,
        n_iter=n_iter,
        cv=min(CV_FOLDS, 3),
        scoring='neg_mean_absolute_error',
        n_jobs=-1,
        verbose=2,
        random_state=RANDOM_STATE,
    )
    
    search.fit(X_train, y_train)
    
    logger.info(f"Best RF MAE: {-search.best_score_:.4f} m")
    logger.info(f"Best params: {search.best_params_}")
    
    return search.best_estimator_, search.best_params_


def run_optimization():
    """
    Run full optimization pipeline to find best regressor parameters.
    """
    logger.info("Starting regressor hyperparameter optimization...")
    
    # Load and preprocess data
    data = load_processed_data()
    data = run_preprocessing(data)
    feat = run_feature_extraction(data)
    
    # Encode labels
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    y_label_encoded = le.fit_transform(feat["y_label"])
    feat["y_label"] = y_label_encoded
    
    feat = run_anomaly_detection(feat)
    
    # Scale and apply PCA
    X_scaled = transform(feat["X"])
    X_pca = apply_pca(X_scaled)
    
    # Split into train/test
    idx = np.arange(len(X_pca))
    idx_train, idx_test = train_test_split(
        idx, test_size=TEST_SPLIT,
        stratify=feat["y_label"],
        random_state=RANDOM_STATE
    )
    
    X_train = X_pca[idx_train]
    X_test = X_pca[idx_test]
    y_x_train = feat["y_x"][idx_train]
    y_x_test = feat["y_x"][idx_test]
    y_y_train = feat["y_y"][idx_train]
    y_y_test = feat["y_y"][idx_test]
    
    logger.info(f"Training set: {X_train.shape}, Test set: {X_test.shape}")
    
    # Optimize X regressor
    logger.info("\n" + "="*60)
    logger.info("OPTIMIZING X-COORDINATE REGRESSOR")
    logger.info("="*60)
    best_xgb_x, best_params_x = optimize_xgb_regressor(X_train, y_x_train)
    
    # Optimize Y regressor
    logger.info("\n" + "="*60)
    logger.info("OPTIMIZING Y-COORDINATE REGRESSOR")
    logger.info("="*60)
    best_xgb_y, best_params_y = optimize_xgb_regressor(X_train, y_y_train)
    
    # Test performance
    from sklearn.metrics import mean_absolute_error
    mae_x = mean_absolute_error(y_x_test, best_xgb_x.predict(X_test))
    mae_y = mean_absolute_error(y_y_test, best_xgb_y.predict(X_test))
    euclidean = np.sqrt(mae_x**2 + mae_y**2)
    
    logger.info("\n" + "="*60)
    logger.info("OPTIMIZATION RESULTS")
    logger.info("="*60)
    logger.info(f"X MAE: {mae_x:.4f} m")
    logger.info(f"Y MAE: {mae_y:.4f} m")
    logger.info(f"Euclidean error: {euclidean:.4f} m")
    logger.info("="*60)
    
    # Print best parameters for config.py
    logger.info("\nAdd these to src/utils/config.py XGB_REGRESSOR_PARAMS:")
    logger.info(f"X: {best_params_x}")
    logger.info(f"Y: {best_params_y}")
    
    return best_params_x, best_params_y


if __name__ == "__main__":
    run_optimization()
