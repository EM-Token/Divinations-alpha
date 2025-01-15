from typing import List, Dict, Tuple
import numpy as np
from dataclasses import dataclass
from datetime import datetime
from scipy import stats
from sklearn.cluster import DBSCAN
from ..utils.compatibility import requires_package, PackageCompatibility
from ..utils.fallbacks import NumpyFallback, ScikitLearnFallback

@dataclass
class TradingPattern:
    pattern_type: str
    confidence: float
    start_time: datetime
    end_time: datetime
    severity: float
    description: str

class PatternAnalyzer:
    def __init__(self):
        self.np = PackageCompatibility.get_compatible_package('numpy')
        self.sklearn = PackageCompatibility.get_compatible_package('scikit-learn')
        
        self.known_patterns = {
            "pump_and_dump": self._detect_pump_dump,
            "accumulation": self._detect_accumulation,
            "distribution": self._detect_distribution,
            "wash_trading": self._detect_wash_trading,
            "liquidity_manipulation": self._detect_liquidity_manipulation
        }
        
    async def analyze_patterns(self, price_data: List[Dict], volume_data: List[Dict]) -> List[TradingPattern]:
        patterns = []
        
        for pattern_name, detector in self.known_patterns.items():
            detected_patterns = await detector(price_data, volume_data)
            patterns.extend(detected_patterns)
            
        return patterns
        
    async def _detect_pump_dump(self, price_data: List[Dict], volume_data: List[Dict]) -> List[TradingPattern]:
        patterns = []
        prices = np.array([p['close'] for p in price_data])
        volumes = np.array([v['volume'] for v in volume_data])
        times = [p['timestamp'] for p in price_data]
        
        # Calculate price changes and volume ratios
        price_changes = np.diff(prices) / prices[:-1]
        volume_ratios = volumes[1:] / np.mean(volumes)
        
        # Look for sudden price increases with high volume
        for i in range(len(price_changes)):
            if price_changes[i] > 0.2 and volume_ratios[i] > 3:  # 20% price jump with 3x volume
                # Look for subsequent dump
                if i + 5 < len(price_changes):
                    future_prices = prices[i+1:i+6]
                    if min(future_prices) < prices[i] * 0.8:  # 20% drop
                        patterns.append(TradingPattern(
                            pattern_type="pump_and_dump",
                            confidence=0.8,
                            start_time=times[i],
                            end_time=times[i+5],
                            severity=abs(price_changes[i]),
                            description="Detected pump and dump pattern with high volume"
                        ))
                        
        return patterns
        
    async def _detect_accumulation(self, price_data: List[Dict], volume_data: List[Dict]) -> List[TradingPattern]:
        patterns = []
        prices = np.array([p['close'] for p in price_data])
        volumes = np.array([v['volume'] for v in volume_data])
        times = [p['timestamp'] for p in price_data]
        
        # Look for periods of sideways trading with increasing buy volume
        window_size = 12  # 1-hour windows for 5-minute candles
        
        for i in range(len(prices) - window_size):
            window_prices = prices[i:i+window_size]
            window_volumes = volumes[i:i+window_size]
            
            price_volatility = np.std(window_prices) / np.mean(window_prices)
            volume_trend = np.polyfit(range(window_size), window_volumes, 1)[0]
            
            if price_volatility < 0.05 and volume_trend > 0:  # Low price volatility with increasing volume
                patterns.append(TradingPattern(
                    pattern_type="accumulation",
                    confidence=0.7,
                    start_time=times[i],
                    end_time=times[i+window_size-1],
                    severity=volume_trend / np.mean(window_volumes),
                    description="Detected accumulation pattern with increasing volume"
                ))
                
        return patterns
        
    async def _detect_wash_trading(self, price_data: List[Dict], volume_data: List[Dict]) -> List[TradingPattern]:
        patterns = []
        volumes = np.array([v['volume'] for v in volume_data])
        times = [p['timestamp'] for p in price_data]
        
        # Use DBSCAN to detect clusters of similar-sized trades
        X = volumes.reshape(-1, 1)
        clustering = DBSCAN(eps=np.std(volumes)*0.1, min_samples=5).fit(X)
        
        # Look for suspicious clusters
        unique_labels = set(clustering.labels_)
        for label in unique_labels:
            if label == -1:  # Noise points
                continue
                
            cluster_volumes = volumes[clustering.labels_ == label]
            if len(cluster_volumes) > 10:  # More than 10 similar-sized trades
                cluster_times = [times[i] for i, l in enumerate(clustering.labels_) if l == label]
                patterns.append(TradingPattern(
                    pattern_type="wash_trading",
                    confidence=0.9,
                    start_time=min(cluster_times),
                    end_time=max(cluster_times),
                    severity=len(cluster_volumes) / len(volumes),
                    description=f"Detected {len(cluster_volumes)} similar-sized trades"
                ))
                
        return patterns 

    async def _detect_distribution(self, price_data: List[Dict], volume_data: List[Dict]) -> List[TradingPattern]:
        """Detect distribution patterns (opposite of accumulation)"""
        patterns = []
        prices = np.array([p['close'] for p in price_data])
        volumes = np.array([v['volume'] for v in volume_data])
        times = [p['timestamp'] for p in price_data]
        
        window_size = 12  # 1-hour windows for 5-minute candles
        
        for i in range(len(prices) - window_size):
            window_prices = prices[i:i+window_size]
            window_volumes = volumes[i:i+window_size]
            
            # Look for declining prices with increasing volume
            price_trend = np.polyfit(range(window_size), window_prices, 1)[0]
            volume_trend = np.polyfit(range(window_size), window_volumes, 1)[0]
            
            if price_trend < 0 and volume_trend > 0:
                # Calculate how strong the distribution is
                distribution_strength = abs(price_trend) * volume_trend
                
                if distribution_strength > np.mean(volumes) * 0.1:  # Significant distribution
                    patterns.append(TradingPattern(
                        pattern_type="distribution",
                        confidence=min(0.9, distribution_strength / np.mean(volumes)),
                        start_time=times[i],
                        end_time=times[i+window_size-1],
                        severity=distribution_strength,
                        description="Detected distribution pattern with declining prices and increasing volume"
                    ))
        
        return patterns

    async def _detect_liquidity_manipulation(self, price_data: List[Dict], volume_data: List[Dict]) -> List[TradingPattern]:
        """Detect potential liquidity manipulation"""
        patterns = []
        prices = np.array([p['close'] for p in price_data])
        volumes = np.array([v['volume'] for v in volume_data])
        times = [p['timestamp'] for p in price_data]
        
        # Calculate bid-ask spread if available
        spreads = np.array([p.get('high', p['close']) - p.get('low', p['close']) for p in price_data])
        
        window_size = 5  # 25-minute windows
        
        for i in range(len(prices) - window_size):
            window_spreads = spreads[i:i+window_size]
            window_volumes = volumes[i:i+window_size]
            
            # Look for widening spreads with low volume
            spread_increase = (window_spreads[-1] - window_spreads[0]) / window_spreads[0]
            volume_decline = (window_volumes[-1] - window_volumes[0]) / window_volumes[0]
            
            if spread_increase > 0.3 and volume_decline < -0.3:  # 30% spread increase with 30% volume decline
                patterns.append(TradingPattern(
                    pattern_type="liquidity_manipulation",
                    confidence=0.7,
                    start_time=times[i],
                    end_time=times[i+window_size-1],
                    severity=spread_increase,
                    description="Detected potential liquidity manipulation with widening spreads"
                ))
        
        return patterns

    async def _detect_momentum_shift(self, price_data: List[Dict], volume_data: List[Dict]) -> List[TradingPattern]:
        """Detect significant momentum shifts"""
        patterns = []
        prices = np.array([p['close'] for p in price_data])
        volumes = np.array([v['volume'] for v in volume_data])
        times = [p['timestamp'] for p in price_data]
        
        # Calculate momentum indicators
        window_size = 20
        momentum = np.zeros_like(prices)
        for i in range(window_size, len(prices)):
            momentum[i] = (prices[i] - prices[i-window_size]) / prices[i-window_size]
        
        # Look for momentum divergence
        price_changes = np.diff(prices) / prices[:-1]
        momentum_changes = np.diff(momentum)
        
        for i in range(len(momentum_changes) - 5):
            # Price making new highs but momentum declining
            if (price_changes[i] > 0 and momentum_changes[i] < 0 and 
                abs(momentum_changes[i]) > np.std(momentum_changes) * 2):
                patterns.append(TradingPattern(
                    pattern_type="bearish_divergence",
                    confidence=0.8,
                    start_time=times[i],
                    end_time=times[i+5],
                    severity=abs(momentum_changes[i]),
                    description="Detected bearish divergence with declining momentum"
                ))
            
            # Price making new lows but momentum improving
            elif (price_changes[i] < 0 and momentum_changes[i] > 0 and 
                  abs(momentum_changes[i]) > np.std(momentum_changes) * 2):
                patterns.append(TradingPattern(
                    pattern_type="bullish_divergence",
                    confidence=0.8,
                    start_time=times[i],
                    end_time=times[i+5],
                    severity=abs(momentum_changes[i]),
                    description="Detected bullish divergence with improving momentum"
                ))
        
        return patterns

    async def _detect_whale_activity(self, price_data: List[Dict], volume_data: List[Dict]) -> List[TradingPattern]:
        """Detect potential whale activity"""
        patterns = []
        volumes = np.array([v['volume'] for v in volume_data])
        times = [p['timestamp'] for p in price_data]
        
        # Calculate volume thresholds
        mean_volume = np.mean(volumes)
        std_volume = np.std(volumes)
        whale_threshold = mean_volume + (std_volume * 3)  # 3 standard deviations above mean
        
        # Look for large individual transactions
        for i, volume in enumerate(volumes):
            if volume > whale_threshold:
                # Calculate impact on price
                if i > 0:
                    price_impact = abs(price_data[i]['close'] - price_data[i-1]['close']) / price_data[i-1]['close']
                    
                    patterns.append(TradingPattern(
                        pattern_type="whale_activity",
                        confidence=min(0.95, volume / whale_threshold),
                        start_time=times[i],
                        end_time=times[i],
                        severity=price_impact,
                        description=f"Detected whale activity with {volume/mean_volume:.1f}x average volume"
                    ))
        
        return patterns 

    @requires_package('numpy')
    def _calculate_momentum(self, prices: List[float], window: int, _package=None) -> List[float]:
        try:
            price_array = _package.array(prices)
            momentum = _package.zeros_like(price_array)
            for i in range(window, len(price_array)):
                momentum[i] = (price_array[i] - price_array[i-window]) / price_array[i-window]
            return momentum
        except AttributeError:
            # Fallback implementation
            momentum = [0.0] * len(prices)
            for i in range(window, len(prices)):
                momentum[i] = (prices[i] - prices[i-window]) / prices[i-window]
            return momentum

    @requires_package('scikit-learn')
    def _detect_clusters(self, volumes: List[float], _package=None) -> Dict:
        try:
            X = self.np.array(volumes).reshape(-1, 1)
            clustering = _package.cluster.DBSCAN(
                eps=self.np.std(volumes)*0.1,
                min_samples=5
            ).fit(X)
            return {'labels': clustering.labels_}
        except AttributeError:
            # Use fallback implementation
            return ScikitLearnFallback.dbscan(
                volumes,
                eps=NumpyFallback.std(volumes)*0.1,
                min_samples=5
            ) 