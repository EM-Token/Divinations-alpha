import asyncio
from src.api.server import app
import uvicorn
from pathlib import Path
from utils.logging import setup_logging
import logging

# Set up root logger
logger = logging.getLogger(__name__)

def create_required_directories():
    """Create necessary directories if they don't exist"""
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    Path("src/static").mkdir(exist_ok=True)

def main():
    setup_logging()  # Configure logging for all modules
    create_required_directories()
    logger.info("Starting Trading Assistant...")
    
    # Run the FastAPI server
    uvicorn.run(
        "src.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main() 