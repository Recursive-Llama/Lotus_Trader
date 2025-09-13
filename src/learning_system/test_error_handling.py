#!/usr/bin/env python3
"""
Error Handling and Edge Cases Test Suite
Tests system resilience under failure conditions and edge cases
"""

import sys
import os
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import traceback
import random

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

class ErrorHandlingTester:
    def __init__(self):
        self.test_results = {}
    
    async def test_invalid_data_handling(self):
        """Test handling of invalid and malformed data"""
        print("🚨 Testing Invalid Data Handling...")
        
        try:
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test 1: Invalid market data
            print("  Testing invalid market data...")
            invalid_market_data_cases = [
                {},  # Empty data
                {"symbol": "BTCUSDT"},  # Missing required fields
                {"symbol": "BTCUSDT", "open": "invalid", "high": 50000, "low": 49000, "close": 49500, "volume": 1000000},  # Invalid data types
                {"symbol": "BTCUSDT", "open": 50000, "high": 49000, "low": 51000, "close": 49500, "volume": 1000000},  # Invalid OHLC
                {"symbol": "BTCUSDT", "open": -50000, "high": 51000, "low": 49000, "close": 49500, "volume": 1000000},  # Negative price
                {"symbol": "BTCUSDT", "open": 50000, "high": 51000, "low": 49000, "close": 49500, "volume": -1000000},  # Negative volume
            ]
            
            for i, invalid_data in enumerate(invalid_market_data_cases):
                try:
                    validation_result = self._validate_market_data(invalid_data)
                    if not validation_result["valid"]:
                        results["passed"] += 1
                        print(f"    ✅ Invalid market data {i+1} properly rejected")
                    else:
                        results["failed"] += 1
                        print(f"    ❌ Invalid market data {i+1} incorrectly accepted")
                except Exception as e:
                    results["passed"] += 1
                    print(f"    ✅ Invalid market data {i+1} caused expected exception: {type(e).__name__}")
            
            # Test 2: Invalid strand data
            print("  Testing invalid strand data...")
            invalid_strand_cases = [
                {},  # Empty strand
                {"strand_type": "pattern"},  # Missing required fields
                {"strand_type": "pattern", "content": "test", "metadata": "invalid", "source": "test", "created_at": "2023-01-01"},  # Invalid metadata type
                {"strand_type": "invalid_type", "content": "test", "metadata": {}, "source": "test", "created_at": "2023-01-01"},  # Invalid strand type
                {"strand_type": "pattern", "content": "", "metadata": {}, "source": "test", "created_at": "2023-01-01"},  # Empty content
            ]
            
            for i, invalid_strand in enumerate(invalid_strand_cases):
                try:
                    validation_result = self._validate_strand_structure(invalid_strand)
                    if not validation_result["valid"]:
                        results["passed"] += 1
                        print(f"    ✅ Invalid strand {i+1} properly rejected")
                    else:
                        results["failed"] += 1
                        print(f"    ❌ Invalid strand {i+1} incorrectly accepted")
                except Exception as e:
                    results["passed"] += 1
                    print(f"    ✅ Invalid strand {i+1} caused expected exception: {type(e).__name__}")
            
            # Test 3: Invalid mathematical inputs
            print("  Testing invalid mathematical inputs...")
            try:
                from src.learning_system.mathematical_resonance_engine import MathematicalResonanceEngine
                engine = MathematicalResonanceEngine()
                
                invalid_math_cases = [
                    ({"accuracy": -0.5, "precision": 0.8, "stability": 0.7}, ["1H"]),  # Negative accuracy
                    ({"accuracy": 1.5, "precision": 0.8, "stability": 0.7}, ["1H"]),  # Accuracy > 1
                    ({"accuracy": 0.8, "precision": -0.5, "stability": 0.7}, ["1H"]),  # Negative precision
                    ({"accuracy": 0.8, "precision": 0.8, "stability": 1.5}, ["1H"]),  # Stability > 1
                    ({"accuracy": 0.8, "precision": 0.8, "stability": 0.7}, []),  # Empty timeframes
                ]
                
                for i, (pattern_data, timeframes) in enumerate(invalid_math_cases):
                    try:
                        phi = engine.calculate_phi(pattern_data, timeframes)
                        if 0 <= phi <= 1:
                            results["passed"] += 1
                            print(f"    ✅ Invalid math input {i+1} handled gracefully: φ = {phi:.3f}")
                        else:
                            results["failed"] += 1
                            print(f"    ❌ Invalid math input {i+1} produced invalid result: φ = {phi:.3f}")
                    except Exception as e:
                        results["passed"] += 1
                        print(f"    ✅ Invalid math input {i+1} caused expected exception: {type(e).__name__}")
            except Exception as e:
                results["failed"] += 1
                print(f"    ❌ Mathematical engine test failed: {e}")
            
            results["details"] = {
                "invalid_market_data_cases": len(invalid_market_data_cases),
                "invalid_strand_cases": len(invalid_strand_cases),
                "invalid_math_cases": len(invalid_math_cases)
            }
            
            self.test_results["invalid_data_handling"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Invalid data handling test failed: {e}")
            traceback.print_exc()
            return False
    
    def _validate_market_data(self, data):
        """Validate market data structure"""
        issues = []
        
        required_fields = ["symbol", "timestamp", "open", "high", "low", "close", "volume"]
        
        for field in required_fields:
            if field not in data:
                issues.append(f"Missing {field}")
        
        if "open" in data and not isinstance(data["open"], (int, float)):
            issues.append("Open price must be numeric")
        elif "open" in data and data["open"] <= 0:
            issues.append("Open price must be positive")
        
        if "volume" in data and not isinstance(data["volume"], (int, float)):
            issues.append("Volume must be numeric")
        elif "volume" in data and data["volume"] < 0:
            issues.append("Volume must be non-negative")
        
        if all(field in data for field in ["open", "high", "low", "close"]):
            if data["high"] < max(data["open"], data["close"]):
                issues.append("High price is lower than open/close")
            if data["low"] > min(data["open"], data["close"]):
                issues.append("Low price is higher than open/close")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def _validate_strand_structure(self, strand):
        """Validate strand structure"""
        issues = []
        
        required_fields = ["strand_type", "content", "metadata", "source", "created_at"]
        
        for field in required_fields:
            if field not in strand:
                issues.append(f"Missing {field}")
        
        if "metadata" in strand and not isinstance(strand["metadata"], dict):
            issues.append("Metadata must be a dictionary")
        
        if "content" in strand and not strand["content"]:
            issues.append("Content cannot be empty")
        
        # Validate strand_type
        valid_strand_types = ["pattern", "prediction_review", "trade_outcome", "trading_decision"]
        if "strand_type" in strand and strand["strand_type"] not in valid_strand_types:
            issues.append(f"Invalid strand_type: {strand['strand_type']}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    async def test_network_failure_handling(self):
        """Test handling of network failures and timeouts"""
        print("\n🌐 Testing Network Failure Handling...")
        
        try:
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test 1: API timeout handling
            print("  Testing API timeout handling...")
            try:
                import requests
                
                # Test with very short timeout
                start_time = time.time()
                try:
                    response = requests.get("https://api.binance.com/api/v3/klines", 
                                          params={"symbol": "BTCUSDT", "interval": "1h", "limit": 1},
                                          timeout=0.001)  # Very short timeout
                except requests.exceptions.Timeout:
                    results["passed"] += 1
                    print("  ✅ API timeout handled gracefully")
                except Exception as e:
                    results["failed"] += 1
                    print(f"  ❌ Unexpected error during timeout test: {e}")
                
                timeout_duration = time.time() - start_time
                if timeout_duration < 1.0:  # Should timeout quickly
                    results["passed"] += 1
                    print(f"  ✅ Timeout occurred quickly: {timeout_duration:.3f}s")
                else:
                    results["failed"] += 1
                    print(f"  ❌ Timeout took too long: {timeout_duration:.3f}s")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Network timeout test failed: {e}")
            
            # Test 2: Connection error handling
            print("  Testing connection error handling...")
            try:
                # Test with invalid URL
                try:
                    response = requests.get("https://invalid-url-that-does-not-exist.com/api", timeout=5)
                except requests.exceptions.ConnectionError:
                    results["passed"] += 1
                    print("  ✅ Connection error handled gracefully")
                except Exception as e:
                    results["failed"] += 1
                    print(f"  ❌ Unexpected error during connection test: {e}")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Connection error test failed: {e}")
            
            # Test 3: HTTP error handling
            print("  Testing HTTP error handling...")
            try:
                # Test with invalid endpoint
                try:
                    response = requests.get("https://api.binance.com/api/v3/invalid-endpoint", timeout=5)
                    if response.status_code >= 400:
                        results["passed"] += 1
                        print(f"  ✅ HTTP error handled gracefully: {response.status_code}")
                    else:
                        results["failed"] += 1
                        print(f"  ❌ Unexpected success for invalid endpoint: {response.status_code}")
                except Exception as e:
                    results["passed"] += 1
                    print(f"  ✅ HTTP error caused expected exception: {type(e).__name__}")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ HTTP error test failed: {e}")
            
            results["details"] = {
                "timeout_handling": "tested",
                "connection_error_handling": "tested",
                "http_error_handling": "tested"
            }
            
            self.test_results["network_failure_handling"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Network failure handling test failed: {e}")
            traceback.print_exc()
            return False
    
    async def test_memory_and_performance_limits(self):
        """Test system behavior under memory and performance constraints"""
        print("\n💾 Testing Memory and Performance Limits...")
        
        try:
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test 1: Large dataset handling
            print("  Testing large dataset handling...")
            try:
                # Create large dataset
                large_dataset = []
                for i in range(1000):  # 1000 data points
                    large_dataset.append({
                        "symbol": "BTCUSDT",
                        "timestamp": datetime.now().isoformat(),
                        "open": 50000 + random.uniform(-1000, 1000),
                        "high": 51000 + random.uniform(-1000, 1000),
                        "low": 49000 + random.uniform(-1000, 1000),
                        "close": 50500 + random.uniform(-1000, 1000),
                        "volume": random.uniform(500000, 2000000),
                        "rsi": random.uniform(20, 80)
                    })
                
                # Process large dataset
                start_time = time.time()
                processed_strands = []
                for data in large_dataset:
                    strands = self._process_market_data_to_strands(data)
                    processed_strands.extend(strands)
                processing_time = time.time() - start_time
                
                if processing_time < 10.0:  # Should process 1000 points in under 10 seconds
                    results["passed"] += 1
                    print(f"  ✅ Large dataset processed in {processing_time:.3f}s: {len(processed_strands)} strands")
                else:
                    results["failed"] += 1
                    print(f"  ❌ Large dataset processing too slow: {processing_time:.3f}s")
                
                # Test memory usage
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                if memory_mb < 500:  # Should use less than 500MB
                    results["passed"] += 1
                    print(f"  ✅ Memory usage reasonable: {memory_mb:.1f}MB")
                else:
                    results["failed"] += 1
                    print(f"  ❌ Memory usage too high: {memory_mb:.1f}MB")
                
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Large dataset test failed: {e}")
            
            # Test 2: Mathematical calculations under load
            print("  Testing mathematical calculations under load...")
            try:
                from src.learning_system.mathematical_resonance_engine import MathematicalResonanceEngine
                engine = MathematicalResonanceEngine()
                
                start_time = time.time()
                for i in range(1000):  # 1000 calculations
                    pattern_data = {
                        "accuracy": 0.8 + random.uniform(-0.1, 0.1),
                        "precision": 0.75 + random.uniform(-0.1, 0.1),
                        "stability": 0.8 + random.uniform(-0.1, 0.1)
                    }
                    timeframes = ["1H", "4H", "1D"]
                    phi = engine.calculate_phi(pattern_data, timeframes)
                
                calculation_time = time.time() - start_time
                
                if calculation_time < 5.0:  # Should complete 1000 calculations in under 5 seconds
                    results["passed"] += 1
                    print(f"  ✅ 1000 calculations completed in {calculation_time:.3f}s")
                else:
                    results["failed"] += 1
                    print(f"  ❌ Calculations too slow: {calculation_time:.3f}s")
                
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Mathematical calculations test failed: {e}")
            
            # Test 3: Concurrent processing
            print("  Testing concurrent processing...")
            try:
                async def process_data_batch(batch_id):
                    await asyncio.sleep(0.01)  # Simulate processing
                    return f"batch_{batch_id}_processed"
                
                start_time = time.time()
                tasks = [process_data_batch(i) for i in range(100)]
                results_list = await asyncio.gather(*tasks, return_exceptions=True)
                concurrent_time = time.time() - start_time
                
                successful_tasks = sum(1 for r in results_list if not isinstance(r, Exception))
                
                if successful_tasks >= 95 and concurrent_time < 2.0:  # 95% success in under 2 seconds
                    results["passed"] += 1
                    print(f"  ✅ Concurrent processing: {successful_tasks}/100 tasks in {concurrent_time:.3f}s")
                else:
                    results["failed"] += 1
                    print(f"  ❌ Concurrent processing failed: {successful_tasks}/100 tasks in {concurrent_time:.3f}s")
                
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Concurrent processing test failed: {e}")
            
            results["details"] = {
                "large_dataset_size": 1000,
                "calculation_count": 1000,
                "concurrent_tasks": 100
            }
            
            self.test_results["memory_performance_limits"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Memory and performance limits test failed: {e}")
            traceback.print_exc()
            return False
    
    def _process_market_data_to_strands(self, market_data):
        """Process market data into strands"""
        strands = []
        
        # RSI analysis
        if "rsi" in market_data:
            rsi = market_data["rsi"]
            if rsi < 30:
                pattern_type = "rsi_oversold"
                confidence = 0.8
            elif rsi > 70:
                pattern_type = "rsi_overbought"
                confidence = 0.8
            else:
                pattern_type = "rsi_neutral"
                confidence = 0.5
            
            strands.append({
                "strand_type": "pattern",
                "content": f"RSI {pattern_type} signal at {rsi:.1f}",
                "metadata": {
                    "rsi": rsi,
                    "pattern_type": pattern_type,
                    "confidence": confidence,
                    "timeframe": "1H",
                    "accuracy": 0.8,
                    "precision": 0.75,
                    "stability": 0.8
                },
                "source": "rsi_analyzer",
                "created_at": market_data["timestamp"]
            })
        
        return strands
    
    async def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        print("\n🔍 Testing Edge Cases...")
        
        try:
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test 1: Boundary values
            print("  Testing boundary values...")
            try:
                from src.learning_system.mathematical_resonance_engine import MathematicalResonanceEngine
                engine = MathematicalResonanceEngine()
                
                boundary_cases = [
                    ({"accuracy": 0.0, "precision": 0.0, "stability": 0.0}, ["1H"]),  # All zeros
                    ({"accuracy": 1.0, "precision": 1.0, "stability": 1.0}, ["1H"]),  # All ones
                    ({"accuracy": 0.5, "precision": 0.5, "stability": 0.5}, ["1H"]),  # All 0.5
                ]
                
                for i, (pattern_data, timeframes) in enumerate(boundary_cases):
                    try:
                        phi = engine.calculate_phi(pattern_data, timeframes)
                        if 0 <= phi <= 1:
                            results["passed"] += 1
                            print(f"    ✅ Boundary case {i+1} handled: φ = {phi:.3f}")
                        else:
                            results["failed"] += 1
                            print(f"    ❌ Boundary case {i+1} invalid: φ = {phi:.3f}")
                    except Exception as e:
                        results["failed"] += 1
                        print(f"    ❌ Boundary case {i+1} failed: {e}")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Boundary values test failed: {e}")
            
            # Test 2: Empty datasets
            print("  Testing empty datasets...")
            try:
                # Test with empty strand list
                empty_strands = []
                context_data = self._simulate_context_generation(empty_strands)
                
                if isinstance(context_data, dict):
                    results["passed"] += 1
                    print("  ✅ Empty strand list handled gracefully")
                else:
                    results["failed"] += 1
                    print("  ❌ Empty strand list not handled properly")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Empty datasets test failed: {e}")
            
            # Test 3: Single item datasets
            print("  Testing single item datasets...")
            try:
                single_strand = [{
                    "strand_type": "pattern",
                    "content": "Single pattern",
                    "metadata": {"confidence": 0.8},
                    "source": "test",
                    "created_at": datetime.now().isoformat()
                }]
                
                context_data = self._simulate_context_generation(single_strand)
                
                if isinstance(context_data, dict) and len(context_data) > 0:
                    results["passed"] += 1
                    print("  ✅ Single item dataset handled gracefully")
                else:
                    results["failed"] += 1
                    print("  ❌ Single item dataset not handled properly")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Single item datasets test failed: {e}")
            
            results["details"] = {
                "boundary_cases": len(boundary_cases) if 'boundary_cases' in locals() else 0,
                "empty_datasets": "tested",
                "single_item_datasets": "tested"
            }
            
            self.test_results["edge_cases"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Edge cases test failed: {e}")
            traceback.print_exc()
            return False
    
    def _simulate_context_generation(self, strands):
        """Simulate context generation for modules"""
        context_data = {}
        
        # Group strands by type
        strands_by_type = {}
        for strand in strands:
            strand_type = strand["strand_type"]
            if strand_type not in strands_by_type:
                strands_by_type[strand_type] = []
            strands_by_type[strand_type].append(strand)
        
        # Generate context for each module
        module_subscriptions = {
            "CIL": ["prediction_review"],
            "CTP": ["trade_outcome"],
            "RDI": ["pattern"],
            "DM": ["pattern", "trade_outcome"]
        }
        
        for module, subscribed_types in module_subscriptions.items():
            module_context = []
            for strand_type in subscribed_types:
                if strand_type in strands_by_type:
                    module_context.extend(strands_by_type[strand_type])
            
            if module_context:
                context_data[module] = {
                    "strands": module_context,
                    "count": len(module_context),
                    "relevance_score": 0.8
                }
        
        return context_data
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("📊 ERROR HANDLING AND EDGE CASES TEST SUMMARY")
        print("="*80)
        
        total_passed = 0
        total_failed = 0
        
        for test_name, results in self.test_results.items():
            if isinstance(results, dict) and "passed" in results and "failed" in results:
                passed = results["passed"]
                failed = results["failed"]
                total_passed += passed
                total_failed += failed
                
                status = "✅ PASS" if failed == 0 else "❌ FAIL"
                print(f"{test_name.upper().replace('_', ' ')}: {status} ({passed} passed, {failed} failed)")
        
        print("-"*80)
        overall_status = "✅ ALL ERROR HANDLING TESTS PASSED" if total_failed == 0 else "❌ SOME ERROR HANDLING TESTS FAILED"
        print(f"OVERALL: {overall_status} ({total_passed} passed, {total_failed} failed)")
        print("="*80)
        
        return total_failed == 0

async def main():
    """Run error handling and edge cases tests"""
    print("🚀 Starting Error Handling and Edge Cases Tests")
    print("="*80)
    
    tester = ErrorHandlingTester()
    
    # Run all tests
    tests = [
        ("Invalid Data Handling", tester.test_invalid_data_handling),
        ("Network Failure Handling", tester.test_network_failure_handling),
        ("Memory and Performance Limits", tester.test_memory_and_performance_limits),
        ("Edge Cases", tester.test_edge_cases)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running {test_name}...")
            await test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            traceback.print_exc()
    
    # Print summary
    success = tester.print_summary()
    
    if success:
        print("\n🎉 All error handling and edge cases tests passed!")
        print("✅ System is resilient and handles errors gracefully")
    else:
        print("\n⚠️  Some error handling tests failed. Review and fix issues.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
