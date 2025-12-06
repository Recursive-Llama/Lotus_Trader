#!/usr/bin/env python3
"""
Isolated Binance API Test

Tests the Binance /api/v3/klines endpoint for historical OHLC data backfill.
This test runs independently before integrating Binance API into Regime Price Collector.

Reference: docs/regime_engine_implementation_plan.md - Phase 1: Infrastructure
"""

import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json


# Binance API Configuration
BINANCE_BASE_URL = "https://api.binance.com"
KLINES_ENDPOINT = "/api/v3/klines"

# Test symbols (majors we need for regime drivers)
TEST_SYMBOLS = ["BTCUSDT", "SOLUSDT", "ETHUSDT", "BNBUSDT"]

# Test intervals (regime timeframes)
TEST_INTERVALS = ["1m", "1h", "1d"]

# Rate limit: Binance allows up to 1200 requests per minute (20 req/sec)
# We'll be conservative: 1 request per 100ms = 10 req/sec max
RATE_LIMIT_DELAY = 0.1  # seconds between requests


class BinanceAPITester:
    """Test Binance API endpoint for klines data"""
    
    def __init__(self):
        self.base_url = BINANCE_BASE_URL
        self.results = {
            "endpoint_tests": [],
            "batching_tests": [],
            "rate_limit_tests": [],
            "error_handling_tests": [],
            "summary": {}
        }
    
    def test_single_request(
        self, 
        symbol: str, 
        interval: str, 
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> Tuple[bool, Dict]:
        """
        Test a single klines request
        
        Returns:
            (success: bool, result: dict with response data or error info)
        """
        url = f"{self.base_url}{KLINES_ENDPOINT}"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        
        try:
            start = time.time()
            response = requests.get(url, params=params, timeout=10)
            elapsed = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                return True, {
                    "status_code": 200,
                    "candles_count": len(data),
                    "response_time_ms": round(elapsed * 1000, 2),
                    "first_candle": data[0] if data else None,
                    "last_candle": data[-1] if data else None,
                    "raw_response_sample": data[:2] if len(data) >= 2 else data
                }
            else:
                return False, {
                    "status_code": response.status_code,
                    "error": response.text,
                    "response_time_ms": round(elapsed * 1000, 2)
                }
        except requests.exceptions.RequestException as e:
            return False, {
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def test_endpoint_basic(self) -> Dict:
        """Test basic endpoint functionality"""
        print("\n" + "="*60)
        print("TEST 1: Basic Endpoint Functionality")
        print("="*60)
        
        results = []
        
        for symbol in TEST_SYMBOLS:
            for interval in TEST_INTERVALS:
                print(f"\nTesting: {symbol} @ {interval} (limit=100)")
                success, result = self.test_single_request(symbol, interval, limit=100)
                
                if success:
                    print(f"  ✅ SUCCESS: {result['candles_count']} candles, {result['response_time_ms']}ms")
                    print(f"  First candle timestamp: {result['first_candle'][0] if result['first_candle'] else 'N/A'}")
                    print(f"  Last candle timestamp: {result['last_candle'][0] if result['last_candle'] else 'N/A'}")
                else:
                    print(f"  ❌ FAILED: {result.get('error', 'Unknown error')}")
                
                results.append({
                    "symbol": symbol,
                    "interval": interval,
                    "success": success,
                    "result": result
                })
                
                # Rate limit: be nice to Binance
                time.sleep(RATE_LIMIT_DELAY)
        
        self.results["endpoint_tests"] = results
        return results
    
    def test_max_limit(self) -> Dict:
        """Test maximum limit (1000 candles per request)"""
        print("\n" + "="*60)
        print("TEST 2: Maximum Limit (1000 candles)")
        print("="*60)
        
        results = []
        
        # Test with max limit for different intervals
        for interval in TEST_INTERVALS:
            symbol = "BTCUSDT"  # Use BTC as test case
            print(f"\nTesting: {symbol} @ {interval} (limit=1000)")
            
            success, result = self.test_single_request(symbol, interval, limit=1000)
            
            if success:
                print(f"  ✅ SUCCESS: {result['candles_count']} candles received")
                print(f"  Response time: {result['response_time_ms']}ms")
                
                # Verify we got close to 1000 (might be slightly less)
                if result['candles_count'] >= 900:
                    print(f"  ✅ Limit working correctly (got {result['candles_count']} candles)")
                else:
                    print(f"  ⚠️  Got fewer candles than expected: {result['candles_count']}")
            else:
                print(f"  ❌ FAILED: {result.get('error', 'Unknown error')}")
            
            results.append({
                "interval": interval,
                "success": success,
                "result": result
            })
            
            time.sleep(RATE_LIMIT_DELAY)
        
        self.results["batching_tests"].append({
            "test": "max_limit",
            "results": results
        })
        return results
    
    def test_batching_logic(self) -> Dict:
        """Test batching logic for historical backfill"""
        print("\n" + "="*60)
        print("TEST 3: Batching Logic (Historical Backfill)")
        print("="*60)
        
        # Calculate time ranges for backfilling
        from datetime import timezone
        now = datetime.now(timezone.utc)
        
        # Test: Backfill 1 day of 1h candles (should need 1 request)
        # Test: Backfill 7 days of 1h candles (should need 1 request, 7*24 = 168 candles)
        # Test: Backfill 30 days of 1h candles (should need 1 request, 30*24 = 720 candles)
        # Test: Backfill 90 days of 1h candles (should need 1 request, 90*24 = 2160 candles - need 3 batches)
        
        test_cases = [
            {"days": 1, "interval": "1h", "expected_batches": 1},
            {"days": 7, "interval": "1h", "expected_batches": 1},
            {"days": 30, "interval": "1h", "expected_batches": 1},
            {"days": 90, "interval": "1h", "expected_batches": 3},  # 90*24 = 2160 candles, need 3 batches
        ]
        
        results = []
        
        for case in test_cases:
            days = case["days"]
            interval = case["interval"]
            expected_batches = case["expected_batches"]
            
            print(f"\nTesting: Backfill {days} days of {interval} candles")
            
            # Calculate candles needed
            if interval == "1h":
                candles_needed = days * 24
            elif interval == "1d":
                candles_needed = days
            elif interval == "1m":
                candles_needed = days * 24 * 60
            else:
                candles_needed = 0
            
            batches_needed = (candles_needed + 999) // 1000  # Round up
            
            print(f"  Candles needed: {candles_needed}")
            print(f"  Batches needed: {batches_needed}")
            
            # Simulate batching: fetch oldest data first
            end_time = int(now.timestamp() * 1000)  # milliseconds
            start_time = int((now - timedelta(days=days)).timestamp() * 1000)
            
            batches = []
            current_end = end_time
            
            for batch_num in range(batches_needed):
                # Calculate start time for this batch (going backwards)
                batch_start = current_end - (1000 * self._interval_to_ms(interval))
                
                print(f"  Batch {batch_num + 1}: Fetching from {datetime.fromtimestamp(batch_start/1000)} to {datetime.fromtimestamp(current_end/1000)}")
                
                success, result = self.test_single_request(
                    "BTCUSDT", 
                    interval, 
                    limit=1000,
                    start_time=batch_start,
                    end_time=current_end
                )
                
                if success:
                    batches.append({
                        "batch_num": batch_num + 1,
                        "candles_received": result["candles_count"],
                        "response_time_ms": result["response_time_ms"]
                    })
                    print(f"    ✅ Received {result['candles_count']} candles")
                else:
                    print(f"    ❌ Failed: {result.get('error', 'Unknown')}")
                    break
                
                # Move to next batch (going backwards in time)
                if result.get("first_candle"):
                    current_end = int(result["first_candle"][0]) - 1  # Start before first candle
                
                time.sleep(RATE_LIMIT_DELAY)
            
            results.append({
                "days": days,
                "interval": interval,
                "candles_needed": candles_needed,
                "batches_needed": batches_needed,
                "batches_completed": len(batches),
                "success": len(batches) == batches_needed,
                "batches": batches
            })
        
        self.results["batching_tests"].append({
            "test": "batching_logic",
            "results": results
        })
        return results
    
    def test_error_handling(self) -> Dict:
        """Test error handling (invalid symbols, intervals, etc.)"""
        print("\n" + "="*60)
        print("TEST 4: Error Handling")
        print("="*60)
        
        error_cases = [
            {"symbol": "INVALID", "interval": "1h", "limit": 100, "expected_error": True},
            {"symbol": "BTCUSDT", "interval": "invalid", "limit": 100, "expected_error": True},
            {"symbol": "BTCUSDT", "interval": "1h", "limit": 2000, "expected_error": True},  # Over max limit
            {"symbol": "BTCUSDT", "interval": "1h", "limit": -1, "expected_error": True},  # Invalid limit
        ]
        
        results = []
        
        for case in error_cases:
            symbol = case["symbol"]
            interval = case["interval"]
            limit = case["limit"]
            expected_error = case["expected_error"]
            
            print(f"\nTesting error case: {symbol} @ {interval} (limit={limit})")
            
            success, result = self.test_single_request(symbol, interval, limit=limit)
            
            if expected_error:
                if not success:
                    print(f"  ✅ Correctly returned error: {result.get('error', 'Unknown')}")
                else:
                    print(f"  ⚠️  Expected error but got success (unexpected)")
            else:
                if success:
                    print(f"  ✅ Success (as expected)")
                else:
                    print(f"  ❌ Unexpected error: {result.get('error', 'Unknown')}")
            
            results.append({
                "case": case,
                "success": success,
                "result": result,
                "expected_error": expected_error,
                "correct": (not success) == expected_error
            })
            
            time.sleep(RATE_LIMIT_DELAY)
        
        self.results["error_handling_tests"] = results
        return results
    
    def test_rate_limits(self) -> Dict:
        """Test rate limit behavior"""
        print("\n" + "="*60)
        print("TEST 5: Rate Limit Behavior")
        print("="*60)
        
        # Send rapid requests to see if we hit rate limits
        print("\nSending 20 rapid requests (should be within rate limit)...")
        
        start_time = time.time()
        successes = 0
        failures = 0
        rate_limit_errors = 0
        
        for i in range(20):
            success, result = self.test_single_request("BTCUSDT", "1h", limit=10)
            if success:
                successes += 1
            else:
                failures += 1
                if "429" in str(result.get("status_code", "")) or "rate limit" in str(result.get("error", "")).lower():
                    rate_limit_errors += 1
            
            # Small delay to avoid hitting limits
            time.sleep(0.05)  # 50ms between requests
        
        elapsed = time.time() - start_time
        
        print(f"\n  Total requests: 20")
        print(f"  Successes: {successes}")
        print(f"  Failures: {failures}")
        print(f"  Rate limit errors: {rate_limit_errors}")
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Average response time: {(elapsed/20)*1000:.2f}ms")
        
        result = {
            "total_requests": 20,
            "successes": successes,
            "failures": failures,
            "rate_limit_errors": rate_limit_errors,
            "total_time_seconds": elapsed,
            "avg_response_time_ms": (elapsed/20)*1000
        }
        
        self.results["rate_limit_tests"] = result
        return result
    
    def _interval_to_ms(self, interval: str) -> int:
        """Convert interval string to milliseconds"""
        if interval == "1m":
            return 60 * 1000
        elif interval == "1h":
            return 60 * 60 * 1000
        elif interval == "1d":
            return 24 * 60 * 60 * 1000
        else:
            raise ValueError(f"Unknown interval: {interval}")
    
    def generate_summary(self) -> Dict:
        """Generate test summary"""
        summary = {
            "endpoint_tests": {
                "total": len(self.results["endpoint_tests"]),
                "successes": sum(1 for r in self.results["endpoint_tests"] if r["success"]),
                "failures": sum(1 for r in self.results["endpoint_tests"] if not r["success"])
            },
            "batching_tests": {
                "max_limit_tests": len([r for r in self.results["batching_tests"] if r.get("test") == "max_limit"]),
                "batching_logic_tests": len([r for r in self.results["batching_tests"] if r.get("test") == "batching_logic"])
            },
            "error_handling_tests": {
                "total": len(self.results["error_handling_tests"]),
                "correct": sum(1 for r in self.results["error_handling_tests"] if r.get("correct", False))
            },
            "rate_limit_tests": self.results["rate_limit_tests"]
        }
        
        self.results["summary"] = summary
        return summary
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        summary = self.results["summary"]
        
        print(f"\nEndpoint Tests:")
        print(f"  Total: {summary['endpoint_tests']['total']}")
        print(f"  Successes: {summary['endpoint_tests']['successes']}")
        print(f"  Failures: {summary['endpoint_tests']['failures']}")
        
        print(f"\nBatching Tests:")
        print(f"  Max limit tests: {summary['batching_tests']['max_limit_tests']}")
        print(f"  Batching logic tests: {summary['batching_tests']['batching_logic_tests']}")
        
        print(f"\nError Handling Tests:")
        print(f"  Total: {summary['error_handling_tests']['total']}")
        print(f"  Correct behavior: {summary['error_handling_tests']['correct']}")
        
        if summary.get("rate_limit_tests"):
            print(f"\nRate Limit Tests:")
            print(f"  Total requests: {summary['rate_limit_tests']['total_requests']}")
            print(f"  Successes: {summary['rate_limit_tests']['successes']}")
            print(f"  Rate limit errors: {summary['rate_limit_tests']['rate_limit_errors']}")
        
        print("\n" + "="*60)
        print("✅ Binance API Test Complete")
        print("="*60)
    
    def save_results(self, filename: str = "binance_api_test_results.json"):
        """Save test results to JSON file"""
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\nResults saved to: {filename}")


def main():
    """Run all Binance API tests"""
    print("="*60)
    print("Binance API Isolated Test")
    print("="*60)
    print("\nTesting /api/v3/klines endpoint for regime price data backfill")
    print("Reference: docs/regime_engine_implementation_plan.md")
    
    tester = BinanceAPITester()
    
    # Run all tests
    tester.test_endpoint_basic()
    tester.test_max_limit()
    tester.test_batching_logic()
    tester.test_error_handling()
    tester.test_rate_limits()
    
    # Generate and print summary
    tester.generate_summary()
    tester.print_summary()
    
    # Save results
    tester.save_results()
    
    print("\n✅ All tests completed!")
    print("\nNext steps:")
    print("1. Review test results")
    print("2. Verify data quality (OHLC format, timestamps)")
    print("3. Integrate Binance API into Regime Price Collector")


if __name__ == "__main__":
    main()

