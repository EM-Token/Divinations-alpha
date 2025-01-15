from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
import json
import os
from asyncio import create_task
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

from agents.trading_agent import TradingAgent
from models.token import Token, TokenStatus, TradingSignal
from models.metrics import TokenMetrics
from .websocket import websocket_manager

app = FastAPI(title="Trading Assistant API")

# Get RPC URL from environment
rpc_url = os.getenv("SOLANA_RPC_URL")
if not rpc_url:
    raise ValueError("SOLANA_RPC_URL environment variable is not set")

# Background task for token fetching
async def fetch_tokens_periodically():
    while True:
        try:
            await trading_agent.fetch_live_tokens()
        except Exception as e:
            logger.error(f"Error fetching tokens: {e}", exc_info=True)
        await asyncio.sleep(300)  # Fetch every 5 minutes

@app.on_event("startup")
async def startup_event():
    logger.info("Starting token fetch background task")
    create_task(fetch_tokens_periodically())

# Initialize trading agent with config
trading_agent = TradingAgent({
    "rpc_url": rpc_url,
    "twitter_api_key": os.getenv("TWITTER_API_KEY"),
    "twitter_api_secret": os.getenv("TWITTER_API_SECRET"),
    "birdeye_api_key": os.getenv("BIRDEYE_API_KEY"),
    "risk_threshold": 70,
    "min_confidence": 0.6
})

logger.info(f"Initialized with RPC URL: {rpc_url}")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for web interface
app.mount("/static", StaticFiles(directory="src/static"), name="static")

class TokenAnalysis(BaseModel):
    address: str
    name: str
    risk_score: float
    trading_signal: str
    status: str
    metrics: Dict
    patterns: List[str]
    last_updated: datetime

class TokenResponse(BaseModel):
    address: str
    name: str
    symbol: str
    logoURI: Optional[str]
    volume24hUSD: float
    price: float
    liquidity: float
    status: str
    patterns: List[str]
    risk_score: float
    trading_signal: str

@app.get("/")
async def root():
    return FileResponse("src/static/index.html")

@app.get("/tokens", response_model=List[TokenResponse])
async def get_tokens():
    """Get all tracked tokens and their analysis"""
    tokens = []
    for token in trading_agent.active_tokens.values():
        tokens.append({
            "address": token.address,
            "name": token.name,
            "symbol": token.symbol,
            "logoURI": token.logoURI,
            "volume24hUSD": token.volume24hUSD,
            "price": token.price,
            "liquidity": token.liquidity,
            "status": token.status.value,
            "patterns": ["example_pattern"],
            "risk_score": token.risk_score,
            "trading_signal": token.trading_signal.value
        })
    return tokens

@app.get("/tokens/{address}")
async def get_token(address: str) -> TokenAnalysis:
    """Get detailed analysis for a specific token"""
    token = trading_agent.active_tokens.get(address)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
        
    return TokenAnalysis(
        address=token.address,
        name=token.name,
        risk_score=token.risk_score,
        trading_signal=token.trading_signal.value,
        status=token.status.value,
        metrics=token.metrics.__dict__,
        patterns=await pattern_analyzer.analyze_patterns(
            await blockchain_data.get_price_history(token.address, token.creation_time),
            await blockchain_data.get_transactions(token.address, token.creation_time)
        ),
        last_updated=datetime.now()
    )

@app.get("/api/twitter-sentiment")
async def get_twitter_sentiment(symbol: str, name: str):
    """Get Twitter sentiment analysis for a token"""
    try:
        sentiment_data = await trading_agent.sentiment_analyzer.analyze_sentiment(symbol, name)
        return {
            "sentiment_score": sentiment_data.get("overall_sentiment", 0),
            "tweets": sentiment_data.get("tweets", [])
        }
    except Exception as e:
        logger.error(f"Error getting Twitter sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tokens/analyze")
async def analyze_token(address: str):
    """Trigger analysis for a specific token"""
    try:
        await trading_agent.analyze_token(address)
        return {"status": "success", "message": "Analysis completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle any incoming messages if needed
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

@app.post("/tokens/{address}/patterns")
async def notify_pattern(address: str, pattern: Dict):
    """Notify connected clients about detected patterns"""
    await websocket_manager.broadcast_pattern_alert({
        "token_address": address,
        "pattern": pattern
    })
    return {"status": "success"} 