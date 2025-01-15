import asyncio
import aiohttp
import json
from datetime import datetime

async def test_token_analysis():
    # Test data
    test_token = {
        "address": "test_token_address",
        "name": "Test Token",
        "creator_address": "creator_address",
        "symbol": "TEST"
    }
    
    # Send to API
    async with aiohttp.ClientSession() as session:
        async with session.post(
            'http://localhost:8000/tokens/analyze',
            json=test_token
        ) as response:
            result = await response.json()
            print("Analysis result:", json.dumps(result, indent=2))

        # Get token details
        async with session.get(
            f'http://localhost:8000/tokens/{test_token["address"]}'
        ) as response:
            details = await response.json()
            print("\nToken details:", json.dumps(details, indent=2))

if __name__ == "__main__":
    asyncio.run(test_token_analysis()) 