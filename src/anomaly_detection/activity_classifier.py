"""
PRIORITY 2: Activity Classification
Classifies what people are doing: Walking, Standing, Sitting, or Unknown
"""

import numpy as np
from sklearn.preprocessing import StandardScaler
from src.utils.helper import get_logger

logger = get_logger(__name__)


class ActivityClassifier:
    """
    Classifies human activities based on CSI patterns.
    
    Activities:
    - WALKING: Periodic, high-energy movement (legs/arms)
    - STANDING: Medium energy, some micro-movements
    - SITTING: Low energy, minimal movement
    - UNKNOWN: Insufficient data
    """
    
    # Activity signatures (derived from CSI characteristics)
    WALKING_FEATURES = {
        'periodicity': (0.5, 2.0),      # Hz, typical gait frequency
        'energy': (0.4, 1.0),           # Normalized energy
        'regularity': (0.6, 1.0)        # Autocorrelation strength
    }
    
    STANDING_FEATURES = {
        'periodicity': (0.1, 0.5),
        'energy': (0.2, 0.5),
        'regularity': (0.3, 0.7)
    }
    
    SITTING_FEATURES = {
        'periodicity': (0.0, 0.2),
        'energy': (0.05, 0.25),
        'regularity': (0.1, 0.4)
    }
    
    def __init__(self, window_size=20, sampling_rate=10):
        """
        Parameters
        ----------
        window_size : int
            Number of CSI packets to analyze
        sampling_rate : float
            Packets per second (approx 10-15 for ESP32)
        """
        self.window_size = window_size
        self.sampling_rate = sampling_rate
        self.scaler = StandardScaler()
        self.feature_history = []
    
    def classify(self, csi_data: np.ndarray) -> dict:
        """
        Classify activity from CSI window.
        
        Parameters
        ----------
        csi_data : np.ndarray
            CSI data, shape (num_packets, features) or (num_packets,)
            
        Returns
        -------
        dict : {
            'activity': str ('WALKING', 'STANDING', 'SITTING', 'UNKNOWN'),
            'confidence': float (0-1),
            'scores': dict (scores for each activity),
            'features': dict (extracted features),
            'description': str
        }
        """
        if csi_data is None or len(csi_data) < 5:
            return self._get_unknown_state()
        
        # Extract features
        features = self._extract_features(csi_data)
        self.feature_history.append(features)
        
        # Classify based on features
        scores = self._score_activities(features)
        activity = max(scores, key=scores.get)
        confidence = scores[activity]
        
        return {
            'activity': activity,
            'confidence': confidence,
            'scores': scores,
            'features': features,
            'description': self._get_description(activity, confidence),
        }
    
    def _extract_features(self, csi_data: np.ndarray) -> dict:
        """Extract activity-relevant features from CSI data."""
        # Ensure 1D
        flat = csi_data.flatten()
        
        # Energy (RMS)
        energy = np.sqrt(np.mean(flat ** 2))
        energy_norm = min(1.0, energy / np.std(flat) if np.std(flat) > 0 else 0)
        
        # Periodicity (via autocorrelation)
        periodicity = self._compute_periodicity(flat)
        
        # Regularity (energy regularity)
        regularity = self._compute_regularity(flat)
        
        # Entropy (complexity)
        entropy = self._compute_entropy(flat)
        
        return {
            'energy': energy_norm,
            'periodicity': periodicity,
            'regularity': regularity,
            'entropy': entropy,
        }
    
    def _compute_periodicity(self, signal: np.ndarray, max_lag=20) -> float:
        """
        Compute periodicity strength (0-1).
        Walking has high periodicity (gait cycle).
        Sitting has low periodicity.
        """
        if len(signal) < max_lag + 1:
            return 0.0
        
        # Autocorrelation at first significant lag
        mean = np.mean(signal)
        c0 = np.sum((signal - mean) ** 2) / len(signal)
        
        if c0 < 1e-6:
            return 0.0
        
        # Check for periodicity at typical gait frequency (0.5-2 Hz)
        # With ~10Hz sampling, lag 5-20 corresponds to gait
        acf_values = []
        for lag in range(5, min(max_lag, len(signal) // 2)):
            c = np.sum((signal[:-lag] - mean) * (signal[lag:] - mean)) / len(signal)
            acf_values.append(abs(c / c0))
        
        periodicity = np.max(acf_values) if acf_values else 0.0
        return min(1.0, periodicity)
    
    def _compute_regularity(self, signal: np.ndarray) -> float:
        """
        Compute regularity of the signal (0-1).
        Regular motion = higher regularity.
        """
        if len(signal) < 2:
            return 0.0
        
        # Compute differences
        diffs = np.diff(signal)
        
        # Regularity based on variance of differences
        # Low variance = regular, high variance = irregular
        mean_diff = np.mean(np.abs(diffs))
        std_diff = np.std(diffs)
        
        if mean_diff < 1e-6:
            return 0.0
        
        regularity = 1.0 / (1.0 + std_diff / mean_diff)
        return min(1.0, regularity)
    
    def _compute_entropy(self, signal: np.ndarray, bins=10) -> float:
        """
        Compute entropy (complexity) of signal.
        High entropy = complex/irregular, Low = simple/regular
        """
        # Normalize to histogram bins
        signal_norm = (signal - np.min(signal)) / (np.max(signal) - np.min(signal) + 1e-6)
        hist, _ = np.histogram(signal_norm, bins=bins, range=(0, 1))
        hist = hist / np.sum(hist)  # Normalize to probability
        
        # Shannon entropy
        entropy = -np.sum(hist[hist > 0] * np.log2(hist[hist > 0]))
        entropy_norm = entropy / np.log2(bins)  # Normalize by max entropy
        
        return min(1.0, entropy_norm)
    
    def _score_activities(self, features: dict) -> dict:
        """Score each activity based on feature ranges."""
        scores = {}
        
        # Walking: high energy + high periodicity
        walking_score = self._compute_activity_score(
            features, self.WALKING_FEATURES
        )
        scores['WALKING'] = walking_score
        
        # Standing: medium energy + medium periodicity
        standing_score = self._compute_activity_score(
            features, self.STANDING_FEATURES
        )
        scores['STANDING'] = standing_score
        
        # Sitting: low energy + low periodicity
        sitting_score = self._compute_activity_score(
            features, self.SITTING_FEATURES
        )
        scores['SITTING'] = sitting_score
        
        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        else:
            scores = {k: 0.33 for k in scores}
        
        return scores
    
    def _compute_activity_score(self, features: dict, feature_ranges: dict) -> float:
        """Compute match score between features and expected ranges."""
        score = 1.0
        
        for feature, (min_val, max_val) in feature_ranges.items():
            if feature not in features:
                continue
            
            value = features[feature]
            
            # Gaussian-like scoring
            # Peak at center of range, decay outside
            mid = (min_val + max_val) / 2
            width = (max_val - min_val) / 2
            
            if width < 1e-6:
                distance = 0.0
            else:
                distance = abs(value - mid) / width
            
            # Gaussian: exp(-distance^2)
            feature_score = np.exp(-distance ** 2)
            score *= feature_score
        
        return score
    
    def _get_description(self, activity: str, confidence: float) -> str:
        """Generate human-readable description."""
        conf_pct = int(confidence * 100)
        
        if activity == 'WALKING':
            return f"🚶 WALKING ({conf_pct}% confidence)"
        elif activity == 'STANDING':
            return f"🧍 STANDING ({conf_pct}% confidence)"
        elif activity == 'SITTING':
            return f"🪑 SITTING ({conf_pct}% confidence)"
        else:
            return f"❓ UNKNOWN ({conf_pct}% confidence)"
    
    def _get_unknown_state(self) -> dict:
        return {
            'activity': 'UNKNOWN',
            'confidence': 0.0,
            'scores': {'WALKING': 0.25, 'STANDING': 0.25, 'SITTING': 0.25},
            'features': {},
            'description': 'Insufficient data for classification'
        }
    
    def reset(self):
        """Reset classifier state."""
        self.feature_history.clear()
