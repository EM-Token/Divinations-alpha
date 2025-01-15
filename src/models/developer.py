from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime

@dataclass
class TokenHistory:
    token_address: str
    creation_date: datetime
    rug_pulled: bool
    max_price: float
    min_price: float
    current_status: str

@dataclass
class Developer:
    address: str
    first_seen: datetime
    total_tokens_created: int
    rug_pull_count: int
    token_history: List[TokenHistory]
    trust_score: float  # 0 to 100
    
    def calculate_trust_score(self) -> float:
        """
        Calculate trust score based on developer's history
        """
        if self.total_tokens_created == 0:
            return 50.0  # Neutral score for new developers
            
        # Higher weight for recent rug pulls
        rug_pull_ratio = self.rug_pull_count / self.total_tokens_created
        base_score = 100 * (1 - rug_pull_ratio)
        
        # Adjust score based on token history
        if self.rug_pull_count > 0:
            base_score *= 0.5  # Severe penalty for any rug pulls
            
        return max(0.0, min(100.0, base_score)) 