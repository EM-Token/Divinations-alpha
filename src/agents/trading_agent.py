from typing import List, Dict, Optional
from datetime import datetime
import asyncio
from models.token import Token, TokenStatus, TradingSignal
from models.developer import Developer
from analyzers.transaction_analyzer import TransactionAnalyzer
from analyzers.chart_analyzer import ChartAnalyzer
from .sentiment_agent import SentimentAnalyzer
from api.websocket import websocket_manager
import aiohttp
import logging
import base58
from utils.rpc import make_rpc_call
import time

logger = logging.getLogger(__name__)

class TradingAgent:
    def __init__(self, config: Dict):
        if not config.get("rpc_url"):
            raise ValueError("RPC URL is required")
        if not config.get("birdeye_api_key"):
            raise ValueError("Birdeye API key is required")
        
        self.transaction_analyzer = TransactionAnalyzer()
        self.chart_analyzer = ChartAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer(
            config["twitter_api_key"],
            config["twitter_api_secret"]
        )
        
        self.active_tokens: Dict[str, Token] = {}
        self.risk_threshold = config.get("risk_threshold", 70)
        self.min_confidence = config.get("min_confidence", 0.6)
        self.rpc_url = config["rpc_url"]
        self.birdeye_api_key = config["birdeye_api_key"]
        self.last_fetch_time = None
        
    async def process_new_token(self, token_data: Dict):
        """Process a newly discovered token"""
        token = Token(
            address=token_data["address"],
            name=token_data["name"],
            creator_address=token_data["creator_address"]
        )
        
        self.active_tokens[token.address] = token
        await self.analyze_token(token)
        
    async def analyze_token(self, token: Token):
        """Run comprehensive analysis on a token"""
        # Notify clients that analysis is starting
        await websocket_manager.broadcast_token_update({
            "address": token.address,
            "name": token.name,
            "status": TokenStatus.ANALYZING.value,
            "message": "Analyzing token..."
        })
        
        token.status = TokenStatus.ANALYZING
        
        # Get transaction and price data
        transactions = await self._get_transactions(token)
        price_history = await self._get_price_history(token)
        
        # Run all analyses in parallel
        try:
            # Run analyses separately to handle empty data
            transaction_analysis = await self.transaction_analyzer.analyze_transactions(token, transactions) if transactions else {
                "sniper_count": 0,
                "bot_count": 0,
                "insider_count": 0
            }
            
            chart_analysis = await self.chart_analyzer.analyze_chart(price_history) if price_history else {
                "natural_chart": True,
                "patterns": []
            }
            
            # Don't automatically analyze sentiment
            sentiment_analysis = {"overall_sentiment": 0.0}
        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            transaction_analysis = {"sniper_count": 0, "bot_count": 0, "insider_count": 0}
            chart_analysis = {"natural_chart": True, "patterns": []}
            sentiment_analysis = {"overall_sentiment": 0.0}
        
        # Update token metrics
        token.metrics.sniper_count = transaction_analysis["sniper_count"]
        token.metrics.bot_buyer_count = transaction_analysis["bot_count"]
        token.metrics.insider_count = transaction_analysis["insider_count"]
        token.metrics.natural_chart = chart_analysis["natural_chart"]
        token.metrics.social_sentiment = sentiment_analysis["overall_sentiment"]
        
        # Calculate risk score
        token.risk_score = self._calculate_risk_score(
            transaction_analysis,
            chart_analysis,
            sentiment_analysis
        )
        
        # Determine trading signal
        token.trading_signal = self._determine_trading_signal(token)
        token.status = TokenStatus.APPROVED if token.risk_score < self.risk_threshold else TokenStatus.SUSPICIOUS
        
        # Notify connected clients about the analysis
        await websocket_manager.broadcast_token_update({
            "address": token.address,
            "name": token.name,
            "risk_score": token.risk_score,
            "trading_signal": token.trading_signal.value,
            "status": token.status.value,
            "metrics": token.metrics.__dict__,
            "logo_url": token.logo_url if hasattr(token, 'logo_url') else None
        })
        
        # Notify about detected patterns
        for pattern in chart_analysis.get("patterns", []):
            await websocket_manager.broadcast_pattern_alert({
                "token_address": token.address,
                "pattern": {
                    "type": pattern,
                    "confidence": 1.0,  # Default confidence
                    "description": f"Detected {pattern} pattern"
                }
            })
        
    def _calculate_risk_score(self, 
                            transaction_analysis: Dict,
                            chart_analysis: Dict,
                            sentiment_analysis: Dict) -> float:
        """Calculate overall risk score"""
        risk_score = 50.0  # Start neutral
        
        # Transaction risks
        risk_score += transaction_analysis["sniper_count"] * 2
        risk_score += transaction_analysis["bot_count"] * 1.5
        risk_score += transaction_analysis["insider_count"] * 3
        
        # Chart risks
        if not chart_analysis["natural_chart"]:
            risk_score += 20
        
        for pattern in chart_analysis["patterns"]:
            if pattern == "pump_and_dump":
                risk_score += 15
            elif pattern == "wash_trading":
                risk_score += 10
                
        # Sentiment risks
        sentiment_score = sentiment_analysis["overall_sentiment"]
        if sentiment_score < 0:
            risk_score += abs(sentiment_score) * 10
            
        return min(100.0, max(0.0, risk_score))
        
    def _determine_trading_signal(self, token: Token) -> TradingSignal:
        """Determine trading signal based on analysis"""
        if token.risk_score >= self.risk_threshold:
            return TradingSignal.SELL
            
        if token.metrics.social_sentiment > 0.5 and token.metrics.natural_chart:
            return TradingSignal.BUY
            
        return TradingSignal.WAIT
        
    async def _get_transactions(self, token: Token) -> List[Dict]:
        """Fetch token transactions from blockchain"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://public-api.birdeye.so/defi/v2/token/txs",
                    params={
                        "address": token.address,
                        "chain": "solana",
                        "type": "swap",
                        "offset": 0,
                        "limit": 100
                    },
                    headers={
                        "X-API-KEY": self.birdeye_api_key,
                        "accept": "*/*"
                    }
                ) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch transactions: {await response.text()}")
                        return []
                        
                    data = await response.json()
                    if not data.get("success"):
                        logger.debug(f"No transaction data available yet for {token.address}")
                        return []
                    
                    transactions = data.get("data", {}).get("items", [])
                    logger.info(f"Found {len(transactions)} transactions for {token.address}")
                    return transactions
        except Exception as e:
            logger.error(f"Error fetching transactions: {e}")
            return []
        
    async def _get_price_history(self, token: Token) -> List[Dict]:
        """Fetch token price history"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://public-api.birdeye.so/defi/v2/price/history",
                    params={
                        "token": token.address,
                        "chain": "solana",
                        "interval": "1H",
                        "limit": 24
                    },
                    headers={
                        "X-API-KEY": self.birdeye_api_key,
                        "accept": "application/json"
                    }
                ) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch price history: {await response.text()}")
                        return []
                        
                    data = await response.json()
                    return data.get("data", {}).get("items", [])
        except Exception as e:
            logger.error(f"Error fetching price history: {e}")
            return []
        
    async def fetch_live_tokens(self):
        """Fetch trending tokens from Birdeye"""
        logger.info("Fetching trending tokens from Birdeye...")
        
        if not self.birdeye_api_key:
            logger.error("No Birdeye API key configured")
            return
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://public-api.birdeye.so/defi/token_trending",
                    params={
                        "chain": "solana",
                        "page": 1,
                        "perPage": 20,
                        "sortBy": "v24hUSD",
                        "sortOrder": "desc",
                        "timeframe": "1H"
                    },
                    headers={
                        "X-API-KEY": self.birdeye_api_key,
                        "accept": "*/*"
                    }
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Birdeye API error: {error_text}")
                        logger.error(f"Status code: {response.status}")
                        logger.error(f"Headers used: {response.request_info.headers}")
                        return
                        
                    data = await response.json()
            
            if data.get("success") and isinstance(data.get("data", {}).get("tokens"), list):
                tokens = data["data"]["tokens"]
                tokens_with_logos = [
                    token for token in tokens 
                    if token.get("logoURI")
                ]
                
                for token in tokens_with_logos:
                    try:
                        token_address = token.get("address")
                        if not token_address:
                            continue
                            
                        token_data = {
                            "address": token_address,
                            "name": token.get("name", f"Token {token_address[:8]}"),
                            "creator_address": "Unknown",
                            "symbol": token.get("symbol") or "",
                            "description": f"24h Volume: ${token.get('volume24hUSD', 0):,.2f} | Price: ${token.get('price', 0):,.6f}",
                            "logoURI": token.get("logoURI"),
                            "volume24hUSD": token.get("volume24hUSD", 0),
                            "price": token.get("price", 0),
                            "liquidity": token.get("liquidity", 0),
                            "status": TokenStatus.NEW.value,
                            "patterns": ["example_pattern"],
                            "risk_score": 0,
                            "trading_signal": TradingSignal.WAIT.value
                        }
                        
                        # Only require address to be present
                        if not token_data["address"]:
                            logger.warning("Skipping token with no address")
                            continue
                        
                        # Log token data for debugging
                        logger.debug(f"Raw token data: {token}")
                        logger.info(f"Processing token: {token_data}")
                        await self.process_new_token(token_data)
                    except Exception as e:
                        logger.error(f"Error processing token {token.get('address', 'unknown')}: {e}", exc_info=True)
            else:
                logger.error(f"Invalid response from Birdeye: {data}")
        except Exception as e:
            logger.error(f"Error fetching live tokens: {e}", exc_info=True) 