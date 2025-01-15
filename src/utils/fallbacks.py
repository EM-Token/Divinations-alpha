import warnings
from typing import Any, List, Dict
import numpy as np
from scipy import stats

class NumpyFallback:
    """Fallback implementations for numpy functions"""
    
    @staticmethod
    def array(data: Any) -> np.ndarray:
        try:
            return np.array(data, dtype=np.float64)
        except:
            # Fallback to list implementation
            return [float(x) for x in data]

    @staticmethod
    def std(data: List[float]) -> float:
        if len(data) < 2:
            return 0.0
        mean = sum(data) / len(data)
        squared_diff_sum = sum((x - mean) ** 2 for x in data)
        return (squared_diff_sum / (len(data) - 1)) ** 0.5

class ScikitLearnFallback:
    """Fallback implementations for scikit-learn functionality"""
    
    @staticmethod
    def dbscan(data: List[float], eps: float, min_samples: int) -> Dict:
        """Simple implementation of DBSCAN clustering"""
        labels = [-1] * len(data)
        cluster_id = 0
        
        for i in range(len(data)):
            if labels[i] != -1:
                continue
                
            neighbors = []
            for j in range(len(data)):
                if abs(data[i] - data[j]) <= eps:
                    neighbors.append(j)
                    
            if len(neighbors) >= min_samples:
                labels[i] = cluster_id
                for neighbor in neighbors:
                    labels[neighbor] = cluster_id
                cluster_id += 1
                
        return {
            'labels': labels,
            'n_clusters': cluster_id
        }

class PandasFallback:
    """Fallback implementations for pandas functionality"""
    
    @staticmethod
    def rolling_mean(data: List[float], window: int) -> List[float]:
        result = []
        for i in range(len(data)):
            if i < window - 1:
                result.append(sum(data[:i+1]) / (i+1))
            else:
                result.append(sum(data[i-window+1:i+1]) / window)
        return result 