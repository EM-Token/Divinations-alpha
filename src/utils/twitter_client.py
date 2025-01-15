from typing import Dict, List, Optional
import aiohttp
import base64
from PIL import Image
import io
import hmac
import hashlib
import time
import urllib.parse

class TwitterClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.twitter.com/2"
        self.session = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self._get_auth_headers())
        return self.session

    def _get_auth_headers(self) -> Dict[str, str]:
        timestamp = str(int(time.time()))
        nonce = base64.b64encode(str(int(time.time())).encode()).decode()
        
        # Create signature base string
        params = {
            'oauth_consumer_key': self.api_key,
            'oauth_nonce': nonce,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': timestamp,
            'oauth_version': '1.0'
        }
        
        # Create signature
        base_string = '&'.join([
            'GET',
            urllib.parse.quote(self.base_url, safe=''),
            urllib.parse.quote('&'.join([
                f"{k}={urllib.parse.quote(v, safe='')}"
                for k, v in sorted(params.items())
            ]), safe='')
        ])
        
        signing_key = f"{urllib.parse.quote(self.api_secret, safe='')}&"
        signature = base64.b64encode(
            hmac.new(
                signing_key.encode(),
                base_string.encode(),
                hashlib.sha1
            ).digest()
        ).decode()
        
        # Create authorization header
        auth_header = (
            'OAuth '
            f'oauth_consumer_key="{urllib.parse.quote(self.api_key)}", '
            f'oauth_nonce="{urllib.parse.quote(nonce)}", '
            'oauth_signature_method="HMAC-SHA1", '
            f'oauth_timestamp="{timestamp}", '
            f'oauth_signature="{urllib.parse.quote(signature)}", '
            'oauth_version="1.0"'
        )
        
        return {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }

    async def search_tweets(self, query: str, max_results: int = 100) -> List[Dict]:
        session = await self.get_session()
        params = {
            'query': query,
            'max_results': str(max_results),
            'tweet.fields': 'created_at,public_metrics'
        }
        
        async with session.get(f"{self.base_url}/tweets/search/recent", params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('data', [])
            else:
                raise Exception(f"Twitter API error: {await response.text()}")

    def validate_media(self, media_data: bytes) -> bool:
        """Validate media using PIL instead of imghdr"""
        try:
            img = Image.open(io.BytesIO(media_data))
            return img.format.lower() in ['png', 'jpeg', 'jpg', 'gif']
        except Exception:
            return False 