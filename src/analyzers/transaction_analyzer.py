from typing import List, Dict, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from models.token import Token

@dataclass
class TransactionPattern:
    address: str
    buy_count: int
    sell_count: int
    total_volume: float
    first_tx_time: datetime
    last_tx_time: datetime
    avg_tx_size: float

class TransactionAnalyzer:
    def __init__(self):
        self.known_bot_patterns: List[Dict] = [
            {"min_tx_per_minute": 10, "max_size_variance": 0.1},
            {"min_buy_sell_ratio": 5, "min_transactions": 20}
        ]
        self.known_bot_addresses: Set[str] = set()  # Load from database
        self.sniper_threshold_seconds = 120  # 2 minutes after creation
        
    async def analyze_transactions(self, token: Token, transactions: List[Dict]) -> Dict:
        """Analyze transaction patterns to detect bots and snipers"""
        creation_time = token.creation_time
        address_patterns: Dict[str, TransactionPattern] = {}
        
        # Build transaction patterns for each address
        for tx in transactions:
            pattern = self._update_address_pattern(address_patterns, tx)
            address_patterns[tx['address']] = pattern
        
        # Detect different types of actors
        snipers = self._detect_snipers(address_patterns, creation_time)
        bots = self._detect_bots(address_patterns)
        insiders = self._detect_insiders(address_patterns, creation_time)
        
        return {
            "sniper_count": len(snipers),
            "bot_count": len(bots),
            "insider_count": len(insiders),
            "suspicious_addresses": list(snipers | bots | insiders)
        }
    
    def _update_address_pattern(self, patterns: Dict[str, TransactionPattern], tx: Dict) -> TransactionPattern:
        """Update transaction pattern for an address"""
        address = tx['address']
        if address not in patterns:
            patterns[address] = TransactionPattern(
                address=address,
                buy_count=0,
                sell_count=0,
                total_volume=0,
                first_tx_time=tx['timestamp'],
                last_tx_time=tx['timestamp'],
                avg_tx_size=0
            )
        
        pattern = patterns[address]
        if tx['type'] == 'buy':
            pattern.buy_count += 1
        else:
            pattern.sell_count += 1
            
        pattern.total_volume += tx['amount']
        pattern.last_tx_time = max(pattern.last_tx_time, tx['timestamp'])
        pattern.avg_tx_size = pattern.total_volume / (pattern.buy_count + pattern.sell_count)
        
        return pattern
    
    def _detect_snipers(self, patterns: Dict[str, TransactionPattern], creation_time: datetime) -> Set[str]:
        """Detect addresses that sniped the token early"""
        snipers = set()
        sniper_window = creation_time + timedelta(seconds=self.sniper_threshold_seconds)
        
        for address, pattern in patterns.items():
            if (pattern.first_tx_time <= sniper_window and 
                pattern.buy_count > 0 and 
                pattern.total_volume > 0):  # Add minimum volume threshold
                snipers.add(address)
                
        return snipers
    
    def _detect_bots(self, patterns: Dict[str, TransactionPattern]) -> Set[str]:
        """Detect bot-like trading patterns"""
        bots = set()
        
        for address, pattern in patterns.items():
            if address in self.known_bot_addresses:
                bots.add(address)
                continue
                
            # Check for high-frequency trading
            duration = (pattern.last_tx_time - pattern.first_tx_time).total_seconds() / 60
            tx_per_minute = (pattern.buy_count + pattern.sell_count) / max(duration, 1)
            
            # Check for uniform transaction sizes
            if tx_per_minute >= self.known_bot_patterns[0]["min_tx_per_minute"]:
                bots.add(address)
                
        return bots
    
    def _detect_insiders(self, patterns: Dict[str, TransactionPattern], creation_time: datetime) -> Set[str]:
        """Detect potential insider addresses"""
        insiders = set()
        insider_window = creation_time + timedelta(minutes=2)
        
        for address, pattern in patterns.items():
            if (pattern.first_tx_time <= insider_window and 
                pattern.total_volume > 0):  # Add significant volume threshold
                
                # Check if they sold quickly after buying
                if pattern.sell_count > 0:
                    sell_delay = (pattern.last_tx_time - pattern.first_tx_time).total_seconds()
                    if sell_delay < 300:  # 5 minutes
                        insiders.add(address)
                
        return insiders 