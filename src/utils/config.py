import json
from typing import Dict
import os
from dotenv import load_dotenv

def load_config(config_path: str) -> Dict:
    """Load configuration from JSON file and environment variables"""
    load_dotenv()  # Load environment variables from .env file
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Override with environment variables if they exist
        config["rpc_url"] = os.getenv("SOLANA_RPC_URL", config.get("rpc_url"))
        config["api_key"] = os.getenv("API_KEY", config.get("api_key"))
        config["twitter_api_key"] = os.getenv("TWITTER_API_KEY", config.get("twitter_api_key"))
        config["twitter_api_secret"] = os.getenv("TWITTER_API_SECRET", config.get("twitter_api_secret"))
        
        # Validate configuration
        required_fields = [
            "rpc_url",
            "api_key",
            "twitter_api_key",
            "twitter_api_secret"
        ]
        
        missing_fields = [field for field in required_fields if not config.get(field)]
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")
            
        return config
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in config file: {config_path}")