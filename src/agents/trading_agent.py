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

logger = logging.getLogger(__name__)

class TradingAgent:
    def __init__(self, config: Dict):
        if not config.get("rpc_url"):
            raise ValueError("RPC URL is required")
        
        self.transaction_analyzer = TransactionAnalyzer()
        self.chart_analyzer = ChartAnalyzer()
        self.sentiment_analyzer = SentimentAnalyzer(
            config["twitter_api_key"],
            config["twitter_api_secret"]
        )
        
        self.active_tokens: Dict[str, Token] = {}
        self.risk_threshold = config.get("risk_threshold", 70)
        self.min_confidence = config.get("min_confidence", 0.6)
        # Format RPC URL
        rpc_url = str(config["rpc_url"]).strip()
        if not rpc_url.startswith('http'):
            rpc_url = f"https://{rpc_url}"
        logger.info(f"Using RPC URL: {rpc_url}")
        self.rpc_url = rpc_url
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
        token.status = TokenStatus.ANALYZING
        
        # Run all analyses in parallel
        transaction_analysis, chart_analysis, sentiment_analysis = await asyncio.gather(
            self.transaction_analyzer.analyze_transactions(token, await self._get_transactions(token)),
            self.chart_analyzer.analyze_chart(await self._get_price_history(token)),
            self.sentiment_analyzer.analyze_sentiment(token.symbol, token.name)
        )
        
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
            "metrics": token.metrics.__dict__
        })
        
        # Notify about detected patterns
        for pattern in patterns:
            await websocket_manager.broadcast_pattern_alert({
                "token_address": token.address,
                "pattern": pattern.__dict__
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
        # Implementation depends on blockchain API
        pass
        
    async def _get_price_history(self, token: Token) -> List[Dict]:
        """Fetch token price history"""
        # Implementation depends on price data source
        pass 
        
    async def fetch_live_tokens(self):
        """Fetch recent token transactions from Solana"""
        logger.info("Fetching live tokens from Solana...")
        
        if not self.rpc_url:
            logger.error("No RPC URL configured")
            return
        
        try:
            logger.info(f"Making RPC call to {self.rpc_url}")
            # Get recent signatures first
            response = await make_rpc_call(
                self.rpc_url,
                "getSignaturesForAddress",
                [
                    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                    {
                        "limit": 10,
                        "commitment": "confirmed"
                    }
                ]
            )

            if not response:
                logger.error("No response received from RPC call")
                return

            logger.debug(f"Raw RPC response: {response}")
            
            if not isinstance(response, dict):
                logger.error(f"Unexpected response type: {type(response)}")
                return
                
            data = response
            logger.info(f"Received response from Solana: {data}")
            
            if "result" in data and isinstance(data["result"], list):
                logger.info(f"Found {len(data['result'])} transactions")
                for sig_info in data['result']:
                    try:
                        if not sig_info or not isinstance(sig_info, dict):
                            logger.warning("Invalid signature info format")
                            continue
                            
                        signature = sig_info.get('signature')
                        if not signature:
                            logger.warning("Missing signature in transaction info")
                            continue
                            
                        # Get transaction details
                        tx_response = await make_rpc_call(
                            self.rpc_url,
                            "getTransaction",
                            [
                                signature,
                                {
                                    "encoding": "jsonParsed",
                                    "maxSupportedTransactionVersion": 0
                                }
                            ]
                        )
                        
                        if not tx_response:
                            logger.warning(f"No response for transaction {signature}")
                            continue
                            
                        if not isinstance(tx_response, dict):
                            logger.warning(f"Invalid response type for transaction {signature}")
                            continue
                            
                        tx_result = tx_response.get("result")
                        if not tx_result or not isinstance(tx_result, dict):
                            logger.warning(f"No result data for transaction {signature}")
                            continue
                        
                        tx_meta = tx_result.get('meta')
                        if not tx_meta or not isinstance(tx_meta, dict):
                            logger.warning(f"No meta data for transaction {signature}")
                            continue
                            
                        post_balances = tx_meta.get('postTokenBalances')
                        if not post_balances or not isinstance(post_balances, list):
                            logger.debug(f"No token balances in transaction {signature}")
                            continue
                            
                        # Extract token data from transaction
                        token_address = None
                        creator_address = None
                        
                        # Find the new token mint
                        for balance in post_balances:
                            if isinstance(balance, dict) and balance.get('mint'):
                                token_address = balance['mint']
                                break
                                
                        # Get creator from the first account
                        message = tx_result.get('transaction', {}).get('message', {})
                        if isinstance(message, dict) and message.get('accountKeys'):
                            account_keys = message['accountKeys']
                            if isinstance(account_keys, list) and len(account_keys) > 0:
                                creator_address = account_keys[0]
                            
                        if not token_address or not creator_address:
                            logger.debug(f"Missing token or creator address in transaction {signature}")
                            continue
                            
                        token_data = {
                            "address": token_address,
                            "name": f"Token {token_address[:8] if token_address else 'Unknown'}",
                            "creator_address": creator_address,
                            "symbol": "",
                            "description": ""
                        }
                        
                        if not all(token_data.values()):
                            logger.warning(f"Skipping token with incomplete data: {token_data}")
                            continue
                            
                        logger.info(f"Processing token: {token_data}")
                        await self.process_new_token(token_data)
                    except Exception as e:
                        logger.error(f"Error processing transaction {sig_info.get('signature', 'unknown')}: {e}", exc_info=True)
            else:
                logger.error(f"No results in response: {data}")
        except Exception as e:
            logger.error(f"Error fetching live tokens: {e}", exc_info=True) 