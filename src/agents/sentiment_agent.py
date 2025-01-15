from typing import List, Dict, Optional
import aiohttp
import asyncio
from datetime import datetime, timedelta
from textblob import TextBlob
from utils.twitter_client import TwitterClient
from dataclasses import dataclass
import logging
import base64
import json
import time

logger = logging.getLogger(__name__)

@dataclass
class SentimentResult:
    score: float  # -1 to 1
    confidence: float  # 0 to 1
    source: str
    timestamp: datetime
    text: str

class SentimentAnalyzer:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.bearer_token = None
        self.sentiment_cache = {}  # Cache for sentiment results
        self.cache_duration = 300  # 5 minutes in seconds
        self.last_twitter_call = 0  # Track last Twitter API call
        self.twitter_rate_limit = 300  # 5 minutes in seconds
        
    async def _get_bearer_token(self) -> str:
        """Get OAuth 2.0 Bearer Token from Twitter"""
        if self.bearer_token:
            return self.bearer_token
            
        try:
            # Encode credentials
            credentials = base64.b64encode(
                f"{self.api_key}:{self.api_secret}".encode()
            ).decode()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.twitter.com/oauth2/token",
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    data={"grant_type": "client_credentials"},
                    ssl=True
                ) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get bearer token: {await response.text()}")
                        return None
                        
                    data = await response.json()
                    self.bearer_token = data.get("access_token")
                    return self.bearer_token
                    
        except Exception as e:
            logger.error(f"Error getting bearer token: {e}")
            return None
        
    async def analyze_sentiment(self, symbol: str, name: str) -> Optional[Dict]:
        """Analyze social sentiment for a token"""
        try:
            # Check cache first
            cache_key = f"{symbol}:{name}"
            current_time = time.time()
            
            if cache_key in self.sentiment_cache:
                cached_result, timestamp = self.sentiment_cache[cache_key]
                if current_time - timestamp < self.cache_duration:
                    logger.debug(f"Using cached sentiment for {cache_key}")
                    return cached_result
            
            # Check Twitter rate limit
            if current_time - self.last_twitter_call < self.twitter_rate_limit:
                logger.warning("Twitter rate limit in effect, returning neutral sentiment")
                return {"overall_sentiment": 0.0, "tweets": []}
            
            # Get bearer token first
            bearer_token = await self._get_bearer_token()
            if not bearer_token:
                logger.warning("Twitter authentication failed, returning neutral sentiment")
                return {"overall_sentiment": 0.0, "tweets": []}
            
            # Search Twitter for mentions
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.twitter.com/2/tweets/search/recent",
                    params={
                        "query": f"({symbol} OR {name}) -is:retweet",
                        "max_results": 100
                    },
                    headers={
                        "Authorization": f"Bearer {bearer_token}"
                    }
                ) as response:
                    # Update last Twitter API call time
                    self.last_twitter_call = current_time
                    
                    if response.status != 200:
                        logger.error(f"Twitter API error: {await response.text()}")
                        if response.status == 429:  # Rate limit error
                            logger.warning("Twitter rate limit exceeded, using cached or neutral sentiment")
                            return self.sentiment_cache.get(cache_key, ({"overall_sentiment": 0.0, "tweets": []}, 0))[0]
                        return {"overall_sentiment": 0.0, "tweets": []}
                    
                    data = await response.json()
                    
                    if "data" not in data:
                        logger.warning(f"No tweets found for {symbol}")
                        return {"overall_sentiment": 0.0, "tweets": []}
                    
                    # Process tweets and calculate sentiment
                    tweets = []
                    total_sentiment = 0
                    
                    for tweet in data["data"]:
                        blob = TextBlob(tweet["text"])
                        sentiment = blob.sentiment.polarity
                        total_sentiment += sentiment
                        
                        tweets.append({
                            "text": tweet["text"],
                            "created_at": tweet.get("created_at", ""),
                            "sentiment": sentiment
                        })
                    
                    overall_sentiment = total_sentiment / len(tweets) if tweets else 0
                    
                    result = {
                        "overall_sentiment": overall_sentiment,
                        "tweets": tweets
                    }
                    
                    # Cache the result
                    self.sentiment_cache[cache_key] = (result, current_time)
                    return result
            
        except Exception as e:
            logger.error(f"Error analyzing Twitter sentiment: {e}")
            return None
        
    async def _analyze_twitter(self, search_terms: List[str]) -> Dict:
        """Analyze Twitter sentiment"""
        sentiments: List[SentimentResult] = []
        
        for term in search_terms:
            try:
                # Search recent tweets
                tweets = await self.twitter_client.search_tweets(term)
                
                for tweet in tweets:
                    # Skip retweets and replies
                    if tweet.get('referenced_tweets'):  # Skip retweets and replies
                        continue
                        
                    blob = TextBlob(tweet['text'])
                    sentiments.append(SentimentResult(
                        score=blob.sentiment.polarity,
                        confidence=blob.sentiment.subjectivity,
                        source="twitter",
                        timestamp=datetime.fromisoformat(tweet['created_at'].replace('Z', '+00:00')),
                        text=tweet['text']
                    ))
                    
            except Exception as e:
                print(f"Error analyzing Twitter sentiment: {e}")
                
        if not sentiments:
            return {"score": 0.0, "confidence": 0.0}
            
        # Calculate weighted average based on recency
        total_weight = 0
        weighted_sum = 0
        
        for sent in sentiments:
            age = datetime.now() - sent.timestamp
            weight = 1.0 / (1 + age.total_seconds() / 3600)  # Decay weight with age
            weighted_sum += sent.score * weight
            total_weight += weight
            
        return {
            "score": weighted_sum / total_weight if total_weight > 0 else 0,
            "confidence": min(1.0, len(sentiments) / 50),  # Scale with number of data points
            "sample_size": len(sentiments)
        }
        
    async def _analyze_news(self, search_terms: List[str]) -> Dict:
        """Analyze news sentiment using news APIs"""
        # Similar to Twitter analysis but for news sources
        # Implementation would depend on which news APIs you're using
        return {"score": 0.0, "confidence": 0.0}  # Placeholder
        
    async def _analyze_telegram(self, search_terms: List[str]) -> Dict:
        """Analyze Telegram sentiment"""
        # Implementation would require Telegram API integration
        return {"score": 0.0, "confidence": 0.0}  # Placeholder 