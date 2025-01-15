import asyncio
import json
from typing import Dict
from data.blockchain_listener import BlockchainListener
from data.blockchain_data import BlockchainDataFetcher
from agents.trading_agent import TradingAgent
from utils.config import load_config

class TradingAssistant:
    def __init__(self, config_path: str = "config.json"):
        self.config = load_config(config_path)
        self.blockchain_data = BlockchainDataFetcher(
            self.config["rpc_url"],
            self.config["api_key"]
        )
        self.trading_agent = TradingAgent(self.config)
        self.blockchain_listener = BlockchainListener(
            self.config["rpc_url"],
            self.process_new_token
        )

    async def start(self):
        """Start the trading assistant"""
        print("Starting Trading Assistant...")
        
        # Start blockchain monitoring
        await self.blockchain_listener.start_monitoring()

    async def process_new_token(self, token_data: Dict):
        """Process newly discovered tokens"""
        try:
            print(f"New token discovered: {token_data['name']}")
            await self.trading_agent.process_new_token(token_data)
            
            # Get the analyzed token
            token = self.trading_agent.active_tokens[token_data['address']]
            
            # Log analysis results
            print(f"Analysis complete for {token.name}:")
            print(f"Risk Score: {token.risk_score}")
            print(f"Trading Signal: {token.trading_signal.value}")
            print(f"Status: {token.status.value}")
            print("Metrics:")
            print(f"- Sniper Count: {token.metrics.sniper_count}")
            print(f"- Bot Buyers: {token.metrics.bot_buyer_count}")
            print(f"- Insider Count: {token.metrics.insider_count}")
            print(f"- Natural Chart: {token.metrics.natural_chart}")
            print(f"- Social Sentiment: {token.metrics.social_sentiment}")
            
        except Exception as e:
            print(f"Error processing token: {e}")

async def main():
    # Load configuration
    assistant = TradingAssistant()
    
    try:
        await assistant.start()
        
        # Keep the program running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 