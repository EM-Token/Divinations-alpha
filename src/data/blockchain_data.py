from typing import List, Dict, Optional
import aiohttp
from datetime import datetime, timedelta

class BlockchainDataFetcher:
    def __init__(self, rpc_url: str, api_key: str):
        self.rpc_url = rpc_url
        self.api_key = api_key
        self.session = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })
        return self.session

    async def get_transactions(self, token_address: str, start_time: datetime) -> List[Dict]:
        """Fetch token transactions from blockchain"""
        session = await self.get_session()
        
        try:
            # Fetch from Solana or other blockchain
            params = {
                "method": "getSignaturesForAddress",
                "params": [
                    token_address,
                    {
                        "limit": 1000,
                        "until": start_time.isoformat()
                    }
                ],
                "id": 1,
                "jsonrpc": "2.0"
            }
            
            async with session.post(self.rpc_url, json=params) as response:
                data = await response.json()
                signatures = data.get("result", [])
                
                # Fetch transaction details for each signature
                transactions = []
                for sig in signatures:
                    tx_data = await self._get_transaction_details(sig["signature"])
                    if tx_data:
                        transactions.append(tx_data)
                        
                return transactions
                
        except Exception as e:
            print(f"Error fetching transactions: {e}")
            return []

    async def get_price_history(self, token_address: str, 
                              start_time: datetime,
                              interval: str = "5m") -> List[Dict]:
        """Fetch token price history"""
        session = await self.get_session()
        
        try:
            # You might want to use a DEX API or price aggregator
            params = {
                "token_address": token_address,
                "start_time": int(start_time.timestamp()),
                "end_time": int(datetime.now().timestamp()),
                "interval": interval
            }
            
            # Example using a DEX API endpoint
            async with session.get(f"{self.rpc_url}/v1/prices", params=params) as response:
                data = await response.json()
                return self._format_price_data(data)
                
        except Exception as e:
            print(f"Error fetching price history: {e}")
            return []

    async def _get_transaction_details(self, signature: str) -> Optional[Dict]:
        """Fetch detailed transaction information"""
        session = await self.get_session()
        
        try:
            params = {
                "method": "getTransaction",
                "params": [
                    signature,
                    "json"
                ],
                "id": 1,
                "jsonrpc": "2.0"
            }
            
            async with session.post(self.rpc_url, json=params) as response:
                data = await response.json()
                return self._format_transaction_data(data.get("result", {}))
                
        except Exception as e:
            print(f"Error fetching transaction details: {e}")
            return None

    def _format_transaction_data(self, tx_data: Dict) -> Dict:
        """Format raw transaction data into standardized format"""
        return {
            "signature": tx_data.get("transaction", {}).get("signatures", [])[0],
            "timestamp": datetime.fromtimestamp(tx_data.get("blockTime", 0)),
            "type": self._determine_transaction_type(tx_data),
            "amount": self._extract_amount(tx_data),
            "address": self._extract_address(tx_data)
        }

    def _format_price_data(self, price_data: Dict) -> List[Dict]:
        """Format raw price data into standardized format"""
        return [{
            "timestamp": datetime.fromtimestamp(candle["time"]),
            "open": float(candle["open"]),
            "high": float(candle["high"]),
            "low": float(candle["low"]),
            "close": float(candle["close"]),
            "volume": float(candle["volume"])
        } for candle in price_data.get("candles", [])]

    def _determine_transaction_type(self, tx_data: Dict) -> str:
        """Determine if transaction is buy or sell"""
        # Implementation depends on specific blockchain
        return "buy"  # Placeholder

    def _extract_amount(self, tx_data: Dict) -> float:
        """Extract transaction amount"""
        # Implementation depends on specific blockchain
        return 0.0  # Placeholder

    def _extract_address(self, tx_data: Dict) -> str:
        """Extract relevant address from transaction"""
        # Implementation depends on specific blockchain
        return ""  # Placeholder 