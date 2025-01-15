import pytest
from fastapi.testclient import TestClient
import os
import json
from pathlib import Path
from typing import Dict
import sys

from src.api.server import app
from src.models.token import Token, TokenStatus
from src.agents.trading_agent import TradingAgent

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def test_config() -> Dict:
    return {
        "rpc_url": "test_rpc_url",
        "api_key": "test_api_key",
        "twitter_api_key": "test_twitter_key",
        "twitter_api_secret": "test_twitter_secret",
        "risk_threshold": 70,
        "min_confidence": 0.6
    }

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_token():
    return Token(
        address="test_address",
        name="Test Token",
        creator_address="creator_address"
    )

@pytest.fixture
def trading_agent(test_config):
    return TradingAgent(test_config) 