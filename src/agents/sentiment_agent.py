from typing import List, Dict, Optional
import aiohttp
import asyncio
from datetime import datetime, timedelta
from textblob import TextBlob
from utils.twitter_client import TwitterClient
from dataclasses import dataclass

@dataclass
class SentimentResult:
    score: float  # -1 to 1
    confidence: float  # 0 to 1
    source: str
    timestamp: datetime
    text: str

class SentimentAnalyzer:
    def __init__(self, twitter_api_key: str, twitter_api_secret: str):
        self.twitter_client = TwitterClient(twitter_api_key, twitter_api_secret)
        self.sentiment_cache = {}
        self.cache_duration = timedelta(minutes=5)
        
    async def analyze_sentiment(self, token_symbol: str, token_name: str) -> Dict:
        """Analyze overall sentiment from multiple sources"""
        search_terms = [token_symbol, token_name]
        
        # Gather sentiment from different sources
        results = await asyncio.gather(
            self._analyze_twitter(search_terms),
            self._analyze_news(search_terms),
            self._analyze_telegram(search_terms)
        )
        
        # Combine results with weighted average
        twitter_sentiment, news_sentiment, telegram_sentiment = results
        
        weights = {
            "twitter": 0.5,
            "news": 0.3,
            "telegram": 0.2
        }
        
        combined_score = (
            twitter_sentiment["score"] * weights["twitter"] +
            news_sentiment["score"] * weights["news"] +
            telegram_sentiment["score"] * weights["telegram"]
        )
        
        # Calculate confidence based on number of sources and their individual confidences
        confidence = (
            twitter_sentiment["confidence"] * weights["twitter"] +
            news_sentiment["confidence"] * weights["news"] +
            telegram_sentiment["confidence"] * weights["telegram"]
        )
        
        return {
            "overall_sentiment": combined_score,
            "confidence": confidence,
            "sources": {
                "twitter": twitter_sentiment,
                "news": news_sentiment,
                "telegram": telegram_sentiment
            }
        }
        
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