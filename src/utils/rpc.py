import asyncio
from typing import Dict, Optional
import aiohttp
import logging

logger = logging.getLogger(__name__)

async def make_rpc_call(url: str, method: str, params: list, retries: int = 3, delay: int = 1) -> Optional[Dict]:
    """Make RPC call with retries"""
    logger.info(f"Making RPC call to {url} with method {method}")
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                request_data = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params
                }
                logger.debug(f"Request data: {request_data}")
                async with session.post(
                    url,
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        logger.debug(f"Response data: {response_data}")
                        return response_data
                    else:
                        error_text = await response.text()
                        logger.error(f"RPC error (attempt {attempt + 1}/{retries}): {error_text}")
        except Exception as e:
            logger.error(f"RPC call failed (attempt {attempt + 1}/{retries}): {e}")
        
        if attempt < retries - 1:
            await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
    
    logger.error(f"All {retries} attempts failed for method {method}")
    return None 