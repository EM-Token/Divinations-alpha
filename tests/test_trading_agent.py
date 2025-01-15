import pytest
from src.models.token import Token, TokenStatus, TradingSignal

async def test_process_new_token(trading_agent, sample_token):
    token_data = {
        "address": sample_token.address,
        "name": sample_token.name,
        "creator_address": sample_token.creator_address
    }
    
    await trading_agent.process_new_token(token_data)
    
    assert sample_token.address in trading_agent.active_tokens
    assert trading_agent.active_tokens[sample_token.address].status in [TokenStatus.APPROVED, TokenStatus.SUSPICIOUS]

async def test_risk_score_calculation(trading_agent):
    transaction_analysis = {
        "sniper_count": 5,
        "bot_count": 3,
        "insider_count": 2
    }
    
    chart_analysis = {
        "natural_chart": False,
        "patterns": ["pump_and_dump"]
    }
    
    sentiment_analysis = {
        "overall_sentiment": -0.5
    }
    
    risk_score = trading_agent._calculate_risk_score(
        transaction_analysis,
        chart_analysis,
        sentiment_analysis
    )
    
    assert 0 <= risk_score <= 100
    assert risk_score > 50  # Should be high risk given the inputs 