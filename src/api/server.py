from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
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
        await asyncio.sleep(60)  # Fetch every minute

@app.on_event("startup")
async def startup_event():
    logger.info("Starting token fetch background task")
    create_task(fetch_tokens_periodically())

# Initialize trading agent with config
trading_agent = TradingAgent({
    "rpc_url": rpc_url,
    "twitter_api_key": os.getenv("TWITTER_API_KEY"),
    "twitter_api_secret": os.getenv("TWITTER_API_SECRET"),
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

@app.get("/")
async def root():
    return FileResponse("src/static/index.html")

@app.get("/tokens")
async def get_tokens() -> List[TokenAnalysis]:
    """Get all tracked tokens and their analysis"""
    # Add a test token if none exist
    if not trading_agent.active_tokens:
        test_token = Token(
            address="test_token_address",
            name="Test Token",
            creator_address="test_creator"
        )
        # Initialize metrics
        test_token.metrics = TokenMetrics(
            sniper_count=2,
            bot_buyer_count=1,
            insider_count=0,
            natural_chart=True,
            social_sentiment=0.5
        )
        test_token.risk_score = 65.5
        test_token.trading_signal = TradingSignal.WAIT
        test_token.status = TokenStatus.APPROVED
        trading_agent.active_tokens[test_token.address] = test_token

    tokens = []
    for token in trading_agent.active_tokens.values():
        tokens.append(TokenAnalysis(
            address=token.address,
            name=token.name,
            risk_score=token.risk_score,
            trading_signal=token.trading_signal.value,
            status=token.status.value,
            metrics=token.metrics.__dict__,
            patterns=["example_pattern"],  # Simplified for testing
            last_updated=datetime.now()
        ))
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