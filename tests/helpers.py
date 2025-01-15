from datetime import datetime, timedelta
import numpy as np
from typing import List, Dict

def generate_test_price_data(
    duration_hours: int = 24,
    interval_minutes: int = 5,
    base_price: float = 100,
    volatility: float = 0.1
) -> List[Dict]:
    """Generate synthetic price data for testing"""
    data_points = int((duration_hours * 60) / interval_minutes)
    base_time = datetime.now() - timedelta(hours=duration_hours)
    
    prices = []
    current_price = base_price
    
    for i in range(data_points):
        current_time = base_time + timedelta(minutes=i*interval_minutes)
        price_change = np.random.normal(0, volatility)
        current_price *= (1 + price_change)
        
        prices.append({
            'timestamp': current_time,
            'open': current_price * (1 + np.random.normal(0, 0.001)),
            'high': current_price * (1 + abs(np.random.normal(0, 0.002))),
            'low': current_price * (1 - abs(np.random.normal(0, 0.002))),
            'close': current_price,
            'volume': abs(np.random.normal(1000, 200))
        })
    
    return prices 