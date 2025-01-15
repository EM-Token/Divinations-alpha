from typing import List, Dict, Tuple
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from utils.image_handler import ImageHandler
import logging

logger = logging.getLogger(__name__)

@dataclass
class PricePoint:
    timestamp: datetime
    price: float
    volume: float

class ChartAnalyzer:
    def __init__(self):
        self.min_data_points = 10
        self.pump_dump_threshold = 0.3  # 30% price change
        self.volume_spike_threshold = 3.0  # 3x average volume
        self.image_handler = ImageHandler()
        
    async def analyze_chart(self, price_history: List[PricePoint]) -> Dict:
        """Analyze price chart for suspicious patterns"""
        if len(price_history) < self.min_data_points:
            return {
                "natural_chart": True,
                "confidence": 0.5,
                "patterns": [],
                "chart_image": None
            }
            
        patterns = []
        prices = np.array([p.price for p in price_history])
        volumes = np.array([p.volume for p in price_history])
        
        # Generate and save chart image with error handling
        chart_image_base64 = None
        try:
            chart_image = self._generate_chart_image(prices, volumes)
            chart_path = self.image_handler.save_chart_image(
                f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                chart_image
            )
            chart_image_base64 = self.image_handler.image_to_base64(chart_path)
        except Exception as e:
            logger.error(f"Failed to generate chart image: {e}")
        
        # Detect pump and dump patterns
        pump_dumps = self._detect_pump_dump(prices, volumes)
        if pump_dumps:
            patterns.extend(["pump_and_dump"] * len(pump_dumps))
            
        # Detect unusual volume patterns
        volume_spikes = self._detect_volume_spikes(volumes)
        if volume_spikes:
            patterns.append("unusual_volume")
            
        # Detect wash trading
        if self._detect_wash_trading(price_history):
            patterns.append("wash_trading")
            
        # Calculate how natural the chart looks
        natural_score = self._calculate_natural_score(patterns, prices, volumes)
        
        return {
            "natural_chart": natural_score > 0.7,
            "confidence": natural_score,
            "patterns": patterns,
            "chart_image": chart_image_base64
        }
        
    def _detect_pump_dump(self, prices: np.ndarray, volumes: np.ndarray) -> List[Tuple[int, int]]:
        """Detect pump and dump patterns in the price chart"""
        patterns = []
        window_size = min(len(prices) // 4, 20)
        
        for i in range(len(prices) - window_size):
            window = prices[i:i+window_size]
            max_idx = np.argmax(window)
            min_idx = np.argmin(window)
            
            if max_idx < min_idx:
                price_change = (window[max_idx] - window[min_idx]) / window[max_idx]
                if price_change > self.pump_dump_threshold:
                    patterns.append((i + max_idx, i + min_idx))
                    
        return patterns
        
    def _detect_volume_spikes(self, volumes: np.ndarray) -> List[int]:
        """Detect unusual volume spikes"""
        spikes = []
        moving_avg = np.convolve(volumes, np.ones(5)/5, mode='valid')
        
        for i in range(len(volumes) - 4):
            if volumes[i+4] > moving_avg[i] * self.volume_spike_threshold:
                spikes.append(i+4)
                
        return spikes
        
    def _detect_wash_trading(self, price_history: List[PricePoint]) -> bool:
        """Detect potential wash trading patterns"""
        if len(price_history) < 10:
            return False
            
        # Look for repetitive patterns in price and volume
        price_diffs = np.diff([p.price for p in price_history])
        volume_diffs = np.diff([p.volume for p in price_history])
        
        # Check for too many exact matches in price movements
        unique_moves = len(np.unique(price_diffs))
        if unique_moves < len(price_diffs) * 0.3:  # Less than 30% unique moves
            return True
            
        return False
        
    def _calculate_natural_score(self, patterns: List[str], prices: np.ndarray, volumes: np.ndarray) -> float:
        """Calculate how natural the chart looks (0 to 1)"""
        base_score = 1.0
        
        # Penalize for each detected pattern
        base_score -= len(patterns) * 0.1
        
        # Check price continuity
        price_jumps = np.abs(np.diff(prices)) / prices[:-1]
        if np.any(price_jumps > 0.5):  # 50% price jump
            base_score -= 0.2
            
        # Check volume distribution
        volume_std = np.std(volumes)
        volume_mean = np.mean(volumes)
        if volume_std / volume_mean > 2:  # High volume volatility
            base_score -= 0.1
            
        return max(0.0, min(1.0, base_score)) 
        
    def _generate_chart_image(self, prices: np.ndarray, volumes: np.ndarray) -> bytes:
        """Generate chart image using matplotlib and convert to bytes"""
        import matplotlib.pyplot as plt
        import io
        
        plt.figure(figsize=(10, 6))
        
        # Plot price
        plt.subplot(2, 1, 1)
        plt.plot(prices, label='Price')
        plt.title('Price and Volume Analysis')
        plt.legend()
        
        # Plot volume
        plt.subplot(2, 1, 2)
        plt.bar(range(len(volumes)), volumes, label='Volume')
        plt.legend()
        
        # Save to bytes
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        
        return buf.getvalue() 