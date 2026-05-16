"""
PRIORITY 3: Crowd Density Estimation
Estimates number of people (1-3 or more) based on CSI signal complexity.
"""

import numpy as np
from collections import deque
from src.utils.helper import get_logger

logger = get_logger(__name__)


class CrowdDensityEstimator:
    """
    Estimates the number of people in the room based on CSI signal characteristics.
    
    Principle:
    - More people = more reflections = more CSI complexity/variance
    - Single person: moderate variance
    - Multiple people: high variance + multi-modal patterns
    
    Outputs:
    - EMPTY: 0 people
    - SINGLE: 1 person
    - FEW: 2-3 people
    - MANY: 4+ people (or high uncertainty)
    """
    
    # Empirical thresholds (tune based on your environment)
    EMPTY_THRESHOLD = 0.05
    SINGLE_THRESHOLD = 0.15
    FEW_THRESHOLD = 0.35
    
    def __init__(self, buffer_size=30):
        """
        Parameters
        ----------
        buffer_size : int
            Number of CSI windows to analyze
        """
        self.buffer_size = buffer_size
        self.buffer = deque(maxlen=buffer_size)
        self.density_history = deque(maxlen=10)
    
    def estimate(self, csi_data: np.ndarray) -> dict:
        """
        Estimate crowd density from CSI window.
        
        Parameters
        ----------
        csi_data : np.ndarray
            CSI data, shape (num_packets, features) or flattened
            
        Returns
        -------
        dict : {
            'count': str ('EMPTY', 'SINGLE', 'FEW', 'MANY'),
            'estimated_people': int (1-4+),
            'confidence': float (0-1),
            'complexity': float,
            'variance': float,
            'description': str
        }
        """
        if csi_data is None or len(csi_data) == 0:
            return self._get_empty_state()
        
        # Compute complexity metrics
        flat = csi_data.flatten()
        self.buffer.append(flat)
        
        if len(self.buffer) < max(5, self.buffer_size // 3):
            return self._get_insufficient_data()
        
        # Extract metrics
        complexity = self._compute_complexity()
        variance = self._compute_variance()
        multimodality = self._compute_multimodality()
        
        # Estimate count
        count, count_int, confidence = self._estimate_count(
            complexity, variance, multimodality
        )
        
        # Store in history for smoothing
        self.density_history.append(count)
        
        # Smoothed count (majority)
        smoothed_count = self._get_smoothed_count()
        
        return {
            'count': smoothed_count,
            'raw_count': count,
            'estimated_people': count_int,
            'confidence': confidence,
            'complexity': complexity,
            'variance': variance,
            'multimodality': multimodality,
            'description': self._get_description(smoothed_count, count_int, confidence),
            'buffer_fill': len(self.buffer) / self.buffer_size
        }
    
    def _compute_complexity(self) -> float:
        """
        Compute signal complexity (entropy-based).
        More people = higher complexity.
        """
        if len(self.buffer) < 2:
            return 0.0
        
        # Aggregate all buffered samples
        all_data = np.concatenate(list(self.buffer))
        
        # Spectral entropy (complexity in frequency domain)
        fft_coeffs = np.abs(np.fft.fft(all_data))
        fft_norm = fft_coeffs / np.sum(fft_coeffs)
        
        # Shannon entropy
        entropy = -np.sum(fft_norm[fft_norm > 1e-10] * 
                         np.log2(fft_norm[fft_norm > 1e-10]))
        
        # Normalize by max entropy
        max_entropy = np.log2(len(fft_norm))
        complexity = entropy / (max_entropy + 1e-6)
        
        return min(1.0, complexity)
    
    def _compute_variance(self) -> float:
        """
        Compute variance across CSI windows.
        More people = higher variance in patterns.
        """
        if len(self.buffer) < 2:
            return 0.0
        
        # Variance of mean amplitudes across windows
        window_means = [np.mean(np.abs(w)) for w in self.buffer]
        variance = np.var(window_means)
        
        # Normalize
        mean_amplitude = np.mean(window_means)
        if mean_amplitude < 1e-6:
            return 0.0
        
        normalized_variance = variance / (mean_amplitude ** 2 + 1e-6)
        return min(1.0, normalized_variance)
    
    def _compute_multimodality(self) -> float:
        """
        Detect multimodal distribution (multiple peaks).
        Multiple people = multiple activity modes = higher multimodality.
        """
        if len(self.buffer) < 3:
            return 0.0
        
        all_data = np.concatenate(list(self.buffer))
        
        # Compute histogram
        hist, bin_edges = np.histogram(all_data, bins=20)
        
        # Count peaks (local maxima)
        peaks = 0
        for i in range(1, len(hist) - 1):
            if hist[i] > hist[i-1] and hist[i] > hist[i+1]:
                peaks += 1
        
        # Normalize: expected 1-2 peaks for single person, 2-4 for multiple
        multimodality = min(1.0, peaks / 4.0)
        
        return multimodality
    
    def _estimate_count(self, complexity: float, variance: float, 
                       multimodality: float) -> tuple:
        """
        Estimate number of people based on metrics.
        
        Returns
        -------
        (count_label, count_int, confidence)
        """
        # Weighted combination of metrics
        score = (0.4 * complexity + 0.3 * variance + 0.3 * multimodality)
        
        # Classify
        if score < self.EMPTY_THRESHOLD:
            count_label = 'EMPTY'
            count_int = 0
            confidence = 1.0 - (score / self.EMPTY_THRESHOLD)
        elif score < self.SINGLE_THRESHOLD:
            count_label = 'SINGLE'
            count_int = 1
            # Confidence is higher near center of range
            mid = (self.EMPTY_THRESHOLD + self.SINGLE_THRESHOLD) / 2
            confidence = 1.0 - abs(score - mid) / (self.SINGLE_THRESHOLD - self.EMPTY_THRESHOLD)
        elif score < self.FEW_THRESHOLD:
            count_label = 'FEW'
            count_int = 2 if score < (self.SINGLE_THRESHOLD + self.FEW_THRESHOLD) / 2 else 3
            mid = (self.SINGLE_THRESHOLD + self.FEW_THRESHOLD) / 2
            confidence = 1.0 - abs(score - mid) / (self.FEW_THRESHOLD - self.SINGLE_THRESHOLD)
        else:
            count_label = 'MANY'
            count_int = 4
            confidence = min(1.0, (score - self.FEW_THRESHOLD) / 0.3)
        
        confidence = max(0.0, min(1.0, confidence))
        return count_label, count_int, confidence
    
    def _get_smoothed_count(self) -> str:
        """Get majority count from history."""
        if not self.density_history:
            return 'EMPTY'
        counts = list(self.density_history)
        return max(set(counts), key=counts.count)
    
    def _get_description(self, count: str, count_int: int, confidence: float) -> str:
        """Generate human-readable description."""
        conf_pct = int(confidence * 100)
        
        if count == 'EMPTY':
            return f"👥 EMPTY: No one detected ({conf_pct}% confidence)"
        elif count == 'SINGLE':
            return f"👥 1 PERSON (~{count_int} detected, {conf_pct}% confidence)"
        elif count == 'FEW':
            return f"👥 FEW PEOPLE (~{count_int} detected, {conf_pct}% confidence)"
        else:
            return f"👥 MANY PEOPLE (4+ detected, {conf_pct}% confidence)"
    
    def _get_empty_state(self) -> dict:
        return {
            'count': 'EMPTY',
            'raw_count': 'EMPTY',
            'estimated_people': 0,
            'confidence': 0.0,
            'complexity': 0.0,
            'variance': 0.0,
            'multimodality': 0.0,
            'description': 'Initializing...',
            'buffer_fill': 0.0
        }
    
    def _get_insufficient_data(self) -> dict:
        return {
            'count': 'EMPTY',
            'raw_count': 'EMPTY',
            'estimated_people': 0,
            'confidence': 0.0,
            'complexity': 0.0,
            'variance': 0.0,
            'multimodality': 0.0,
            'description': f'Buffering... ({len(self.buffer)}/{self.buffer_size})',
            'buffer_fill': len(self.buffer) / self.buffer_size
        }
    
    def reset(self):
        """Reset estimator state."""
        self.buffer.clear()
        self.density_history.clear()
