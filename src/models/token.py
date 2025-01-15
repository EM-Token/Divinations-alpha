from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum

class TokenStatus(Enum):
    NEW = "new"
    ANALYZING = "analyzing"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPICIOUS = "suspicious"

class TradingSignal(Enum):
    BUY = "buy"
    SELL = "sell"
    WAIT = "wait"

@dataclass
class TokenMetrics:
    volume_5m: float = 0.0
    sniper_count: int = 0
    bot_buyer_count: int = 0
    insider_count: int = 0
    dev_selling: bool = False
    natural_chart: bool = True
    social_sentiment: float = 0.0  # -1 to 1

@dataclass
class Token:
    address: str
    name: str
    creator_address: str
    symbol: str = ""
    description: str = ""
    status: TokenStatus = TokenStatus.NEW
    risk_score: float = 0.0
    trading_signal: TradingSignal = TradingSignal.WAIT
    metrics: TokenMetrics = field(default_factory=TokenMetrics)
    creation_time: datetime = field(default_factory=datetime.now) 