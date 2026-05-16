"""
PRIORITY 1: Movement Detection
Detects if room is active, idle, or empty based on CSI variance over time.
"""

import numpy as np
from collections import deque
from src.utils.helper import get_logger

logger = get_logger(__name__)


class MovementDetector:
    """
    Detects movement/activity by analyzing CSI temporal variance.
    
    States:
    - EMPTY: No one in room (very low variance)
    - IDLE: Someone present but stationary (moderate variance)
    - ACTIVE: One or more people moving (high variance)
    """
    
    def __init__(self, buffer_size=20, active_threshold=0.25, idle_threshold=0.08):
        """
        Parameters
        ----------
        buffer_size : int
            Number of CSI windows to buffer for variance calculation
        active_threshold : float
            CSI variance threshold for "ACTIVE" state
        idle_threshold : float
            CSI variance threshold for "IDLE" state
            Values below this = EMPTY
        """
        self.buffer_size = buffer_size
        self.active_threshold = active_threshold
        self.idle_threshold = idle_threshold
        self.buffer = deque(maxlen=buffer_size)
        self.state_history = deque(maxlen=10)  # For smoothing
        
    def add_window(self, csi_window: np.ndarray) -> dict:
        """
        Add a new CSI window and analyze for movement.
        
        Parameters
        ----------
        csi_window : np.ndarray
            CSI data, shape (num_packets, num_subcarriers, 2) or flattened
            
        Returns
        -------
        dict : {
            'state': str ('EMPTY', 'IDLE', 'ACTIVE'),
            'variance': float,
            'confidence': float (0-1),
            'description': str
        }
        """
        if csi_window is None or len(csi_window) == 0:
            return self._get_empty_state()
        
        # Flatten and compute amplitude
        flat = csi_window.flatten()
        amplitude = np.abs(flat)
        
        self.buffer.append(amplitude)
        
        # Not enough data yet
        if len(self.buffer) < self.buffer_size // 2:
            return self._get_buffering_state()
        
        # Compute variance across all buffered amplitudes
        variance = self._compute_variance()
        
        # Classify state
        state = self._classify_state(variance)
        confidence = self._compute_confidence(variance)
        
        # Store state history for smoothing
        self.state_history.append(state)
        
        # Smoothed state (majority in last 10)
        smoothed_state = self._get_smoothed_state()
        
        return {
            'state': smoothed_state,
            'raw_state': state,
            'variance': variance,
            'confidence': confidence,
            'description': self._get_description(smoothed_state, variance, confidence),
            'buffer_fill': len(self.buffer) / self.buffer_size
        }
    
    def _compute_variance(self) -> float:
        """Compute normalized variance across buffered windows."""
        amplitudes = np.array(list(self.buffer))
        # Variance of means across windows
        window_means = amplitudes.mean(axis=1)
        variance = np.std(window_means) / (np.mean(window_means) + 1e-6)
        return variance
    
    def _classify_state(self, variance: float) -> str:
        """Classify activity state based on variance."""
        if variance >= self.active_threshold:
            return "ACTIVE"
        elif variance >= self.idle_threshold:
            return "IDLE"
        else:
            return "EMPTY"
    
    def _compute_confidence(self, variance: float) -> float:
        """Compute confidence score (0-1) for the state."""
        if variance >= self.active_threshold:
            # Confidence increases with variance above threshold
            confidence = min(1.0, (variance - self.active_threshold) / (0.5 - self.active_threshold))
        elif variance >= self.idle_threshold:
            # Confidence in idle state
            mid = (self.idle_threshold + self.active_threshold) / 2
            confidence = min(1.0, abs(variance - mid) / (self.active_threshold - self.idle_threshold))
        else:
            # Confidence in empty state increases as variance decreases
            confidence = 1.0 - (variance / self.idle_threshold)
        
        return max(0.0, min(1.0, confidence))
    
    def _get_smoothed_state(self) -> str:
        """Return majority state from history (for smoothing)."""
        if not self.state_history:
            return "EMPTY"
        states = list(self.state_history)
        return max(set(states), key=states.count)
    
    def _get_description(self, state: str, variance: float, confidence: float) -> str:
        """Generate human-readable description."""
        conf_pct = int(confidence * 100)
        
        if state == "ACTIVE":
            return f"🔴 ACTIVE: Movement detected! ({conf_pct}% confidence)"
        elif state == "IDLE":
            return f"🟡 IDLE: Person present but stationary ({conf_pct}% confidence)"
        else:
            return f"🟢 EMPTY: No one in room ({conf_pct}% confidence)"
    
    def _get_empty_state(self) -> dict:
        return {
            'state': 'EMPTY',
            'raw_state': 'EMPTY',
            'variance': 0.0,
            'confidence': 0.0,
            'description': 'Initializing...',
            'buffer_fill': 0.0
        }
    
    def _get_buffering_state(self) -> dict:
        return {
            'state': 'EMPTY',
            'raw_state': 'EMPTY',
            'variance': 0.0,
            'confidence': 0.0,
            'description': f'Buffering... ({len(self.buffer)}/{self.buffer_size})',
            'buffer_fill': len(self.buffer) / self.buffer_size
        }
    
    def reset(self):
        """Reset detector state."""
        self.buffer.clear()
        self.state_history.clear()
