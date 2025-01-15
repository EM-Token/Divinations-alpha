from dataclasses import dataclass

@dataclass
class TokenMetrics:
    sniper_count: int = 0
    bot_buyer_count: int = 0
    insider_count: int = 0
    natural_chart: bool = True
    social_sentiment: float = 0.0 