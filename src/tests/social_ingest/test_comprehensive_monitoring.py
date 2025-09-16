#!/usr/bin/env python3
"""
Comprehensive Monitoring Test

Simulates the complete monitoring process with 5 tweets per curator,
testing duplicate detection, LLM processing, and token detection.
"""

import asyncio
import logging
import sys
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockLLMClient:
    """Mock LLM client for testing"""
    
    async def generate_async(self, prompt, system_message=None, image=None):
        """Mock LLM response with realistic token detection"""
        text = prompt.lower()
        
        # Check for specific token mentions
        if '$slc' in text or 'slc' in text:
            return json.dumps({
                "token_name": "SLC",
                "network": "solana",
                "contract_address": "So1aNa1234567890abcdef",
                "sentiment": "positive",
                "confidence": 0.85,
                "trading_intention": "buy",
                "has_chart": False,
                "chart_type": None,
                "chart_analysis": None,
                "handle_mentioned": None,
                "needs_verification": False,
                "additional_info": "Mentioned with positive sentiment"
            })
        elif '$barron' in text or 'barron' in text:
            return json.dumps({
                "token_name": "BARRON",
                "network": "solana",
                "contract_address": "So1aNa9876543210fedcba",
                "sentiment": "positive",
                "confidence": 0.90,
                "trading_intention": "buy",
                "has_chart": False,
                "chart_type": None,
                "chart_analysis": None,
                "handle_mentioned": None,
                "needs_verification": False,
                "additional_info": "Mentioned as a win"
            })
        elif 'codecopenflow' in text:
            return json.dumps({
                "token_name": None,
                "network": None,
                "contract_address": None,
                "sentiment": "positive",
                "confidence": 0.8,
                "trading_intention": "buy",
                "has_chart": False,
                "chart_type": None,
                "chart_analysis": None,
                "handle_mentioned": "@Codecopenflow",
                "needs_verification": True,
                "additional_info": "Handle mention that might be a token"
            })
        elif '$pepe' in text or 'pepe' in text:
            return json.dumps({
                "token_name": "PEPE",
                "network": "ethereum",
                "contract_address": "0x1234567890abcdef",
                "sentiment": "positive",
                "confidence": 0.75,
                "trading_intention": "buy",
                "has_chart": True,
                "chart_type": "price",
                "chart_analysis": "breakout pattern",
                "handle_mentioned": None,
                "needs_verification": False,
                "additional_info": "Meme token mentioned"
            })
        elif any(keyword in text for keyword in ['$', 'token', 'coin', 'pump', 'moon', 'buy', 'sell']):
            return json.dumps({
                "token_name": "UNKNOWN",
                "network": "solana",
                "contract_address": "So1aNa0000000000000000",
                "sentiment": "neutral",
                "confidence": 0.50,
                "trading_intention": "unknown",
                "has_chart": False,
                "chart_type": None,
                "chart_analysis": None,
                "handle_mentioned": None,
                "needs_verification": False,
                "additional_info": "Generic token mention detected"
            })
        else:
            return "null"


class MockSocialIngest:
    """Mock social ingest module for testing"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.processed_tweets = set()
        self.results = []
    
    async def process_social_signal(self, curator_id: str, message_data: Dict[str, Any]) -> Any:
        """Process a social signal with duplicate detection"""
        tweet_url = message_data.get('url', '')
        
        # Check for duplicates
        if tweet_url in self.processed_tweets:
            logger.debug(f"Duplicate tweet skipped: {tweet_url}")
            return None
        
        # Mark as processed
        self.processed_tweets.add(tweet_url)
        
        # Extract token info with LLM
        token_info = await self._extract_token_info_with_llm(message_data.get('text', ''))
        if not token_info:
            return None
        
        # Handle handle mentions
        if token_info.get('handle_mentioned') and token_info.get('needs_verification'):
            handle_token_info = await self._scan_handle_for_token(token_info['handle_mentioned'])
            if handle_token_info:
                token_info = handle_token_info
            else:
                return None
        
        # Create result
        result = {
            'curator_id': curator_id,
            'token_name': token_info.get('token_name'),
            'network': token_info.get('network'),
            'sentiment': token_info.get('sentiment'),
            'confidence': token_info.get('confidence'),
            'tweet_text': message_data.get('text', '')[:100],
            'tweet_url': tweet_url,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.results.append(result)
        return result
    
    async def _extract_token_info_with_llm(self, text: str) -> Any:
        """Extract token info using LLM"""
        try:
            response = await self.llm_client.generate_async(text)
            if response and response != "null":
                return json.loads(response)
        except Exception as e:
            logger.error(f"LLM error: {e}")
        return None
    
    async def _scan_handle_for_token(self, handle: str) -> Any:
        """Mock handle scanning"""
        known_tokens = {
            '@Codecopenflow': {
                'token_name': 'CODECOPENFLOW',
                'network': 'solana',
                'contract_address': 'So1aNaCodecopenflow1234567890abcdef',
                'sentiment': 'positive',
                'confidence': 0.8,
                'trading_intention': 'buy',
                'has_chart': False,
                'chart_type': None,
                'chart_analysis': None,
                'additional_info': 'Found token info from handle profile scan'
            }
        }
        return known_tokens.get(handle)


class ComprehensiveTester:
    """Comprehensive monitoring tester"""
    
    def __init__(self):
        self.llm_client = MockLLMClient()
        self.social_ingest = MockSocialIngest(self.llm_client)
        self.curators = [
            {'id': '0xdetweiler', 'handle': '@0xdetweiler', 'name': '0xdetweiler'},
            {'id': 'louiscooper', 'handle': '@LouisCooper_', 'name': 'Louis Cooper'},
            {'id': 'zinceth', 'handle': '@zinceth', 'name': 'Zinceth'},
            {'id': 'cryptotrissy', 'handle': '@Cryptotrissy', 'name': 'Crypto Trissy'},
            {'id': 'cryptoxhunter', 'handle': '@CryptoxHunter', 'name': 'Crypto Hunter'}
        ]
    
    def generate_mock_tweets(self, curator: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        """Generate mock tweets for a curator"""
        base_tweets = [
            f"Just found $SLC on Raydium, looks like a solid play!",
            f"My big $BARRON win last week was incredible!",
            f"I have mentioned @Codecopenflow a lot. It has become one of my highest conviction bags.",
            f"PEPE is pumping hard right now! Time to ape in before it moons.",
            f"Found a new token called FOO on Solana. Looks promising!",
            f"DOGE to the moon! This is the way. 🚀",
            f"Just had lunch, weather is nice today. No crypto talk here.",
            f"$NEWTOKEN is looking bullish, might be a good entry point.",
            f"Chart analysis shows strong support at current levels.",
            f"Market is looking good today, lots of opportunities."
        ]
        
        tweets = []
        for i in range(count):
            tweet_text = base_tweets[i % len(base_tweets)]
            tweets.append({
                'text': tweet_text,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'url': f"https://twitter.com/{curator['handle'].replace('@', '')}/status/{1234567890 + i}",
                'has_image': False,
                'image_url': None
            })
        
        return tweets
    
    async def test_curator(self, curator: Dict[str, Any], tweet_count: int = 5):
        """Test a single curator with mock tweets"""
        logger.info(f"🔍 Testing Curator: {curator['handle']}")
        logger.info("-" * 50)
        
        # Generate mock tweets
        tweets = self.generate_mock_tweets(curator, tweet_count)
        logger.info(f"📝 Generated {len(tweets)} mock tweets")
        
        # Process each tweet
        processed_count = 0
        successful_detections = 0
        
        for i, tweet in enumerate(tweets):
            logger.info(f"   Tweet {i+1}: {tweet['text'][:60]}...")
            
            # Process the tweet
            result = await self.social_ingest.process_social_signal(
                f"twitter:{curator['handle']}", 
                tweet
            )
            
            if result:
                logger.info(f"   ✅ Token detected: {result.get('token_name', 'unknown')}")
                successful_detections += 1
            else:
                logger.info(f"   ❌ No token detected")
            
            processed_count += 1
        
        logger.info(f"📊 Curator {curator['handle']}: {successful_detections}/{processed_count} tweets had tokens")
        logger.info("")
        
        return {
            'curator': curator,
            'total_tweets': processed_count,
            'successful_detections': successful_detections,
            'success_rate': (successful_detections / processed_count * 100) if processed_count > 0 else 0
        }
    
    async def test_all_curators(self, tweets_per_curator: int = 5):
        """Test all curators with mock tweets"""
        logger.info("🧪 Comprehensive Monitoring Test")
        logger.info("=" * 60)
        logger.info(f"📊 Testing {len(self.curators)} curators")
        logger.info(f"🎯 {tweets_per_curator} tweets per curator")
        logger.info("")
        
        results = []
        
        # Test each curator
        for i, curator in enumerate(self.curators):
            logger.info(f"Curator {i+1}/{len(self.curators)}")
            result = await self.test_curator(curator, tweets_per_curator)
            results.append(result)
        
        # Print comprehensive summary
        self._print_comprehensive_summary(results)
        
        return results
    
    def _print_comprehensive_summary(self, results: List[Dict[str, Any]]):
        """Print comprehensive test summary"""
        logger.info("📊 COMPREHENSIVE TEST SUMMARY")
        logger.info("=" * 60)
        
        total_curators = len(results)
        total_tweets = sum(r['total_tweets'] for r in results)
        total_detections = sum(r['successful_detections'] for r in results)
        overall_success_rate = (total_detections / total_tweets * 100) if total_tweets > 0 else 0
        
        logger.info(f"📈 Curators tested: {total_curators}")
        logger.info(f"📝 Total tweets processed: {total_tweets}")
        logger.info(f"🎯 Successful token detections: {total_detections}")
        logger.info(f"📊 Overall success rate: {overall_success_rate:.1f}%")
        logger.info("")
        
        # Per-curator breakdown
        logger.info("📋 Per-Curator Results:")
        for result in results:
            curator = result['curator']
            successful = result['successful_detections']
            total = result['total_tweets']
            rate = result['success_rate']
            
            logger.info(f"   {curator['handle']}: {successful}/{total} ({rate:.1f}%)")
        
        logger.info("")
        
        # Duplicate detection summary
        total_processed = len(self.social_ingest.processed_tweets)
        logger.info(f"🔄 Unique tweets processed: {total_processed}")
        logger.info(f"❌ Duplicates avoided: {total_tweets - total_processed}")
        
        logger.info("")
        logger.info("🎉 Comprehensive test completed!")


async def main():
    """Main test function"""
    tester = ComprehensiveTester()
    await tester.test_all_curators(tweets_per_curator=5)


if __name__ == "__main__":
    asyncio.run(main())
