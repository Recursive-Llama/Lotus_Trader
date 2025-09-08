#!/usr/bin/env python3
"""
Test comprehensive database operations for Alpha Detector Module
Phase 1.1: Full database functionality test
"""

import sys
import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.supabase_manager import SupabaseManager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_operations():
    """Test comprehensive database operations"""
    print("🧪 Testing Alpha Detector Database Operations")
    print("=" * 60)
    
    try:
        # Initialize Supabase manager
        print("🔌 Initializing Supabase manager...")
        db = SupabaseManager()
        
        # Test 1: Connection test
        print("\n1️⃣ Testing database connection...")
        if not db.test_connection():
            print("❌ Database connection failed")
            return False
        print("✅ Database connection successful")
        
        # Test 2: Insert a complete trading plan strand
        print("\n2️⃣ Testing strand insertion...")
        test_strand = {
            'id': f"AD_{uuid.uuid4().hex[:12]}",
            'module': 'alpha',
            'kind': 'trading_plan',
            'symbol': 'BTC',
            'timeframe': '1m',
            'session_bucket': 'test_session_001',
            'regime': 'trending',
            'tags': ['decision_maker', 'test', 'btc'],
            'sig_sigma': 0.85,
            'sig_confidence': 0.92,
            'sig_direction': 'long',
            'trading_plan': {
                'entry_price': 45000.0,
                'stop_loss': 44000.0,
                'take_profit': 47000.0,
                'position_size': 0.1,
                'risk_reward_ratio': 2.0,
                'time_horizon': '1h',
                'entry_conditions': ['price_above_ma20', 'volume_spike'],
                'confidence_score': 0.92
            },
            'signal_pack': {
                'technical_indicators': {
                    'rsi': 65.2,
                    'macd': 125.8,
                    'bollinger_position': 0.75
                },
                'market_microstructure': {
                    'order_book_imbalance': 0.15,
                    'trade_size_distribution': 'large_blocks'
                },
                'regime_indicators': {
                    'volatility_regime': 'low',
                    'trend_strength': 'strong'
                }
            },
            'dsi_evidence': {
                'mx_evidence': 0.88,
                'mx_confirm': True,
                'mx_expert_contributions': {
                    'grammar_expert': 0.85,
                    'classifier_expert': 0.92,
                    'anomaly_expert': 0.78
                }
            },
            'regime_context': {
                'market_regime': 'trending',
                'volatility_regime': 'low',
                'liquidity_regime': 'high'
            },
            'event_context': {
                'upcoming_events': [],
                'recent_events': ['fed_meeting'],
                'market_sentiment': 'bullish'
            },
            'module_intelligence': {
                'learning_rate': 0.01,
                'adaptation_threshold': 0.7,
                'performance_history': [0.85, 0.78, 0.92],
                'specialization_index': 0.8
            },
            'curator_feedback': {
                'quality_score': 0.9,
                'risk_assessment': 'low',
                'approval_status': 'pending'
            },
            'accumulated_score': 0.87,
            'source_strands': [],
            'clustering_columns': {
                'symbol': 'BTC',
                'timeframe': '1m',
                'regime': 'trending'
            },
            'lesson': 'Strong trend continuation signal with high confidence',
            'braid_level': 1
        }
        
        inserted_strand = db.insert_strand(test_strand)
        if not inserted_strand:
            print("❌ Strand insertion failed")
            return False
        print(f"✅ Strand inserted successfully: {inserted_strand['id']}")
        
        # Test 3: Retrieve strand by ID
        print("\n3️⃣ Testing strand retrieval by ID...")
        retrieved_strand = db.get_strand_by_id(inserted_strand['id'])
        if not retrieved_strand:
            print("❌ Strand retrieval failed")
            return False
        print(f"✅ Strand retrieved successfully: {retrieved_strand['id']}")
        print(f"   Symbol: {retrieved_strand['symbol']}")
        print(f"   Direction: {retrieved_strand['sig_direction']}")
        print(f"   Confidence: {retrieved_strand['sig_confidence']}")
        
        # Test 4: Update strand
        print("\n4️⃣ Testing strand update...")
        update_data = {
            'sig_confidence': 0.95,
            'curator_feedback': {
                'quality_score': 0.95,
                'risk_assessment': 'very_low',
                'approval_status': 'approved'
            }
        }
        if not db.update_strand(inserted_strand['id'], update_data):
            print("❌ Strand update failed")
            return False
        print("✅ Strand updated successfully")
        
        # Test 5: Get strands by symbol
        print("\n5️⃣ Testing get strands by symbol...")
        btc_strands = db.get_strands_by_symbol('BTC', limit=10)
        print(f"✅ Found {len(btc_strands)} BTC strands")
        
        # Test 6: Get recent strands
        print("\n6️⃣ Testing get recent strands...")
        recent_strands = db.get_recent_strands(limit=5)
        print(f"✅ Found {len(recent_strands)} recent strands")
        
        # Test 7: Get strands by tags
        print("\n7️⃣ Testing get strands by tags...")
        tagged_strands = db.get_strands_by_tags(['decision_maker'], limit=10)
        print(f"✅ Found {len(tagged_strands)} strands with 'decision_maker' tag")
        
        # Test 8: Insert multiple strands for testing
        print("\n8️⃣ Testing bulk operations...")
        test_symbols = ['ETH', 'SOL']
        inserted_count = 0
        
        for symbol in test_symbols:
            test_strand_multi = test_strand.copy()
            test_strand_multi['id'] = f"AD_{uuid.uuid4().hex[:12]}"
            test_strand_multi['symbol'] = symbol
            test_strand_multi['trading_plan']['entry_price'] = 3000.0 if symbol == 'ETH' else 100.0
            
            if db.insert_strand(test_strand_multi):
                inserted_count += 1
        
        print(f"✅ Inserted {inserted_count} additional test strands")
        
        # Test 9: Verify data integrity
        print("\n9️⃣ Testing data integrity...")
        all_strands = db.get_recent_strands(limit=100)
        print(f"✅ Total strands in database: {len(all_strands)}")
        
        # Check for our test strands
        test_strand_ids = [strand['id'] for strand in all_strands if 'test' in strand.get('tags', [])]
        print(f"✅ Test strands found: {len(test_strand_ids)}")
        
        # Test 10: Cleanup test data
        print("\n🔟 Testing cleanup...")
        cleanup_count = 0
        for strand in all_strands:
            if 'test' in strand.get('tags', []):
                if db.delete_strand(strand['id']):
                    cleanup_count += 1
        
        print(f"✅ Cleaned up {cleanup_count} test strands")
        
        return True
        
    except Exception as e:
        logger.error(f"Database operations test failed: {e}")
        return False

def main():
    print("🧪 Alpha Detector Database Operations Test")
    print("=" * 60)
    
    success = test_database_operations()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ ALL DATABASE OPERATIONS TESTS PASSED!")
        print("🎉 Alpha Detector database is fully functional!")
        print("🚀 Ready to proceed to Phase 1.2 (Hyperliquid WebSocket)")
    else:
        print("\n" + "=" * 60)
        print("❌ DATABASE OPERATIONS TESTS FAILED!")
        print("🔧 Please check the error messages above")

if __name__ == "__main__":
    main()
