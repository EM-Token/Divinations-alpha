import pytest
from datetime import datetime, timedelta
import numpy as np
from src.analyzers.pattern_analyzer import PatternAnalyzer

@pytest.fixture
def pattern_analyzer():
    return PatternAnalyzer()

@pytest.fixture
def sample_price_data():
    base_time = datetime.now()
    prices = []
    for i in range(100):
        prices.append({
            'timestamp': base_time + timedelta(minutes=5*i),
            'close': 100 + np.sin(i/10) * 10,  # Create a sine wave pattern
            'volume': 1000 + np.random.normal(0, 100)
        })
    return prices

async def test_pump_dump_detection(pattern_analyzer, sample_price_data):
    # Inject a pump and dump pattern
    pump_start = 50
    for i in range(5):
        sample_price_data[pump_start + i]['close'] *= 1.2  # 20% increase
        sample_price_data[pump_start + i]['volume'] *= 3   # 3x volume
    for i in range(5):
        sample_price_data[pump_start + 5 + i]['close'] *= 0.7  # 30% decrease
    
    patterns = await pattern_analyzer._detect_pump_dump(sample_price_data, sample_price_data)
    
    assert len(patterns) > 0
    assert any(p.pattern_type == "pump_and_dump" for p in patterns)
    
async def test_wash_trading_detection(pattern_analyzer, sample_price_data):
    # Inject wash trading pattern
    wash_start = 30
    for i in range(10):
        sample_price_data[wash_start + i]['volume'] = 1000  # Identical volumes
    
    patterns = await pattern_analyzer._detect_wash_trading(sample_price_data, sample_price_data)
    
    assert len(patterns) > 0
    assert any(p.pattern_type == "wash_trading" for p in patterns) 